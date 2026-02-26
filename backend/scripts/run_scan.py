"""
Trigger a scan via the API.
Run: python scripts/run_scan.py [--regions us-east-1 us-west-2]
"""
import argparse
import json
import urllib.request

BASE_URL = "http://localhost:8000"


def main():
    parser = argparse.ArgumentParser(description="Trigger a cloud governance scan")
    parser.add_argument("--regions", nargs="+", default=["us-east-1", "us-west-2"])
    args = parser.parse_args()

    payload = json.dumps({"regions": args.regions}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/scans",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    print(f"✅ Scan started: {data['id']}")
    print(f"   Status: {data['status']}")
    print(f"   Regions: {data['regions']}")
    print(f"   Poll: GET {BASE_URL}/api/v1/scans/{data['id']}")


if __name__ == "__main__":
    main()
