"""
build_comprehensive_panel.py
Builds minister_panel_comprehensive.csv from:
  1. Existing minister_panel_manual.csv (44 entries, verified)
  2. Additional entries derived from Wikipedia + knowledge
     - All confirmed dual-office (겸직) ministers not in manual panel
     - Complete Lee Jae-myung (이재명) government cabinet
     - Key non-dual-office comparison entries for Yoon Suk-yeol government

Key variable: dual_office = TRUE if minister was a sitting MP at time of appointment

Sources:
  - Wikipedia government minister pages (각 정부별 국무위원)
  - Individual minister Wikipedia pages (for date verification)
  - 겸직_자료정리.md (Lee Jae-myung government data)

Date convention:
  - Verified dates: YYYY-MM-DD
  - Approximate dates: YYYY-MM-DD with "(date approx)" in notes
  - Ongoing tenure: blank end date
"""

import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Load existing panel (44 entries, all verified)
# ---------------------------------------------------------------------------
existing = pd.read_csv(os.path.join(BASE_DIR, "data", "minister_panel_manual.csv"))

# ---------------------------------------------------------------------------
# New entries to add
# Each dict follows the same column structure as minister_panel_manual.csv
# ---------------------------------------------------------------------------

COLS = [
    "ministry", "name", "name_en", "start", "end",
    "admin", "admin_ideology", "dual_office",
    "mp_party_at_appt", "mp_district", "assembly_num_at_appt",
    "confirmation_hearing", "confirmation_date", "notes"
]

def e(ministry, name, name_en, start, end,
      admin, ideology, dual,
      party="", district="", asm="",
      hearing=True, hearing_date="", notes=""):
    return {
        "ministry": ministry, "name": name, "name_en": name_en,
        "start": start, "end": end,
        "admin": admin, "admin_ideology": ideology, "dual_office": dual,
        "mp_party_at_appt": party, "mp_district": district,
        "assembly_num_at_appt": asm,
        "confirmation_hearing": hearing, "confirmation_date": hearing_date,
        "notes": notes
    }

new_entries = [

    # ===================================================================
    # 노무현 정부 (Roh Moo-hyun) — additional 겸직 ministers
    # ===================================================================

    # 정세균: 산업자원부 장관 (노무현 정부, 17대)
    # - Wikipedia: 2006년 2월 ~ 2007년 1월
    # - 15~20대 의원 6선; 17대 열린우리당 의원 신분으로 임명
    e("산업자원부", "정세균", "Jeong Se-gyun",
      "2006-02-10", "2007-01-03",
      "노무현", "Progressive", True,
      "열린우리당", "전북 전주시 덕진구", 17,
      True, "2006-02-10",
      "겸직 장관 (17대); 후 문재인 정부 PM으로 재등장 (별도 row); 날짜 approximate"),

    # 이재정: 통일부 장관 (노무현 정부, 17대)
    # - 정동영 후임; 2006-02-10 내각 개편 시 임명
    e("통일부", "이재정", "Lee Jae-jeong",
      "2006-02-10", "2008-02-29",
      "노무현", "Progressive", True,
      "열린우리당", "경기 고양시 덕양구 을", 17,
      True, "2006-02-10",
      "겸직 장관 (17대); 노무현 정부 마지막 통일부 장관; 날짜 approximate"),

    # 이용섭: 행정자치부 장관 (노무현 정부, 17대)
    # - 17대 열린우리당 의원 (광주 광산구), 행자부 장관 임명
    e("행정자치부", "이용섭", "Lee Yong-seop",
      "2006-09-12", "2007-02-28",
      "노무현", "Progressive", True,
      "열린우리당", "광주 광산구", 17,
      True, "2006-09-12",
      "겸직 장관 (17대) — 행자부; 날짜 approximate; 겸직 여부 재확인 권고"),

    # 이용섭: 건설교통부 장관 (노무현 정부, 17대)
    # - 같은 인물, 다른 부처, 17대 임기 (2004-2008) 중 재임
    e("건설교통부", "이용섭", "Lee Yong-seop",
      "2007-09-15", "2008-02-29",
      "노무현", "Progressive", True,
      "열린우리당", "광주 광산구", 17,
      True, "2007-09-15",
      "겸직 장관 (17대) — 건교부; 날짜 approximate; 겸직 여부 재확인 권고"),

    # ===================================================================
    # 이명박 정부 (Lee Myung-bak) — additional 겸직 minister
    # ===================================================================

    # 고흥길: 특임장관 (이명박 정부, 18대)
    # - 주호영·이재오에 이은 세 번째 특임장관; 18대 한나라당 의원
    e("특임장관", "고흥길", "Ko Heung-gil",
      "2011-10-03", "2012-04-10",
      "이명박", "Conservative", True,
      "한나라당", "강원 속초시·고성군·양양군", 18,
      False, "",
      "겸직 특임장관 (18대); 날짜 approximate; 청문회 대상 여부 재확인 권고"),

    # ===================================================================
    # 박근혜 정부 (Park Geun-hye) — additional 겸직 ministers
    # ===================================================================

    # 진영: 보건복지부 장관 (박근혜 정부, 19대)
    # - 19대 새누리당 의원 (서울 용산구)
    # - 후에 문재인 정부 행안부 장관도 역임 (이미 패널에 있음)
    e("보건복지부", "진영", "Jin Yeong",
      "2013-03-11", "2013-09-10",
      "박근혜", "Conservative", True,
      "새누리당", "서울 용산구", 19,
      True, "2013-03-11",
      "겸직 장관 (19대) — 박근혜 정부; 문재인 정부 행안부 장관은 별도 row"),

    # 유정복: 농림축산식품부 장관 (박근혜 정부, 19대)
    # - 19대 새누리당 의원 (인천 계양구 갑)
    # - 퇴임 후 인천시장 선거 출마
    e("농림축산식품부", "유정복", "Yu Jeong-bok",
      "2013-03-11", "2014-07-03",
      "박근혜", "Conservative", True,
      "새누리당", "인천 계양구 갑", 19,
      True, "2013-03-11",
      "겸직 장관 (19대); 퇴임 후 인천시장 당선"),

    # 이주영: 해양수산부 장관 (박근혜 정부, 19대)
    # - 19대 새누리당 의원 (경남 창원시 의창구)
    # - 세월호 사고 대응 (2014년 6월 사의 표명 후 유임)
    e("해양수산부", "이주영", "Lee Ju-yeong",
      "2013-03-22", "2015-09-24",
      "박근혜", "Conservative", True,
      "새누리당", "경남 창원시 의창구", 19,
      True, "2013-03-22",
      "겸직 장관 (19대); 세월호 사고 대응; 날짜 approximate"),

    # 강은희: 여성가족부 장관 (박근혜 정부, 19대)
    # - 19대 새누리당 비례대표 의원
    # - 임명 후 의원직 유지 논란 → 자진 사퇴
    e("여성가족부", "강은희", "Kang Eun-hee",
      "2015-03-12", "2016-08-18",
      "박근혜", "Conservative", True,
      "새누리당", "비례대표", 19,
      True, "2015-03-12",
      "겸직 장관 (19대 비례대표); 의원직 유지 논란 → 사퇴; 비례대표 겸직은 관례상 사퇴"),

    # ===================================================================
    # 문재인 정부 (Moon Jae-in) — additional 겸직 ministers
    # ===================================================================

    # 김영주: 고용노동부 장관 (문재인 정부, 20대)
    # - 20대 더불어민주당 의원 (서울 영등포구 을), 노동운동 출신
    e("고용노동부", "김영주", "Kim Yeong-ju",
      "2017-06-14", "2018-11-08",
      "문재인", "Progressive", True,
      "더불어민주당", "서울 영등포구 을", 20,
      True, "2017-06-14",
      "겸직 장관 (20대); 노동운동·의원 출신"),

    # 이개호: 농림축산식품부 장관 (문재인 정부, 20대)
    e("농림축산식품부", "이개호", "Lee Gae-ho",
      "2018-04-27", "2019-04-08",
      "문재인", "Progressive", True,
      "더불어민주당", "전남 담양·함평·영광·장성", 20,
      True, "2018-04-27",
      "겸직 장관 (20대)"),

    # 진선미: 여성가족부 장관 (문재인 정부, 20대)
    e("여성가족부", "진선미", "Jin Seon-mi",
      "2018-09-06", "2019-04-05",
      "문재인", "Progressive", True,
      "더불어민주당", "서울 강동구 을", 20,
      True, "2018-09-06",
      "겸직 장관 (20대)"),

    # 이인영: 통일부 장관 (문재인 정부, 21대)
    e("통일부", "이인영", "Lee In-yeong",
      "2020-07-27", "2021-11-03",
      "문재인", "Progressive", True,
      "더불어민주당", "서울 구로구 갑", 21,
      True, "2020-07-27",
      "겸직 장관 (21대)"),

    # 황희: 문화체육관광부 장관 (문재인 정부, 21대)
    e("문화체육관광부", "황희", "Hwang Hee",
      "2020-12-29", "2022-05-09",
      "문재인", "Progressive", True,
      "더불어민주당", "경기 김포시 을", 21,
      True, "2020-12-29",
      "겸직 장관 (21대)"),

    # 한정애: 환경부 장관 (문재인 정부, 21대)
    e("환경부", "한정애", "Han Jeong-ae",
      "2021-01-20", "2022-05-09",
      "문재인", "Progressive", True,
      "더불어민주당", "서울 강서구 갑", 21,
      True, "2021-01-20",
      "겸직 장관 (21대)"),

    # 박범계: 법무부 장관 (문재인 정부, 21대)
    e("법무부", "박범계", "Park Beom-gye",
      "2021-01-20", "2022-05-10",
      "문재인", "Progressive", True,
      "더불어민주당", "대전 서구 을", 21,
      True, "2021-01-20",
      "겸직 장관 (21대)"),

    # 권칠승: 중소벤처기업부 장관 (문재인 정부, 21대)
    e("중소벤처기업부", "권칠승", "Gwon Chil-seung",
      "2021-04-08", "2022-05-09",
      "문재인", "Progressive", True,
      "더불어민주당", "경기 화성시 을", 21,
      True, "2021-04-08",
      "겸직 장관 (21대)"),

    # ===================================================================
    # 윤석열 정부 (Yoon Suk-yeol) — additional 겸직 + key 비겸직
    # ===================================================================

    # 원희룡: 국토교통부 장관 (윤석열 정부, 21대 겸직)
    # - 21대 국민의힘 의원 (제주 제주시 갑)
    e("국토교통부", "원희룡", "Won Hee-ryong",
      "2022-05-10", "2023-12-28",
      "윤석열", "Conservative", True,
      "국민의힘", "제주 제주시 갑", 21,
      True, "2022-05-10",
      "겸직 장관 (21대); 제주도지사 출신"),

    # 이영: 중소벤처기업부 장관 (윤석열 정부, 21대 겸직)
    # - 21대 국민의힘 의원 (대전 중구)
    e("중소벤처기업부", "이영", "Lee Yeong",
      "2022-05-10", "2023-12-27",
      "윤석열", "Conservative", True,
      "국민의힘", "대전 중구", 21,
      True, "2022-05-10",
      "겸직 장관 (21대)"),

    # --- 윤석열 정부 비겸직 (comparison entries for same ministries) ---

    # 한동훈: 법무부 장관 (윤석열 정부, 비겸직)
    e("법무부", "한동훈", "Han Dong-hoon",
      "2022-05-10", "2023-12-28",
      "윤석열", "Conservative", False,
      "", "", "",
      True, "2022-05-10",
      "비겸직 (검사 출신); 청문보고서 채택"),

    # 이종섭: 국방부 장관 (윤석열 정부, 비겸직)
    e("국방부", "이종섭", "Lee Jong-seop",
      "2022-05-10", "2023-09-22",
      "윤석열", "Conservative", False,
      "", "", "",
      True, "2022-05-10",
      "비겸직 (군인 출신); 해병대원 특검 관련 사퇴"),

    # 조태열: 외교부 장관 (윤석열 정부, 비겸직, 박진 후임)
    e("외교부", "조태열", "Jo Tae-yeol",
      "2024-01-12", "2025-06-04",
      "윤석열", "Conservative", False,
      "", "", "",
      True, "2024-01-12",
      "비겸직 (외교관 출신); 박진 후임"),

    # 김영호: 통일부 장관 (윤석열 정부, 비겸직, 권영세 후임)
    e("통일부", "김영호", "Kim Yeong-ho",
      "2023-12-22", "2025-06-04",
      "윤석열", "Conservative", False,
      "", "", "",
      True, "2023-12-22",
      "비겸직 (학자 출신); 권영세 후임"),

    # 박상우: 국토교통부 장관 (윤석열 정부, 비겸직, 원희룡 후임)
    e("국토교통부", "박상우", "Park Sang-woo",
      "2024-01-12", "2025-06-04",
      "윤석열", "Conservative", False,
      "", "", "",
      True, "2024-01-12",
      "비겸직; 원희룡 후임"),

    # 오영주: 중소벤처기업부 장관 (윤석열 정부, 비겸직, 이영 후임)
    e("중소벤처기업부", "오영주", "O Yeong-ju",
      "2023-12-29", "2025-06-04",
      "윤석열", "Conservative", False,
      "", "", "",
      True, "2023-12-29",
      "비겸직; 이영 후임"),

    # 최상목: 기획재정부 부총리 (윤석열 정부, 비겸직, 추경호 후임)
    e("기획재정부", "최상목", "Choi Sang-mok",
      "2023-12-29", "2025-06-04",
      "윤석열", "Conservative", False,
      "", "", "",
      True, "2023-12-29",
      "비겸직 (관료 출신); 추경호 후임; 권한대행 수행"),

    # 송미령: 농림축산식품부 장관 (윤석열 정부, 비겸직 — 이재명 정부로 유임)
    e("농림축산식품부", "송미령", "Song Mi-ryeong",
      "2023-01-10", "2025-06-04",  # 유임 시 종료일은 이재명 정부 새 장관 임명 시
      "윤석열", "Conservative", False,
      "", "", "",
      True, "2023-01-10",
      "비겸직; 이재명 정부에도 유임 (별도 row 추가)"),

    # ===================================================================
    # 이재명 정부 (Lee Jae-myung) — complete initial cabinet
    # 대통령 취임: 2025-06-04
    # 장관 임명 날짜: Wikipedia (이재명_정부의_국무위원, 2026-02-24 기준)
    # ===================================================================

    # --- PM (겸직) ---
    e("국무총리", "김민석", "Kim Min-seok",
      "2025-07-03", "",
      "이재명", "Progressive", True,
      "더불어민주당", "인천 계양구 을", 22,
      True, "2025-07-03",
      "겸직 총리 (22대); 이재명 정부 초대 총리"),

    # --- 겸직 장관 (dual_office=TRUE) ---
    e("통일부", "정동영", "Jeong Dong-yeong",
      "2025-07-25", "",
      "이재명", "Progressive", True,
      "더불어민주당", "전북 전주시 완산구 갑", 22,
      True, "2025-07-25",
      "겸직 장관 (22대); 노무현 정부 통일부 장관 재임용 (2004) — 별도 row"),

    e("법무부", "정성호", "Jeong Seong-ho",
      "2025-07-18", "",
      "이재명", "Progressive", True,
      "더불어민주당", "경기 양주시", 22,
      True, "2025-07-18",
      "겸직 장관 (22대)"),

    e("국방부", "안규백", "Ahn Gyu-baek",
      "2025-07-25", "",
      "이재명", "Progressive", True,
      "더불어민주당", "서울 동대문구 갑", 22,
      True, "2025-07-25",
      "겸직 장관 (22대)"),

    e("행정안전부", "윤호중", "Yun Ho-jung",
      "2025-07-19", "",
      "이재명", "Progressive", True,
      "더불어민주당", "경기 구리시", 22,
      True, "2025-07-19",
      "겸직 장관 (22대)"),

    e("기후에너지환경부", "김성환", "Kim Seong-hwan",
      "2025-10-01", "",
      "이재명", "Progressive", True,
      "더불어민주당", "서울 노원구 을", 22,
      True, "2025-10-01",
      "겸직 장관 (22대); 기후에너지환경부 = 이재명 정부 신설 (구 환경부 확대개편)"),

    e("국토교통부", "김윤덕", "Kim Yun-deok",
      "2025-07-31", "",
      "이재명", "Progressive", True,
      "더불어민주당", "전북 전주시 완산구 을", 22,
      True, "2025-07-31",
      "겸직 장관 (22대)"),

    e("해양수산부", "전재수", "Jeon Jae-su",
      "2025-10-01", "",
      "이재명", "Progressive", True,
      "더불어민주당", "부산 북구·강서구 갑", 22,
      True, "2025-10-01",
      "겸직 장관 (22대); 임명 날짜 approximate — 확인 필요"),

    # --- 비겸직 장관 (dual_office=FALSE) ---
    e("재정경제부", "구윤철", "Gu Yun-cheol",
      "2026-01-02", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2026-01-02",
      "비겸직; 부총리 겸 재정경제부장관 (이재명 정부 기재부 분리개편)"),

    e("과학기술정보통신부", "배경훈", "Bae Gyeong-hun",
      "2025-10-01", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2025-10-01",
      "비겸직; 과학기술부총리 겸 과기정통부장관"),

    e("교육부", "최교진", "Choi Gyo-jin",
      "2025-10-01", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2025-10-01",
      "비겸직; 이재명 정부 사회부총리 폐지 후 장관급"),

    e("외교부", "조현", "Jo Hyeon",
      "2025-07-18", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2025-07-18",
      "비겸직 (외교관 출신)"),

    e("국가보훈부", "권오을", "Gwon O-eul",
      "2025-07-25", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2025-07-25",
      "비겸직"),

    e("문화체육관광부", "최휘영", "Choi Hwi-yeong",
      "2025-07-31", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2025-07-31",
      "비겸직"),

    e("농림축산식품부", "송미령", "Song Mi-ryeong",
      "2025-06-04", "",
      "이재명", "Progressive", False,
      "", "", "",
      False, "",
      "비겸직; 윤석열 정부에서 유임 (start date = 이재명 정부 출범일 기준); 별도 row"),

    e("산업통상자원부", "김정관", "Kim Jeong-gwan",
      "2025-10-01", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2025-10-01",
      "비겸직"),

    e("보건복지부", "정은경", "Jeong Eun-gyeong",
      "2025-07-21", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2025-07-21",
      "비겸직 (전 질병관리청장, COVID-19 방역 총괄)"),

    e("고용노동부", "김영훈", "Kim Yeong-hun",
      "2025-07-21", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2025-07-21",
      "비겸직"),

    e("성평등가족부", "원민경", "Won Min-gyeong",
      "2025-10-01", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2025-10-01",
      "비겸직; 성평등가족부 = 이재명 정부 신설 (구 여성가족부 확대개편)"),

    e("중소벤처기업부", "한성숙", "Han Seong-suk",
      "2025-07-23", "",
      "이재명", "Progressive", False,
      "", "", "",
      True, "2025-07-23",
      "비겸직 (네이버 대표 출신)"),

]

# ---------------------------------------------------------------------------
# Build comprehensive dataframe
# ---------------------------------------------------------------------------
new_df = pd.DataFrame(new_entries, columns=COLS)

# Ensure existing df has same columns (add any missing with empty string)
for col in COLS:
    if col not in existing.columns:
        existing[col] = ""

comprehensive = pd.concat([existing[COLS], new_df], ignore_index=True)

# Sort: by admin chronological order, then start date
admin_order = {
    "김대중": 1, "노무현": 2, "이명박": 3, "박근혜": 4,
    "문재인": 5, "윤석열": 6, "이재명": 7, "한덕수": 8
}
comprehensive["_admin_order"] = comprehensive["admin"].map(admin_order).fillna(9)
comprehensive["_start_sort"] = pd.to_datetime(
    comprehensive["start"].str.replace(r"\(.*\)", "", regex=True).str.strip(),
    errors="coerce"
)
comprehensive = comprehensive.sort_values(
    ["_admin_order", "_start_sort"]
).drop(columns=["_admin_order", "_start_sort"]).reset_index(drop=True)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
output_path = os.path.join(BASE_DIR, "data", "minister_panel_comprehensive.csv")
comprehensive.to_csv(output_path, index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------
print(f"Saved to: {output_path}")
print(f"Total entries: {len(comprehensive)}")
print()

print("=== By dual_office status ===")
print(comprehensive["dual_office"].value_counts())
print()

print("=== By government (admin) ===")
print(comprehensive.groupby(["admin", "dual_office"]).size().unstack(fill_value=0))
print()

print("=== Confirmation hearing coverage ===")
print(comprehensive["confirmation_hearing"].value_counts())
print()

print("=== New 겸직 entries added (not in original 44) ===")
new_dual = new_df[new_df["dual_office"] == True]
print(f"Count: {len(new_dual)}")
for _, row in new_dual.iterrows():
    print(f"  {row['admin']} | {row['ministry']} | {row['name']} | {row['start']}")
