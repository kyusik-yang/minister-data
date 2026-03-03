"""
Collect MP metadata from 열린국회정보 API (nwvrqwxyaytdsfvhu).
Strategy: individual name lookup for each unique questioner in dyads.
Output: data/raw/mp_metadata.csv
"""

import requests
import csv
import time
import sys
import json
import pandas as pd
from pathlib import Path

OUTFILE = Path(__file__).parent.parent / "data" / "raw" / "mp_metadata.csv"
DYADS_FILE = Path(__file__).parent.parent / "data" / "processed" / "minister_dyads.csv"

API_URL = "https://open.assembly.go.kr/portal/openapi/nwvrqwxyaytdsfvhu"

FIELDS = [
    "name_kr", "name_hj", "name_en",
    "birth", "sex", "party", "district",
    "elect_type", "term_count", "committee",
    "units_raw", "mona_cd",
]

API_KEY_MAP = {
    "HG_NM": "name_kr",
    "HJ_NM": "name_hj",
    "ENG_NM": "name_en",
    "BTH_DATE": "birth",
    "SEX_GBN_NM": "sex",
    "POLY_NM": "party",
    "ORIG_NM": "district",
    "ELECT_GBN_NM": "elect_type",
    "REELE_GBN_NM": "term_count",
    "CMIT_NM": "committee",
    "UNITS": "units_raw",
    "MONA_CD": "mona_cd",
}


def lookup_name(name: str) -> list[dict]:
    """Look up an MP by name. Returns list of matching records."""
    params = {
        "Type": "json",
        "KEY": "",
        "pIndex": 1,
        "pSize": 5,
        "HG_NM": name,
    }
    try:
        resp = requests.get(API_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        body = data.get("nwvrqwxyaytdsfvhu")
        if not body or len(body) < 2:
            return []
        rows = body[1].get("row", [])
        result = []
        for item in rows:
            rec = {}
            for api_key, col in API_KEY_MAP.items():
                rec[col] = item.get(api_key, "")
            result.append(rec)
        return result
    except Exception as e:
        print(f"  ERROR looking up {name}: {e}", file=sys.stderr)
        return []


def main():
    # Get all unique questioner names from dyads
    df = pd.read_csv(DYADS_FILE)
    unique_names = sorted(df["q_speaker"].dropna().unique())
    print(f"Unique questioners to look up: {len(unique_names)}")

    found = []
    not_found = []

    for i, name in enumerate(unique_names):
        records = lookup_name(name)
        if records:
            # If multiple matches, take all (e.g., two MPs with same name)
            for rec in records:
                found.append(rec)
            if i % 50 == 0:
                print(f"  [{i}/{len(unique_names)}] {name}: {len(records)} result(s)")
        else:
            not_found.append(name)
            if i % 50 == 0:
                print(f"  [{i}/{len(unique_names)}] {name}: NOT FOUND")
        time.sleep(0.15)

    print(f"\nFound:     {len(found)} records for {len(unique_names) - len(not_found)} names")
    print(f"Not found: {len(not_found)} names")
    if not_found:
        print("  Not found:", not_found[:20])
        if len(not_found) > 20:
            print(f"  ... and {len(not_found)-20} more")

    # Deduplicate by mona_cd (official MP ID)
    seen_mona = {}
    deduped = []
    for rec in found:
        mona = rec.get("mona_cd", "")
        if mona and mona in seen_mona:
            continue
        if mona:
            seen_mona[mona] = True
        deduped.append(rec)

    print(f"After dedup: {len(deduped)} unique MPs")

    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTFILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"Saved to {OUTFILE}")

    # Save not-found list for reference
    not_found_file = OUTFILE.parent / "mp_metadata_not_found.txt"
    with open(not_found_file, "w", encoding="utf-8") as f:
        f.write("\n".join(not_found))
    print(f"Not-found list saved to {not_found_file}")


if __name__ == "__main__":
    main()
