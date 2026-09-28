"""
apply_corrections_v3.py

Applies third batch of verified corrections to minister_panel_comprehensive.csv
based on full systematic verification of all 285 entries (2026-03-01, session 3).

FALSE NEGATIVES found and corrected (3 total):
- 유일호 (박근혜 국토교통부): FALSE -> TRUE (19대 의원, 서울 송파구 을; start date also corrected)
- 유일호 (박근혜 기획재정부): FALSE -> TRUE (19대 의원, 서울 송파구 을)
- 신원식 (윤석열 국방부): already corrected by verification agent; confirmed TRUE

Date corrections (no dual_office change):
- 맹형규 (이명박 행정안전부): start 2010-08-10 -> 2010-04-15 (Wikipedia: 2010년 4월 15일 임명)
- 유인촌 (윤석열 문화체육관광부): start 2023-09-22 -> 2023-10-07 (actual appointment)

All 226 FALSE entries verified (노무현 71건, 이명박 42건, 박근혜 37건, 문재인 36건,
윤석열 26건, 이재명 12건, 김대중 2건).
No other FALSE NEGATIVES found.
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
# FALSE NEGATIVE corrections (dual_office FALSE -> TRUE)
# ===========================================================================

# 유일호 (박근혜 국토교통부): was 19대 서울 송파구 을 MP (2012-05-30~2016-05-29)
# Appointed 국토부 장관 2015-03-16 (NOT 2014-07-16 as in dataset)
# - 서승환 was 국토부 장관 2013-03-11~2015-03-13; 유일호 succeeded him 2015-03-16
# - At appointment (2015-03-16), still a sitting 19대 MP -> dual_office=TRUE
df = fix(df, "유일호", "국토교통부", "박근혜",
    dual_office=True,
    start="2015-03-16",
    end="2016-01-13",
    mp_party_at_appt="새누리당",
    mp_district="서울 송파구 을",
    assembly_num_at_appt=19.0,
    notes="겸직 장관 (19대 의원 서울 송파구 을); start MAJOR CORRECTION 2014-07-16→2015-03-16 (서승환 후임, 서승환은 2013-03-11~2015-03-13); dual_office FALSE NEGATIVE 수정 (TRUE); end→2016-01-13 (기재부 이동)")

# 유일호 (박근혜 기획재정부): same person, was 19대 MP on 2016-01-13
# 19대 ended 2016-05-29; appointed 2016-01-13 -> still sitting MP
df = fix(df, "유일호", "기획재정부", "박근혜",
    dual_office=True,
    mp_party_at_appt="새누리당",
    mp_district="서울 송파구 을",
    assembly_num_at_appt=19.0,
    notes="겸직 장관 (19대 의원 서울 송파구 을; 19대 임기 2012-05-30~2016-05-29); dual_office FALSE NEGATIVE 수정 (TRUE); 2016-01-13 임명 당시 현직 19대 의원 신분")


# ===========================================================================
# Date corrections (dual_office not changed)
# ===========================================================================

# 맹형규 (이명박 행정안전부): start date wrong in dataset
# Wikipedia: 맹형규 제3대 행안부 장관 임명 2010년 4월 15일 (not 2010-08-10)
# Note: He was NOT a sitting MP (didn't get 18대 party nomination) -> stays FALSE
df = fix(df, "맹형규", "행정안전부", "이명박",
    start="2010-04-15",
    notes="비겸직 (17대 서울 송파구 갑; 18대 공천 배제 낙마; 청와대 정무수석 2008-2009); start CORRECTION 2010-08-10→2010-04-15 (Wikipedia: 2010년 4월 15일 제3대 행안부 장관 임명)")

# 유인촌 (윤석열 문화체육관광부): start date wrong
# The 2023-09-22 cabinet reshuffle date was the announcement; actual appointment 2023-10-07
df = fix(df, "유인촌", "문화체육관광부", "윤석열",
    start="2023-10-07",
    notes="비겸직 (연예인/전직 장관 출신; 국회의원 아님); start CORRECTION 2023-09-22→2023-10-07 (실제 임명일; 신원식 동일일자)")


# ===========================================================================
# Print summary
# ===========================================================================

print(f"\nTotal corrections applied: {len(changed_rows)}")

dual_changes = [r for r in changed_rows if r["field"] == "dual_office"]
print(f"\ndual_office changes: {len(dual_changes)}")
for r in dual_changes:
    print(f"  {r['admin']} | {r['ministry']} | {r['name']}: {r['old']} -> {r['new']}")

print(f"\nNew counts:")
print(f"  Total entries: {len(df)}")
print(f"  dual_office=TRUE: {df['dual_office'].sum()}")
print(f"  dual_office=FALSE: {(~df['dual_office']).sum()}")

print(f"\nAll 겸직 entries after corrections:")
for _, r in df[df["dual_office"]].iterrows():
    asm = r['assembly_num_at_appt']
    asm_str = f"{int(asm)}대" if pd.notna(asm) else "?"
    print(f"  [{r['admin']}] {r['ministry']} | {r['name']} | {r['start']} | {r['mp_district']} ({asm_str})")

df.to_csv(CSV_OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved to {CSV_OUT}")
