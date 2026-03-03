"""
apply_corrections_v6.py

Fixes 24 pre-2005 entries where confirmation_hearing was incorrectly set to TRUE.

Context:
- 장관급 인사청문 의무화: 2005-07-28 (17대 국회법 개정)
- Before that, only 국무총리 had mandatory confirmation hearings
- 노무현 초기 장관들 (2003-2005-07-27) were NOT subject to confirmation hearings
- The build_comprehensive_panel_v2.py script defaulted to confirmation_hearing=TRUE
  for all entries and used start date as placeholder for confirmation_date

Corrections:
- 24 entries: confirmation_hearing TRUE->FALSE, confirmation_date cleared to ""
- All are 노무현 government ministers, 2003-02-27 to 2005-06-20

Note: 김진표 (교육인적자원부, 2005-01-28) was already fixed in v5.
      This v6 fixes the remaining 24 including 김진표 재정경제부 (2003-02-27).
"""

import pandas as pd
import os

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_IN  = os.path.join(BASE, "data", "minister_panel_comprehensive.csv")
CSV_OUT = os.path.join(BASE, "data", "minister_panel_comprehensive.csv")

df = pd.read_csv(CSV_IN, encoding="utf-8-sig", dtype=str)
df = df.fillna("")

changed = []

# All entries: confirmation_hearing=TRUE, not PM, confirmation_date < 2005-07-28
mask = (
    (df["confirmation_hearing"].str.upper() == "TRUE")
    & (df["ministry"] != "국무총리")
    & (df["confirmation_date"] < "2005-07-28")
    & (df["confirmation_date"] != "")
)
count = mask.sum()
print(f"Rows matching pre-2005 TRUE mask: {count}")

for idx in df[mask].index:
    row = df.loc[idx]
    changed.append({
        "name":     row["name"],
        "ministry": row["ministry"],
        "admin":    row["admin"],
        "old_hearing":  row["confirmation_hearing"],
        "old_date":     row["confirmation_date"],
    })
    df.loc[idx, "confirmation_hearing"] = "FALSE"
    df.loc[idx, "confirmation_date"]    = ""
    # Update notes
    old_notes = str(df.loc[idx, "notes"]) if pd.notna(df.loc[idx, "notes"]) else ""
    df.loc[idx, "notes"] = (old_notes + "; " if old_notes else "") + \
        "confirmation_hearing CORRECTION TRUE→FALSE: 2005-07-28 이전 임명 (국무위원 인사청문 의무화 이전); confirmation_date cleared"

print(f"\nTotal corrections applied: {len(changed)}")
for r in changed:
    print(f"  [{r['admin']}] {r['ministry']} | {r['name']}: "
          f"hearing {r['old_hearing']}→FALSE, date '{r['old_date']}'→''")

# Final counts
hearing_true = (df["confirmation_hearing"].str.upper() == "TRUE").sum()
hearing_false = (df["confirmation_hearing"].str.upper() == "FALSE").sum()

def to_bool(v):
    return str(v).strip().lower() in ("true", "1", "yes")
dual_true = df["dual_office"].apply(to_bool).sum()

print(f"\nFinal counts:")
print(f"  Total entries:            {len(df)}")
print(f"  dual_office=TRUE:         {dual_true}")
print(f"  dual_office=FALSE:        {len(df) - dual_true}")
print(f"  confirmation_hearing=TRUE:  {hearing_true}")
print(f"  confirmation_hearing=FALSE: {hearing_false}")

df.to_csv(CSV_OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved to {CSV_OUT}")
