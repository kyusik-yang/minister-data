"""Fetch the National Assembly open API tables on historical members, terms 15-22.

Endpoints (codes taken from the official API spec sheets saved in sources/api/specs/):
  nfzegpkvaclgtscxt  역대 국회의원 의원이력 (former members, FRTO_DATE = activity period)
  nexgtxtmaamffofof  국회의원 의원이력 (sitting members, all of their terms)
  npffdutiapkzbfyvr  역대 국회의원 인적사항 (per term: party, district, election type, birth)
  nprlapfmaufmqytet  역대 국회의원 현황 (헌정회 data: career text, death date)
  nokivirranikoinnk  역대 국회 선거일, 의원정수, 임기정보

The API key is read from ASSEMBLY_API_KEY and never written to disk. Raw JSON pages are
saved under sources/api/<endpoint>/ with a manifest of request times (UTC).
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


def fetch_all(ep, extra, tag, key):
    out = ROOT / ep
    out.mkdir(parents=True, exist_ok=True)
    page, got, log = 1, 0, []
    while True:
        params = {"KEY": key, "Type": "json", "pIndex": page, "pSize": 1000, **extra}
        r = httpx.get(BASE + ep, params=params, headers={"User-Agent": UA}, timeout=90)
        r.raise_for_status()
        d = r.json()
        if ep not in d:
            log.append({"page": page, "fetched_utc": now(), "note": r.text[:200]})
            break
        head = d[ep][0]["head"]
        total = head[0]["list_total_count"]
        rows = d[ep][1]["row"]
        got += len(rows)
        (out / f"{tag}_p{page:02d}.json").write_text(r.text, encoding="utf-8")
        log.append({"page": page, "rows": len(rows), "total": total, "fetched_utc": now()})
        print(ep, tag, page, got, total)
        if got >= total:
            break
        page += 1
        time.sleep(0.6)
    return {"endpoint": BASE + ep, "params": {k: v for k, v in extra.items()}, "tag": tag, "pages": log}


def main():
    key = os.environ.get("ASSEMBLY_API_KEY")
    if not key:
        sys.exit("ASSEMBLY_API_KEY not set")
    manifest = []
    for t in range(15, 23):
        manifest.append(fetch_all("nfzegpkvaclgtscxt", {"PROFILE_UNIT_CD": f"1000{t}"}, f"t{t}", key))
        time.sleep(0.6)
        manifest.append(fetch_all("npffdutiapkzbfyvr", {"UNIT_CD": f"1000{t}"}, f"t{t}", key))
        time.sleep(0.6)
        manifest.append(fetch_all("nprlapfmaufmqytet", {"DAESU": str(t)}, f"t{t}", key))
        time.sleep(0.6)
    manifest.append(fetch_all("nexgtxtmaamffofof", {}, "all", key))
    manifest.append(fetch_all("nokivirranikoinnk", {}, "all", key))
    (ROOT / "history_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
