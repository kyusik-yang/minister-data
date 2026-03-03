"""
Merge MP metadata into minister_dyads.csv.
Matches q_speaker (hangul or hanja) to name_kr or name_hj in mp_metadata.
Adds columns: q_party, q_sex, q_birth, q_elect_type, q_term_count, q_units
Output: data/processed/minister_dyads_with_meta.csv
"""

import pandas as pd
from pathlib import Path

DYADS_FILE = Path("data/processed/minister_dyads.csv")
META_FILE = Path("data/raw/mp_metadata.csv")
OUTFILE = Path("data/processed/minister_dyads_with_meta.csv")


def main():
    dyads = pd.read_csv(DYADS_FILE)
    meta = pd.read_csv(META_FILE)

    print(f"Dyads: {len(dyads)} rows")
    print(f"Meta: {len(meta)} unique MPs")

    # Build lookup dict: name -> metadata record
    # Key: (name_kr, name_hj) both map to same record
    lookup = {}
    for _, row in meta.iterrows():
        name_kr = str(row["name_kr"]).strip()
        name_hj = str(row["name_hj"]).strip()
        rec = {
            "q_party": row.get("party", ""),
            "q_sex": row.get("sex", ""),
            "q_birth": row.get("birth", ""),
            "q_elect_type": row.get("elect_type", ""),
            "q_term_count": row.get("term_count", ""),
            "q_units": row.get("units_raw", ""),
            "q_mona_cd": row.get("mona_cd", ""),
        }
        if name_kr and name_kr != "nan":
            lookup[name_kr] = rec
        if name_hj and name_hj != "nan":
            lookup[name_hj] = rec

    # Merge
    merged_cols = ["q_party", "q_sex", "q_birth", "q_elect_type", "q_term_count", "q_units", "q_mona_cd"]
    for col in merged_cols:
        dyads[col] = None

    matched = 0
    for idx, row in dyads.iterrows():
        name = str(row["q_speaker"]).strip() if pd.notna(row["q_speaker"]) else ""
        if name in lookup:
            for col, val in lookup[name].items():
                dyads.at[idx, col] = val
            matched += 1

    print(f"\nMatched {matched}/{len(dyads)} dyads ({100*matched/len(dyads):.1f}%)")

    # Coverage by assembly
    for asm in sorted(dyads["assembly"].unique()):
        sub = dyads[dyads["assembly"] == asm]
        n_matched = sub["q_party"].notna().sum()
        print(f"  {asm}대: {n_matched}/{len(sub)} ({100*n_matched/len(sub):.0f}%)")

    # Party distribution for matched
    print("\nTop questioner parties (all assemblies):")
    print(dyads["q_party"].value_counts().head(10))

    # Save
    dyads.to_csv(OUTFILE, index=False, encoding="utf-8")
    print(f"\nSaved to {OUTFILE}")
    print(f"Columns: {list(dyads.columns)}")


if __name__ == "__main__":
    main()
