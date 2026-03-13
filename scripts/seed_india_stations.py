"""
Seed ALL-INDIA air_stations into PostgreSQL from cpcb_stations_raw.json.

- Reads the 591 CPCB stations from data/processed/cpcb_stations_raw.json
- Generates a SQL file (docker/postgres/seed_india_air_stations.sql) with UPSERT
- Extracts operator name from station label (text after last " - ")
- Lat/lon are set to NULL (no geometry) — will be enriched later via geocoding

Usage:
  python scripts/seed_india_stations.py              # generate SQL file
  python scripts/seed_india_stations.py --print       # print to stdout instead
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATION_JSON = ROOT / "data" / "processed" / "cpcb_stations_raw.json"
OUTPUT_SQL = ROOT / "docker" / "postgres" / "seed_india_air_stations.sql"


def extract_operator(label: str) -> str:
    """Extract board/operator from label like 'Evelyn Lodge, Asansol - WBPCB'."""
    if " - " in label:
        return label.rsplit(" - ", 1)[-1].strip()
    return "Unknown"


def sql_escape(s: str) -> str:
    """Escape single quotes for SQL."""
    return s.replace("'", "''")


def load_stations() -> list[dict]:
    """Load flat list of {station_id, label, city, state, operator}."""
    raw = json.loads(STATION_JSON.read_text(encoding="utf-8"))
    dd = raw.get("dropdown", raw)
    cities_by_state: dict[str, list] = dd["cities"]
    stations_by_city: dict[str, list] = dd["stations"]

    result = []
    for state, city_list in cities_by_state.items():
        for city_obj in city_list:
            city = city_obj["value"]
            for st in stations_by_city.get(city, []):
                result.append({
                    "station_id": st["value"],
                    "label": st["label"],
                    "city": city,
                    "state": state,
                    "operator": extract_operator(st["label"]),
                })
    return result


def generate_sql(stations: list[dict]) -> str:
    lines = [
        "-- ==========================================================================",
        "-- PRITHVINET: All-India CPCB Air Quality Stations",
        f"-- Auto-generated from cpcb_stations_raw.json ({len(stations)} stations)",
        "-- Uses ON CONFLICT to upsert — safe to run multiple times",
        "-- ==========================================================================",
        "",
    ]

    # Group by state for readability
    by_state: dict[str, list[dict]] = {}
    for s in stations:
        by_state.setdefault(s["state"], []).append(s)

    for state in sorted(by_state.keys()):
        state_stations = by_state[state]
        lines.append(f"-- {state} ({len(state_stations)} stations)")
        for s in state_stations:
            sid = sql_escape(s["station_id"])
            name = sql_escape(s["label"])
            city = sql_escape(s["city"])
            st = sql_escape(s["state"])
            op = sql_escape(s["operator"])
            lines.append(
                f"INSERT INTO air_stations (station_id, station_name, city, state, station_type, operator) "
                f"VALUES ('{sid}', '{name}', '{city}', '{st}', 'CAAQMS', '{op}') "
                f"ON CONFLICT (station_id) DO UPDATE SET "
                f"station_name = EXCLUDED.station_name, city = EXCLUDED.city, "
                f"state = EXCLUDED.state, operator = EXCLUDED.operator, "
                f"updated_at = NOW();"
            )
        lines.append("")

    lines.append(f"-- Total: {len(stations)} stations across {len(by_state)} states")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate All-India air_stations seed SQL")
    parser.add_argument("--print", action="store_true", help="Print to stdout instead of file")
    args = parser.parse_args()

    stations = load_stations()
    sql = generate_sql(stations)

    if args.print:
        print(sql)
    else:
        OUTPUT_SQL.write_text(sql, encoding="utf-8")
        print(f"Written {len(stations)} station INSERTs to {OUTPUT_SQL}")
        # Count unique states and cities
        states = set(s["state"] for s in stations)
        cities = set(s["city"] for s in stations)
        print(f"  States: {len(states)}, Cities: {len(cities)}, Stations: {len(stations)}")


if __name__ == "__main__":
    main()
