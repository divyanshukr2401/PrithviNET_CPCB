"""
OCEMS Alerts enrichment service.

Builds alert-first regulator workflows on top of existing live OCEMS telemetry by:
- loading the uploaded industry/contact workbook
- loading the standards/legal workbook
- matching live factory telemetry to workbook industries
- generating enriched alert payloads and believable draft notices

This service does not send mail. It only prepares realistic notice content.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import re

import pandas as pd
from loguru import logger

from app.core.config import settings
from app.services.ingestion.clickhouse_writer import ch_writer
from app.services.ingestion.postgres_writer import pg_writer
from app.services.ocems.auto_healer import auto_healer


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _normalize_org_name(value: str) -> str:
    base = _slugify(value)
    replacements = {
        "limited": "ltd",
        "private": "pvt",
        "corporation": "corp",
        "company": "co",
        "industries": "industry",
        "cements": "cement",
        "thermal power station": "tps",
        "thermal power project": "tps",
        "plant": "",
        "works": "",
        "unit": "",
        "captvie": "captive",
        "formerly known as": "",
        "formally name": "",
    }
    normalized = f" {base} "
    for old, new in replacements.items():
        normalized = normalized.replace(f" {old} ", f" {new} ")
    return re.sub(r"\s+", " ", normalized).strip()


def _normalize_place(value: str) -> str:
    place = _slugify(value)
    replacements = {
        "balodabazar bhatapara": "balodabazar bhatapara",
        "balodabazar-bhatapara": "balodabazar bhatapara",
        "raigarh": "raigarh",
        "raipur": "raipur",
        "korba": "korba",
        "durg": "durg",
        "bilaspur": "bilaspur",
    }
    for old, new in replacements.items():
        place = place.replace(old, new)
    return re.sub(r"\s+", " ", place).strip()


def _clean_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _clean_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _severity_from_exceedance(exceedance_pct: float) -> str:
    if exceedance_pct >= 200:
        return "critical"
    if exceedance_pct >= 100:
        return "high"
    if exceedance_pct >= 50:
        return "medium"
    return "low"


def _escape_clickhouse(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _notice_priority(severity: str, diagnosis: Optional[str]) -> str:
    if diagnosis == "fault_detected":
        return "sensor-review"
    if severity == "critical":
        return "immediate"
    if severity == "high":
        return "urgent"
    return "standard"


def _derive_initial_diagnosis(
    row: dict[str, Any],
) -> tuple[Optional[str], str, Optional[str]]:
    anomaly_type = str(row.get("anomaly_type") or "").lower()
    quality_flag = str(row.get("quality_flag") or "").lower()
    if quality_flag == "suspect" or anomaly_type in {
        "stuck",
        "flatline",
        "sensor_fault",
    }:
        return (
            "fault_detected",
            "Telemetry flags suggest a probable OCEMS/DAHS issue. Run the auto-healer to confirm whether this is a sensor fault or data acquisition anomaly.",
            "flag_review",
        )
    if anomaly_type and anomaly_type not in {"none", "normal"}:
        return (
            "real_event",
            "The event is currently treated as an operational exceedance. Run the auto-healer for a parameter-level diagnostic before issuing a final notice.",
            "escalate",
        )
    return (
        None,
        "Alert detected from exceedance telemetry. Run the auto-healer to classify the event before formal escalation.",
        None,
    )


@dataclass
class IndustryRecord:
    industry_name: str
    normalized_name: str
    category: Optional[str]
    cpcb_category: Optional[str]
    state: Optional[str]
    district: Optional[str]
    normalized_state: str
    normalized_district: str
    latitude: Optional[float]
    longitude: Optional[float]
    ocems_type: Optional[str]
    raw_materials: Optional[str]
    air_pollutants: Optional[str]
    water_pollutants: Optional[str]
    solid_waste: Optional[str]
    website: Optional[str]
    phone: Optional[str]
    email: Optional[str]


class OCEMSAlertsService:
    def __init__(self) -> None:
        self._industry_cache: Optional[list[IndustryRecord]] = None
        self._industry_mtime: Optional[float] = None
        self._standards_cache: Optional[dict[str, Any]] = None
        self._standards_mtime: Optional[float] = None
        self._match_overrides = {
            "OCEMS-CG-001": "Bhilai Steel Plant",
            "OCEMS-CG-003": "Godawari Power & Ispat Limited",
            "OCEMS-CG-005": "NTPC Ltd Korba",
            "OCEMS-CG-006": "NTPC Ltd",
            "OCEMS-CG-009": "ACC Limited Jamul Cement Works",
            "OCEMS-CG-011": "AMBUJA CEMENTS LTD UNIT BHATAPARA",
            "OCEMS-CG-012": "UltraTech Cement Limited (Unit - Hirmi Cement Works)",
            "OCEMS-CG-013": "Bharat Aluminium Company Limted",
        }

    async def _monitored_filter_options(
        self,
        industries: list[IndustryRecord],
    ) -> dict[str, list[str]]:
        factories = await pg_writer.get_factories()
        districts = sorted(
            {
                str(factory.get("district"))
                for factory in factories
                if factory.get("district")
            }
        )

        client = ch_writer._get_client()
        city_result = client.query("SELECT DISTINCT city FROM ocems_raw ORDER BY city")
        telemetry_cities = sorted(
            {str(row[0]) for row in city_result.result_rows if row and row[0]}
        )
        parameter_result = client.query(
            "SELECT DISTINCT parameter FROM ocems_raw ORDER BY parameter"
        )
        parameters = sorted(
            {str(row[0]) for row in parameter_result.result_rows if row and row[0]}
        )

        matched_categories = set()
        for factory in factories:
            matched = self._match_industry(factory, industries)
            if matched and matched.cpcb_category:
                matched_categories.add(matched.cpcb_category)

        combined_districts = sorted(set(districts) | set(telemetry_cities))
        return {
            "districts": combined_districts,
            "cpcb_categories": sorted(matched_categories),
            "parameters": parameters,
        }

    def _industry_path(self) -> Path:
        return Path(settings.OCEMS_INDUSTRY_WORKBOOK)

    def _standards_path(self) -> Path:
        return Path(settings.OCEMS_STANDARDS_WORKBOOK)

    def _load_industries(self) -> list[IndustryRecord]:
        path = self._industry_path()
        if not path.exists():
            logger.warning(f"Industry workbook not found: {path}")
            return []

        mtime = path.stat().st_mtime
        if self._industry_cache is not None and self._industry_mtime == mtime:
            return self._industry_cache

        df = pd.read_excel(path, sheet_name="Full Dataset (8170 Industries)")
        records: list[IndustryRecord] = []
        for row in df.to_dict(orient="records"):
            industry_name = _clean_value(row.get("Industry Name"))
            if not industry_name:
                continue
            state = _clean_value(row.get("State"))
            district = _clean_value(row.get("District"))
            records.append(
                IndustryRecord(
                    industry_name=industry_name,
                    normalized_name=_normalize_org_name(industry_name),
                    category=_clean_value(row.get("Category (CPCB)")),
                    cpcb_category=_clean_value(row.get("CPCB Category")),
                    state=state,
                    district=district,
                    normalized_state=_normalize_place(state or ""),
                    normalized_district=_normalize_place(district or ""),
                    latitude=_clean_float(
                        row.get("Latitude (\ufffdN)")
                        if "Latitude (\ufffdN)" in row
                        else row.get("Latitude (°N)")
                    ),
                    longitude=_clean_float(
                        row.get("Longitude (\ufffdE)")
                        if "Longitude (\ufffdE)" in row
                        else row.get("Longitude (°E)")
                    ),
                    ocems_type=_clean_value(row.get("OCEMS Type")),
                    raw_materials=_clean_value(row.get("Key Raw Materials / Inputs")),
                    air_pollutants=_clean_value(row.get("Air Pollutants Released")),
                    water_pollutants=_clean_value(row.get("Water Pollutants Released")),
                    solid_waste=_clean_value(row.get("Solid / Hazardous Waste")),
                    website=_clean_value(row.get("Official Website")),
                    phone=_clean_value(row.get("Contact Phone")),
                    email=_clean_value(row.get("Official Email")),
                )
            )

        self._industry_cache = records
        self._industry_mtime = mtime
        logger.info(f"Loaded {len(records)} industry rows for OCEMS Alerts")
        return records

    def _sheet_preview(self, df: pd.DataFrame, limit: int = 12) -> list[str]:
        lines: list[str] = []
        for row in df.head(limit).itertuples(index=False):
            text = " | ".join(
                str(cell).strip()
                for cell in row
                if str(cell).strip() and str(cell).strip() != "nan"
            )
            if text:
                lines.append(text)
        return lines

    def _load_standards(self) -> dict[str, Any]:
        path = self._standards_path()
        if not path.exists():
            logger.warning(f"Standards workbook not found: {path}")
            return {}

        mtime = path.stat().st_mtime
        if self._standards_cache is not None and self._standards_mtime == mtime:
            return self._standards_cache

        workbook = pd.ExcelFile(path)
        sheets: dict[str, list[str]] = {}
        for sheet in workbook.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet, header=None).fillna("")
            sheets[sheet] = self._sheet_preview(df)

        self._standards_cache = sheets
        self._standards_mtime = mtime
        logger.info("Loaded OCEMS standards/legal workbook previews")
        return sheets

    def _match_industry(
        self,
        factory: dict[str, Any],
        industries: list[IndustryRecord],
    ) -> Optional[IndustryRecord]:
        override = self._match_overrides.get(factory.get("factory_id", ""))
        target_name = _normalize_org_name(override or factory.get("factory_name", ""))
        district = _normalize_place(factory.get("district", ""))
        state = _normalize_place(factory.get("state", ""))

        scoped = [
            item
            for item in industries
            if (not state or item.normalized_state == state)
            and (
                not district
                or item.normalized_district == district
                or district in item.normalized_district
                or item.normalized_district in district
            )
        ]
        if not scoped:
            scoped = [
                item
                for item in industries
                if not state or item.normalized_state == state
            ]

        exact = [item for item in scoped if item.normalized_name == target_name]
        if exact:
            return exact[0]

        contains = [
            item
            for item in scoped
            if target_name
            and (
                target_name in item.normalized_name
                or item.normalized_name in target_name
            )
        ]
        if contains:
            contains.sort(
                key=lambda item: abs(len(item.normalized_name) - len(target_name))
            )
            return contains[0]

        return None

    def _standards_context(self, parameter: str, industry_type: str) -> dict[str, Any]:
        previews = self._load_standards()
        air_lines = previews.get("AIR \u2013 Industrial Stack Limits", [])
        penalty_lines = previews.get("Penalties & Enforcement", [])
        legal_lines = previews.get("Legal Framework & Acts", [])

        relevant_lines = [
            line
            for line in air_lines
            if parameter.lower() in line.lower()
            or industry_type.lower() in line.lower()
        ][:4]
        if not relevant_lines:
            relevant_lines = air_lines[:4]

        return {
            "standard_summary": relevant_lines,
            "penalty_summary": penalty_lines[:4],
            "legal_summary": legal_lines[:4],
            "authority": "CPCB / SPCB / MoEFCC",
        }

    def _draft_notice(
        self,
        alert: dict[str, Any],
        diagnosis: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        industry_name = alert.get("industry_name") or alert.get("factory_name")
        parameter = alert.get("parameter")
        severity = alert.get("severity")
        exceedance_pct = alert.get("exceedance_pct", 0)
        value = alert.get("value")
        limit = alert.get("limit")
        district = alert.get("district") or alert.get("city")
        recipient = alert.get("contact_email") or "compliance@industry.local"
        diagnosis_label = diagnosis.get("top_diagnosis") if diagnosis else None
        action_line = (
            "Our OCEMS diagnostic engine indicates a probable sensor or DAHS anomaly. Please verify calibration, connectivity, and instrument health immediately."
            if diagnosis_label == "fault_detected"
            else "The event appears operationally significant and requires immediate mitigation, root-cause review, and corrective action."
        )
        priority = _notice_priority(severity or "medium", diagnosis_label)
        subject = f"Notice of Non-Compliance - {industry_name} - {parameter} exceedance ({severity or 'alert'})"
        body = (
            f"To,\n"
            f"The Occupier / Environmental Compliance In-charge\n"
            f"{industry_name}\n"
            f"{district}, {alert.get('state') or 'India'}\n\n"
            f"Subject: Notice regarding OCEMS-recorded exceedance of {parameter} emission limit\n\n"
            f"This is to inform you that PRITHVINET flagged a {severity or 'significant'} non-compliance event for {parameter}. "
            f"The latest observed value was {value} against the applicable limit of {limit}, corresponding to an exceedance of {exceedance_pct:.1f}%.\n\n"
            f"Alert context:\n"
            f"- Factory ID: {alert.get('factory_id')}\n"
            f"- Industry type: {alert.get('industry_type')}\n"
            f"- Event time: {alert.get('timestamp')}\n"
            f"- Severity: {(severity or 'medium').upper()}\n"
            f"- Diagnostic note: {diagnosis.get('diagnosis_summary') if diagnosis else 'OCEMS auto-healer review pending'}\n\n"
            f"{action_line}\n\n"
            f"You are advised to submit an immediate explanation, corrective action taken report, and updated compliance status to the Board."
        )

        return {
            "to": recipient,
            "cc": ["regional.officer@cecb.local", "ocems.cell@cecb.local"],
            "subject": subject,
            "body": body,
            "priority": priority,
            "status": "draft_ready",
            "disclaimer": "Draft generated for regulator workflow preview only. Email delivery is not active.",
        }

    async def get_alert_summary(self, hours: int = 72) -> dict[str, Any]:
        factories = await pg_writer.get_factories()
        client = ch_writer._get_client()
        result = client.query(f"""
            SELECT countIf(value > emission_limit) AS active_alerts,
                   countIf(value > emission_limit AND exceedance_pct >= 200) AS critical_alerts,
                   count(DISTINCT factory_id) AS monitored_units,
                   round(avg(100.0 * if(value <= emission_limit, 1, 0)), 1) AS avg_compliance_signal
            FROM ocems_raw
            WHERE timestamp >= (
                SELECT max(timestamp) - INTERVAL {hours} HOUR
                FROM ocems_raw
            )
        """)
        row = result.result_rows[0] if result.result_rows else (0, 0, 0, 0)
        return {
            "total_units": len(factories),
            "active_alerts": int(row[0]),
            "critical_alerts": int(row[1]),
            "monitored_units": int(row[2]),
            "avg_compliance_signal": float(row[3] or 0),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def get_alerts(
        self,
        district: Optional[str] = None,
        cpcb_category: Optional[str] = None,
        parameter: Optional[str] = None,
        severity: Optional[str] = None,
        hours: int = 72,
    ) -> dict[str, Any]:
        industries = self._load_industries()
        factories = await pg_writer.get_factories(city=district)
        factory_map = {factory["factory_id"]: factory for factory in factories}

        district_filter = (
            f"AND lower(city) = '{_escape_clickhouse(_slugify(district))}'"
            if district
            else ""
        )
        parameter_filter = (
            f"AND parameter = '{_escape_clickhouse(parameter)}'" if parameter else ""
        )
        client = ch_writer._get_client()
        result = client.query(f"""
            SELECT factory_id, parameter, city, industry_type,
                   value, emission_limit, exceedance_pct,
                   timestamp, anomaly_type, quality_flag,
                   dahs_status, sensor_health
            FROM ocems_raw
            WHERE value > emission_limit
              AND timestamp >= (
                  SELECT max(timestamp) - INTERVAL {hours} HOUR
                  FROM ocems_raw
              )
              {district_filter}
              {parameter_filter}
            ORDER BY exceedance_pct DESC, timestamp DESC
            LIMIT 150
        """)
        columns = result.column_names
        rows = [dict(zip(columns, row)) for row in result.result_rows]

        alerts: list[dict[str, Any]] = []
        for row in rows:
            factory = factory_map.get(row.get("factory_id"))
            if not factory:
                continue
            matched = self._match_industry(factory, industries)
            severity_value = _severity_from_exceedance(
                float(row.get("exceedance_pct") or 0)
            )
            if severity and severity_value != severity:
                continue
            if cpcb_category and (
                not matched
                or (matched.cpcb_category or "").lower() != cpcb_category.lower()
            ):
                continue
            top_diagnosis, diagnosis_summary, recommended_action = (
                _derive_initial_diagnosis(row)
            )

            alert = {
                "alert_id": f"{factory['factory_id']}::{row.get('parameter')}::{row.get('timestamp')}",
                "factory_id": factory["factory_id"],
                "factory_name": factory.get("factory_name"),
                "industry_name": matched.industry_name
                if matched
                else factory.get("factory_name"),
                "industry_type": row.get("industry_type")
                or factory.get("industry_type"),
                "cpcb_category": matched.cpcb_category if matched else None,
                "district": matched.district if matched else factory.get("district"),
                "state": matched.state if matched else factory.get("state"),
                "parameter": row.get("parameter"),
                "value": round(float(row.get("value") or 0), 2),
                "limit": round(float(row.get("emission_limit") or 0), 2),
                "exceedance_pct": round(float(row.get("exceedance_pct") or 0), 1),
                "severity": severity_value,
                "timestamp": str(row.get("timestamp") or ""),
                "anomaly_type": row.get("anomaly_type") or "",
                "quality_flag": row.get("quality_flag") or "",
                "dahs_status": row.get("dahs_status") or "online",
                "sensor_health": float(row.get("sensor_health") or 0),
                "contact_email": matched.email if matched else None,
                "contact_phone": matched.phone if matched else None,
                "website": matched.website if matched else None,
                "ocems_type": matched.ocems_type if matched else None,
                "air_pollutants": matched.air_pollutants if matched else None,
                "water_pollutants": matched.water_pollutants if matched else None,
                "solid_waste": matched.solid_waste if matched else None,
                "raw_materials": matched.raw_materials if matched else None,
                "diagnosis_summary": diagnosis_summary,
                "top_diagnosis": top_diagnosis,
                "recommended_action": recommended_action,
                "overall_health": float(row.get("sensor_health") or 0),
                "dahs_uptime_pct": 100.0
                if (row.get("dahs_status") or "online") == "online"
                else 0.0,
                "match_status": "matched" if matched else "fallback",
                "standards_context": self._standards_context(
                    str(row.get("parameter") or ""),
                    str(row.get("industry_type") or factory.get("industry_type") or ""),
                ),
            }
            alert["notice_draft"] = self._draft_notice(alert, None)
            alerts.append(alert)

        filters = {
            "district": district,
            "cpcb_category": cpcb_category,
            "parameter": parameter,
            "severity": severity,
            "hours": hours,
        }
        monitored_options = await self._monitored_filter_options(industries)
        return {
            "alerts": alerts,
            "total": len(alerts),
            "filters": filters,
            "filter_options": {
                "districts": monitored_options["districts"],
                "cpcb_categories": monitored_options["cpcb_categories"],
                "parameters": monitored_options["parameters"],
                "severities": ["critical", "high", "medium", "low"],
            },
        }

    async def get_alert_detail(self, alert_id: str) -> dict[str, Any]:
        parts = alert_id.split("::", 2)
        if len(parts) < 3:
            raise ValueError("Invalid alert_id")
        factory_id, parameter, timestamp = parts[0], parts[1], parts[2]
        alerts = await self.get_alerts(parameter=parameter, hours=96)
        for alert in alerts["alerts"]:
            if (
                alert["factory_id"] == factory_id
                and alert["parameter"] == parameter
                and alert["timestamp"] == timestamp
            ):
                diagnosis = await auto_healer.diagnose(
                    factory_id=factory_id,
                    parameter=parameter,
                    hours=6,
                )
                diagnosis_item = diagnosis.diagnoses[0] if diagnosis.diagnoses else None
                if diagnosis_item:
                    alert["diagnosis_summary"] = diagnosis_item.explanation
                    alert["top_diagnosis"] = diagnosis_item.diagnosis
                    alert["recommended_action"] = diagnosis_item.recommended_action
                alert["overall_health"] = round(float(diagnosis.overall_health), 1)
                alert["dahs_uptime_pct"] = round(float(diagnosis.dahs_uptime_pct), 1)
                alert["notice_draft"] = self._draft_notice(
                    alert,
                    {
                        "top_diagnosis": alert.get("top_diagnosis"),
                        "diagnosis_summary": alert.get("diagnosis_summary"),
                    },
                )
                return alert
        raise ValueError("Alert not found")

    async def build_notice_draft(self, alert_id: str) -> dict[str, Any]:
        alert = await self.get_alert_detail(alert_id)
        return alert["notice_draft"]


ocems_alerts = OCEMSAlertsService()
