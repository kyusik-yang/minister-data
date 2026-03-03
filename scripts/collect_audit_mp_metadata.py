"""
Collect MP metadata for national audit (국정감사) dyad questioners.
Uses ALLNAMEMBER (역대국회의원인명록) API to get historical party affiliations.

Output:
  data/raw/audit_mp_metadata.csv  -- lookup table: (name, assembly) -> party, sex, elect_type
  data/processed/minister_audit_dyads_with_meta.csv -- merged dyads
"""

import csv
import json
import time
import warnings
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import requests
import pandas as pd

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent.parent
DYADS_FILE = BASE_DIR / "data" / "processed" / "minister_audit_dyads.csv"
META_OUT = BASE_DIR / "data" / "raw" / "audit_mp_metadata.csv"
DYADS_OUT = BASE_DIR / "data" / "processed" / "minister_audit_dyads_with_meta.csv"

API_URL = "https://open.assembly.go.kr/portal/openapi/ALLNAMEMBER"

# Map audit year -> assembly ordinal (based on Korean electoral calendar)
# 17th: 2004.05-2008.05 (국감 2004-2006)
# 20th: 2016.06-2020.05 (국감 2016-2019)
# 21st: 2020.06-2024.05 (국감 2020-2023)
# 22nd: 2024.06-2028.05 (국감 2024-2025)
YEAR_TO_ASSEMBLY = {
    2004: 17, 2005: 17, 2006: 17,
    2016: 20, 2017: 20, 2018: 20, 2019: 20,
    2020: 21, 2021: 21, 2022: 21, 2023: 21,
    2024: 22, 2025: 22,
}

ASSEMBLY_KR = {
    17: "제17대", 20: "제20대", 21: "제21대", 22: "제22대",
}


def parse_assembly_list(raw: str) -> list[str]:
    """Parse 'GTELT_ERACO' field like '제16대, 제17대, 제20대' into list."""
    if not raw:
        return []
    return [x.strip() for x in raw.split(",")]


def parse_multi_value(raw: str, n_terms: int) -> list[str]:
    """
    Parse slash-separated multi-value field like 'party_a/party_b/party_c'.
    If count mismatches n_terms, return last value repeated.
    """
    if not raw:
        return [""] * n_terms
    parts = [x.strip() for x in raw.split("/")]
    if len(parts) == n_terms:
        return parts
    if len(parts) == 1:
        return parts * n_terms
    # Mismatch: return as-is with padding
    if len(parts) < n_terms:
        parts = parts + [parts[-1]] * (n_terms - len(parts))
    return parts[:n_terms]


def get_party_for_assembly(record: dict, target_assembly: int) -> str:
    """Extract party name for a given assembly from ALLNAMEMBER record."""
    assemblies = parse_assembly_list(record.get("GTELT_ERACO", ""))
    if not assemblies:
        return record.get("PLPT_NM", "") or ""

    target_kr = ASSEMBLY_KR.get(target_assembly, f"제{target_assembly}대")
    n = len(assemblies)
    parties = parse_multi_value(record.get("PLPT_NM", ""), n)
    elect_types = parse_multi_value(record.get("ELECD_DIV_NM", ""), n)

    for i, asm in enumerate(assemblies):
        if asm == target_kr:
            return parties[i] if i < len(parties) else (parties[-1] if parties else "")

    return ""


def get_elect_type_for_assembly(record: dict, target_assembly: int) -> str:
    """Extract elect_type for a given assembly from ALLNAMEMBER record."""
    assemblies = parse_assembly_list(record.get("GTELT_ERACO", ""))
    if not assemblies:
        return record.get("ELECD_DIV_NM", "") or ""

    target_kr = ASSEMBLY_KR.get(target_assembly, f"제{target_assembly}대")
    n = len(assemblies)
    elect_types = parse_multi_value(record.get("ELECD_DIV_NM", ""), n)

    for i, asm in enumerate(assemblies):
        if asm == target_kr:
            return elect_types[i] if i < len(elect_types) else ""

    return ""


def lookup_member(name: str) -> list[dict]:
    """Query ALLNAMEMBER API by name. Returns all matching records."""
    params = {
        "Type": "json",
        "KEY": "",
        "pIndex": 1,
        "pSize": 10,
        "NAAS_NM": name,
    }
    try:
        resp = requests.get(API_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        body = data.get("ALLNAMEMBER", [])
        if len(body) < 2:
            return []
        return body[1].get("row", [])
    except Exception as e:
        print(f"  ERROR {name}: {e}", file=sys.stderr)
        return []


def main():
    df = pd.read_csv(DYADS_FILE)
    print(f"Loaded {len(df)} audit dyads from {DYADS_FILE.name}")

    # Add assembly column
    df["assembly"] = df["year"].map(YEAR_TO_ASSEMBLY)
    missing_assembly = df["assembly"].isna().sum()
    if missing_assembly:
        print(f"  WARNING: {missing_assembly} dyads have unknown assembly (year not in YEAR_TO_ASSEMBLY)")

    # Build unique (name, assembly) pairs to look up
    pairs = df[["q_speaker", "assembly"]].dropna().drop_duplicates()
    print(f"Unique (speaker, assembly) pairs: {len(pairs)}")

    # Build lookup: name -> list of API records
    unique_names = sorted(pairs["q_speaker"].unique())
    print(f"Unique speaker names: {len(unique_names)}")

    name_to_records: dict[str, list[dict]] = {}
    not_found: list[str] = []

    # Parallel API calls with 6 workers
    def fetch_one(name: str) -> tuple[str, list[dict]]:
        return name, lookup_member(name)

    done = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch_one, n): n for n in unique_names}
        for future in as_completed(futures):
            name, records = future.result()
            name_to_records[name] = records
            if not records:
                not_found.append(name)
            done += 1
            if done % 100 == 0:
                print(f"  [{done}/{len(unique_names)}] progress...", flush=True)

    print(f"\nFound: {len(unique_names) - len(not_found)}, Not found: {len(not_found)}", flush=True)
    if not_found[:20]:
        print(f"  Not found (first 20): {not_found[:20]}")

    # Build (name, assembly) -> metadata lookup
    meta_rows = []
    for _, row in pairs.iterrows():
        name = row["q_speaker"]
        asm = int(row["assembly"])
        records = name_to_records.get(name, [])

        if not records:
            meta_rows.append({
                "q_speaker": name,
                "assembly": asm,
                "q_party": "",
                "q_sex": "",
                "q_elect_type": "",
                "q_birth": "",
                "q_term_count": "",
                "q_mona_cd": "",
            })
            continue

        # Find record that includes this assembly
        target_kr = ASSEMBLY_KR.get(asm, f"제{asm}대")
        matched = None
        for rec in records:
            assemblies = parse_assembly_list(rec.get("GTELT_ERACO", ""))
            if target_kr in assemblies:
                matched = rec
                break

        # Fallback: use first record if only one result
        if matched is None and len(records) == 1:
            matched = records[0]

        if matched is None:
            meta_rows.append({
                "q_speaker": name,
                "assembly": asm,
                "q_party": "",
                "q_sex": "",
                "q_elect_type": "",
                "q_birth": "",
                "q_term_count": "",
                "q_mona_cd": "",
            })
            continue

        party = get_party_for_assembly(matched, asm)
        elect_type = get_elect_type_for_assembly(matched, asm)

        meta_rows.append({
            "q_speaker": name,
            "assembly": asm,
            "q_party": party,
            "q_sex": matched.get("NTR_DIV", "") or "",
            "q_elect_type": elect_type,
            "q_birth": matched.get("BIRDY_DT", "") or "",
            "q_term_count": matched.get("RLCT_DIV_NM", "") or "",
            "q_mona_cd": matched.get("NAAS_CD", "") or "",
        })

    meta_df = pd.DataFrame(meta_rows)
    META_OUT.parent.mkdir(parents=True, exist_ok=True)
    meta_df.to_csv(META_OUT, index=False, encoding="utf-8")
    print(f"\nSaved metadata: {len(meta_df)} (name, assembly) pairs to {META_OUT.name}")

    # Party coverage
    filled = (meta_df["q_party"] != "").sum()
    print(f"Party filled: {filled}/{len(meta_df)} ({100*filled/len(meta_df):.1f}%)")

    # Merge into dyads
    df_merged = df.merge(
        meta_df[["q_speaker", "assembly", "q_party", "q_sex", "q_elect_type", "q_birth", "q_term_count", "q_mona_cd"]],
        on=["q_speaker", "assembly"],
        how="left",
    )

    # Print party coverage stats
    party_filled = (df_merged["q_party"].notna() & (df_merged["q_party"] != "")).sum()
    print(f"Dyad party coverage: {party_filled}/{len(df_merged)} ({100*party_filled/len(df_merged):.1f}%)")

    # Party distribution
    print("\nTop parties in audit dyads:")
    print(df_merged["q_party"].value_counts().head(15))

    df_merged.to_csv(DYADS_OUT, index=False, encoding="utf-8")
    print(f"\nSaved merged dyads ({len(df_merged)} rows) to {DYADS_OUT.name}")

    # Summary by year
    print("\nParty coverage by year:")
    for yr in sorted(df_merged["year"].unique()):
        sub = df_merged[df_merged["year"] == yr]
        filled_yr = (sub["q_party"].notna() & (sub["q_party"] != "")).sum()
        print(f"  {yr}: {filled_yr}/{len(sub)} ({100*filled_yr/len(sub):.0f}%)")


if __name__ == "__main__":
    main()
