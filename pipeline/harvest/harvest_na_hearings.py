"""Harvest the National Assembly open API table 인사청문회 (endpoint nrvsawtaauyihadij).

One row per 인사청문요청안 / 임명동의안 with candidate, post, dates and plenary result.
The key is read from ASSEMBLY_API_KEY and never written to disk.
Raw JSON pages are saved under na_hearing_api/ with a manifest of request times (UTC).
"""
import json, os, subprocess, time
from pathlib import Path
import httpx
import pandas as pd

EP = "nrvsawtaauyihadij"
BASE = "https://open.assembly.go.kr/portal/openapi/" + EP
UA = "kyusik-research/0.1 (kyusik.yang@nyu.edu)"
OUT = Path(__file__).resolve().parent / "na_hearing_api"

def now():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip()

def main():
    key = os.environ["ASSEMBLY_API_KEY"]
    rows, manifest = [], []
    for age in range(15, 23):
        page = 1
        while True:
            params = {"KEY": key, "Type": "json", "pIndex": page, "pSize": 1000, "AGE": str(age)}
            r = httpx.get(BASE, params=params, headers={"User-Agent": UA}, timeout=90)
            r.raise_for_status()
            d = r.json()
            ts = now()
            if EP not in d:
                manifest.append({"age": age, "page": page, "fetched_utc": ts, "note": r.text[:200]})
                break
            head = d[EP][0]["head"]; total = head[0]["list_total_count"]
            got = d[EP][1]["row"]
            (OUT / f"age{age}_p{page:02d}.json").write_text(r.text, encoding="utf-8")
            manifest.append({"age": age, "page": page, "rows": len(got), "total": total, "fetched_utc": ts})
            for g in got:
                g["_fetched_utc"] = ts
            rows += got
            if page * 1000 >= total:
                break
            page += 1
            time.sleep(0.6)
        time.sleep(0.6)
    (OUT / "manifest.json").write_text(json.dumps({"endpoint": BASE, "params": "Type=json&pSize=1000&AGE=N (KEY omitted)", "pages": manifest}, ensure_ascii=False, indent=1), encoding="utf-8")
    df = pd.DataFrame(rows)
    df.to_csv(Path(__file__).resolve().parent / "na_hearing_requests_15_22.csv", index=False)
    print(df.shape); print(df.AGE.value_counts().sort_index().to_string())

if __name__ == "__main__":
    main()
