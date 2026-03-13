"""Test the CPCB file_Path and download_file API endpoints."""
import json
import base64
import httpx

BASE = "https://airquality.cpcb.gov.in/dataRepository"
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "q=0.8;application/json;q=0.9",
    "Referer": "https://airquality.cpcb.gov.in/ccr/",
}

def post_b64(endpoint, payload_dict):
    """POST base64-encoded JSON body, decode base64 JSON response."""
    body = base64.b64encode(json.dumps(payload_dict).encode()).decode()
    r = httpx.post(f"{BASE}/{endpoint}", content=body, headers=HEADERS, timeout=30)
    try:
        decoded = base64.b64decode(r.text).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return {"_raw": r.text[:500], "_status": r.status_code}


def main():
    # Test 1: file_Path with daily + cityLevel (simplest: no station needed)
    payload1 = {
        "station_id": "",
        "station_name": "",
        "state": "Chhattisgarh",
        "city": "Raipur",
        "year": "",
        "frequency": "daily",
        "dataType": "cityLevel",
    }
    print("=== Test 1: daily cityLevel (Chhattisgarh/Raipur) ===")
    result1 = post_b64("file_Path", payload1)
    print(json.dumps(result1, indent=2, ensure_ascii=False)[:2000])

    # Test 2: file_Path with hourly + stationLevel
    payload2 = {
        "station_id": "site_5985",
        "station_name": "Evelyn Lodge, Asansol - WBPCB",
        "state": "West Bengal",
        "city": "Asansol",
        "year": "2024",
        "frequency": "hourly",
        "dataType": "stationLevel",
    }
    print("\n=== Test 2: hourly stationLevel (Asansol, 2024) ===")
    result2 = post_b64("file_Path", payload2)
    print(json.dumps(result2, indent=2, ensure_ascii=False)[:2000])

    # Test 3: Try downloading a file if we get a path
    paths = []
    for result in [result1, result2]:
        if isinstance(result, dict) and "data" in result:
            for item in result["data"]:
                if "filepath" in item:
                    paths.append(item["filepath"])

    if paths:
        print(f"\n=== Test 3: download_file with path: {paths[0]} ===")
        download_url = f"{BASE}/download_file?file_name={paths[0]}"
        print(f"URL: {download_url}")
        r = httpx.get(download_url, headers=HEADERS, timeout=30, follow_redirects=True)
        print(f"Status: {r.status_code}")
        print(f"Content-Type: {r.headers.get('content-type')}")
        print(f"Content-Length: {len(r.content)}")
        print(f"First 200 bytes (repr): {repr(r.content[:200])}")
    else:
        print("\n=== No file paths returned to test download ===")
        print("Results 1 keys:", list(result1.keys()) if isinstance(result1, dict) else "not dict")
        print("Results 2 keys:", list(result2.keys()) if isinstance(result2, dict) else "not dict")


if __name__ == "__main__":
    main()
