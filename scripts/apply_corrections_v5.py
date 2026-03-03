"""
apply_corrections_v5.py

Applies fifth batch of corrections to minister_panel_comprehensive.csv
based on 나무위키 인사청문회 comprehensive table (2026-03-01, session 4).

Changes:
1. 11 NaN confirmation_date entries:
   - 2 reclassified to confirmation_hearing=FALSE (no hearing held)
   - 9 given actual hearing dates

2. 3 이명박 특임장관 entries: confirmation_hearing corrected FALSE->TRUE + dates added

3. 이재명 정부: all 19 confirmation_dates corrected from start-date placeholders
   to actual hearing dates from 나무위키

Source: 나무위키 인사청문회 '사례' section (Section 5), retrieved 2026-03-01
        https://namu.wiki/w/인사청문회
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
# Part 1: 11 NaN confirmation_date entries (original targets)
# ===========================================================================

# 김진표 (노무현 교육인적자원부, 2005-01-28):
# 국무위원 인사청문 의무화 법 시행: 2005-07-28 (국회법 개정)
# 김진표 임명일 2005-01-28 < 법 시행일 -> 인사청문 대상 아님 -> confirmation_hearing=FALSE
# 나무위키 참여정부 사례 표에 김진표 교육인적자원부장관 항목 없음 (확인)
df = fix(df, "김진표", "교육인적자원부", "노무현",
    confirmation_hearing=False,
    notes="겸직 장관 (17대 의원 경기 수원시 영통구); 임명 2005-01-28은 국무위원 인사청문 의무화(2005-07-28 국회법 개정) 이전 → 인사청문 미실시; confirmation_hearing CORRECTION True→False")

# 전재희 (이명박 보건복지부, 2008-08-06):
# 나무위키: "보건복지가족부장관 전재희 인사청문 미실시 임명"
# 이유: 18대 국회 상임위 미구성 상태에서 임명 (보건복지가족위원회 구성일 2008-09-01)
df = fix(df, "전재희", "보건복지부", "이명박",
    confirmation_hearing=False,
    notes="겸직 장관 (18대 의원 경기 광명시 을); 인사청문 미실시 - 18대 국회 보건복지가족위원회 구성(2008-09-01) 이전 임명(2008-08-06); 나무위키 인사청문회 5.3절 확인; confirmation_hearing CORRECTION True→False")

# 임태희 (이명박 고용노동부, start 2009-09-30):
# 나무위키: "노동부장관 임태희 2009년 9월 22일 미채택 임명"
df = fix(df, "임태희", "고용노동부", "이명박",
    confirmation_date="2009-09-22",
    notes="겸직 장관 (18대 의원 경기 성남시 분당구 을); 인사청문: 2009-09-22 (미채택 후 임명 강행); 출처: 나무위키 인사청문회 5.3절")

# 최경환 (이명박 지식경제부, start 2009-09-19):
# 나무위키: "지식경제부장관 최경환 2009년 9월 15일 채택 임명"
df = fix(df, "최경환", "지식경제부", "이명박",
    confirmation_date="2009-09-15",
    notes="겸직 장관 (18대 의원 경북 경산시·청도군, 한나라당); 인사청문: 2009-09-15 (채택); mp_district CORRECTION 대구 달성군→경북 경산시·청도군 (notes field already correct; 대구 달성군은 추경호 21대 기재부); 출처: 나무위키 인사청문회 5.3절")

# 진수희 (이명박 보건복지부, start 2010-08-30):
# 나무위키: "보건복지부장관 진수희 2010년 8월 23일 채택 임명"
df = fix(df, "진수희", "보건복지부", "이명박",
    confirmation_date="2010-08-23",
    notes="겸직 장관 (18대 의원 서울 성동구 갑); 인사청문: 2010-08-23 (채택); 출처: 나무위키 인사청문회 5.3절")

# 유정복 (이명박 농림수산식품부, start 2010-08-30):
# 나무위키: "농림수산식품부장관 유정복 2010년 8월 23일 채택 임명"
df = fix(df, "유정복", "농림수산식품부", "이명박",
    confirmation_date="2010-08-23",
    notes="겸직 장관 (18대 의원 경기 김포시); 인사청문: 2010-08-23 (채택); 출처: 나무위키 인사청문회 5.3절")

# 정병국 (이명박 문화체육관광부, start 2011-01-27):
# 나무위키: "문화체육관광부장관 정병국 2011년 1월 17일 채택 임명"
df = fix(df, "정병국", "문화체육관광부", "이명박",
    confirmation_date="2011-01-17",
    notes="겸직 장관 (18대 의원 경기 양평군·가평군); 인사청문: 2011-01-17 (채택); 출처: 나무위키 인사청문회 5.3절")

# 이주영 (박근혜 해양수산부, start 2014-03-06):
# 나무위키: "해양수산부장관 이주영 2014년 3월 4일 채택 임명"
df = fix(df, "이주영", "해양수산부", "박근혜",
    confirmation_date="2014-03-04",
    notes="겸직 장관 (19대 의원 경남 창원시 마산합포구); 인사청문: 2014-03-04 (채택); start MAJOR CORRECTION 2013-03-22→2014-03-06 (윤진숙 후임); 출처: 나무위키 인사청문회 5.4절")

# 강은희 (박근혜 여성가족부, start 2016-01-13):
# 나무위키: "여성가족부장관 강은희 2016년 1월 7일 채택 임명"
df = fix(df, "강은희", "여성가족부", "박근혜",
    confirmation_date="2016-01-07",
    notes="겸직 장관 (19대 비례의원); 인사청문: 2016-01-07 (채택); start MAJOR CORRECTION 2015-03-12→2016-01-13 (취임식일 확인); 출처: 나무위키 인사청문회 5.4절")

# 권칠승 (문재인 중소벤처기업부, start 2021-02-05):
# 나무위키: "중소벤처기업부장관 권칠승 2021년 2월 3일 채택 임명"
df = fix(df, "권칠승", "중소벤처기업부", "문재인",
    confirmation_date="2021-02-03",
    notes="겸직 장관 (21대 의원 경기 화성시 병); 인사청문: 2021-02-03 (채택); 출처: 나무위키 인사청문회 5.5절")

# 전재수 (이재명 해양수산부, start 2025-07-24):
# 나무위키: "해양수산부장관 전재수 2025년 7월 14일 채택 임명"
df = fix(df, "전재수", "해양수산부", "이재명",
    confirmation_date="2025-07-14",
    notes="겸직 장관 (22대 의원 부산 북구 갑 3선; 21대는 북구·강서구 갑이었으나 22대 선거구 개편으로 강서구 분리); mp_district CORRECTION 부산 북구·강서구 갑→부산 북구 갑; 인사청문: 2025-07-14 (채택); 출처: 나무위키 인사청문회 5.7절")


# ===========================================================================
# Part 2: 이명박 특임장관 3건 (confirmation_hearing FALSE->TRUE + date)
# ===========================================================================

# 주호영 (이명박 특임장관, start 2009-09-30):
# 나무위키: "특임장관 주호영 2009년 9월 15일 채택 임명"
df = fix(df, "주호영", "특임장관", "이명박",
    confirmation_hearing=True,
    confirmation_date="2009-09-15",
    notes="겸직 장관 (18대 의원 대구 수성구 을); 인사청문: 2009-09-15 (채택); confirmation_hearing CORRECTION False→True; 출처: 나무위키 인사청문회 5.3절")

# 이재오 (이명박 특임장관, start 2010-08-30):
# 나무위키: "이재오 2010년 8월 23일 채택 임명"
# Note: 2010-07-28 보궐선거 서울 은평구 을 당선 후 바로 장관 임명
df = fix(df, "이재오", "특임장관", "이명박",
    confirmation_hearing=True,
    confirmation_date="2010-08-23",
    notes="겸직 장관 (18대 의원 서울 은평구 을; 2010-07-28 보궐선거 당선 후 임명); 인사청문: 2010-08-23 (채택); confirmation_hearing CORRECTION False→True; 출처: 나무위키 인사청문회 5.3절")

# 고흥길 (이명박 특임장관, start 2012-02-24):
# 나무위키: "고흥길 2012년 2월 14일 채택 임명"
df = fix(df, "고흥길", "특임장관", "이명박",
    confirmation_hearing=True,
    confirmation_date="2012-02-14",
    notes="겸직 장관 (18대 의원 경기 성남시 분당구 갑); 인사청문: 2012-02-14 (채택); confirmation_hearing CORRECTION False→True; 출처: 나무위키 인사청문회 5.3절")


# ===========================================================================
# Part 3: 이재명 정부 confirmation_date corrections
# All previous values were placeholders (= start date or ministry launch date)
# Corrected to actual hearing dates from 나무위키 인사청문회 5.7절
# ===========================================================================

# 김민석 (국무총리): hearing 2025-06-24~25 (start: 2025-07-03)
df = fix(df, "김민석", "국무총리", "이재명",
    confirmation_date="2025-06-24",
    notes="겸직 총리 (22대 의원 서울 영등포구 을 4선); 인사청문: 2025-06-24~25 (미채택 후 가결); district MAJOR CORRECTION 인천 계양구 을→서울 영등포구 을 (이재명의 전 지역구와 혼동); confirmation_date CORRECTION 2025-07-03→2025-06-24; 출처: 나무위키 인사청문회 5.7절")

# 정성호 (법무부): hearing 2025-07-16 (start: 2025-07-18)
df = fix(df, "정성호", "법무부", "이재명",
    confirmation_date="2025-07-16",
    notes="겸직 장관 (22대 의원 경기 동두천시·양주시·연천군 갑 5선); district corrected 경기 양주시→동두천시·양주시·연천군 갑; 인사청문: 2025-07-16 (채택); confirmation_date CORRECTION 2025-07-18→2025-07-16; 출처: 나무위키 인사청문회 5.7절")

# 조현 (외교부): hearing 2025-07-17 (start: 2025-07-18)
df = fix(df, "조현", "외교부", "이재명",
    confirmation_date="2025-07-17",
    notes="비겸직 (외교관 출신; 국회의원 아님); 인사청문: 2025-07-17 (채택); confirmation_date CORRECTION 2025-07-18→2025-07-17; 출처: 나무위키 인사청문회 5.7절")

# 윤호중 (행정안전부): hearing 2025-07-18 (start: 2025-07-19)
df = fix(df, "윤호중", "행정안전부", "이재명",
    confirmation_date="2025-07-18",
    notes="겸직 장관 (22대 의원 경기 구리시 5선); 인사청문: 2025-07-18 (채택); confirmation_date CORRECTION 2025-07-19→2025-07-18; 출처: 나무위키 인사청문회 5.7절")

# 정은경 (보건복지부): hearing 2025-07-18 (start: 2025-07-21)
df = fix(df, "정은경", "보건복지부", "이재명",
    confirmation_date="2025-07-18",
    notes="비겸직 (질병관리청장 출신; 국회의원 아님); 인사청문: 2025-07-18 (채택); confirmation_date CORRECTION 2025-07-21→2025-07-18; 출처: 나무위키 인사청문회 5.7절")

# 김영훈 (고용노동부): hearing 2025-07-16 (start: 2025-07-21)
df = fix(df, "김영훈", "고용노동부", "이재명",
    confirmation_date="2025-07-16",
    notes="비겸직 (노동계 출신; 국회의원 아님); 인사청문: 2025-07-16 (채택); confirmation_date CORRECTION 2025-07-21→2025-07-16; 출처: 나무위키 인사청문회 5.7절")

# 한성숙 (중소벤처기업부): hearing 2025-07-15 (start: 2025-07-23)
df = fix(df, "한성숙", "중소벤처기업부", "이재명",
    confirmation_date="2025-07-15",
    notes="비겸직 (네이버 CEO 출신; 국회의원 아님); 인사청문: 2025-07-15 (채택); confirmation_date CORRECTION 2025-07-23→2025-07-15; 출처: 나무위키 인사청문회 5.7절")

# 정동영 (통일부): hearing 2025-07-14 (start: 2025-07-25)
df = fix(df, "정동영", "통일부", "이재명",
    confirmation_date="2025-07-14",
    notes="겸직 장관 (22대 의원 전북 전주시 병 5선; 22대 선거구 개편으로 완산구→전주시 병); district corrected 완산구 갑→전주시 병; 인사청문: 2025-07-14 (미채택 후 임명); confirmation_date CORRECTION 2025-07-25→2025-07-14; 출처: 나무위키 인사청문회 5.7절")

# 안규백 (국방부): hearing 2025-07-15 (start: 2025-07-25)
df = fix(df, "안규백", "국방부", "이재명",
    confirmation_date="2025-07-15",
    notes="겸직 장관 (22대 의원 서울 동대문구 갑 5선); 인사청문: 2025-07-15 (미채택 후 임명); confirmation_date CORRECTION 2025-07-25→2025-07-15; 출처: 나무위키 인사청문회 5.7절")

# 권오을 (국가보훈부): hearing 2025-07-15 (start: 2025-07-25)
df = fix(df, "권오을", "국가보훈부", "이재명",
    confirmation_date="2025-07-15",
    notes="비겸직 (국회의원 아님); 인사청문: 2025-07-15 (미채택 후 임명); confirmation_date CORRECTION 2025-07-25→2025-07-15; 출처: 나무위키 인사청문회 5.7절")

# 김윤덕 (국토교통부): hearing 2025-07-29 (start: 2025-07-31)
df = fix(df, "김윤덕", "국토교통부", "이재명",
    confirmation_date="2025-07-29",
    notes="겸직 장관 (22대 의원 전북 전주시 갑 3선); district corrected 완산구 을→전주시 갑 (22대 선거구 개편); 인사청문: 2025-07-29 (채택); confirmation_date CORRECTION 2025-07-31→2025-07-29; 출처: 나무위키 인사청문회 5.7절")

# 최휘영 (문화체육관광부): hearing 2025-07-29 (start: 2025-07-31)
df = fix(df, "최휘영", "문화체육관광부", "이재명",
    confirmation_date="2025-07-29",
    notes="비겸직 (국회의원 아님); 인사청문: 2025-07-29 (채택); confirmation_date CORRECTION 2025-07-31→2025-07-29; 출처: 나무위키 인사청문회 5.7절")

# 김성환 (기후에너지환경부): actual hearing was as 환경부장관 2025-07-15
# Ministry renamed/expanded to 기후에너지환경부 on 2025-10-01
# confirmation_date was set to 2025-10-01 (ministry launch date) -- WRONG
df = fix(df, "김성환", "기후에너지환경부", "이재명",
    confirmation_date="2025-07-15",
    notes="겸직 장관 (22대 의원 서울 노원구 을 3선); 2025년 7월 환경부장관 인사청문 2025-07-15 (채택) 후 임명; 2025-10-01 기후에너지환경부 출범으로 직함 변경; confirmation_date CORRECTION 2025-10-01→2025-07-15 (환경부장관 청문일; 기후에너지환경부 출범일 아님); 출처: 나무위키 인사청문회 5.7절")

# 배경훈 (과학기술정보통신부): hearing 2025-07-14 (start: 2025-10-01)
df = fix(df, "배경훈", "과학기술정보통신부", "이재명",
    confirmation_date="2025-07-14",
    notes="비겸직 (국회의원 아님); 인사청문: 2025-07-14 (채택); confirmation_date CORRECTION 2025-10-01→2025-07-14; 출처: 나무위키 인사청문회 5.7절")

# 최교진 (교육부): hearing 2025-09-02 (start: 2025-10-01)
df = fix(df, "최교진", "교육부", "이재명",
    confirmation_date="2025-09-02",
    notes="비겸직 (교육감 출신; 국회의원 아님); 2차 교육부장관 후보 (1차 이진숙 2025-07-16 미채택 철회 후 재지명); 인사청문: 2025-09-02 (채택); confirmation_date CORRECTION 2025-10-01→2025-09-02; 출처: 나무위키 인사청문회 5.7절")

# 김정관 (산업통상자원부): hearing 2025-07-17 (start: 2025-10-01)
df = fix(df, "김정관", "산업통상자원부", "이재명",
    confirmation_date="2025-07-17",
    notes="비겸직 (국회의원 아님); 인사청문: 2025-07-17 (채택); confirmation_date CORRECTION 2025-10-01→2025-07-17; 출처: 나무위키 인사청문회 5.7절")

# 원민경 (성평등가족부): hearing 2025-09-03 (start: 2025-10-01)
# Ministry was 여성가족부 -> 성평등가족부; first candidate 강선우 withdrew 2025-07-14
df = fix(df, "원민경", "성평등가족부", "이재명",
    confirmation_date="2025-09-03",
    notes="비겸직 (국회의원 아님); 2차 성평등가족부장관 후보 (1차 강선우 2025-07-14 미채택 사퇴 후 재지명); 인사청문: 2025-09-03 (채택); confirmation_date CORRECTION 2025-10-01→2025-09-03; 출처: 나무위키 인사청문회 5.7절")

# 구윤철 (기획재정부): hearing 2025-07-17; start=2026-01-02 (likely reorganization date)
# Note: 이재명 정부 초기 기획재정부장관으로 확인 청문 2025-07-17, 이후 기획예산처 신설(2026) 시
# 기획재정부 분리 재편. start=2026-01-02은 조직 개편 후 기획재정부장관으로서의 시작일.
df = fix(df, "구윤철", "기획재정부", "이재명",
    confirmation_date="2025-07-17",
    notes="비겸직 (국회의원 아님); 기획재정부장관 인사청문: 2025-07-17 (채택); start=2026-01-02은 기획예산처 신설에 따른 부처 재편 후 기획재정부장관 재임 시작일로 추정; confirmation_date CORRECTION 2026-01-02→2025-07-17; 출처: 나무위키 인사청문회 5.7절")


# ===========================================================================
# Print summary
# ===========================================================================

print(f"\nTotal field changes: {len(changed_rows)}")

hearing_changes = [r for r in changed_rows if r["field"] == "confirmation_hearing"]
date_changes = [r for r in changed_rows if r["field"] == "confirmation_date"]
print(f"\nconfirmation_hearing changes: {len(hearing_changes)}")
for r in hearing_changes:
    print(f"  [{r['admin']}] {r['ministry']} | {r['name']}: {r['old']} -> {r['new']}")

print(f"\nconfirmation_date changes: {len(date_changes)}")
for r in date_changes:
    print(f"  [{r['admin']}] {r['ministry']} | {r['name']}: {r['old']} -> {r['new']}")

print(f"\nFinal counts:")
print(f"  Total entries: {len(df)}")
print(f"  dual_office=TRUE: {df['dual_office'].sum()}")
print(f"  dual_office=FALSE: {(~df['dual_office']).sum()}")
print(f"  confirmation_hearing=True: {(df['confirmation_hearing'] == True).sum()}")
print(f"  confirmation_date NaN (hearing=True): {(df['confirmation_hearing'] == True) & df['confirmation_date'].isna()}")

df.to_csv(CSV_OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved to {CSV_OUT}")
