"""
Download historical AQI data from CPCB Data Repository for all Indian stations.

Strategy:
  - For each station, request hourly stationLevel data for each year (2024, 2023, …)
  - Download all monthly XLSX files returned by file_Path endpoint
  - Save to data/raw/{state}/{city}/{station_label}/{year}/{month}.xlsx
  - Resumable: skips files that already exist on disk
  - Rate-limited: configurable delay between requests

Usage:
  python scripts/download_cpcb_historical.py                    # all stations, 2024-2023
  python scripts/download_cpcb_historical.py --state Chhattisgarh
  python scripts/download_cpcb_historical.py --years 2024       # single year
  python scripts/download_cpcb_historical.py --daily             # daily city-level instead
  python scripts/download_cpcb_historical.py --dry-run           # just print what would be downloaded
"""

from __future__ import annotations

import argparse
import base64
import json
import time
import re
import sys
from pathlib import Path

import httpx

# Force unbuffered output for background/nohup execution
import functools

print = functools.partial(print, flush=True)

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
STATION_JSON = ROOT / "data" / "processed" / "cpcb_stations_raw.json"
RAW_DIR = ROOT / "data" / "raw"

# ── CPCB API ───────────────────────────────────────────────────────────
BASE_URL = "https://airquality.cpcb.gov.in/dataRepository"
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "q=0.8;application/json;q=0.9",
    "Referer": "https://airquality.cpcb.gov.in/ccr/",
}

# ── Helpers ────────────────────────────────────────────────────────────


def sanitize(name: str) -> str:
    """Make a string safe for use as a directory/file name."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(".")


def post_b64(
    client: httpx.Client, endpoint: str, payload: dict, retries: int = 3
) -> dict:
    """POST base64-encoded JSON, decode base64 JSON response. Retries on failure."""
    body = base64.b64encode(json.dumps(payload).encode()).decode()
    for attempt in range(retries):
        try:
            r = client.post(
                f"{BASE_URL}/{endpoint}", content=body, headers=HEADERS, timeout=30
            )
            decoded = base64.b64decode(r.text).decode("utf-8")
            return json.loads(decoded)
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(
                    f"    [RETRY] post_b64 attempt {attempt + 1} failed: {e}, retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                print(f"    [ERROR] post_b64 failed after {retries} attempts: {e}")
                return {"_raw": str(e)[:500], "_status": 0}


def download_file(
    client: httpx.Client, filepath: str, dest: Path, retries: int = 3
) -> bool:
    """Download a single XLSX file from CPCB. Returns True on success. Retries on failure."""
    url = f"{BASE_URL}/download_file?file_name={filepath}"
    for attempt in range(retries):
        try:
            r = client.get(url, headers=HEADERS, timeout=60, follow_redirects=True)
            if r.status_code == 200 and len(r.content) > 100:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(r.content)
                return True
            else:
                if attempt < retries - 1:
                    time.sleep(2 ** (attempt + 1))
                    continue
                return False
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(
                    f"    [RETRY] download attempt {attempt + 1} failed: {e}, retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                print(f"    [ERROR] download failed after {retries} attempts: {e}")
                return False
    return False


# ── Station registry loader ───────────────────────────────────────────


def load_stations(state_filter: str | None = None) -> list[dict]:
    """
    Load stations from cpcb_stations_raw.json.
    Returns list of {state, city, station_id, station_label}.
    """
    raw = json.loads(STATION_JSON.read_text(encoding="utf-8"))
    dd = raw.get("dropdown", raw)
    cities_by_state: dict[str, list] = dd["cities"]
    stations_by_city: dict[str, list] = dd["stations"]

    result = []
    for state, city_list in cities_by_state.items():
        if state_filter and state.lower() != state_filter.lower():
            continue
        for city_obj in city_list:
            city = city_obj["value"]
            for st in stations_by_city.get(city, []):
                result.append(
                    {
                        "state": state,
                        "city": city,
                        "station_id": st["value"],
                        "station_label": st["label"],
                    }
                )
    return result


# ── Main download loop ────────────────────────────────────────────────


def run(
    state_filter: str | None,
    years: list[int],
    daily: bool,
    dry_run: bool,
    delay: float,
):
    stations = load_stations(state_filter)
    print(
        f"Loaded {len(stations)} stations"
        + (f" (state={state_filter})" if state_filter else "")
    )

    if daily:
        print("Mode: DAILY city-level (one file per city per year)")
    else:
        print(f"Mode: HOURLY station-level (monthly files per station)")
    print(f"Years: {years}")
    print(f"Output: {RAW_DIR}")
    print()

    # Stats
    total_downloaded = 0
    total_skipped = 0
    total_failed = 0
    total_api_calls = 0

    client = httpx.Client(
        http2=False,
        verify=False,
        timeout=httpx.Timeout(connect=15, read=60, write=30, pool=60),
        limits=httpx.Limits(
            max_connections=5, max_keepalive_connections=2, keepalive_expiry=30
        ),
    )

    if daily:
        # For daily mode, group by (state, city) to avoid duplicate requests
        seen_cities: set[tuple[str, str]] = set()
        for st in stations:
            key = (st["state"], st["city"])
            if key in seen_cities:
                continue
            seen_cities.add(key)

            state_dir = sanitize(st["state"])
            city_dir = sanitize(st["city"])

            for year in years:
                payload = {
                    "station_id": "",
                    "station_name": "",
                    "state": st["state"],
                    "city": st["city"],
                    "year": "",
                    "frequency": "daily",
                    "dataType": "cityLevel",
                }
                total_api_calls += 1
                result = post_b64(client, "file_Path", payload)
                time.sleep(delay)

                if result.get("status") != "success" or "data" not in result:
                    print(
                        f"  [{st['state']}/{st['city']}] file_Path failed: {str(result)[:200]}"
                    )
                    total_failed += 1
                    continue

                for item in result["data"]:
                    fp = item.get("filepath", "")
                    item_year = item.get("year", "")
                    if not fp:
                        continue
                    if item_year and int(item_year) not in years:
                        continue

                    fname = fp.split("/")[-1]
                    dest = RAW_DIR / "daily" / state_dir / city_dir / fname

                    if dest.exists():
                        total_skipped += 1
                        continue

                    if dry_run:
                        print(f"  [DRY] {dest}")
                        total_downloaded += 1
                        continue

                    ok = download_file(client, fp, dest)
                    if ok:
                        total_downloaded += 1
                        print(f"  [OK] {dest.name} ({dest.stat().st_size:,} bytes)")
                    else:
                        total_failed += 1
                        print(f"  [FAIL] {fp}")
                    time.sleep(delay)

                # Only need one file_Path call per city for daily mode (returns all years)
                break  # break out of year loop — daily returns all years in one call

    else:
        # Hourly station-level: one file_Path call per (station, year)
        RECONNECT_EVERY = (
            20  # recreate HTTP client every N stations to avoid stale connections
        )
        for idx, st in enumerate(stations):
            # Recreate client periodically
            if idx % RECONNECT_EVERY == 0:
                if idx > 0:
                    client.close()
                    time.sleep(2)
                client = httpx.Client(
                    http2=False,
                    verify=False,
                    timeout=httpx.Timeout(connect=15, read=60, write=30, pool=60),
                    limits=httpx.Limits(
                        max_connections=5,
                        max_keepalive_connections=2,
                        keepalive_expiry=30,
                    ),
                )
                if idx > 0:
                    print(f"  [RECONNECT] Recreated HTTP client at station {idx + 1}")

            state_dir = sanitize(st["state"])
            city_dir = sanitize(st["city"])
            station_dir = sanitize(st["station_label"])

            print(
                f"[{idx + 1}/{len(stations)}] {st['station_label']} ({st['city']}, {st['state']})"
            )

            for year in years:
                payload = {
                    "station_id": st["station_id"],
                    "station_name": st["station_label"],
                    "state": st["state"],
                    "city": st["city"],
                    "year": str(year),
                    "frequency": "hourly",
                    "dataType": "stationLevel",
                }
                total_api_calls += 1
                result = post_b64(client, "file_Path", payload)
                time.sleep(delay)

                if result.get("status") != "success" or "data" not in result:
                    print(f"  [{year}] file_Path failed: {str(result)[:200]}")
                    total_failed += 1
                    continue

                files = result["data"]
                for item in files:
                    fp = item.get("filepath", "")
                    month = item.get("month", "unknown")
                    if not fp:
                        continue

                    fname = fp.split("/")[-1]
                    dest = (
                        RAW_DIR
                        / "hourly"
                        / state_dir
                        / city_dir
                        / station_dir
                        / str(year)
                        / fname
                    )

                    if dest.exists():
                        total_skipped += 1
                        continue

                    if dry_run:
                        print(f"  [DRY] {year}/{month}: {fname}")
                        total_downloaded += 1
                        continue

                    ok = download_file(client, fp, dest)
                    if ok:
                        total_downloaded += 1
                        size = dest.stat().st_size
                        print(f"  [OK] {year}/{month}: {fname} ({size:,} bytes)")
                    else:
                        total_failed += 1
                        print(f"  [FAIL] {year}/{month}: {fp}")
                    time.sleep(delay)

    client.close()

    print()
    print("=" * 60)
    print(f"API calls made:    {total_api_calls}")
    print(f"Files downloaded:  {total_downloaded}")
    print(f"Files skipped:     {total_skipped}")
    print(f"Files failed:      {total_failed}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Download CPCB historical AQI data")
    parser.add_argument("--state", type=str, default=None, help="Filter by state name")
    parser.add_argument(
        "--years",
        type=str,
        default="2025,2024",
        help="Comma-separated years (default: 2025,2024)",
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="Download daily city-level data instead of hourly station-level",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds between API requests (default: 0.5)",
    )
    args = parser.parse_args()

    years = [int(y.strip()) for y in args.years.split(",")]
    run(
        state_filter=args.state,
        years=years,
        daily=args.daily,
        dry_run=args.dry_run,
        delay=args.delay,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Download stopped by user.")
    except Exception as exc:
        import traceback

        print(f"\n[FATAL] Unhandled exception: {exc}")
        traceback.print_exc()
        sys.exit(1)
