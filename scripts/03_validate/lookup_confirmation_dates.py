"""
lookup_confirmation_dates.py

Queries Pharos API (record.assembly.go.kr) to find 인사청문 meeting dates
for the 11 minister_panel entries where confirmation_hearing=True but
confirmation_date is NaN.

Searches both record2 (상임위원회) and record3 (특별위원회) by minister name,
filtering for meetings with '인사청문' in the committee or item name.
"""

import requests
import time
import json
from typing import Optional

PHAROS_URL = "https://record.assembly.go.kr/assembly/mnts/search/search.do"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DualOfficeResearch/2.0; Academic)",
    "Referer":    "https://record.assembly.go.kr/",
}
TH_MAP = {16: 18, 17: 19, 18: 20, 19: 21, 20: 22, 21: 23, 22: 24}

# 11 targets: (name, ministry, admin, assembly_num, approximate_start_date)
TARGETS = [
    ("김진표",  "교육인적자원부",    "노무현", 17, "2005-01-28"),
    ("전재희",  "보건복지부",       "이명박", 18, "2008-08-06"),
    ("임태희",  "고용노동부",       "이명박", 18, "2009-09-30"),
    ("최경환",  "지식경제부",       "이명박", 18, "2009-09-19"),
    ("진수희",  "보건복지부",       "이명박", 18, "2010-08-30"),
    ("유정복",  "농림수산식품부",    "이명박", 18, "2010-08-30"),
    ("정병국",  "문화체육관광부",    "이명박", 18, "2011-01-27"),
    ("이주영",  "해양수산부",       "박근혜", 19, "2014-03-06"),
    ("강은희",  "여성가족부",       "박근혜", 19, "2016-01-13"),
    ("권칠승",  "중소벤처기업부",    "문재인", 21, "2021-02-05"),
    ("전재수",  "해양수산부",       "이재명", 22, "2025-07-24"),
]


def pharos_search(session, name, assembly_num, collection):
    """Search Pharos by minister name for a given assembly + collection."""
    th = TH_MAP.get(assembly_num)
    if th is None:
        return []

    results = []
    seen = set()

    for start in range(1, 500, 10):
        body = {
            "S_TH":       str(th),
            "E_TH":       str(th),
            "collection": collection,
            "schword":    name,
            "startCount": str(start),
        }
        try:
            r = session.post(PHAROS_URL, data=body, timeout=30)
            r.raise_for_status()
            data = r.json().get(collection, {})
        except Exception as e:
            print(f"  ERROR: {e}")
            break

        total = int(data.get("totalCount", 0) or 0)
        items = data.get("resultList", [])
        if not items:
            break

        for item in items:
            mnts_id  = item.get("MNTS_ID", "")
            item_nm  = item.get("ITEM_NM", "")
            cmit_nm  = item.get("CMIT_NM", "")
            date_str = (item.get("DATE", "") or "")[:8]
            spk      = item.get("SPK_CNTS", "") or ""

            is_hearing = (
                "인사청문" in item_nm
                or "인사청문" in cmit_nm
                or "인사청문" in spk
            )

            if is_hearing and mnts_id not in seen:
                seen.add(mnts_id)
                results.append({
                    "mnts_id":  mnts_id,
                    "date":     date_str,
                    "item_nm":  item_nm,
                    "cmit_nm":  cmit_nm,
                    "collection": collection,
                })

        if len(results) >= total or start + 10 > total + 10:
            break
        time.sleep(0.3)

    return results


def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("=" * 70)
    print("Searching Pharos API for confirmation_date (11 NaN entries)")
    print("=" * 70)

    all_results = {}

    for name, ministry, admin, assembly, start_date in TARGETS:
        print(f"\n[{admin}] {ministry} - {name}  (start: {start_date}, {assembly}대)")

        found = []
        for coll in ["record3", "record2"]:
            hits = pharos_search(session, name, assembly, coll)
            if hits:
                print(f"  {coll}: {len(hits)} hearing meetings found")
                for h in hits:
                    fmt_date = h['date']
                    if len(fmt_date) == 8:
                        fmt_date = f"{fmt_date[:4]}-{fmt_date[4:6]}-{fmt_date[6:]}"
                    print(f"    {fmt_date}  [{h['cmit_nm']}]  {h['item_nm'][:60]}")
                found.extend(hits)
            else:
                print(f"  {coll}: no results")
            time.sleep(0.5)

        all_results[f"{admin}|{ministry}|{name}"] = found

    print("\n" + "=" * 70)
    print("SUMMARY — best candidate dates:")
    print("=" * 70)
    for (name, ministry, admin, assembly, start_date) in TARGETS:
        key = f"{admin}|{ministry}|{name}"
        hits = all_results.get(key, [])
        dates = sorted(set(h["date"] for h in hits if h["date"]))
        if dates:
            # Pick the date closest to (but before) start_date
            start_compact = start_date.replace("-", "")
            candidates = [d for d in dates if d <= start_compact]
            best = max(candidates) if candidates else min(dates)
            fmt = f"{best[:4]}-{best[4:6]}-{best[6:]}" if len(best) == 8 else best
            print(f"  {admin} {ministry} {name}: {fmt}  (all: {[f'{d[:4]}-{d[4:6]}-{d[6:]}' for d in dates]})")
        else:
            print(f"  {admin} {ministry} {name}: NOT FOUND in Pharos")


if __name__ == "__main__":
    main()
