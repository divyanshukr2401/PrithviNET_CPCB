"""
PrithviNET AI Copilot — Data Context Builders.

Summarises live AQI / Water / Noise data + Indian event calendar
into compact text blocks that are injected into the Gemini system prompt.
This keeps token usage low (~2-3K tokens context) while giving the LLM
enough grounding to answer factual and policy questions accurately.
"""

from __future__ import annotations

import json
from datetime import datetime, date
from typing import Optional

from loguru import logger

from app.services.ingestion.clickhouse_writer import ch_writer
from app.core.redis import get_redis


# ═══════════════════════════════════════════════════════════════════════
# Indian environmental events calendar
# ═══════════════════════════════════════════════════════════════════════

ENVIRONMENTAL_EVENTS = [
    # Air quality events
    {
        "month_range": [10, 11],
        "event": "Diwali (Festival of Lights)",
        "impact": "AQI",
        "severity": "Severe",
        "detail": "Firecracker burning causes PM2.5/PM10 spikes across North & Central India. Delhi-NCR, UP, Bihar, Chhattisgarh worst affected.",
    },
    {
        "month_range": [10, 11],
        "event": "Post-monsoon crop stubble burning",
        "impact": "AQI",
        "severity": "Severe",
        "detail": "Paddy stubble burning in Punjab, Haryana & western UP. Smoke plumes reach Delhi-NCR, causing AQI > 400.",
    },
    {
        "month_range": [12, 1, 2],
        "event": "Winter temperature inversion",
        "impact": "AQI",
        "severity": "High",
        "detail": "Cold, still air traps pollutants near ground level. Indo-Gangetic plain cities see persistent 'Very Poor' to 'Severe' AQI.",
    },
    {
        "month_range": [3, 4, 5],
        "event": "Pre-monsoon dust storms",
        "impact": "AQI",
        "severity": "Moderate",
        "detail": "Dust storms from Thar Desert raise PM10 in Rajasthan, Gujarat, western MP. Occasional impact on Chhattisgarh.",
    },
    {
        "month_range": [6, 7, 8, 9],
        "event": "Monsoon season (JJAS)",
        "impact": "AQI",
        "severity": "Low",
        "detail": "Rainfall washes out particulates. AQI generally 'Good' to 'Satisfactory' across most of India.",
    },
    {
        "month_range": [11],
        "event": "Chhath Puja",
        "impact": "AQI",
        "severity": "Moderate",
        "detail": "Biomass burning and ritual fires in Bihar, Jharkhand, eastern UP.",
    },
    # Water quality events
    {
        "month_range": [1, 2],
        "event": "Magh Mela / Kumbh Mela (Prayagraj)",
        "impact": "WQI",
        "severity": "High",
        "detail": "Millions of pilgrims bathe in Sangam (Ganga-Yamuna confluence). BOD, coliform levels spike in Prayagraj stretch.",
    },
    {
        "month_range": [3],
        "event": "Holi festival",
        "impact": "WQI",
        "severity": "Moderate",
        "detail": "Chemical dyes and colors washed into rivers and drains. Heavy metal contamination risk in smaller rivers.",
    },
    {
        "month_range": [7, 8, 9],
        "event": "Peak monsoon flooding",
        "impact": "WQI",
        "severity": "High",
        "detail": "Urban runoff, sewage overflow, agricultural pesticide runoff. Turbidity and coliform counts spike.",
    },
    {
        "month_range": [10, 11],
        "event": "Idol immersion (Durga Puja/Ganesh Chaturthi)",
        "impact": "WQI",
        "severity": "Moderate",
        "detail": "Paint, plaster-of-Paris idols immersed in rivers/lakes. Heavy metals (Pb, Cr) and BOD increase.",
    },
    {
        "month_range": [4, 5, 6],
        "event": "Pre-monsoon low river flows",
        "impact": "WQI",
        "severity": "Moderate",
        "detail": "Reduced river discharge concentrates pollutants. Dissolved oxygen drops in Ganga, Yamuna, Godavari stretches.",
    },
    # Noise events
    {
        "month_range": [10, 11],
        "event": "Diwali firecrackers",
        "impact": "Noise",
        "severity": "Severe",
        "detail": "Noise levels exceed 100 dB(A) in residential areas. CPCB 55 dB(A) night limit violated across all zones.",
    },
    {
        "month_range": [1, 8, 9],
        "event": "Election rallies / Independence & Republic Day",
        "impact": "Noise",
        "severity": "Moderate",
        "detail": "Loudspeakers, processions, rallies exceed commercial zone limits (65 dB day).",
    },
    {
        "month_range": [12, 1],
        "event": "New Year celebrations",
        "impact": "Noise",
        "severity": "Moderate",
        "detail": "Firecrackers and loudspeakers in urban areas. Night noise limits violated.",
    },
]


def _get_current_events() -> str:
    """Return events relevant to the current month."""
    current_month = datetime.now().month
    relevant = [e for e in ENVIRONMENTAL_EVENTS if current_month in e["month_range"]]
    if not relevant:
        return "No major environmental events are associated with this time of year."
    lines = []
    for e in relevant:
        lines.append(
            f"- **{e['event']}** ({e['impact']}, Severity: {e['severity']}): {e['detail']}"
        )
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# AQI context — top/bottom stations from ClickHouse
# ═══════════════════════════════════════════════════════════════════════


async def build_aqi_context() -> str:
    """Build a compact AQI summary from ClickHouse live data."""
    try:
        client = ch_writer._get_client()

        # Worst 15 stations by AQI (latest reading per station)
        worst = client.query("""
            SELECT station_id, city,
                   argMax(value, timestamp) AS latest_aqi,
                   max(timestamp) AS ts
            FROM air_quality_raw
            WHERE parameter = 'AQI'
              AND timestamp >= now() - INTERVAL 2 HOUR
            GROUP BY station_id, city
            ORDER BY latest_aqi DESC
            LIMIT 15
        """)
        worst_cols = worst.column_names
        worst_rows = [dict(zip(worst_cols, r)) for r in worst.result_rows]

        # Best 10 stations
        best = client.query("""
            SELECT station_id, city,
                   argMax(value, timestamp) AS latest_aqi,
                   max(timestamp) AS ts
            FROM air_quality_raw
            WHERE parameter = 'AQI'
              AND timestamp >= now() - INTERVAL 2 HOUR
              AND value > 0
            GROUP BY station_id, city
            ORDER BY latest_aqi ASC
            LIMIT 10
        """)
        best_cols = best.column_names
        best_rows = [dict(zip(best_cols, r)) for r in best.result_rows]

        # City-level averages (no state column available)
        city_avg = client.query("""
            SELECT city,
                   round(avg(latest_aqi)) AS avg_aqi,
                   count() AS stations
            FROM (
                SELECT station_id, city,
                       argMax(value, timestamp) AS latest_aqi
                FROM air_quality_raw
                WHERE parameter = 'AQI'
                  AND timestamp >= now() - INTERVAL 2 HOUR
                GROUP BY station_id, city
            )
            GROUP BY city
            ORDER BY avg_aqi DESC
            LIMIT 25
        """)
        city_cols = city_avg.column_names
        city_rows = [dict(zip(city_cols, r)) for r in city_avg.result_rows]

        # Overall stats
        overall = client.query("""
            SELECT count(DISTINCT station_id) AS total_stations,
                   round(avg(latest_aqi)) AS national_avg,
                   max(latest_aqi) AS national_max,
                   min(latest_aqi) AS national_min,
                   countIf(latest_aqi > 300) AS severe_count,
                   countIf(latest_aqi > 200) AS poor_plus_count
            FROM (
                SELECT station_id,
                       argMax(value, timestamp) AS latest_aqi
                FROM air_quality_raw
                WHERE parameter = 'AQI'
                  AND timestamp >= now() - INTERVAL 2 HOUR
                GROUP BY station_id
            )
        """)
        ov = (
            dict(zip(overall.column_names, overall.result_rows[0]))
            if overall.result_rows
            else {}
        )

        lines = ["## Current Air Quality Snapshot (LIVE)"]
        lines.append(f"- **Total active stations**: {ov.get('total_stations', '?')}")
        lines.append(f"- **National average AQI**: {ov.get('national_avg', '?')}")
        lines.append(
            f"- **Range**: {ov.get('national_min', '?')} – {ov.get('national_max', '?')}"
        )
        lines.append(
            f"- **Stations in Poor+**: {ov.get('poor_plus_count', '?')} | **Severe**: {ov.get('severe_count', '?')}"
        )

        lines.append("\n### Worst 15 Stations (Highest AQI):")
        for r in worst_rows:
            lines.append(
                f"  - {r['station_id']} ({r['city']}): AQI {int(r['latest_aqi'])}"
            )

        lines.append("\n### Best 10 Stations (Lowest AQI):")
        for r in best_rows:
            lines.append(
                f"  - {r['station_id']} ({r['city']}): AQI {int(r['latest_aqi'])}"
            )

        lines.append("\n### City-wise Average AQI (Top 25):")
        for r in city_rows:
            lines.append(
                f"  - {r['city']}: avg AQI {int(r['avg_aqi'])} ({r['stations']} stations)"
            )

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Copilot AQI context build failed: {e}")
        return "AQI data is currently unavailable."


# ═══════════════════════════════════════════════════════════════════════
# Water Quality context — from Redis cache
# ═══════════════════════════════════════════════════════════════════════


async def build_water_context() -> str:
    """Build water quality summary from Redis-cached CPCB data."""
    try:
        r = await get_redis()

        # Try the actual cache key pattern used by the water quality fetcher
        raw = await r.get("water_quality_heatmap:v2:all_states:limit=5000")
        if not raw:
            # Fallback: scan for any water_quality_heatmap key
            keys = await r.keys("water_quality_heatmap:*")
            if keys:
                raw = await r.get(keys[0])

        if not raw:
            return "Water quality data is not currently cached. The Water Quality tab needs to be loaded at least once to populate the cache."

        points = json.loads(raw)
        if isinstance(points, dict) and "points" in points:
            points = points["points"]

        total = len(points)
        if total == 0:
            return "No water quality monitoring points available."

        # Categorize by WQI
        excellent = [p for p in points if p.get("wqi", 0) >= 80]
        good = [p for p in points if 60 <= p.get("wqi", 0) < 80]
        fair = [p for p in points if 40 <= p.get("wqi", 0) < 60]
        poor = [p for p in points if 20 <= p.get("wqi", 0) < 40]
        very_poor = [p for p in points if p.get("wqi", 0) < 20]

        # Worst 10 stations
        sorted_pts = sorted(points, key=lambda p: p.get("wqi", 100))
        worst_10 = sorted_pts[:10]

        lines = ["## Current Water Quality Snapshot"]
        lines.append(f"- **Total monitoring stations**: {total}")
        lines.append(f"- **Excellent (WQI ≥ 80)**: {len(excellent)}")
        lines.append(f"- **Good (60–80)**: {len(good)}")
        lines.append(f"- **Fair (40–60)**: {len(fair)}")
        lines.append(f"- **Poor (20–40)**: {len(poor)}")
        lines.append(f"- **Very Poor (< 20)**: {len(very_poor)}")

        lines.append("\n### Worst 10 Stations (Lowest WQI):")
        for p in worst_10:
            name = p.get("station_name", p.get("name", "Unknown"))
            state = p.get("state", "?")
            wqi = round(p.get("wqi", 0), 1)
            lines.append(f"  - {name} ({state}): WQI {wqi}")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Copilot water context build failed: {e}")
        return "Water quality data is currently unavailable."


# ═══════════════════════════════════════════════════════════════════════
# Noise context — from ClickHouse
# ═══════════════════════════════════════════════════════════════════════


async def build_noise_context() -> str:
    """Build noise monitoring summary from ClickHouse."""
    try:
        client = ch_writer._get_client()

        result = client.query("""
            SELECT station_id, city, zone,
                   round(avg(value), 1) AS avg_leq,
                   round(max(value), 1) AS max_leq,
                   countIf(is_exceedance = 1) AS violations,
                   count() AS readings
            FROM noise_raw
            WHERE metric = 'Leq'
              AND timestamp >= now() - INTERVAL 6 HOUR
            GROUP BY station_id, city, zone
            ORDER BY avg_leq DESC
        """)
        cols = result.column_names
        rows = [dict(zip(cols, r)) for r in result.result_rows]

        if not rows:
            return "No recent noise monitoring data available."

        # Zone limits (CPCB Noise Standards 2000)
        zone_limits = {
            "industrial": {"day": 75, "night": 70},
            "commercial": {"day": 65, "night": 55},
            "residential": {"day": 55, "night": 45},
            "silence": {"day": 50, "night": 40},
        }

        violations_count = sum(r["violations"] for r in rows)
        total_readings = sum(r["readings"] for r in rows)

        lines = ["## Current Noise Monitoring Snapshot (Last 6 Hours)"]
        lines.append(f"- **Active stations**: {len(rows)}")
        lines.append(f"- **Total readings**: {total_readings}")
        lines.append(
            f"- **Exceedances**: {violations_count} ({round(100 * violations_count / max(1, total_readings), 1)}%)"
        )

        # Loudest stations
        lines.append("\n### Loudest 10 Stations:")
        for r in rows[:10]:
            zone = r["zone"]
            limit = zone_limits.get(zone, {}).get("day", "?")
            status = (
                "EXCEEDING"
                if r["avg_leq"] > (limit if isinstance(limit, (int, float)) else 999)
                else "Within limit"
            )
            lines.append(
                f"  - {r['station_id']} ({r['city']}, {zone.title()} zone): Avg {r['avg_leq']} dB(A), Max {r['max_leq']} dB(A) [{status}, limit: {limit} dB]"
            )

        lines.append("\n### CPCB Noise Standards 2000:")
        for zone, limits in zone_limits.items():
            lines.append(
                f"  - {zone.title()}: Day {limits['day']} dB(A), Night {limits['night']} dB(A)"
            )

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Copilot noise context build failed: {e}")
        return "Noise monitoring data is currently unavailable."


# ═══════════════════════════════════════════════════════════════════════
# Master context builder
# ═══════════════════════════════════════════════════════════════════════


async def build_full_context(active_layer: Optional[str] = None) -> str:
    """
    Build the complete data context for the copilot.
    If active_layer is specified, prioritize that data.
    Always includes event calendar and all available data sources.
    """
    sections = []

    # Current date/time context
    now = datetime.now()
    sections.append(
        f"**Current Date/Time**: {now.strftime('%B %d, %Y at %I:%M %p IST')} (Month: {now.strftime('%B')})"
    )

    # Event calendar (always included)
    sections.append("\n## Seasonal & Event Context for Current Period")
    sections.append(_get_current_events())

    # Always include all data sources (order by priority — active layer first)
    builders = {
        "aqi": build_aqi_context,
        "water": build_water_context,
        "noise": build_noise_context,
    }

    if active_layer and active_layer in builders:
        # Active layer first (priority), then others
        sections.append("\n" + await builders[active_layer]())
        for key, builder in builders.items():
            if key != active_layer:
                sections.append("\n" + await builder())
    else:
        # No specific layer — include all
        for builder in builders.values():
            sections.append("\n" + await builder())

    return "\n".join(sections)
