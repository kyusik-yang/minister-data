"""Fetch the full ALLNAMEMBER table (역대 국회의원 정보) from the National Assembly open API.

The API key is read from the ASSEMBLY_API_KEY environment variable and is never
written to disk. Each page of the raw JSON response is saved under
sources/api/allnamember/ together with a manifest recording the request time.

Usage:
    ASSEMBLY_API_KEY=... python3 scripts/01_fetch_allnamember.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

BASE = "https://open.assembly.go.kr/portal/openapi/ALLNAMEMBER"
UA = "kyusik-research/0.1 (kyusik.yang@nyu.edu)"
OUT = Path(__file__).resolve().parent.parent / "sources" / "api" / "allnamember"


def now():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip()


def fetch(page, key, size=100):
    params = {"KEY": key, "Type": "json", "pIndex": page, "pSize": size}
    r = httpx.get(BASE, params=params, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return r.text


def main():
    key = os.environ.get("ASSEMBLY_API_KEY")
    if not key:
        sys.exit("ASSEMBLY_API_KEY not set")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"endpoint": BASE, "params": "Type=json&pSize=100&pIndex=N (KEY omitted)",
                "started_utc": now(), "pages": []}
    page, total, got = 1, None, 0
    while True:
        txt = fetch(page, key)
        body = json.loads(txt)
        block = body.get("ALLNAMEMBER")
        if not block:
            print("stop, unexpected body", txt[:300])
            break
        head = block[0]["head"]
        code = head[1]["RESULT"]["CODE"]
        if code != "INFO-000":
            print("stop", code)
            break
        total = head[0]["list_total_count"]
        rows = block[1]["row"]
        got += len(rows)
        (OUT / f"page_{page:03d}.json").write_text(txt, encoding="utf-8")
        manifest["pages"].append({"page": page, "rows": len(rows), "fetched_utc": now()})
        print(page, got, total)
        if got >= total:
            break
        page += 1
        time.sleep(0.6)
    manifest["finished_utc"] = now()
    manifest["list_total_count"] = total
    manifest["rows_fetched"] = got
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
