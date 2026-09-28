"""Fetch the National Assembly open API tables on historical members for terms 12-14.

Same endpoints and parameters as 03_fetch_na_history_apis.py, restricted to terms 12, 13, 14:
  nfzegpkvaclgtscxt  역대 국회의원 의원이력 (former members, FRTO_DATE = activity period)
  npffdutiapkzbfyvr  역대 국회의원 인적사항 (per term: party, district, election type, birth)
  nprlapfmaufmqytet  역대 국회의원 현황 (헌정회 data: career text, death date)

The sitting-member table nexgtxtmaamffofof and ALLNAMEMBER are not refetched. Their saved
snapshots of 2026-09-25 (sources/api/nexgtxtmaamffofof/, sources/api/allnamember/) already
cover every term, so the 12-14 rows and the 15-22 rows rest on the same pull.

Raw pages go to sources/api/term<N>/<endpoint>_p<page>.json with sources/api/term<N>/manifest.json
(request parameters without the key, UTC request times). The key is read from ASSEMBLY_API_KEY
and never written to disk.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

BASE = "https://open.assembly.go.kr/portal/openapi/"
UA = "kyusik-research/0.1 (kyusik.yang@nyu.edu)"
ROOT = Path(__file__).resolve().parent.parent / "sources" / "api"


def now():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip()


def fetch_all(ep, extra, out, key):
    page, got, log = 1, 0, []
    while True:
        params = {"KEY": key, "Type": "json", "pIndex": page, "pSize": 1000, **extra}
        ts = now()
        r = httpx.get(BASE + ep, params=params, headers={"User-Agent": UA}, timeout=90)
        r.raise_for_status()
        d = r.json()
        if ep not in d:
            (out / f"{ep}_p{page:02d}_nodata.json").write_text(r.text, encoding="utf-8")
            log.append({"page": page, "fetched_utc": ts, "note": r.text[:200]})
            print(ep, extra, "no data", r.text[:200])
            break
        head = d[ep][0]["head"]
        total = head[0]["list_total_count"]
        rows = d[ep][1]["row"]
        got += len(rows)
        (out / f"{ep}_p{page:02d}.json").write_text(r.text, encoding="utf-8")
        log.append({"page": page, "rows": len(rows), "total": total, "fetched_utc": ts})
        print(ep, extra, page, got, total)
        if got >= total:
            break
        page += 1
        time.sleep(0.6)
    return {"endpoint": BASE + ep, "params": dict(extra), "pages": log}


def main():
    key = os.environ.get("ASSEMBLY_API_KEY")
    if not key:
        sys.exit("ASSEMBLY_API_KEY not set")
    for t in (12, 13, 14):
        out = ROOT / f"term{t}"
        out.mkdir(parents=True, exist_ok=True)
        manifest = {"term": t, "note": "KEY omitted; Type=json, pSize=1000", "started_utc": now(), "requests": []}
        manifest["requests"].append(fetch_all("nfzegpkvaclgtscxt", {"PROFILE_UNIT_CD": f"1000{t}"}, out, key))
        time.sleep(0.6)
        manifest["requests"].append(fetch_all("npffdutiapkzbfyvr", {"UNIT_CD": f"1000{t}"}, out, key))
        time.sleep(0.6)
        manifest["requests"].append(fetch_all("nprlapfmaufmqytet", {"DAESU": str(t)}, out, key))
        time.sleep(0.6)
        manifest["finished_utc"] = now()
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
