"""OCEMS Compliance and Auto-Healer API Endpoints — wired to real services."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime

from app.services.ocems.auto_healer import auto_healer
from app.services.ocems.alerts import ocems_alerts
from app.services.ingestion.clickhouse_writer import ch_writer
from app.services.ingestion.postgres_writer import pg_writer
from app.core.redis import cached

router = APIRouter()


@router.get("/alerts/summary")
async def get_alerts_summary(hours: int = Query(72, ge=1, le=168)):
    """Get OCEMS Alerts summary for the alert-first compliance workflow."""
    return await ocems_alerts.get_alert_summary(hours=hours)


@router.get("/alerts")
async def get_alerts(
    district: Optional[str] = Query(None),
    cpcb_category: Optional[str] = Query(None),
    parameter: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    hours: int = Query(72, ge=1, le=168),
):
    """Return enriched OCEMS Alerts with industry contact and legal context."""
    return await ocems_alerts.get_alerts(
        district=district,
        cpcb_category=cpcb_category,
        parameter=parameter,
        severity=severity,
        hours=hours,
    )


@router.get("/alerts/{alert_id}")
async def get_alert_detail(alert_id: str):
    """Return a single enriched alert detail record."""
    try:
        return await ocems_alerts.get_alert_detail(alert_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/alerts/{alert_id}/notice-draft")
async def get_notice_draft(alert_id: str):
    """Generate a believable regulator notice draft without sending mail."""
    try:
        return await ocems_alerts.build_notice_draft(alert_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/")
@cached(ttl_seconds=120, prefix="compliance_summary")
async def get_compliance_summary():
    """Get overall OCEMS compliance summary across all CG factories."""
    factories = await pg_writer.get_factories()
    try:
        client = ch_writer._get_client()
        result = client.query("""
            SELECT factory_id,
                   countIf(value > emission_limit) AS exceedances,
                   count() AS total,
                   100.0 * countIf(value <= emission_limit) / count() AS compliance_pct
            FROM ocems_raw
            WHERE timestamp >= now() - INTERVAL 24 HOUR
            GROUP BY factory_id
        """)
        columns = result.column_names
        rows = [dict(zip(columns, row)) for row in result.result_rows]
    except Exception:
        rows = []

    compliance_map = {r["factory_id"]: r for r in rows}
    compliant = sum(1 for r in rows if r.get("compliance_pct", 0) >= 95)
    non_compliant = sum(1 for r in rows if 50 <= r.get("compliance_pct", 100) < 95)
    critical = sum(1 for r in rows if r.get("compliance_pct", 100) < 50)

    overall_pct = 0
    if rows:
        overall_pct = round(
            sum(r.get("compliance_pct", 0) for r in rows) / len(rows), 1
        )

    return {
        "total_factories": len(factories),
        "monitored_24h": len(rows),
        "compliant": compliant,
        "non_compliant": non_compliant,
        "critical": critical,
        "overall_compliance_pct": overall_pct,
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get("/factories")
async def get_factories(
    city: Optional[str] = Query(None, description="Filter by city"),
    risk: Optional[str] = Query(None, description="Filter by industry_risk"),
):
    """Get list of factories with compliance status."""
    factories = await pg_writer.get_factories(city=city, risk=risk)
    return {
        "factories": factories,
        "total": len(factories),
        "filters": {"city": city, "risk": risk},
    }


@router.get("/factories/{factory_id}")
async def get_factory_compliance(factory_id: str):
    """Get detailed compliance status for a factory."""
    # Get recent OCEMS readings
    readings = await ch_writer.query_recent_readings(
        "ocems_raw",
        factory_id,
        id_column="factory_id",
        hours=24,
    )
    if not readings:
        raise HTTPException(
            status_code=404, detail=f"No recent data for factory {factory_id}"
        )

    # Group by parameter
    params: dict[str, list] = {}
    for r in readings:
        p = r.get("parameter", "")
        params.setdefault(p, []).append(r)

    import numpy as np

    param_details = {}
    for p, rlist in params.items():
        values = [r["value"] for r in rlist]
        arr = np.array(values)
        limit = rlist[0].get("emission_limit", 100)
        exceedances = int(np.sum(arr > limit))
        param_details[p] = {
            "avg": round(float(np.mean(arr)), 2),
            "max": round(float(np.max(arr)), 2),
            "p95": round(float(np.percentile(arr, 95)), 2),
            "limit": limit,
            "exceedance_count": exceedances,
            "compliance_pct": round(100 * (1 - exceedances / max(1, len(values))), 1),
        }

    sample = readings[0]
    overall_compliance = round(
        sum(d["compliance_pct"] for d in param_details.values())
        / max(1, len(param_details)),
        1,
    )

    return {
        "factory_id": factory_id,
        "industry_type": sample.get("industry_type", ""),
        "city": sample.get("city", ""),
        "dahs_status": sample.get("dahs_status", "online"),
        "sensor_health": sample.get("sensor_health", 100),
        "overall_compliance_pct": overall_compliance,
        "parameters": param_details,
        "total_readings_24h": len(readings),
    }


@router.get("/auto-healer/diagnose/{factory_id}")
async def diagnose_factory(
    factory_id: str,
    parameter: Optional[str] = Query(
        None, description="Specific parameter to diagnose"
    ),
    hours: int = Query(6, ge=1, le=48),
):
    """
    OCEMS Auto-Healer: Diagnose sensor faults vs real pollution events.
    Uses 4-indicator weighted scoring: temporal_gradient, cross_sensor,
    stuck_value, statistical_outlier.
    """
    try:
        result = await auto_healer.diagnose(
            factory_id, parameter=parameter, hours=hours
        )
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagnosis failed: {str(e)}")


@router.get("/exceedances")
@cached(ttl_seconds=120, prefix="compliance_exceed")
async def get_exceedances(
    city: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
):
    """Get recent OCEMS exceedance events."""
    try:
        client = ch_writer._get_client()
        city_filter = f"AND city = '{city}'" if city else ""
        result = client.query(f"""
            SELECT factory_id, parameter, city, industry_type,
                   value, emission_limit, exceedance_pct,
                   timestamp, anomaly_type, quality_flag
            FROM ocems_raw
            WHERE value > emission_limit
              AND timestamp >= now() - INTERVAL {hours} HOUR
              {city_filter}
            ORDER BY exceedance_pct DESC
            LIMIT 200
        """)
        columns = result.column_names
        rows = [dict(zip(columns, row)) for row in result.result_rows]
    except Exception:
        rows = []

    return {
        "exceedances": [
            {
                "factory_id": r.get("factory_id", ""),
                "parameter": r.get("parameter", ""),
                "city": r.get("city", ""),
                "industry_type": r.get("industry_type", ""),
                "value": round(r.get("value", 0), 2),
                "limit": r.get("emission_limit", 0),
                "exceedance_pct": round(r.get("exceedance_pct", 0), 1),
                "timestamp": str(r.get("timestamp", "")),
                "anomaly_type": r.get("anomaly_type", ""),
                "quality_flag": r.get("quality_flag", ""),
            }
            for r in rows
        ],
        "total": len(rows),
        "filter": {"city": city, "hours": hours},
    }
