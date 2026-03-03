"""
apply_corrections_v2.py

Applies second batch of verified corrections to minister_panel_comprehensive.csv
based on 3-agent Wikipedia verification (2026-03-01, session 2).

Agents covered:
- 박근혜 정부 겸직 entries (10 entries)
- 윤석열 정부 겸직 entries (5 entries)
- 이재명 정부 겸직 entries (8 entries)
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
# 박근혜 정부 corrections
# ===========================================================================

# 조윤선 (여성가족부): was 18대 비례 (ended 2012), NOT 19대 MP at appointment 2013-03-11
df = fix(df, "조윤선", "여성가족부", "박근혜",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt=float("nan"),
    notes="비겸직 (18대 한나라당 비례의원 2008-2012; 19대 종로구 공천 실패; 임명 당시 현직 의원 아님)")

# 조윤선 (문화체육관광부): 19대 ended 2016-05-29; appointed 2016-09-05 — NOT MP
df = fix(df, "조윤선", "문화체육관광부", "박근혜",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt=float("nan"),
    start="2016-09-05",
    notes="비겸직 (임명일 2016-09-05 당시 19대 임기 만료 2016-05-29 이후; 비의원 신분; start MAJOR CORRECTION 2015-12-01→2016-09-05)")

# 이주영 (해양수산부): district wrong + start date off by ~1 year
# 윤진숙 (2013-03-22~2013-10-28) was first 해수부 장관; 이주영 replaced her 2014-03-06
df = fix(df, "이주영", "해양수산부", "박근혜",
    mp_district="경남 창원시 마산합포구",
    start="2014-03-06",
    end="2015-03-16",
    notes="겸직 장관 (19대 의원 경남 창원시 마산합포구); district CORRECTION 의창구→마산합포구; start MAJOR CORRECTION 2013-03-22→2014-03-06 (윤진숙 후임); end updated")

# 김희정 (여성가족부): district wrong (비례→부산 연제구) + start correction
df = fix(df, "김희정", "여성가족부", "박근혜",
    mp_district="부산 연제구",
    start="2014-07-16",
    notes="겸직 장관 (19대 의원 부산 연제구 지역구); district CORRECTION 비례대표→부산 연제구; start corrected 2014-07-03→2014-07-16")

# 황우여 (교육부): start date correction (nomination vs formal appointment)
df = fix(df, "황우여", "교육부", "박근혜",
    start="2014-08-08",
    notes="겸직 장관 (19대 의원 인천 연수구); start corrected 2014-07-16→2014-08-08 (취임식일)")

# 유기준 (해양수산부): start date MAJOR CORRECTION
df = fix(df, "유기준", "해양수산부", "박근혜",
    start="2015-03-16",
    end="2015-11-11",
    notes="겸직 장관 (19대 의원 부산 서구); start MAJOR CORRECTION 2014-12-24→2015-03-16; end updated 2015-09-24→2015-11-11")

# 강은희 (여성가족부): start date MAJOR CORRECTION (off by ~9 months)
df = fix(df, "강은희", "여성가족부", "박근혜",
    start="2016-01-13",
    notes="겸직 장관 (19대 비례의원); start MAJOR CORRECTION 2015-03-12→2016-01-13 (취임식일 확인)")


# ===========================================================================
# 윤석열 정부 corrections
# ===========================================================================

# 이영 (중소벤처기업부): district wrong (대전 중구→비례대표) + start correction
# Was 21대 비례 MP (future한국당); appointed 2022-05-13, resigned MP seat 2022-05-20
# dual_office = TRUE (was still MP at appointment date)
df = fix(df, "이영", "중소벤처기업부", "윤석열",
    mp_district="비례대표",
    start="2022-05-13",
    end="2023-12-28",
    notes="겸직 장관 (21대 미래한국당 비례의원; 임명 2022-05-13, 의원직 사퇴 2022-05-20); district CORRECTION 대전 중구→비례대표; start corrected 2022-05-10→2022-05-13")

# 권영세 (통일부): start correction + end correction
df = fix(df, "권영세", "통일부", "윤석열",
    start="2022-05-16",
    end="2023-07-28",
    notes="겸직 장관 (21대 의원 서울 용산구); start corrected 2022-05-21→2022-05-16; end MAJOR CORRECTION 2023-12-21→2023-07-28 (후임 김영호 취임)")

# 추경호 (기획재정부): start correction
df = fix(df, "추경호", "기획재정부", "윤석열",
    start="2022-05-10",
    end="2023-12-29",
    notes="겸직 장관 (21대 의원 대구 달성군); start corrected 2022-05-21→2022-05-10 (윤석열 취임일 동시 임명); end corrected 2023-12-28→2023-12-29 (후임 최상목 임명)")

# 박진 (외교부): start correction + end correction
df = fix(df, "박진", "외교부", "윤석열",
    start="2022-05-12",
    end="2024-01-10",
    notes="겸직 장관 (21대 의원 서울 강남구 을); start corrected 2022-05-21→2022-05-12 (임명재가); end corrected 2024-01-12→2024-01-10 (후임 조태열 임명)")

# 박민식 (국가보훈부): NOT 21대 MP — LOST 21대 election; dual_office must be FALSE
# He was 18대·19대 MP from 부산 북구강서구 갑, but LOST 20대 and 21대 elections
# Appointed as 국가보훈처장 2022-05-13, then 처→부 upgrade ~2023-06-05
df = fix(df, "박민식", "국가보훈부", "윤석열",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt=float("nan"),
    start="2023-06-05",
    end="2023-12-28",
    notes="비겸직 (21대 총선 부산 북구강서구 갑 낙선; 임명 당시 현직 의원 아님; 국가보훈처장 2022-05-13→부 승격 2023-06-05; end approx 강정애 후임)")


# ===========================================================================
# 이재명 정부 corrections
# ===========================================================================

# 김민석 (국무총리): district wrong — was 서울 영등포구 을, NOT 인천 계양구 을
# 인천 계양구 을은 이재명 대통령의 전 지역구
df = fix(df, "김민석", "국무총리", "이재명",
    mp_district="서울 영등포구 을",
    notes="겸직 총리 (22대 의원 서울 영등포구 을 4선); district MAJOR CORRECTION 인천 계양구 을→서울 영등포구 을 (이재명의 전 지역구와 혼동)")

# 정성호 (법무부): district incomplete — 22대 지역구는 경기 동두천시·양주시·연천군 갑
df = fix(df, "정성호", "법무부", "이재명",
    mp_district="경기 동두천시·양주시·연천군 갑",
    notes="겸직 장관 (22대 의원 경기 동두천시·양주시·연천군 갑 5선); district corrected 경기 양주시→동두천시·양주시·연천군 갑")

# 정동영 (통일부, 이재명): 22대 선거구 개편으로 전주시 병 (완산구 갑 아님)
df = fix(df, "정동영", "통일부", "이재명",
    mp_district="전북 전주시 병",
    notes="겸직 장관 (22대 의원 전북 전주시 병 5선; 22대 선거구 개편으로 완산구→전주시 병); district corrected 완산구 갑→전주시 병")

# 김윤덕 (국토교통부): 22대 지역구는 전북 전주시 갑 (완산구 을 아님)
df = fix(df, "김윤덕", "국토교통부", "이재명",
    mp_district="전북 전주시 갑",
    notes="겸직 장관 (22대 의원 전북 전주시 갑 3선); district corrected 완산구 을→전주시 갑 (22대 선거구 개편)")

# 김성환 (기후에너지환경부): was first appointed as 환경부 장관 ~July 2025;
# 기후에너지환경부 officially launched 2025-10-01 as ministry renaming/expansion
# Keep 2025-10-01 as start for this ministry-specific entry, but add note
df = fix(df, "김성환", "기후에너지환경부", "이재명",
    notes="겸직 장관 (22대 의원 서울 노원구 을 3선); 2025년 7월 환경부 장관 임명 후 2025-10-01 기후에너지환경부 출범으로 직함 변경; 인사청문은 환경부 장관으로 진행; start=2025-10-01 is ministry launch date")

# 전재수 (해양수산부): start date WRONG (2025-10-01 → 2025-07-24) + end date known
df = fix(df, "전재수", "해양수산부", "이재명",
    start="2025-07-24",
    end="2025-12-11",
    notes="겸직 장관 (22대 의원 부산 북구·강서구 갑 3선); start CORRECTION 2025-10-01→2025-07-24 (취임식 확인); end 2025-12-11 (면직안 재가)")


# ===========================================================================
# Print summary
# ===========================================================================

print(f"\nTotal corrections applied: {len(changed_rows)}")

dual_changes = [r for r in changed_rows if r["field"] == "dual_office"]
print(f"\ndual_office changes: {len(dual_changes)}")
for r in dual_changes:
    print(f"  {r['admin']} | {r['ministry']} | {r['name']}: {r['old']} → {r['new']}")

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
