"""
Preprocess downloaded CPCB XLSX files and bulk-insert into ClickHouse.

CPCB hourly XLSX format:
  - Row 0 (header): Date | 00:00:00 | 01:00:00 | ... | 23:00:00
  - Data rows: day-of-month (int) | AQI value or 'NA' for each hour

This script:
  1. Walks data/raw/hourly/{state}/{city}/{station}/{year}/*.xlsx
  2. Parses each XLSX into (station_id, timestamp, parameter='AQI', value, ...)
  3. Bulk-inserts into ClickHouse air_quality_raw

Usage:
  python scripts/preprocess_cpcb_historical.py                      # all downloaded data
  python scripts/preprocess_cpcb_historical.py --state Chhattisgarh # one state
  python scripts/preprocess_cpcb_historical.py --dry-run             # count without inserting
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "hourly"
STATION_JSON = ROOT / "data" / "processed" / "cpcb_stations_raw.json"

# Month name → number
MONTH_MAP = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def extract_month_year(filename: str) -> tuple[int, int]:
    """Extract month and year from filename like 'AIIMS_Raipur_CECB_January_2024.xlsx'."""
    stem = Path(filename).stem
    parts = stem.split("_")
    year = int(parts[-1])
    month_name = parts[-2].lower()
    month = MONTH_MAP.get(month_name, 0)
    if month == 0:
        raise ValueError(f"Cannot parse month from filename: {filename}")
    return month, year


def build_station_lookup() -> dict[str, str]:
    """
    Build a mapping from sanitized station_label → station_id (site_XXXX).
    The directory name on disk is the sanitized version of station_label.
    """
    raw = json.loads(STATION_JSON.read_text(encoding="utf-8"))
    dd = raw.get("dropdown", raw)
    cities_by_state = dd["cities"]
    stations_by_city = dd["stations"]

    lookup: dict[str, str] = {}
    for state, city_list in cities_by_state.items():
        for city_obj in city_list:
            city = city_obj["value"]
            for st in stations_by_city.get(city, []):
                label = st["label"]
                # The download script uses label as-is for directory name
                lookup[label] = st["value"]
    return lookup


def aqi_sub_index(aqi_value: int) -> int:
    """Pass-through: the CPCB data IS the AQI."""
    return max(0, min(500, aqi_value))


def parse_xlsx(filepath: Path, station_id: str, city: str, state: str) -> list[tuple]:
    """
    Parse one XLSX file into rows for ClickHouse insertion.
    Returns list of tuples matching air_quality_raw columns.
    """
    try:
        month, year = extract_month_year(filepath.name)
    except ValueError as e:
        print(f"  [SKIP] {filepath.name}: {e}")
        return []

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if len(rows) < 2:
        return []

    header = rows[0]
    # Validate header: first column should be 'Date', rest should be time strings
    if str(header[0]).strip().lower() != "date":
        print(f"  [SKIP] {filepath.name}: unexpected header[0] = {header[0]}")
        return []

    records: list[tuple] = []
    for row in rows[1:]:
        day = row[0]
        if day is None or day == "NA" or day == "":
            continue
        try:
            day = int(day)
        except (ValueError, TypeError):
            continue

        for hour_idx in range(1, min(len(row), 25)):
            val = row[hour_idx]
            if val is None or val == "NA" or val == "" or val == "None":
                continue
            try:
                aqi_val = float(val)
            except (ValueError, TypeError):
                continue

            hour = hour_idx - 1  # 0-23
            try:
                ts = datetime(year, month, day, hour, 0, 0)
            except ValueError:
                # Invalid date (e.g., Feb 30)
                continue

            aqi = aqi_sub_index(int(round(aqi_val)))

            # (station_id, timestamp, parameter, value, unit, aqi,
            #  city, latitude, longitude, zone,
            #  is_anomaly, anomaly_type, quality_flag)
            records.append(
                (
                    station_id,
                    ts,
                    "AQI",
                    aqi_val,
                    "index",
                    aqi,
                    city,
                    0.0,  # latitude — not available, will be enriched later
                    0.0,  # longitude
                    "unknown",
                    0,  # is_anomaly
                    "",  # anomaly_type
                    "valid",
                )
            )

    return records


def run(state_filter: str | None, dry_run: bool, batch_size: int):
    """Main processing loop."""
    station_lookup = build_station_lookup()

    # Discover all XLSX files organized by state/city/station/year
    if not RAW_DIR.exists():
        print(f"No data directory found at {RAW_DIR}")
        return

    states = sorted(p.name for p in RAW_DIR.iterdir() if p.is_dir())
    if state_filter:
        states = [s for s in states if s.lower() == state_filter.lower()]

    total_records = 0
    total_files = 0
    total_inserted = 0

    # Import clickhouse-connect only if not dry-run
    client = None
    if not dry_run:
        try:
            import clickhouse_connect

            client = clickhouse_connect.get_client(
                host="localhost",
                port=8123,
                username="admin",
                password="prithvinet_secure_2024",
                database="prithvinet",
            )
            print("Connected to ClickHouse")
        except Exception as e:
            print(f"ClickHouse connection failed: {e}")
            print("Falling back to dry-run mode")
            dry_run = True

    columns = [
        "station_id",
        "timestamp",
        "parameter",
        "value",
        "unit",
        "aqi",
        "city",
        "latitude",
        "longitude",
        "zone",
        "is_anomaly",
        "anomaly_type",
        "quality_flag",
    ]

    batch_buffer: list[tuple] = []

    for state_dir in sorted(RAW_DIR.iterdir()):
        if not state_dir.is_dir():
            continue
        state_name = state_dir.name
        if state_filter and state_name.lower() != state_filter.lower():
            continue

        print(f"\n=== {state_name} ===")

        for city_dir in sorted(state_dir.iterdir()):
            if not city_dir.is_dir():
                continue
            city_name = city_dir.name

            for station_dir in sorted(city_dir.iterdir()):
                if not station_dir.is_dir():
                    continue
                station_label = station_dir.name
                station_id = station_lookup.get(
                    station_label, f"unknown_{station_label[:20]}"
                )

                for year_dir in sorted(station_dir.iterdir()):
                    if not year_dir.is_dir():
                        continue

                    for xlsx_file in sorted(year_dir.glob("*.xlsx")):
                        records = parse_xlsx(
                            xlsx_file, station_id, city_name, state_name
                        )
                        total_files += 1
                        total_records += len(records)

                        if records:
                            batch_buffer.extend(records)

                        # Flush batch when large enough
                        if len(batch_buffer) >= batch_size and not dry_run and client:
                            try:
                                data = [list(r) for r in batch_buffer]
                                client.insert(
                                    "air_quality_raw", data, column_names=columns
                                )
                                total_inserted += len(batch_buffer)
                            except Exception as e:
                                print(f"  [ERROR] Batch insert failed: {e}")
                            batch_buffer.clear()

                print(
                    f"  {station_label}: {total_files} files, {total_records} records so far"
                )

    # Flush remaining
    if batch_buffer and not dry_run and client:
        try:
            data = [list(r) for r in batch_buffer]
            client.insert("air_quality_raw", data, column_names=columns)
            total_inserted += len(batch_buffer)
        except Exception as e:
            print(f"  [ERROR] Final batch insert failed: {e}")
        batch_buffer.clear()

    if client:
        client.close()

    print()
    print("=" * 60)
    print(f"Files processed:  {total_files}")
    print(f"Records parsed:   {total_records:,}")
    if not dry_run:
        print(f"Records inserted: {total_inserted:,}")
    else:
        print(f"(dry-run — nothing inserted)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Preprocess CPCB XLSX → ClickHouse")
    parser.add_argument("--state", type=str, default=None, help="Filter by state")
    parser.add_argument(
        "--dry-run", action="store_true", help="Parse only, don't insert"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50000,
        help="Rows per ClickHouse insert batch (default: 50000)",
    )
    args = parser.parse_args()

    run(state_filter=args.state, dry_run=args.dry_run, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
