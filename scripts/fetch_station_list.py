"""Fetch and decode the CPCB station list API response."""
import json
import base64
import httpx

def main():
    payload = base64.b64encode(b"{}").decode()
    r = httpx.post(
        "https://airquality.cpcb.gov.in/dataRepository/all_india_stationlist",
        content=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "q=0.8;application/json;q=0.9",
            "Referer": "https://airquality.cpcb.gov.in/ccr/",
        },
        timeout=20,
    )
    print(f"HTTP Status: {r.status_code}, Body length: {len(r.text)}")

    decoded = base64.b64decode(r.text).decode("utf-8")
    data = json.loads(decoded)

    # Save full response
    with open("data/processed/cpcb_stations_raw.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"API status: {data.get('status')}")
    print(f"Top keys: {list(data.keys())}")

    if "dropdown" in data:
        dd = data["dropdown"]
        print(f"Dropdown keys: {list(dd.keys())}")

        if "cities" in dd:
            states = list(dd["cities"].keys())
            print(f"States ({len(states)}): {states}")
            for st in states[:2]:
                print(f"  {st} cities: {dd['cities'][st]}")

        if "stations" in dd:
            sample_keys = list(dd["stations"].keys())[:5]
            print(f"Station lookup keys (first 5): {sample_keys}")
            for k in sample_keys[:2]:
                stations = dd["stations"][k]
                print(f"  {k}: {len(stations)} stations")
                for s in stations[:2]:
                    print(f"    {json.dumps(s, ensure_ascii=False)}")

    # Count total stations
    total = 0
    if "dropdown" in data and "stations" in data["dropdown"]:
        for city_key, st_list in data["dropdown"]["stations"].items():
            total += len(st_list)
    print(f"\nTotal station entries: {total}")


if __name__ == "__main__":
    main()
