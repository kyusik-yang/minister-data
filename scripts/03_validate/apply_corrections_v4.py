"""
apply_corrections_v4.py

Applies fourth batch of corrections to minister_panel_comprehensive.csv
based on full verification of 62 dual_office=TRUE entries (2026-03-01, session 4).

mp_district errors found (3 total):
- 이한동 (김대중 국무총리): 충북 청주시 상당구 -> 경기 포천군·연천군
  (이한동 served 경기 포천-연천-가평 his entire career; no connection to Chungbuk)
- 최경환 (이명박 지식경제부): 대구 달성군 -> 경북 경산시·청도군
  (notes field already correctly said "18대 의원 경북 경산·청도"; data field was wrong)
  (추경호 21대 기재부 = 대구 달성군; 최경환 18대 = 경북 경산시·청도군 -- different people)
- 전재수 (이재명 해양수산부): 부산 북구·강서구 갑 -> 부산 북구 갑
  (22대 redistricting split 강서구 off; 전재수 ran in 북구 갑 alone in 22대)

No dual_office changes, no start/end date changes.
All 62 TRUE entries verified; no FALSE entries mis-coded.
"""

import pandas as pd
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_IN  = os.path.join(BASE, "data", "minister_panel_comprehensive.csv")
CSV_OUT = os.path.join(BASE, "data", "minister_panel_comprehensive.csv")

df = pd.read_csv(CSV_IN, encoding="utf-8-sig")

def to_bool(v):
    if str(v).strip().lower() in ("true", "1", "yes"): return True
    return False
df["dual_office"] = df["dual_office"].apply(to_bool)

changed_rows = []

def fix(df, name, ministry, admin, **kwargs):
    mask = (df["name"] == name) & (df["ministry"] == ministry) & (df["admin"] == admin)
    count = mask.sum()
    if count == 0:
        print(f"WARNING: No row found for {name} | {ministry} | {admin}")
        return df
    if count > 1:
        print(f"WARNING: Multiple rows ({count}) for {name} | {ministry} | {admin}")
    for col, val in kwargs.items():
        if col in df.columns:
            old = df.loc[mask, col].values[0]
            df.loc[mask, col] = val
            if str(old) != str(val):
                changed_rows.append({
                    "name": name, "ministry": ministry, "admin": admin,
                    "field": col, "old": old, "new": val
                })
    return df


# ===========================================================================
# mp_district corrections
# ===========================================================================

# 이한동 (김대중 국무총리): district completely wrong
# He represented 경기 포천군·연천군 (and 가평 in earlier terms) throughout career
# Has zero connection to 충북 청주시 상당구
df = fix(df, "이한동", "국무총리", "김대중",
    mp_district="경기 포천군·연천군",
    notes="겸직 총리 (16대 경기 포천군·연천군, 자유민주연합; 2000-05-22 임명, 16대 개원 2000-05-30 직전); mp_district CORRECTION 충북 청주시 상당구→경기 포천군·연천군")

# 최경환 (이명박 지식경제부, 18대): district wrong despite notes being correct
# Notes say "18대 의원 경북 경산·청도" but mp_district field said 대구 달성군
# 추경호 (윤석열 기재부, 21대) represents 대구 달성군 -- different person
df = fix(df, "최경환", "지식경제부", "이명박",
    mp_district="경북 경산시·청도군",
    notes="겸직 장관 (18대 의원 경북 경산시·청도군, 한나라당); mp_district CORRECTION 대구 달성군→경북 경산시·청도군 (notes field already correct; data field was wrong; 대구 달성군은 추경호 21대 기재부)")

# 전재수 (이재명 해양수산부, 22대): 22대 redistricting
# In 21대, his constituency was 부산 북구·강서구 갑
# In 22대, 강서구 was split; he ran in 부산 북구 갑 alone
df = fix(df, "전재수", "해양수산부", "이재명",
    mp_district="부산 북구 갑",
    notes="겸직 장관 (22대 의원 부산 북구 갑 3선; 21대는 북구·강서구 갑이었으나 22대 선거구 개편으로 강서구 분리); mp_district CORRECTION 부산 북구·강서구 갑→부산 북구 갑")


# ===========================================================================
# Print summary
# ===========================================================================

print(f"\nTotal corrections applied: {len(changed_rows)}")
for r in changed_rows:
    print(f"  [{r['admin']}] {r['ministry']} | {r['name']}: {r['field']}: '{r['old']}' -> '{r['new']}'")

print(f"\nFinal counts:")
print(f"  Total entries: {len(df)}")
print(f"  dual_office=TRUE: {df['dual_office'].sum()}")
print(f"  dual_office=FALSE: {(~df['dual_office']).sum()}")

df.to_csv(CSV_OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved to {CSV_OUT}")
