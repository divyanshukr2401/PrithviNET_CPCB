"""
PrithviNET — PDF Report Generator Service.

Generates government-format environmental monitoring reports for cities or states.
Queries ClickHouse (AQI, Noise) and Redis (Water Quality) for live data,
then builds a professional PDF using fpdf2.

Report Sections:
  1. Header — CPCB/MoEFCC branding, title, date, scope
  2. Air Quality — AQI summary, station table, category distribution, pollutant breakdown
  3. Water Quality — WQI distribution, worst stations, parameter exceedances
  4. Noise Monitoring — Zone compliance, exceedance summary, loudest stations
  5. Footer — Page numbers, disclaimer, generation timestamp
"""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Optional, Sequence

from fpdf import FPDF
from loguru import logger

from app.core.redis import get_redis
from app.services.ingestion.clickhouse_writer import ch_writer
from app.services.ingestion.postgres_writer import pg_writer


# ════════════════════════════════════════════════════════════════
# Constants & Standards
# ════════════════════════════════════════════════════════════════

AQI_CATEGORIES = [
    (0, 50, "Good", (0, 153, 102)),  # #009966
    (51, 100, "Satisfactory", (88, 255, 9)),  # #58FF09
    (101, 200, "Moderate", (255, 222, 51)),  # #FFDE33
    (201, 300, "Poor", (255, 153, 51)),  # #FF9933
    (301, 400, "Very Poor", (255, 0, 0)),  # #FF0000
    (401, 500, "Severe", (128, 0, 0)),  # #800000
]

NOISE_STANDARDS = {
    "industrial": {"day": 75, "night": 70},
    "commercial": {"day": 65, "night": 55},
    "residential": {"day": 55, "night": 45},
    "silence": {"day": 50, "night": 40},
}

WQI_CATEGORIES = [
    (0.00, 0.15, "Excellent", (0, 153, 102)),
    (0.15, 0.30, "Good", (88, 200, 50)),
    (0.30, 0.50, "Fair", (255, 222, 51)),
    (0.50, 0.70, "Poor", (255, 153, 51)),
    (0.70, 1.01, "Very Poor", (255, 0, 0)),
]

POLLUTANT_NAAQS = {
    "PM2.5": {"unit": "ug/m3", "24hr": 60, "annual": 40},
    "PM10": {"unit": "ug/m3", "24hr": 100, "annual": 60},
    "NO2": {"unit": "ug/m3", "24hr": 80, "annual": 40},
    "SO2": {"unit": "ug/m3", "24hr": 80, "annual": 50},
    "CO": {"unit": "mg/m3", "8hr": 2, "1hr": 4},
    "O3": {"unit": "ug/m3", "8hr": 100, "1hr": 180},
    "NH3": {"unit": "ug/m3", "24hr": 400, "annual": 200},
    "Pb": {"unit": "ug/m3", "24hr": 1, "annual": 0.5},
}


def _get_aqi_category(aqi: float) -> str:
    for lo, hi, cat, _ in AQI_CATEGORIES:
        if lo <= aqi <= hi:
            return cat
    return "Severe" if aqi > 400 else "Unknown"


def _get_aqi_color(aqi: float) -> tuple:
    for lo, hi, _, color in AQI_CATEGORIES:
        if lo <= aqi <= hi:
            return color
    return (128, 0, 0)


def _get_wqi_category(wqi: float) -> str:
    for lo, hi, cat, _ in WQI_CATEGORIES:
        if lo <= wqi < hi:
            return cat
    return "Very Poor"


def _normalize_text(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _escape_clickhouse_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _build_city_filter(
    city: Optional[str] = None,
    city_names: Optional[Sequence[str]] = None,
) -> str:
    if city:
        normalized_city = _normalize_text(city)
        if normalized_city:
            return f"AND lower(city) = '{_escape_clickhouse_string(normalized_city)}'"

    normalized_cities = sorted(
        {
            _normalize_text(city_name)
            for city_name in (city_names or [])
            if _normalize_text(city_name)
        }
    )
    if normalized_cities:
        city_values = ", ".join(
            f"'{_escape_clickhouse_string(city_name)}'"
            for city_name in normalized_cities
        )
        return f"AND lower(city) IN ({city_values})"

    return ""


# ════════════════════════════════════════════════════════════════
# Data Collection — AQI (ClickHouse)
# ════════════════════════════════════════════════════════════════


async def get_aqi_data(
    city: Optional[str] = None,
    state: Optional[str] = None,
) -> dict:
    """Fetch AQI data from ClickHouse for the report."""
    try:
        client = ch_writer._get_client()
        station_scope = await pg_writer.get_air_stations(city=city, state=state)
        if state and not station_scope:
            return {"available": False, "error": f"No AQI stations found in {state}"}

        city_names = [str(s["city"]) for s in station_scope if s.get("city")]
        if city:
            city_filter = _build_city_filter(city=city)
        elif state:
            city_filter = _build_city_filter(city_names=city_names)
        else:
            city_filter = ""
        station_name_map = {
            s["station_id"]: s.get("station_name") or s["station_id"]
            for s in station_scope
            if s.get("station_id")
        }

        # Overall stats
        overall = client.query(f"""
            SELECT count(DISTINCT station_id) AS total_stations,
                   round(avg(latest_aqi)) AS avg_aqi,
                   max(latest_aqi) AS max_aqi,
                   min(latest_aqi) AS min_aqi,
                   countIf(latest_aqi > 300) AS severe_count,
                   countIf(latest_aqi > 200 AND latest_aqi <= 300) AS poor_count,
                   countIf(latest_aqi > 100 AND latest_aqi <= 200) AS moderate_count,
                   countIf(latest_aqi > 50 AND latest_aqi <= 100) AS satisfactory_count,
                   countIf(latest_aqi <= 50) AS good_count
            FROM (
                SELECT station_id,
                       argMax(value, timestamp) AS latest_aqi
                FROM air_quality_raw
                WHERE parameter = 'AQI'
                  AND timestamp >= now() - INTERVAL 2 HOUR
                  {city_filter}
                GROUP BY station_id
            )
        """)
        ov = (
            dict(zip(overall.column_names, overall.result_rows[0]))
            if overall.result_rows
            else {}
        )

        # Station-level data (worst first)
        stations = client.query(f"""
            SELECT station_id, city,
                   argMax(value, timestamp) AS latest_aqi,
                   max(timestamp) AS ts
            FROM air_quality_raw
            WHERE parameter = 'AQI'
              AND timestamp >= now() - INTERVAL 2 HOUR
              {city_filter}
            GROUP BY station_id, city
            ORDER BY latest_aqi DESC
            LIMIT 50
        """)
        station_rows = [
            dict(zip(stations.column_names, r)) for r in stations.result_rows
        ]
        for row in station_rows:
            station_id = row.get("station_id")
            row["station_name"] = station_name_map.get(station_id, station_id)

        # Per-pollutant averages
        pollutants = client.query(f"""
            SELECT parameter,
                   round(avg(latest_val), 1) AS avg_val,
                   round(max(latest_val), 1) AS max_val,
                   count() AS station_count
            FROM (
                SELECT station_id, parameter,
                       argMax(value, timestamp) AS latest_val
                FROM air_quality_raw
                WHERE parameter != 'AQI'
                  AND timestamp >= now() - INTERVAL 2 HOUR
                  {city_filter}
                GROUP BY station_id, parameter
            )
            GROUP BY parameter
            ORDER BY parameter
        """)
        pollutant_rows = [
            dict(zip(pollutants.column_names, r)) for r in pollutants.result_rows
        ]

        # City averages (only for state-level / national reports)
        city_rows = []
        if not city:
            city_avg = client.query(f"""
                SELECT city,
                       round(avg(latest_aqi)) AS avg_aqi,
                       count() AS stations
                FROM (
                    SELECT station_id, city,
                           argMax(value, timestamp) AS latest_aqi
                    FROM air_quality_raw
                    WHERE parameter = 'AQI'
                      AND timestamp >= now() - INTERVAL 2 HOUR
                      {city_filter}
                    GROUP BY station_id, city
                )
                GROUP BY city
                ORDER BY avg_aqi DESC
                LIMIT 30
            """)
            city_rows = [
                dict(zip(city_avg.column_names, r)) for r in city_avg.result_rows
            ]

        return {
            "overall": ov,
            "stations": station_rows,
            "pollutants": pollutant_rows,
            "cities": city_rows,
            "available": True,
        }

    except Exception as e:
        logger.warning(f"Report AQI data fetch failed: {e}")
        return {"available": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════
# Data Collection — Water Quality (Redis)
# ════════════════════════════════════════════════════════════════


async def get_water_data(
    state: Optional[str] = None,
    district: Optional[str] = None,
) -> dict:
    """Fetch water quality data from Redis cache."""
    try:
        r = await get_redis()
        raw = await r.get("water_quality_heatmap:v2:all_states:limit=5000")
        if not raw:
            keys = await r.keys("water_quality_heatmap:*")
            if keys:
                raw = await r.get(keys[0])

        if not raw:
            return {"available": False, "error": "Water data not cached"}

        points = json.loads(raw)
        if isinstance(points, dict) and "points" in points:
            points = points["points"]

        if state:
            state_normalized = _normalize_text(state)
            points = [
                p for p in points if _normalize_text(p.get("state")) == state_normalized
            ]
        if district:
            district_normalized = _normalize_text(district)
            points = [
                p
                for p in points
                if _normalize_text(p.get("district")) == district_normalized
            ]

        total = len(points)
        if total == 0:
            return {"available": False, "error": "No water data for filter"}

        # Categorize
        categories = {"Excellent": 0, "Good": 0, "Fair": 0, "Poor": 0, "Very Poor": 0}
        for p in points:
            wqi = p.get("wqi", 0.5)
            cat = _get_wqi_category(wqi)
            categories[cat] = categories.get(cat, 0) + 1

        # Worst 20 stations
        sorted_pts = sorted(points, key=lambda p: p.get("wqi", 0), reverse=True)
        worst = sorted_pts[:20]

        # State-wise summary
        state_summary = {}
        for p in points:
            s = p.get("state", "Unknown")
            if s not in state_summary:
                state_summary[s] = {"count": 0, "total_wqi": 0}
            state_summary[s]["count"] += 1
            state_summary[s]["total_wqi"] += p.get("wqi", 0)

        for s in state_summary:
            state_summary[s]["avg_wqi"] = round(
                state_summary[s]["total_wqi"] / state_summary[s]["count"], 3
            )

        # Sort states by worst avg WQI
        sorted_states = sorted(
            state_summary.items(), key=lambda x: x[1]["avg_wqi"], reverse=True
        )

        # Parameter violations (check against BIS limits)
        param_violations = {}
        bis_limits = {
            "BOD (mg/L)": 3.0,
            "Total Coliform": 5000.0,
            "Fecal Coliform": 2500.0,
            "Conductivity (uS/cm)": 2250.0,
            "Nitrate-N (mg/L)": 45.0,
            "TDS (mg/L)": 2000.0,
            "Turbidity (NTU)": 25.0,
        }
        for p in points:
            params = p.get("parameters", {})
            for pname, limit in bis_limits.items():
                val = params.get(pname)
                if val is not None and isinstance(val, (int, float)) and val > limit:
                    if pname not in param_violations:
                        param_violations[pname] = 0
                    param_violations[pname] += 1

        return {
            "available": True,
            "total": total,
            "categories": categories,
            "worst_stations": worst,
            "state_summary": sorted_states[:15],
            "param_violations": param_violations,
        }

    except Exception as e:
        logger.warning(f"Report water data fetch failed: {e}")
        return {"available": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════
# Data Collection — Noise (ClickHouse)
# ════════════════════════════════════════════════════════════════


async def get_noise_data(
    city: Optional[str] = None,
    state: Optional[str] = None,
) -> dict:
    """Fetch noise monitoring data from ClickHouse."""
    try:
        client = ch_writer._get_client()
        noise_station_scope = await pg_writer.get_noise_stations(city=city, state=state)
        if state and not noise_station_scope:
            return {"available": False, "error": f"No noise stations found in {state}"}

        city_names = [str(s["city"]) for s in noise_station_scope if s.get("city")]
        if city:
            city_filter = _build_city_filter(city=city)
        elif state:
            city_filter = _build_city_filter(city_names=city_names)
        else:
            city_filter = ""

        result = client.query(f"""
            SELECT station_id, city, zone,
                   round(avg(value), 1) AS avg_leq,
                   round(max(value), 1) AS max_leq,
                   round(min(value), 1) AS min_leq,
                   countIf(is_exceedance = 1) AS violations,
                   count() AS readings
            FROM noise_raw
            WHERE metric = 'Leq'
              AND timestamp >= now() - INTERVAL 6 HOUR
              {city_filter}
            GROUP BY station_id, city, zone
            ORDER BY avg_leq DESC
        """)
        rows = [dict(zip(result.column_names, r)) for r in result.result_rows]

        if not rows:
            return {"available": False, "error": "No noise data"}

        # Zone-wise compliance
        hour_now = datetime.now().hour
        is_night = hour_now < 6 or hour_now >= 22
        period = "Night" if is_night else "Day"

        zone_stats = {}
        for row in rows:
            zone = row["zone"].lower() if row.get("zone") else "unknown"
            if zone not in NOISE_STANDARDS:
                continue
            limit = NOISE_STANDARDS[zone]["night" if is_night else "day"]
            is_exceeding = row["avg_leq"] > limit

            if zone not in zone_stats:
                zone_stats[zone] = {
                    "total": 0,
                    "exceeding": 0,
                    "compliant": 0,
                    "limit": limit,
                    "avg_leq_sum": 0,
                }
            zone_stats[zone]["total"] += 1
            zone_stats[zone]["avg_leq_sum"] += row["avg_leq"]
            if is_exceeding:
                zone_stats[zone]["exceeding"] += 1
            else:
                zone_stats[zone]["compliant"] += 1

        for z in zone_stats:
            zone_stats[z]["avg_leq"] = round(
                zone_stats[z]["avg_leq_sum"] / max(1, zone_stats[z]["total"]), 1
            )

        total_violations = sum(r["violations"] for r in rows)
        total_readings = sum(r["readings"] for r in rows)

        return {
            "available": True,
            "stations": rows[:30],
            "zone_stats": zone_stats,
            "period": period,
            "total_stations": len(rows),
            "total_violations": total_violations,
            "total_readings": total_readings,
            "violation_pct": round(100 * total_violations / max(1, total_readings), 1),
        }

    except Exception as e:
        logger.warning(f"Report noise data fetch failed: {e}")
        return {"available": False, "error": str(e)}


# ════════════════════════════════════════════════════════════════
# PDF Builder
# ════════════════════════════════════════════════════════════════


class EnvironmentalReport(FPDF):
    """Government-format environmental monitoring report PDF."""

    def __init__(self, report_title: str, scope: str, scope_value: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report_title = report_title
        self.scope = scope  # "City" or "State" or "National"
        self.scope_value = scope_value  # e.g. "Delhi" or "Chhattisgarh"
        self.generated_at = datetime.now()
        self.set_auto_page_break(auto=True, margin=25)

    # ── Header ─────────────────────────────────────────────
    def header(self):
        if self.page_no() == 1:
            self._draw_title_header()
        else:
            self._draw_continuation_header()

    def _draw_title_header(self):
        # Top bar — dark green
        self.set_fill_color(0, 80, 50)
        self.rect(0, 0, 210, 8, "F")

        # Government body name
        self.set_y(12)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(0, 80, 50)
        self.cell(
            0,
            6,
            "CENTRAL POLLUTION CONTROL BOARD",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        self.set_font("Helvetica", "", 8)
        self.set_text_color(80, 80, 80)
        self.cell(
            0,
            4,
            "Ministry of Environment, Forest and Climate Change | Government of India",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        # Thin green line
        self.set_draw_color(0, 153, 102)
        self.set_line_width(0.8)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

        # Report title
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(20, 20, 20)
        self.cell(0, 8, self.report_title, align="C", new_x="LMARGIN", new_y="NEXT")

        # Scope & date
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 60, 60)
        scope_line = f"{self.scope}: {self.scope_value}"
        self.cell(0, 6, scope_line, align="C", new_x="LMARGIN", new_y="NEXT")

        date_line = f"Report Generated: {self.generated_at.strftime('%B %d, %Y at %I:%M %p IST')}"
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, date_line, align="C", new_x="LMARGIN", new_y="NEXT")

        # PrithviNET attribution
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(0, 153, 102)
        self.cell(
            0,
            5,
            "Generated by PrithviNET Smart Environmental Monitoring Platform",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        # Bottom border of header
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.3)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def _draw_continuation_header(self):
        self.set_font("Helvetica", "", 7)
        self.set_text_color(130, 130, 130)
        self.set_y(5)
        self.cell(
            0,
            4,
            f"PrithviNET Report | {self.scope}: {self.scope_value} | {self.generated_at.strftime('%d %b %Y')}",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.2)
        self.line(10, 11, 200, 11)
        self.ln(6)

    # ── Footer ─────────────────────────────────────────────
    def footer(self):
        self.set_y(-20)
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())

        self.set_font("Helvetica", "", 7)
        self.set_text_color(130, 130, 130)
        self.cell(0, 5, "", new_x="LMARGIN", new_y="NEXT")

        # Left: disclaimer
        self.cell(
            95,
            4,
            "Data sourced from CPCB, NANMN, data.gov.in | For official use only",
            align="L",
        )
        # Right: page number
        self.cell(
            95,
            4,
            f"Page {self.page_no()}/{{nb}}",
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.cell(
            0,
            4,
            f"Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S IST')} | PrithviNET v1.0",
            align="C",
        )

    # ── Section Headers ────────────────────────────────────
    def section_title(self, title: str, color: tuple = (0, 80, 50)):
        self.ln(4)
        # Check if enough space for a section header + some content
        if self.get_y() > 250:
            self.add_page()
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*color)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*color)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def sub_section(self, title: str):
        if self.get_y() > 260:
            self.add_page()
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(40, 40, 40)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def stat_line(self, label: str, value: str):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(60, 60, 60)
        self.cell(55, 5, f"  {label}:", align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 30, 30)
        self.cell(0, 5, value, new_x="LMARGIN", new_y="NEXT")

    # ── Table Helpers ──────────────────────────────────────
    def _table_header(self, headers: Sequence[str], widths: Sequence[float | int]):
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(240, 245, 240)
        self.set_text_color(30, 30, 30)
        self.set_draw_color(200, 200, 200)
        for i, (h, w) in enumerate(zip(headers, widths)):
            self.cell(w, 7, h, border=1, align="C", fill=True)
        self.ln()

    def _table_row(
        self,
        values: Sequence[str],
        widths: Sequence[float | int],
        fill: bool = False,
        fill_color: tuple = (250, 250, 250),
        bold_col: int = -1,
    ):
        self.set_font("Helvetica", "", 8)
        self.set_text_color(40, 40, 40)
        if fill:
            self.set_fill_color(*fill_color)
        self.set_draw_color(220, 220, 220)
        for i, (v, w) in enumerate(zip(values, widths)):
            if i == bold_col:
                self.set_font("Helvetica", "B", 8)
            align = "C" if i > 0 else "L"
            self.cell(w, 6, v, border=1, align=align, fill=fill)
            if i == bold_col:
                self.set_font("Helvetica", "", 8)
        self.ln()

    # ── AQI Section ────────────────────────────────────────
    def add_aqi_section(self, data: dict):
        self.section_title("1. AIR QUALITY INDEX (AQI) MONITORING", (0, 100, 60))

        if not data.get("available"):
            self.body_text("Air quality data is currently unavailable.")
            return

        ov = data.get("overall", {})
        stations = data.get("stations", [])
        pollutants = data.get("pollutants", [])
        cities = data.get("cities", [])

        # Summary stats
        self.sub_section("1.1 Overall Summary")
        self.stat_line("Active Stations", str(ov.get("total_stations", "N/A")))
        avg_aqi = ov.get("avg_aqi", 0)
        self.stat_line("Average AQI", f"{int(avg_aqi)} ({_get_aqi_category(avg_aqi)})")
        self.stat_line(
            "AQI Range", f"{int(ov.get('min_aqi', 0))} - {int(ov.get('max_aqi', 0))}"
        )
        self.stat_line("Severe Stations (AQI > 300)", str(ov.get("severe_count", 0)))
        self.stat_line("Poor Stations (AQI 201-300)", str(ov.get("poor_count", 0)))
        self.ln(3)

        # AQI Category Distribution
        self.sub_section("1.2 AQI Category Distribution")
        cat_headers = ["Category", "AQI Range", "Stations", "Percentage"]
        cat_widths = [40, 35, 30, 35]
        self._table_header(cat_headers, cat_widths)

        total_st = int(ov.get("total_stations", 1)) or 1
        cat_data = [
            ("Good", "0-50", ov.get("good_count", 0)),
            ("Satisfactory", "51-100", ov.get("satisfactory_count", 0)),
            ("Moderate", "101-200", ov.get("moderate_count", 0)),
            ("Poor", "201-300", ov.get("poor_count", 0)),
            ("Very Poor", "301-400", ov.get("severe_count", 0)),  # severe_count is >300
        ]
        for i, (cat, rng, cnt) in enumerate(cat_data):
            cnt_int = int(cnt) if cnt else 0
            pct = round(100 * cnt_int / total_st, 1)
            color_rgb = (
                AQI_CATEGORIES[i][3] if i < len(AQI_CATEGORIES) else (200, 200, 200)
            )
            # Use lighter version for fill
            light_color = tuple(min(255, c + 160) for c in color_rgb)
            self._table_row(
                [cat, rng, str(cnt_int), f"{pct}%"],
                cat_widths,
                fill=True,
                fill_color=light_color,
            )
        self.ln(3)

        # Worst stations table
        if stations:
            self.sub_section("1.3 Station-wise AQI (Worst First)")
            st_headers = ["Station Name", "City", "AQI", "Category"]
            st_widths = [70, 30, 20, 40]
            self._table_header(st_headers, st_widths)

            for i, st in enumerate(stations[:20]):
                aqi_val = int(st.get("latest_aqi", 0))
                cat = _get_aqi_category(aqi_val)
                color = _get_aqi_color(aqi_val)
                light_color = tuple(min(255, c + 160) for c in color)
                station_name = str(st.get("station_name", st.get("station_id", "")))[
                    :38
                ]
                city = str(st.get("city", ""))[:20]
                self._table_row(
                    [station_name, city, str(aqi_val), cat],
                    st_widths,
                    fill=True,
                    fill_color=light_color,
                    bold_col=2,
                )
            self.ln(3)

        # Pollutant breakdown
        if pollutants:
            self.sub_section("1.4 Pollutant-wise Average Concentrations")
            pol_headers = [
                "Pollutant",
                "Avg Value",
                "Max Value",
                "NAAQS 24hr Limit",
                "Stations",
            ]
            pol_widths = [30, 30, 30, 35, 25]
            self._table_header(pol_headers, pol_widths)

            for p in pollutants:
                param = str(p.get("parameter", ""))
                naaqs = POLLUTANT_NAAQS.get(param, {})
                limit_str = str(naaqs.get("24hr", naaqs.get("8hr", "-")))
                avg_v = str(p.get("avg_val", ""))
                max_v = str(p.get("max_val", ""))
                cnt = str(p.get("station_count", ""))
                is_exceeding = False
                try:
                    limit_num = float(limit_str) if limit_str != "-" else None
                    if limit_num and float(avg_v) > limit_num:
                        is_exceeding = True
                except (ValueError, TypeError):
                    pass
                fill_color = (255, 220, 220) if is_exceeding else (245, 250, 245)
                self._table_row(
                    [param, avg_v, max_v, limit_str, cnt],
                    pol_widths,
                    fill=True,
                    fill_color=fill_color,
                )
            self.ln(3)

        # City averages (for state/national reports)
        if cities:
            self.sub_section("1.5 City-wise Average AQI")
            city_headers = ["City", "Avg AQI", "Category", "Stations"]
            city_widths = [50, 30, 40, 30]
            self._table_header(city_headers, city_widths)

            for c in cities[:20]:
                avg = int(c.get("avg_aqi", 0))
                cat = _get_aqi_category(avg)
                color = _get_aqi_color(avg)
                light_color = tuple(min(255, c_val + 160) for c_val in color)
                self._table_row(
                    [str(c.get("city", "")), str(avg), cat, str(c.get("stations", ""))],
                    city_widths,
                    fill=True,
                    fill_color=light_color,
                )
            self.ln(2)

    # ── Water Quality Section ──────────────────────────────
    def add_water_section(self, data: dict):
        self.section_title("2. SURFACE WATER QUALITY MONITORING", (5, 113, 176))

        if not data.get("available"):
            self.body_text(
                "Water quality data is currently unavailable. Ensure the Water Quality tab has been loaded at least once to populate the cache."
            )
            return

        total = data.get("total", 0)
        categories = data.get("categories", {})
        worst = data.get("worst_stations", [])
        state_summary = data.get("state_summary", [])
        param_violations = data.get("param_violations", {})

        # Summary
        self.sub_section("2.1 Overall Summary")
        self.stat_line("Total Monitoring Stations", str(total))
        self.stat_line("Data Source", "CPCB Surface Water Quality via data.gov.in")
        self.stat_line("WQI Scale", "0 (Excellent) to 1 (Very Poor)")
        self.ln(3)

        # WQI Distribution
        self.sub_section("2.2 Water Quality Index Distribution")
        wqi_headers = ["Category", "WQI Range", "Stations", "Percentage"]
        wqi_widths = [40, 35, 30, 35]
        self._table_header(wqi_headers, wqi_widths)

        for cat_name, (lo, hi, _, color) in zip(
            ["Excellent", "Good", "Fair", "Poor", "Very Poor"], WQI_CATEGORIES
        ):
            cnt = categories.get(cat_name, 0)
            pct = round(100 * cnt / max(1, total), 1)
            light = tuple(min(255, c + 160) for c in color)
            self._table_row(
                [cat_name, f"{lo:.2f} - {hi:.2f}", str(cnt), f"{pct}%"],
                wqi_widths,
                fill=True,
                fill_color=light,
            )
        self.ln(3)

        # Worst stations
        if worst:
            self.sub_section("2.3 Stations Requiring Attention (Worst Water Quality)")
            w_headers = ["Station Name", "State", "District", "WQI", "Category"]
            w_widths = [50, 30, 30, 20, 30]
            self._table_header(w_headers, w_widths)

            for p in worst[:15]:
                wqi = p.get("wqi", 0)
                cat = _get_wqi_category(wqi)
                name = str(p.get("station_name", ""))[:28]
                state = str(p.get("state", ""))[:16]
                district = str(p.get("district", ""))[:16]
                self._table_row(
                    [name, state, district, f"{wqi:.3f}", cat],
                    w_widths,
                    fill=True,
                    fill_color=(255, 230, 230) if wqi >= 0.5 else (255, 245, 230),
                )
            self.ln(3)

        # Parameter violations
        if param_violations:
            self.sub_section("2.4 BIS Standard Violations by Parameter")
            pv_headers = ["Parameter", "Stations Exceeding BIS", "% of Total"]
            pv_widths = [60, 45, 40]
            self._table_header(pv_headers, pv_widths)

            for param, cnt in sorted(param_violations.items(), key=lambda x: -x[1]):
                pct = round(100 * cnt / max(1, total), 1)
                self._table_row(
                    [param, str(cnt), f"{pct}%"],
                    pv_widths,
                    fill=True,
                    fill_color=(255, 220, 220) if pct > 20 else (250, 250, 245),
                )
            self.ln(2)

    # ── Noise Section ──────────────────────────────────────
    def add_noise_section(self, data: dict):
        self.section_title("3. ENVIRONMENTAL NOISE MONITORING", (139, 92, 246))

        if not data.get("available"):
            self.body_text("Noise monitoring data is currently unavailable.")
            return

        stations = data.get("stations", [])
        zone_stats = data.get("zone_stats", {})
        period = data.get("period", "Day")

        # Summary
        self.sub_section("3.1 Overall Summary")
        self.stat_line("Active Stations", str(data.get("total_stations", 0)))
        self.stat_line("Monitoring Period", f"Last 6 Hours ({period}time)")
        self.stat_line("Total Readings", str(data.get("total_readings", 0)))
        self.stat_line(
            "Exceedance Readings",
            f"{data.get('total_violations', 0)} ({data.get('violation_pct', 0)}%)",
        )
        self.stat_line("Reference Standard", "CPCB Noise Standards 2000")
        self.ln(3)

        # CPCB Standards Reference
        self.sub_section("3.2 CPCB Noise Standards (Ambient)")
        std_headers = ["Zone", "Day Limit dB(A)", "Night Limit dB(A)", "Active Limit"]
        std_widths = [40, 35, 35, 35]
        self._table_header(std_headers, std_widths)

        for zone, limits in NOISE_STANDARDS.items():
            active = limits["night"] if period == "Night" else limits["day"]
            self._table_row(
                [
                    zone.title(),
                    str(limits["day"]),
                    str(limits["night"]),
                    f"{active} dB(A)",
                ],
                std_widths,
                fill=True,
                fill_color=(245, 240, 255),
            )
        self.ln(3)

        # Zone compliance
        if zone_stats:
            self.sub_section("3.3 Zone-wise Compliance Summary")
            zc_headers = [
                "Zone",
                "Stations",
                "Avg Leq dB(A)",
                "Limit dB(A)",
                "Compliant",
                "Exceeding",
            ]
            zc_widths = [30, 25, 30, 25, 25, 25]
            self._table_header(zc_headers, zc_widths)

            for zone, stats in zone_stats.items():
                exceeding = stats.get("exceeding", 0)
                fill = (255, 220, 220) if exceeding > 0 else (220, 255, 220)
                self._table_row(
                    [
                        zone.title(),
                        str(stats["total"]),
                        str(stats.get("avg_leq", "-")),
                        str(stats["limit"]),
                        str(stats.get("compliant", 0)),
                        str(exceeding),
                    ],
                    zc_widths,
                    fill=True,
                    fill_color=fill,
                )
            self.ln(3)

        # Loudest stations
        if stations:
            self.sub_section("3.4 Station-wise Noise Levels (Loudest First)")
            sn_headers = [
                "Station ID",
                "City",
                "Zone",
                "Avg Leq",
                "Max Leq",
                "Violations",
            ]
            sn_widths = [40, 30, 25, 25, 25, 25]
            self._table_header(sn_headers, sn_widths)

            for st in stations[:20]:
                zone = str(st.get("zone", "")).lower()
                limit = NOISE_STANDARDS.get(zone, {}).get(
                    "night" if period == "Night" else "day", 999
                )
                exceeding = st["avg_leq"] > limit
                sid = str(st.get("station_id", ""))[:22]
                city = str(st.get("city", ""))[:16]
                self._table_row(
                    [
                        sid,
                        city,
                        zone.title(),
                        str(st["avg_leq"]),
                        str(st["max_leq"]),
                        str(st.get("violations", 0)),
                    ],
                    sn_widths,
                    fill=True,
                    fill_color=(255, 220, 220) if exceeding else (240, 255, 240),
                )
            self.ln(2)

    # ── NAAQS Reference Page ───────────────────────────────
    def add_reference_page(self):
        self.add_page()
        self.section_title("ANNEXURE: STANDARDS & METHODOLOGY", (80, 80, 80))

        self.sub_section("A. National Ambient Air Quality Standards (NAAQS)")
        self.body_text(
            "As per CPCB notification under the Air (Prevention and Control of Pollution) Act, 1981. "
            "AQI is computed using sub-indices for PM2.5, PM10, NO2, SO2, CO, O3, NH3, and Pb."
        )
        ref_headers = ["Pollutant", "Unit", "24hr/8hr Limit", "Annual Limit"]
        ref_widths = [30, 25, 40, 40]
        self._table_header(ref_headers, ref_widths)
        for param, info in POLLUTANT_NAAQS.items():
            short_limit = str(info.get("24hr", info.get("8hr", info.get("1hr", "-"))))
            annual = str(info.get("annual", "-"))
            self._table_row(
                [param, info["unit"], short_limit, annual],
                ref_widths,
                fill=True,
                fill_color=(248, 248, 248),
            )
        self.ln(4)

        self.sub_section("B. AQI Category Breakpoints")
        self.body_text("AQI values are categorized as follows per CPCB standard:")
        for lo, hi, cat, color in AQI_CATEGORIES:
            self.set_font("Helvetica", "", 8)
            self.set_text_color(50, 50, 50)
            self.cell(0, 5, f"  {cat}: AQI {lo} - {hi}", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        self.sub_section("C. Water Quality Index (WQI)")
        self.body_text(
            "WQI is computed by normalising key parameters (BOD, Total Coliform, Fecal Coliform, "
            "Conductivity, Nitrate-N, TDS, Turbidity) against BIS limits. Scale: 0 (Excellent) to 1 (Very Poor). "
            "Values are capped at 3x BIS limit to prevent outlier distortion."
        )
        self.ln(2)

        self.sub_section("D. Noise Standards")
        self.body_text(
            "CPCB Noise Rules 2000 under Environment (Protection) Act, 1986. "
            "Daytime: 06:00 - 22:00 hrs, Nighttime: 22:00 - 06:00 hrs."
        )
        self.ln(2)

        self.sub_section("E. Data Sources")
        self.body_text(
            "- Air Quality: CPCB Continuous Ambient Air Quality Monitoring Stations (CAAQMS)\n"
            "- Water Quality: CPCB National Water Quality Monitoring Programme via data.gov.in\n"
            "- Noise: National Ambient Noise Monitoring Network (NANMN)\n"
            "- Standards: NAAQS 2009, BIS IS:10500, CPCB Noise Rules 2000"
        )

    # ── Master Build ───────────────────────────────────────
    def build(
        self,
        aqi_data: dict,
        water_data: dict,
        noise_data: dict,
        include_aqi: bool = True,
        include_water: bool = True,
        include_noise: bool = True,
    ) -> bytes:
        """Build the complete PDF and return as bytes."""
        self.alias_nb_pages()
        self.add_page()

        section_num = 0
        if include_aqi:
            section_num += 1
            self.add_aqi_section(aqi_data)

        if include_water:
            section_num += 1
            if section_num > 1:
                self.add_page()
            self.add_water_section(water_data)

        if include_noise:
            section_num += 1
            if section_num > 1:
                self.add_page()
            self.add_noise_section(noise_data)

        # Always add reference annexure
        self.add_reference_page()

        return bytes(self.output())


# ════════════════════════════════════════════════════════════════
# Public API — Generate Report
# ════════════════════════════════════════════════════════════════


async def generate_city_report(
    city: str,
    include_aqi: bool = True,
    include_water: bool = True,
    include_noise: bool = True,
) -> bytes:
    """Generate a city-level environmental report PDF."""
    logger.info(f"Generating city report for: {city}")

    inferred_state: Optional[str] = None
    city_station_scope = await pg_writer.get_air_stations(city=city)
    for station in city_station_scope:
        station_state = station.get("state")
        if station_state:
            inferred_state = str(station_state)
            break

    # Collect data in parallel (all are async-safe)
    aqi_data = await get_aqi_data(city=city) if include_aqi else {"available": False}
    water_data = (
        await get_water_data(state=inferred_state, district=city)
        if include_water
        else {"available": False}
    )
    noise_data = (
        await get_noise_data(city=city) if include_noise else {"available": False}
    )

    report = EnvironmentalReport(
        report_title="Environmental Monitoring Report",
        scope="City",
        scope_value=city,
    )
    return report.build(
        aqi_data,
        water_data,
        noise_data,
        include_aqi=include_aqi,
        include_water=include_water,
        include_noise=include_noise,
    )


async def generate_state_report(
    state: str,
    include_aqi: bool = True,
    include_water: bool = True,
    include_noise: bool = True,
) -> bytes:
    """Generate a state-level environmental report PDF."""
    logger.info(f"Generating state report for: {state}")

    aqi_data = await get_aqi_data(state=state) if include_aqi else {"available": False}
    water_data = (
        await get_water_data(state=state) if include_water else {"available": False}
    )
    noise_data = (
        await get_noise_data(state=state) if include_noise else {"available": False}
    )

    report = EnvironmentalReport(
        report_title="State Environmental Monitoring Report",
        scope="State",
        scope_value=state,
    )
    return report.build(
        aqi_data,
        water_data,
        noise_data,
        include_aqi=include_aqi,
        include_water=include_water,
        include_noise=include_noise,
    )


async def generate_national_report(
    include_aqi: bool = True,
    include_water: bool = True,
    include_noise: bool = True,
) -> bytes:
    """Generate a national-level environmental report PDF."""
    logger.info("Generating national report")

    aqi_data = await get_aqi_data() if include_aqi else {"available": False}
    water_data = await get_water_data() if include_water else {"available": False}
    noise_data = await get_noise_data() if include_noise else {"available": False}

    report = EnvironmentalReport(
        report_title="National Environmental Monitoring Report",
        scope="Coverage",
        scope_value="All India (591 CPCB Stations)",
    )
    return report.build(
        aqi_data,
        water_data,
        noise_data,
        include_aqi=include_aqi,
        include_water=include_water,
        include_noise=include_noise,
    )
