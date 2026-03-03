"""
apply_corrections_v1.py

Applies verified corrections to minister_panel_comprehensive.csv
based on 4-agent Wikipedia verification (2026-03-01).

Corrections organized by government. Key for matching:
  (name, ministry, admin) = unique row identifier.

All corrections documented with agent source and evidence.
"""

import pandas as pd
import os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_IN  = os.path.join(BASE, "data", "minister_panel_comprehensive.csv")
CSV_OUT = os.path.join(BASE, "data", "minister_panel_comprehensive.csv")

df = pd.read_csv(CSV_IN, encoding="utf-8-sig")

# Ensure boolean column
def to_bool(v):
    if str(v).strip().lower() in ("true", "1", "yes"): return True
    return False

df["dual_office"] = df["dual_office"].apply(to_bool)

changed_rows = []

def fix(df, name, ministry, admin, **kwargs):
    """Apply field corrections to matching row(s)."""
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
# 노무현 정부 corrections
# ===========================================================================

# 김영진 (농림부): district was biret not 안양 동안구 을
df = fix(df, "김영진", "농림부", "노무현",
    mp_district="비례대표",
    notes="겸직 장관 (16대 비례의원 재임 중); date approx; district corrected from 안양 동안구 을")

# 김진표 (교육인적자원부): start date wrong + district wrong
df = fix(df, "김진표", "교육인적자원부", "노무현",
    start="2005-01-28",
    mp_district="경기 수원시 영통구",
    notes="겸직 장관 (17대 의원 재임 중); start date corrected 2004-02-01→2005-01-28; district 팔달구→영통구")

# 정동채 (문화관광부): district 갑 → 을
df = fix(df, "정동채", "문화관광부", "노무현",
    mp_district="광주 서구 을",
    notes="겸직 장관 (17대); district corrected 서구 갑→서구 을")

# 정동영 (통일부): NOT 17대 MP — withdrew from election
df = fix(df, "정동영", "통일부", "노무현",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    notes="비겸직 (17대 총선 불출마; 임명 당시 현직 의원 아님; 16대 전북 전주시 덕진구 의원 전력 있음)")

# 천정배 (법무부): district was 안산 단원구 갑 in 17대 (not 광주 서구)
df = fix(df, "천정배", "법무부", "노무현",
    mp_district="경기 안산시 단원구 갑",
    notes="겸직 장관 (17대); district corrected 광주 서구→경기 안산시 단원구 갑 (광주 서구 을은 19대부터)")

# 정세균 (산업자원부): district was 진안·무주·장수·임실, not 전주시 덕진구
df = fix(df, "정세균", "산업자원부", "노무현",
    mp_district="전북 진안군·무주군·장수군·임실군",
    notes="겸직 장관 (17대); district corrected 전주시 덕진구→진안·무주·장수·임실; date approx")

# 이재정 (통일부): NOT a sitting MP when appointed (left assembly ~2003)
df = fix(df, "이재정", "통일부", "노무현",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    start="2006-12-29",  # Unification Minister appointment (approx Dec 2006)
    notes="비겸직 (16대 비례의원 임기 종료 후 임명; 임명 당시 현직 의원 아님); date approx")

# 이용섭 (행정자치부): bureaucrat, NOT MP at appointment
df = fix(df, "이용섭", "행정자치부", "노무현",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    start="2006-03-27",
    notes="비겸직 (대통령비서실 출신 관료; 18대 MP는 2008년 이후); date corrected 2006-09-12→2006-03-27")

# 이용섭 (건설교통부): bureaucrat, NOT MP
df = fix(df, "이용섭", "건설교통부", "노무현",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    start="2006-12-11",
    notes="비겸직 (관료 출신; 18대 MP는 2008년 이후); date corrected 2007-09-15→2006-12-11")

# 김영주 (산업자원부): identity confusion — actual minister was bureaucrat (born 1950)
# NOT the politician 김영주 (born 1955) who was 17대 비례
df = fix(df, "김영주", "산업자원부", "노무현",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    start="2007-01-29",
    notes="비겸직 (관료 출신 김영주 1950년생; 17대 비례의원 김영주 1955년생과 동명이인 혼동; date corrected)")


# ===========================================================================
# 이명박 정부 corrections
# ===========================================================================

# 정운천 (농림수산식품부): NOT 18대 MP — first MP was 20대 (2016)
df = fix(df, "정운천", "농림수산식품부", "이명박",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    start="2008-02-29",
    end="2008-08-06",
    notes="비겸직 (초대 이명박 농림수산식품부 장관; 18대 MP 아님; 최초 의원 당선은 20대 2016년)")

# 주호영 (특임장관): start date wrong
df = fix(df, "주호영", "특임장관", "이명박",
    start="2009-09-30",
    notes="겸직 장관 (18대 의원); start corrected 2009-03-13→2009-09-30")

# 이달곤 (행정안전부): resigned MP seat BEFORE appointment
df = fix(df, "이달곤", "행정안전부", "이명박",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    start="2009-02-04",
    end="2010-03-20",
    notes="비겸직 (18대 의원직 2009-02-03 사퇴 후 다음날 장관 임명; date approx)")

# 전재희 (보건복지부): district was 지역구 경기 광명시 을, NOT 비례
df = fix(df, "전재희", "보건복지부", "이명박",
    mp_district="경기 광명시 을",
    start="2008-08-06",
    end="2010-08-30",
    notes="겸직 장관 (18대 의원 경기 광명시 을 지역구); constituency 비례→지역구; start corrected to 2008-08-06")

# 이재오 (특임장관): start date off by 20 days
df = fix(df, "이재오", "특임장관", "이명박",
    start="2010-08-30",
    notes="겸직 장관 (18대 의원 서울 은평구 을); start corrected 2010-08-10→2010-08-30")

# 정병국 (문화체육관광부): constituency wrong + start date wrong
df = fix(df, "정병국", "문화체육관광부", "이명박",
    mp_district="경기 양평군·가평군",
    start="2011-01-27",
    end="2011-09-16",
    notes="겸직 장관 (18대 의원); constituency corrected 가평·포천→양평·가평; start corrected 2010-08-10→2011-01-27")

# 임태희 (고용노동부): constituency wrong; dual_office TRUE maintained (was MP at appointment)
df = fix(df, "임태희", "고용노동부", "이명박",
    mp_district="경기 성남시 분당구 을",
    start="2009-09-30",
    end="2010-07-15",
    notes="겸직 장관 (18대 의원; 임명 당시 의원 재임 중이었으나 이후 사퇴); constituency corrected 중원구→분당구 을; start corrected")

# 박재완 (고용노동부): was 17대 비례, NOT 18대 MP
df = fix(df, "박재완", "고용노동부", "이명박",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    start="2010-08-30",
    end="2011-06-01",
    notes="비겸직 (17대 비례의원이었으나 18대에는 의원직 없음; 기획재정부 차관 출신 관료 신분으로 임명)")

# 이주호 (교육과학기술부): UNCERTAIN — possibly 17대 biret, keep TRUE with verify flag
df = fix(df, "이주호", "교육과학기술부", "이명박",
    notes="겸직 장관 (18대 의원 의심; VERIFY: 17대 비례인지 18대 비례인지 확인 필요); date approx")

# 진수희 (보건복지부): constituency was 지역구, not 비례
df = fix(df, "진수희", "보건복지부", "이명박",
    mp_district="서울 성동구 갑",
    start="2010-08-30",
    end="2011-09-15",
    notes="겸직 장관 (18대 의원 서울 성동구 갑 지역구); constituency 비례→지역구; start corrected 2011-06-01→2010-08-30")

# 최경환 (지식경제부): start date was VERY wrong (2011-08 instead of 2009-09)
df = fix(df, "최경환", "지식경제부", "이명박",
    start="2009-09-19",
    end="2011-01-26",
    notes="겸직 장관 (18대 의원 경북 경산·청도); start MAJOR CORRECTION 2011-08-01→2009-09-19; end corrected")

# 유정복 (농림수산식품부, 이명박): dates + district all wrong
df = fix(df, "유정복", "농림수산식품부", "이명박",
    start="2010-08-30",
    end="2011-06-01",
    mp_district="경기 김포시",
    notes="겸직 장관 (18대 의원 경기 김포시); start/end/district ALL corrected; 인천 계양구는 오류")

# 김금래 (여성가족부): start off by 1 day; keep TRUE (appointed as MP then resigned)
df = fix(df, "김금래", "여성가족부", "이명박",
    start="2011-09-16",
    notes="겸직 장관 (18대 비례의원; 임명 당시 의원 신분); start corrected 2011-09-15→2011-09-16")

# 고흥길 (특임장관): constituency completely wrong + start date wrong
df = fix(df, "고흥길", "특임장관", "이명박",
    mp_district="경기 성남시 분당구 갑",
    start="2012-02-24",
    end="2013-03-23",
    notes="겸직 장관 (18대 의원 경기 성남시 분당구 갑); constituency MAJOR CORRECTION 강원→경기 성남; start corrected 2011-10→2012-02-24")

# 박재완 (기획재정부, 이명박): was 17대 biret, NOT 18대 MP
df = fix(df, "박재완", "기획재정부", "이명박",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    start="2011-06-02",
    end="2013-02-24",
    notes="비겸직 (17대 비례의원이었으나 18대에는 의원직 없음; 기획재정부 장관으로 임명 시 관료 신분); start corrected")


# ===========================================================================
# 박근혜 정부 corrections
# ===========================================================================

# 유정복 (안전행정부, 박근혜): dates + district wrong
df = fix(df, "유정복", "안전행정부", "박근혜",
    start="2013-03-13",
    end="2014-03-06",
    mp_district="경기 김포시",
    notes="겸직 장관 (19대 의원 경기 김포시); start/end/district corrected; 인천 계양구는 오류")

# 이완구 (총리): start off by 1 day
df = fix(df, "이완구", "국무총리", "박근혜",
    start="2015-02-17",
    notes="겸직 장관 (19대 의원 충남 부여·청양); start corrected 2015-02-16→2015-02-17")


# ===========================================================================
# 문재인 정부 corrections
# ===========================================================================

# 이낙연 (총리): was 전남도지사, NOT 20대 MP at appointment
df = fix(df, "이낙연", "국무총리", "문재인",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    notes="비겸직 (임명 당시 전남도지사 재직 중; 20대 국회의원 아님; 19대 의원 전력 있음)")

# 김부겸 (행정안전부): start date
df = fix(df, "김부겸", "행정안전부", "문재인",
    start="2017-06-16",
    notes="겸직 장관 (20대 의원 대구 수성구 갑); start corrected 2017-06-14→2017-06-16")

# 김영춘 (해양수산부): start date
df = fix(df, "김영춘", "해양수산부", "문재인",
    start="2017-06-16",
    notes="겸직 장관 (20대 의원 부산 진구 갑); start corrected 2017-06-14→2017-06-16")

# 도종환 (문화체육관광부): start date
df = fix(df, "도종환", "문화체육관광부", "문재인",
    start="2017-06-16",
    notes="겸직 장관 (20대 의원 충북 청주시 흥덕구); start corrected 2017-06-14→2017-06-16")

# 김영록 (농림축산식품부): was 19대 MP, term ended 2016-05-29; NOT 20대 MP
df = fix(df, "김영록", "농림축산식품부", "문재인",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    start="2017-07-03",
    notes="비겸직 (19대 의원 임기 만료 후 20대 미출마; 농림부 장관 임명 2017-07-03 당시 현직 의원 아님)")

# 김영주 (고용노동부): start date + district (갑 not 을)
df = fix(df, "김영주", "고용노동부", "문재인",
    start="2017-08-14",
    mp_district="서울 영등포구 갑",
    notes="겸직 장관 (20대 의원 서울 영등포구 갑); start corrected 2017-06-14→2017-08-14; district 을→갑")

# 김현미 (국토교통부): start date + district
df = fix(df, "김현미", "국토교통부", "문재인",
    start="2017-06-21",
    mp_district="경기 고양시 정",
    notes="겸직 장관 (20대 의원 경기 고양시 정); start corrected 2017-07-03→2017-06-21; district 일산서구→고양시 정")

# 이개호 (농림축산식품부): start date
df = fix(df, "이개호", "농림축산식품부", "문재인",
    start="2018-08-09",
    notes="겸직 장관 (20대 의원 전남 담양·함평·영광·장성); start corrected 2018-04-27→2018-08-09")

# 진선미 (여성가족부): start date + district (갑 not 을)
df = fix(df, "진선미", "여성가족부", "문재인",
    start="2018-09-21",
    mp_district="서울 강동구 갑",
    notes="겸직 장관 (20대 의원 서울 강동구 갑); start corrected 2018-09-06→2018-09-21; district 을→갑")

# 황희 (문화체육관광부): start date + district MAJOR ERROR
df = fix(df, "황희", "문화체육관광부", "문재인",
    start="2021-02-11",
    mp_district="서울 양천구 갑",
    assembly_num_at_appt=21,
    notes="겸직 장관 (21대 의원 서울 양천구 갑); start corrected 2020-12-29→2021-02-11; district MAJOR CORRECTION 경기 김포시 을→서울 양천구 갑")

# 전해철 (행정안전부): start date
df = fix(df, "전해철", "행정안전부", "문재인",
    start="2020-12-24",
    notes="겸직 장관 (21대 의원 경기 안산시 상록구 갑); start corrected 2021-01-20→2020-12-24")

# 한정애 (환경부): start date + district (병 not 갑)
df = fix(df, "한정애", "환경부", "문재인",
    start="2021-01-22",
    mp_district="서울 강서구 병",
    notes="겸직 장관 (21대 의원 서울 강서구 병); start corrected 2021-01-20→2021-01-22; district 갑→병")

# 박범계 (법무부): start date
df = fix(df, "박범계", "법무부", "문재인",
    start="2021-01-28",
    notes="겸직 장관 (21대 의원 대전 서구 을); start corrected 2021-01-20→2021-01-28")

# 권칠승 (중소벤처기업부): start date + district (병 not 을)
df = fix(df, "권칠승", "중소벤처기업부", "문재인",
    start="2021-02-05",
    mp_district="경기 화성시 병",
    notes="겸직 장관 (21대 의원 경기 화성시 병); start corrected 2021-04-08→2021-02-05; district 을→병")

# 임혜숙 (과학기술정보통신부): professor, NOT MP
df = fix(df, "임혜숙", "과학기술정보통신부", "문재인",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    notes="비겸직 (이화여자대학교 교수 출신; 21대 비례의원 아님; 의원 경력 없음)")


# ===========================================================================
# 윤석열 정부 corrections
# ===========================================================================

# 원희룡 (국토교통부): was Jeju governor, NOT 21대 MP
df = fix(df, "원희룡", "국토교통부", "윤석열",
    dual_office=False,
    mp_party_at_appt="",
    mp_district="",
    assembly_num_at_appt="",
    start="2022-05-13",
    end="2023-12-25",
    notes="비겸직 (임명 당시 제주특별자치도지사 재직 중; 21대 의원 아님; 20대 총선 인천 남동구 갑 낙선; 이전 의원직은 16~18대 서울 양천구 갑/관악구 을)")


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
    print(f"  [{r['admin']}] {r['ministry']} | {r['name']} | {r['start']} | {r['mp_party_at_appt']} {r['mp_district']} ({r['assembly_num_at_appt']}대)")

# Save
df.to_csv(CSV_OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved to {CSV_OUT}")
