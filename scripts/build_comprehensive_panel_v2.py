"""
build_comprehensive_panel_v2.py

Complete rebuild of minister_panel_comprehensive.csv.

Changes from v1:
  - Fixes 유정복 error (was listed as 박근혜 농림부 → corrected to
    이명박 농림수산식품부 + 박근혜 안전행정부, both 겸직)
  - Adds all missing 겸직 ministers (노무현~윤석열)
  - Adds ALL 비겸직 ministers for complete comparison group
  - Total entries: ~250 (up from 91)

겸직 definition: minister was a sitting National Assembly member
  at the time of appointment (did not resign MP seat first).

Date convention:
  - Known exact dates: YYYY-MM-DD
  - Approximate dates: YYYY-MM-DD with "(date approx)" in notes
  - Ongoing tenure: blank end date

Assembly term dates:
  16대: 2000-05-30 to 2004-05-29
  17대: 2004-05-30 to 2008-05-29
  18대: 2008-05-30 to 2012-05-29
  19대: 2012-05-30 to 2016-05-29
  20대: 2016-05-30 to 2020-05-29
  21대: 2020-05-30 to 2024-05-29
  22대: 2024-05-30 to present

Sources:
  - Wikipedia government minister pages (각 정부별 국무위원)
  - Individual minister Wikipedia pages
  - minister_panel_manual.csv (44 verified entries, base data)
"""

import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Load existing panel (44 entries, all verified)
# ---------------------------------------------------------------------------
existing = pd.read_csv(
    os.path.join(BASE_DIR, "data", "minister_panel_manual.csv"),
    encoding="utf-8-sig"
)

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

    # =========================================================================
    # 노무현 정부 (Roh Moo-hyun) 2003-02-27 ~ 2008-02-24
    # Progressive / 열린우리당
    # 16대 MP: 2000-05-30 ~ 2004-05-29
    # 17대 MP: 2004-05-30 ~ 2008-05-29
    # =========================================================================

    # --- 겸직 ministers (missing from manual panel) ---

    # 정세균: 산업자원부 장관 (17대 의원, 전북 전주 덕진)
    e("산업자원부", "정세균", "Jeong Se-gyun",
      "2006-02-10", "2007-01-03",
      "노무현", "Progressive", True,
      "열린우리당", "전북 전주시 덕진구", 17,
      True, "2006-02-10",
      "겸직 장관 (17대); date approx"),

    # 이재정: 통일부 장관 (17대 의원, 경기 고양 덕양을)
    e("통일부", "이재정", "Lee Jae-jeong",
      "2006-02-10", "2008-02-24",
      "노무현", "Progressive", True,
      "열린우리당", "경기 고양시 덕양구 을", 17,
      True, "2006-02-10",
      "겸직 장관 (17대); date approx"),

    # 이용섭: 행정자치부 장관 (17대 의원, 광주 광산구)
    e("행정자치부", "이용섭", "Lee Yong-seop",
      "2006-09-12", "2007-02-28",
      "노무현", "Progressive", True,
      "열린우리당", "광주 광산구", 17,
      True, "2006-09-12",
      "겸직 장관 (17대); date approx"),

    # 이용섭: 건설교통부 장관 (17대 의원, 동일 인물)
    e("건설교통부", "이용섭", "Lee Yong-seop",
      "2007-09-15", "2008-02-24",
      "노무현", "Progressive", True,
      "열린우리당", "광주 광산구", 17,
      True, "2007-09-15",
      "겸직 장관 (17대) — 건교부; date approx"),

    # 김진표: 교육인적자원부 장관 (17대 의원 재임 중)
    # Agent confirmed: 겸직 TRUE (17대 의원으로서 겸직)
    e("교육인적자원부", "김진표", "Kim Jin-pyo",
      "2004-02-01", "2005-01-03",
      "노무현", "Progressive", True,
      "열린우리당", "경기 수원시 팔달구", 17,
      True, "2004-02-01",
      "겸직 장관 (17대 의원 재임 중); date approx; agent confirmed"),

    # 정동채: 문화관광부 장관 (17대 의원, 광주 서구 갑)
    # Agent confirmed: 겸직 TRUE
    e("문화관광부", "정동채", "Jeong Dong-chae",
      "2004-06-30", "2006-02-09",
      "노무현", "Progressive", True,
      "열린우리당", "광주 서구 갑", 17,
      True, "2004-06-30",
      "겸직 장관 (17대); date approx; agent confirmed"),

    # 김영진: 농림부 장관 (16대 의원, 안양 동안을)
    # Was 16대 MP when appointed 2003-02 → 겸직 TRUE
    e("농림부", "김영진", "Kim Yeong-jin",
      "2003-02-27", "2004-01-09",
      "노무현", "Progressive", True,
      "새천년민주당", "안양시 동안구 을", 16,
      True, "2003-02-27",
      "겸직 장관 (16대 의원 재임 중); date approx; verify"),

    # 장병완: 기획예산처 장관 (비겸직 — 2010년에야 18대 의원 당선)
    # Agent confirmed: NOT 겸직 (장관 2006-2008, MP 2010-)
    e("기획예산처", "장병완", "Jang Byeong-wan",
      "2006-07-21", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-07-21",
      "비겸직 (18대 의원이었으나 장관 재임 후 당선; 장관 2006-2008, 18대 MP 2010); agent confirmed"),

    # 김영주: 산업자원부 장관 (17대 비례 의원)
    e("산업자원부", "김영주", "Kim Yeong-ju",
      "2007-08-01", "2008-02-24",
      "노무현", "Progressive", True,
      "대통합민주신당", "비례대표", 17,
      True, "2007-08-01",
      "겸직 장관 (17대 비례의원); date approx; verify"),

    # --- 비겸직 ministers (노무현 정부) ---

    # 재정경제부
    e("재정경제부", "김진표", "Kim Jin-pyo",
      "2003-02-27", "2004-01-09",
      "노무현", "Progressive", False, "", "", "",
      True, "2003-02-27",
      "비겸직 (관료 출신; 의원 경력 별도 - 장관 이전 16대 당선 여부 verify)"),

    e("재정경제부", "이헌재", "Lee Heon-jae",
      "2004-01-09", "2004-07-01",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-01-09",
      "비겸직 (관료 출신); date approx"),

    e("재정경제부", "한덕수", "Han Deok-su",
      "2004-07-01", "2006-07-03",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-07-01",
      "비겸직 (관료 출신); date approx"),

    e("재정경제부", "권오규", "Gwon O-gyu",
      "2006-07-03", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-07-03",
      "비겸직 (관료 출신); date approx"),

    # 교육인적자원부 (비겸직)
    e("교육인적자원부", "윤덕홍", "Yun Deok-hong",
      "2003-02-27", "2004-01-09",
      "노무현", "Progressive", False, "", "", "",
      True, "2003-02-27",
      "비겸직 (교수 출신); date approx"),

    e("교육인적자원부", "안병영", "Ahn Byeong-yeong",
      "2004-01-09", "2004-02-01",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-01-09",
      "비겸직 (교수 출신); date approx"),

    e("교육인적자원부", "이기준", "Lee Gi-jun",
      "2004-07-01", "2004-08-01",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-07-01",
      "비겸직 (교수 출신, 서울대 총장); date approx"),

    e("교육인적자원부", "김병준", "Kim Byeong-jun",
      "2006-02-10", "2006-09-12",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (교수 출신); date approx"),

    e("교육인적자원부", "김신일", "Kim Sin-il",
      "2006-09-12", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-09-12",
      "비겸직 (교수 출신); date approx"),

    # 과학기술부
    e("과학기술부", "박호군", "Park Ho-gun",
      "2003-02-27", "2004-07-01",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (교수 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("과학기술부", "오명", "O Myeong",
      "2004-07-01", "2006-02-10",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (교수 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("과학기술부", "김우식", "Kim U-sik",
      "2006-02-10", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (교수 출신); date approx"),

    # 통일부 (비겸직)
    e("통일부", "정세현", "Jeong Se-hyeon",
      "2003-02-27", "2004-06-30",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (관료 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("통일부", "이종석", "Lee Jong-seok",
      "2005-01-03", "2006-02-09",
      "노무현", "Progressive", False, "", "", "",
      True, "2005-01-03",
      "비겸직 (교수 출신); date approx"),

    # 외교통상부
    e("외교통상부", "윤영관", "Yun Yeong-gwan",
      "2003-02-27", "2004-01-19",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (교수 출신, 서울대); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("외교통상부", "반기문", "Ban Ki-moon",
      "2004-01-19", "2006-11-17",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-01-19",
      "비겸직 (외교관 출신; 후 유엔 사무총장); date approx"),

    e("외교통상부", "송민순", "Song Min-sun",
      "2006-11-17", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-11-17",
      "비겸직 (외교관 출신); date approx"),

    # 법무부 (비겸직)
    e("법무부", "강금실", "Kang Geum-sil",
      "2003-02-27", "2004-06-30",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (변호사 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("법무부", "김승규", "Kim Seung-gyu",
      "2004-06-30", "2005-06-20",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-06-30",
      "비겸직 (검사 출신); date approx"),

    e("법무부", "김성호", "Kim Seong-ho",
      "2006-02-10", "2007-09-15",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (검사 출신); date approx"),

    e("법무부", "정성진", "Jeong Seong-jin",
      "2007-09-15", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2007-09-15",
      "비겸직 (검사 출신); date approx"),

    # 국방부
    e("국방부", "조영길", "Jo Yeong-gil",
      "2003-02-27", "2004-07-01",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (군인 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("국방부", "윤광웅", "Yun Gwang-ung",
      "2004-07-01", "2006-11-17",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-07-01",
      "비겸직 (군인 출신); date approx"),

    e("국방부", "김장수", "Kim Jang-su",
      "2006-11-17", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-11-17",
      "비겸직 (군인 출신); date approx"),

    # 행정자치부 (비겸직)
    e("행정자치부", "김두관", "Kim Du-gwan",
      "2003-02-27", "2003-09-01",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (정치운동가 출신, 의원 경력 없음); date approx; 인사청문회 대상 아님"),

    e("행정자치부", "허성관", "Heo Seong-gwan",
      "2003-09-01", "2006-09-12",
      "노무현", "Progressive", False, "", "", "",
      True, "2003-09-01",
      "비겸직 (관료 출신); date approx"),

    e("행정자치부", "오영교", "O Yeong-gyo",
      "2004-07-01", "2006-09-12",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-07-01",
      "비겸직 (관료 출신); date approx"),

    e("행정자치부", "박명재", "Park Myeong-jae",
      "2006-09-12", "2007-03-01",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-09-12",
      "비겸직 (관료 출신); date approx"),

    # 문화관광부 (비겸직)
    e("문화관광부", "이창동", "Lee Chang-dong",
      "2003-02-27", "2004-06-30",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (영화감독 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("문화관광부", "김명곤", "Kim Myeong-gon",
      "2006-02-10", "2007-01-03",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (예술인 출신); date approx"),

    e("문화관광부", "김종민", "Kim Jong-min",
      "2007-01-03", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2007-01-03",
      "비겸직 (공무원 출신); date approx; agent confirmed NOT 겸직"),

    # 농림부 (비겸직)
    e("농림부", "허상만", "Heo Sang-man",
      "2004-01-09", "2006-02-10",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-01-09",
      "비겸직 (관료 출신); date approx"),

    e("농림부", "박홍수", "Park Hong-su",
      "2006-02-10", "2007-09-15",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (관료 출신); date approx"),

    e("농림부", "임상규", "Im Sang-gyu",
      "2007-09-15", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2007-09-15",
      "비겸직 (관료 출신); date approx"),

    # 산업자원부 (비겸직)
    e("산업자원부", "윤진식", "Yun Jin-sik",
      "2003-02-27", "2004-07-01",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (관료 출신); date approx; 인사청문회 대상 아님(2005년 이전); verify"),

    e("산업자원부", "이희범", "Lee Hui-beom",
      "2004-07-01", "2006-02-10",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-07-01",
      "비겸직 (기업인 출신); date approx"),

    # 정보통신부
    e("정보통신부", "진대제", "Jin Dae-je",
      "2003-02-27", "2006-02-10",
      "노무현", "Progressive", False, "", "", "",
      True, "2003-02-27",
      "비겸직 (삼성전자 출신); date approx"),

    e("정보통신부", "노준형", "No Jun-hyeong",
      "2006-02-10", "2007-01-03",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (관료 출신); date approx"),

    e("정보통신부", "유영환", "Yu Yeong-hwan",
      "2007-01-03", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2007-01-03",
      "비겸직 (외교관 출신); date approx"),

    # 보건복지부 (비겸직)
    e("보건복지부", "김화중", "Kim Hwa-jung",
      "2003-02-27", "2004-07-01",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (의사 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("보건복지부", "변재진", "Byeon Jae-jin",
      "2007-09-15", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2007-09-15",
      "비겸직 (관료 출신); date approx"),

    # 환경부 (비겸직 — 한명숙은 비겸직 confirmed)
    e("환경부", "한명숙", "Han Myeong-suk",
      "2003-02-27", "2004-01-09",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (장관 퇴임 후 17대 당선); date approx; agent confirmed NOT 겸직"),

    e("환경부", "곽결호", "Gwak Gyeol-ho",
      "2004-07-01", "2006-02-10",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-07-01",
      "비겸직 (관료 출신); date approx"),

    e("환경부", "이재용", "Lee Jae-yong",
      "2006-02-10", "2006-09-12",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (관료 출신); date approx"),

    e("환경부", "이치범", "Lee Chi-beom",
      "2005-01-03", "2006-02-10",
      "노무현", "Progressive", False, "", "", "",
      True, "2005-01-03",
      "비겸직 (16대 비례의원이었으나 임기 종료 후 임명); date approx"),

    e("환경부", "이규용", "Lee Gyu-yong",
      "2006-09-12", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-09-12",
      "비겸직 (관료 출신); date approx"),

    # 노동부 (비겸직)
    e("노동부", "권기홍", "Gwon Gi-hong",
      "2003-02-27", "2004-07-01",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (관료 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("노동부", "김대환", "Kim Dae-hwan",
      "2004-07-01", "2006-02-10",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-07-01",
      "비겸직 (교수 출신); date approx"),

    e("노동부", "이상수", "Lee Sang-su",
      "2006-02-10", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (16대 의원 임기 종료 후 임명); date approx; agent confirmed NOT 겸직"),

    # 여성가족부 (비겸직)
    e("여성가족부", "지은희", "Ji Eun-hee",
      "2003-02-27", "2004-07-01",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (교수/활동가 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("여성가족부", "장하진", "Jang Ha-jin",
      "2006-06-23", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-06-23",
      "비겸직 (교수 출신); date approx"),

    # 건설교통부 (비겸직)
    e("건설교통부", "최종찬", "Choe Jong-chan",
      "2003-02-27", "2004-07-01",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (관료 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("건설교통부", "강동석", "Kang Dong-seok",
      "2004-07-01", "2006-02-10",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-07-01",
      "비겸직 (관료 출신); date approx"),

    e("건설교통부", "추병직", "Chu Byeong-jik",
      "2006-02-10", "2007-09-15",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (관료 출신); date approx"),

    # 해양수산부 (비겸직)
    e("해양수산부", "허성관", "Heo Seong-gwan",
      "2003-02-27", "2004-01-09",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (관료 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("해양수산부", "최낙정", "Choe Nak-jeong",
      "2004-01-09", "2006-02-10",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-01-09",
      "비겸직 (관료 출신); date approx"),

    e("해양수산부", "장승우", "Jang Seung-u",
      "2006-02-10", "2006-09-12",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (관료 출신); date approx"),

    e("해양수산부", "오거돈", "O Geo-don",
      "2006-09-12", "2007-04-01",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-09-12",
      "비겸직 (관료 출신); date approx"),

    e("해양수산부", "김성진", "Kim Seong-jin",
      "2007-04-01", "2007-09-15",
      "노무현", "Progressive", False, "", "", "",
      True, "2007-04-01",
      "비겸직 (교수 출신); date approx"),

    e("해양수산부", "강무현", "Kang Mu-hyeon",
      "2007-09-15", "2008-02-24",
      "노무현", "Progressive", False, "", "", "",
      True, "2007-09-15",
      "비겸직 (관료 출신); date approx"),

    # 기획예산처 (비겸직)
    e("기획예산처", "박봉흠", "Park Bong-heum",
      "2003-02-27", "2004-07-01",
      "노무현", "Progressive", False, "", "", "",
      False, "",
      "비겸직 (관료 출신); date approx; 인사청문회 대상 아님(2005년 이전)"),

    e("기획예산처", "김병일", "Kim Byeong-il",
      "2004-07-01", "2006-02-10",
      "노무현", "Progressive", False, "", "", "",
      True, "2004-07-01",
      "비겸직 (관료 출신); date approx"),

    e("기획예산처", "변양균", "Byeon Yang-gyun",
      "2006-02-10", "2007-01-03",
      "노무현", "Progressive", False, "", "", "",
      True, "2006-02-10",
      "비겸직 (관료 출신); date approx"),

    # =========================================================================
    # 이명박 정부 (Lee Myung-bak) 2008-02-25 ~ 2013-02-24
    # Conservative / 한나라당 → 새누리당
    # 18대 MP: 2008-05-30 ~ 2012-05-29
    # =========================================================================

    # --- 겸직 ministers (missing from manual panel) ---

    # 고흥길: 특임장관 (18대 의원, 강원 속초·고성·양양)
    e("특임장관", "고흥길", "Ko Heung-gil",
      "2011-10-03", "2012-04-10",
      "이명박", "Conservative", True,
      "한나라당", "강원 속초시·고성군·양양군", 18,
      False, "",
      "겸직 특임장관 (18대); 특임장관 인사청문 대상 여부 확인 필요"),

    # 이달곤: 행정안전부 장관 (18대 비례 의원)
    # Agent confirmed: 겸직 TRUE
    e("행정안전부", "이달곤", "Lee Dal-gon",
      "2010-04-16", "2010-08-11",
      "이명박", "Conservative", True,
      "한나라당", "비례대표", 18,
      True, "2010-04-16",
      "겸직 장관 (18대 비례의원); date approx; agent confirmed"),

    # 최경환: 지식경제부 장관 (18대 의원, 대구 달성군)
    # Agent confirmed: 겸직 TRUE
    e("지식경제부", "최경환", "Choe Gyeong-hwan",
      "2011-08-01", "2013-02-24",
      "이명박", "Conservative", True,
      "한나라당", "대구 달성군", 18,
      True, "2011-08-01",
      "겸직 장관 (18대 의원); date approx; agent confirmed"),

    # 유정복: 농림수산식품부 장관 (18대 의원, 인천 계양을)
    # CORRECTED: was wrongly listed as 박근혜 농림부 in v1
    # Agent confirmed: 겸직 TRUE
    e("농림수산식품부", "유정복", "Yu Jeong-bok",
      "2011-09-05", "2013-02-24",
      "이명박", "Conservative", True,
      "한나라당", "인천 계양구 을", 18,
      True, "2011-09-05",
      "겸직 장관 (18대 의원); date approx; agent confirmed; v1 오류 수정"),

    # 정병국: 문화체육관광부 장관 (18대 의원, 경기 가평군·포천시)
    e("문화체육관광부", "정병국", "Jeong Byeong-guk",
      "2010-08-10", "2011-09-15",
      "이명박", "Conservative", True,
      "한나라당", "경기 가평군·포천시", 18,
      True, "2010-08-10",
      "겸직 장관 (18대 의원); date approx; verify"),

    # 전재희: 보건복지부 장관 (18대 비례 의원)
    e("보건복지부", "전재희", "Jeon Jae-hee",
      "2010-04-16", "2011-06-01",
      "이명박", "Conservative", True,
      "한나라당", "비례대표", 18,
      True, "2010-04-16",
      "겸직 장관 (18대 비례의원); date approx; verify"),

    # 진수희: 보건복지부 장관 (18대 비례 의원)
    e("보건복지부", "진수희", "Jin Su-hee",
      "2011-06-01", "2012-09-01",
      "이명박", "Conservative", True,
      "한나라당", "비례대표", 18,
      True, "2011-06-01",
      "겸직 장관 (18대 비례의원); date approx; verify"),

    # 정운천: 농림수산식품부 장관 (18대 의원, 전북 남원)
    e("농림수산식품부", "정운천", "Jeong Un-cheon",
      "2009-02-05", "2009-09-24",
      "이명박", "Conservative", True,
      "한나라당", "전북 남원시", 18,
      True, "2009-02-05",
      "겸직 장관 (18대 의원); date approx; verify"),

    # 이주호: 교육과학기술부 장관 (18대 의원, 서울 용산)
    e("교육과학기술부", "이주호", "Lee Ju-ho",
      "2010-12-03", "2013-02-24",
      "이명박", "Conservative", True,
      "한나라당", "서울 용산구", 18,
      True, "2010-12-03",
      "겸직 장관 (18대 의원); date approx; verify"),

    # 임태희: 고용노동부 장관 (18대 의원, 경기 성남 중원)
    e("고용노동부", "임태희", "Im Tae-hee",
      "2010-08-10", "2010-11-01",
      "이명박", "Conservative", True,
      "한나라당", "경기 성남시 중원구", 18,
      True, "2010-08-10",
      "겸직 장관 (18대 의원); date approx; verify"),

    # 박재완: 고용노동부 장관 (18대 비례? 또는 17대)
    # Needs agent verification — coding as TRUE pending confirm
    e("고용노동부", "박재완", "Park Jae-wan",
      "2010-11-01", "2012-01-06",
      "이명박", "Conservative", True,
      "한나라당", "비례대표", 18,
      True, "2010-11-01",
      "겸직 장관 (18대 비례의원 추정); date approx; VERIFY 필수 — 17대 비례인지 18대 비례인지 확인"),

    # 박재완: 기획재정부 장관
    e("기획재정부", "박재완", "Park Jae-wan",
      "2012-01-06", "2013-02-24",
      "이명박", "Conservative", True,
      "한나라당", "비례대표", 18,
      True, "2012-01-06",
      "겸직 장관 (18대 비례의원 추정); date approx; VERIFY 필수"),

    # 김금래: 여성가족부 장관 (18대 비례 의원)
    e("여성가족부", "김금래", "Kim Geum-rae",
      "2011-09-15", "2013-02-24",
      "이명박", "Conservative", True,
      "한나라당", "비례대표", 18,
      True, "2011-09-15",
      "겸직 장관 (18대 비례의원); date approx; verify"),

    # --- 비겸직 ministers (이명박 정부) ---

    # 기획재정부 (비겸직)
    e("기획재정부", "강만수", "Kang Man-su",
      "2008-02-29", "2009-02-05",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (관료 출신); date approx"),

    e("기획재정부", "윤증현", "Yun Jeung-hyeon",
      "2009-02-05", "2011-06-01",
      "이명박", "Conservative", False, "", "", "",
      True, "2009-02-05",
      "비겸직 (관료 출신); date approx"),

    # 교육과학기술부 (비겸직)
    e("교육과학기술부", "김도연", "Kim Do-yeon",
      "2008-02-29", "2008-08-06",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (교수 출신, 포항공대 총장); date approx"),

    e("교육과학기술부", "안병만", "Ahn Byeong-man",
      "2008-08-06", "2010-12-03",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-08-06",
      "비겸직 (관료 출신); date approx"),

    # 외교통상부 (비겸직)
    e("외교통상부", "유명환", "Yu Myeong-hwan",
      "2008-02-29", "2010-09-17",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (외교관 출신); date approx"),

    e("외교통상부", "김성환", "Kim Seong-hwan",
      "2010-09-17", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2010-09-17",
      "비겸직 (외교관 출신); date approx"),

    # 통일부 (비겸직)
    e("통일부", "김하중", "Kim Ha-jung",
      "2008-03-02", "2009-09-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-03-02",
      "비겸직 (외교관 출신); date approx"),

    e("통일부", "현인택", "Hyeon In-taek",
      "2009-09-24", "2011-09-15",
      "이명박", "Conservative", False, "", "", "",
      True, "2009-09-24",
      "비겸직 (교수 출신); date approx"),

    e("통일부", "류우익", "Ryu U-ik",
      "2011-09-15", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2011-09-15",
      "비겸직 (교수 출신); date approx"),

    # 법무부 (비겸직)
    e("법무부", "김경한", "Kim Gyeong-han",
      "2008-02-29", "2009-09-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (검사 출신); date approx"),

    e("법무부", "이귀남", "Lee Gwi-nam",
      "2009-09-24", "2011-09-15",
      "이명박", "Conservative", False, "", "", "",
      True, "2009-09-24",
      "비겸직 (검사 출신); date approx"),

    e("법무부", "권재진", "Gwon Jae-jin",
      "2011-09-15", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2011-09-15",
      "비겸직 (검사 출신); date approx"),

    # 국방부 (비겸직)
    e("국방부", "이상희", "Lee Sang-hee",
      "2008-02-29", "2009-09-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (군인 출신); date approx"),

    e("국방부", "김태영", "Kim Tae-yeong",
      "2009-09-24", "2010-11-26",
      "이명박", "Conservative", False, "", "", "",
      True, "2009-09-24",
      "비겸직 (군인 출신); date approx"),

    e("국방부", "김관진", "Kim Gwan-jin",
      "2010-11-26", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2010-11-26",
      "비겸직 (군인 출신); date approx"),

    # 행정안전부 (비겸직)
    e("행정안전부", "원세훈", "Won Se-hun",
      "2008-02-29", "2009-02-05",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (관료 출신); date approx"),

    e("행정안전부", "맹형규", "Maeng Hyeong-gyu",
      "2010-08-10", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2010-08-10",
      "비겸직 (17대 의원 임기 종료 후 임명); date approx; agent confirmed NOT 겸직"),

    # 문화체육관광부 (비겸직)
    e("문화체육관광부", "유인촌", "Yu In-chon",
      "2008-02-29", "2010-08-10",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (연예인 출신); date approx"),

    e("문화체육관광부", "최광식", "Choe Gwang-sik",
      "2011-09-15", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2011-09-15",
      "비겸직 (교수 출신); date approx"),

    # 농림수산식품부 (비겸직)
    e("농림수산식품부", "장태평", "Jang Tae-pyeong",
      "2009-09-24", "2011-09-05",
      "이명박", "Conservative", False, "", "", "",
      True, "2009-09-24",
      "비겸직 (관료 출신); date approx"),

    e("농림수산식품부", "서규용", "Seo Gyu-yong",
      "2012-10-01", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2012-10-01",
      "비겸직 (관료 출신); date approx"),

    # 지식경제부 (비겸직)
    e("지식경제부", "이윤호", "Lee Yun-ho",
      "2008-02-29", "2009-09-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (관료 출신); date approx"),

    e("지식경제부", "최중경", "Choe Jung-gyeong",
      "2011-09-15", "2012-03-01",
      "이명박", "Conservative", False, "", "", "",
      True, "2011-09-15",
      "비겸직 (관료 출신); date approx"),

    e("지식경제부", "홍석우", "Hong Seok-u",
      "2012-03-01", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2012-03-01",
      "비겸직 (기업인 출신); date approx"),

    # 보건복지부 (비겸직)
    e("보건복지부", "김성이", "Kim Seong-i",
      "2008-02-29", "2010-04-16",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (교수 출신); date approx"),

    e("보건복지부", "임채민", "Im Chae-min",
      "2012-09-01", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2012-09-01",
      "비겸직 (관료 출신); date approx"),

    # 환경부 (비겸직)
    e("환경부", "이만의", "Lee Man-eui",
      "2008-02-29", "2011-09-15",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (관료 출신); date approx"),

    e("환경부", "유영숙", "Yu Yeong-suk",
      "2011-09-15", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2011-09-15",
      "비겸직 (교수 출신); date approx"),

    # 고용노동부 (비겸직)
    e("고용노동부", "이영희", "Lee Yeong-hee",
      "2008-02-29", "2010-08-10",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (관료 출신); date approx"),

    e("고용노동부", "이채필", "Lee Chae-pil",
      "2012-03-01", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2012-03-01",
      "비겸직 (관료 출신); date approx"),

    # 여성가족부 (비겸직)
    e("여성가족부", "변도윤", "Byeon Do-yun",
      "2008-03-02", "2009-09-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-03-02",
      "비겸직 (관료 출신); date approx"),

    e("여성가족부", "백희영", "Baek Hui-yeong",
      "2009-09-24", "2011-09-15",
      "이명박", "Conservative", False, "", "", "",
      True, "2009-09-24",
      "비겸직 (교수 출신); date approx"),

    # 국토해양부 (비겸직)
    e("국토해양부", "정종환", "Jeong Jong-hwan",
      "2008-02-29", "2011-06-01",
      "이명박", "Conservative", False, "", "", "",
      True, "2008-02-29",
      "비겸직 (관료 출신); date approx"),

    e("국토해양부", "권도엽", "Gwon Do-yeop",
      "2011-06-01", "2013-02-24",
      "이명박", "Conservative", False, "", "", "",
      True, "2011-06-01",
      "비겸직 (관료 출신); date approx"),

    # =========================================================================
    # 박근혜 정부 (Park Geun-hye) 2013-02-25 ~ 2017-03-10
    # Conservative / 새누리당
    # 19대 MP: 2012-05-30 ~ 2016-05-29
    # 20대 MP: 2016-05-30 ~ 2020-05-29
    # =========================================================================

    # --- 겸직 ministers (missing from manual panel) ---

    # 유정복: 안전행정부(→행정자치부) 장관 (19대 의원, 인천 계양갑)
    # CORRECTED from v1 which had wrong ministry (농림축산식품부)
    e("안전행정부", "유정복", "Yu Jeong-bok",
      "2013-03-11", "2014-07-03",
      "박근혜", "Conservative", True,
      "새누리당", "인천 계양구 갑", 19,
      True, "2013-03-11",
      "겸직 장관 (19대 의원); v1 오류 수정 (농림부→안전행정부); 퇴임 후 인천시장 당선"),

    # 진영: 보건복지부 장관 (19대 의원, 서울 용산)
    # NOT in manual panel (manual panel has 진영 행안부 문재인만 있음)
    e("보건복지부", "진영", "Jin Yeong",
      "2013-03-11", "2013-09-10",
      "박근혜", "Conservative", True,
      "새누리당", "서울 용산구", 19,
      True, "2013-03-11",
      "겸직 장관 (19대); 후 문재인 정부 행안부 장관 (별도 row 있음); date approx"),

    # 조윤선: 여성가족부 장관 (19대 비례 의원)
    e("여성가족부", "조윤선", "Jo Yun-seon",
      "2013-03-11", "2014-07-03",
      "박근혜", "Conservative", True,
      "새누리당", "비례대표", 19,
      True, "2013-03-11",
      "겸직 장관 (19대 비례의원); verify"),

    # 김희정: 여성가족부 장관 (19대 비례 의원)
    e("여성가족부", "김희정", "Kim Hui-jeong",
      "2014-07-03", "2015-03-12",
      "박근혜", "Conservative", True,
      "새누리당", "비례대표", 19,
      True, "2014-07-03",
      "겸직 장관 (19대 비례의원); date approx; verify"),

    # 유기준: 해양수산부 장관 (19대 의원, 부산 서구)
    e("해양수산부", "유기준", "Yu Gi-jun",
      "2014-12-24", "2015-09-24",
      "박근혜", "Conservative", True,
      "새누리당", "부산 서구", 19,
      True, "2014-12-24",
      "겸직 장관 (19대 의원); date approx; verify"),

    # 조윤선: 문화체육관광부 장관 (19대 비례 의원, 임기 2016-05까지)
    e("문화체육관광부", "조윤선", "Jo Yun-seon",
      "2015-12-01", "2017-01-20",
      "박근혜", "Conservative", True,
      "새누리당", "비례대표", 19,
      True, "2015-12-01",
      "겸직 장관 (19대 비례의원; 임기 2016-05까지 겸직); date approx; verify"),

    # 이주영: 해양수산부 장관 (19대 의원, 경남 창원 의창)
    e("해양수산부", "이주영", "Lee Ju-yeong",
      "2013-03-22", "2014-12-24",
      "박근혜", "Conservative", True,
      "새누리당", "경남 창원시 의창구", 19,
      True, "2013-03-22",
      "겸직 장관 (19대 의원); 세월호 대응; date approx"),

    # 강은희: 여성가족부 장관 (19대 비례)
    # NOT in manual panel
    e("여성가족부", "강은희", "Kang Eun-hee",
      "2015-03-12", "2016-08-18",
      "박근혜", "Conservative", True,
      "새누리당", "비례대표", 19,
      True, "2015-03-12",
      "겸직 장관 (19대 비례의원); 의원직 유지 논란 → 사퇴"),

    # 황우여: 교육부 장관 (19대 의원, 인천 남동갑)
    # Already in manual panel

    # 최경환: 기획재정부 부총리 (19대 의원, 대구 달성군)
    # Already in manual panel

    # 이완구: 국무총리 (19대 의원)
    # Already in manual panel

    # 강은희: 여성가족부 장관 (19대 비례)
    # Already in manual panel

    # 진영: 보건복지부 (19대)
    # Already in manual panel

    # --- 비겸직 ministers (박근혜 정부) ---

    # 미래창조과학부 (비겸직)
    e("미래창조과학부", "최문기", "Choe Mun-gi",
      "2013-03-22", "2014-07-03",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-22",
      "비겸직 (교수 출신, KAIST); date approx"),

    e("미래창조과학부", "최양희", "Choe Yang-hee",
      "2014-07-03", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2014-07-03",
      "비겸직 (교수 출신, 서울대); date approx"),

    # 외교부 (비겸직)
    e("외교부", "윤병세", "Yun Byeong-se",
      "2013-03-11", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-11",
      "비겸직 (외교관 출신)"),

    # 통일부 (비겸직)
    e("통일부", "류길재", "Ryu Gil-jae",
      "2013-03-11", "2014-07-03",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-11",
      "비겸직 (교수 출신); date approx"),

    e("통일부", "홍용표", "Hong Yong-pyo",
      "2015-02-17", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2015-02-17",
      "비겸직 (교수 출신); date approx"),

    # 법무부 (비겸직)
    e("법무부", "황교안", "Hwang Gyo-ahn",
      "2013-03-11", "2015-02-16",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-11",
      "비겸직 (검사 출신); 후 국무총리 별도 row"),

    e("법무부", "김현웅", "Kim Hyeon-ung",
      "2015-02-17", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2015-02-17",
      "비겸직 (검사 출신); date approx"),

    # 국방부 (비겸직)
    e("국방부", "김관진", "Kim Gwan-jin",
      "2013-02-25", "2014-07-03",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-02-25",
      "비겸직 (군인 출신; 이명박 정부에서 유임); date approx"),

    e("국방부", "한민구", "Han Min-gu",
      "2014-07-03", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2014-07-03",
      "비겸직 (군인 출신); date approx"),

    # 행정자치부 (비겸직, 안전행정부→행정자치부)
    e("행정자치부", "강병규", "Kang Byeong-gyu",
      "2014-07-03", "2014-11-19",
      "박근혜", "Conservative", False, "", "", "",
      True, "2014-07-03",
      "비겸직 (관료 출신); date approx"),

    e("행정자치부", "정종섭", "Jeong Jong-seop",
      "2014-11-19", "2016-01-13",
      "박근혜", "Conservative", False, "", "", "",
      True, "2014-11-19",
      "비겸직 (교수 출신, 서울대); date approx"),

    e("행정자치부", "홍윤식", "Hong Yun-sik",
      "2016-01-13", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2016-01-13",
      "비겸직 (관료 출신); date approx"),

    # 문화체육관광부 (비겸직)
    e("문화체육관광부", "유진룡", "Yu Jin-ryong",
      "2013-03-11", "2014-07-03",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-11",
      "비겸직 (관료 출신); date approx"),

    e("문화체육관광부", "김종덕", "Kim Jong-deok",
      "2014-07-03", "2015-12-01",
      "박근혜", "Conservative", False, "", "", "",
      True, "2014-07-03",
      "비겸직 (교수 출신); date approx"),

    # 농림축산식품부 (비겸직)
    e("농림축산식품부", "이동필", "Lee Dong-pil",
      "2013-03-11", "2016-01-13",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-11",
      "비겸직 (관료 출신); date approx"),

    e("농림축산식품부", "김재수", "Kim Jae-su",
      "2016-01-13", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2016-01-13",
      "비겸직 (관료 출신); date approx"),

    # 산업통상자원부 (비겸직)
    e("산업통상자원부", "윤상직", "Yun Sang-jik",
      "2013-03-11", "2016-01-13",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-11",
      "비겸직 (관료 출신); date approx"),

    e("산업통상자원부", "주형환", "Ju Hyeong-hwan",
      "2016-01-13", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2016-01-13",
      "비겸직 (관료 출신); date approx"),

    # 보건복지부 (비겸직)
    e("보건복지부", "문형표", "Mun Hyeong-pyo",
      "2013-09-10", "2015-02-17",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-09-10",
      "비겸직 (교수 출신); date approx"),

    e("보건복지부", "정진엽", "Jeong Jin-yeop",
      "2015-02-17", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2015-02-17",
      "비겸직 (의사 출신); date approx"),

    # 환경부 (비겸직)
    e("환경부", "윤성규", "Yun Seong-gyu",
      "2013-03-11", "2016-09-09",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-11",
      "비겸직 (관료 출신); date approx"),

    e("환경부", "조경규", "Jo Gyeong-gyu",
      "2016-09-09", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2016-09-09",
      "비겸직 (관료 출신); date approx"),

    # 고용노동부 (비겸직)
    e("고용노동부", "방하남", "Bang Ha-nam",
      "2013-03-11", "2014-07-03",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-11",
      "비겸직 (교수 출신); date approx"),

    e("고용노동부", "이기권", "Lee Gi-gweon",
      "2014-07-03", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2014-07-03",
      "비겸직 (관료 출신); date approx"),

    # 국토교통부 (비겸직)
    e("국토교통부", "서승환", "Seo Seung-hwan",
      "2013-03-11", "2014-07-16",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-11",
      "비겸직 (교수 출신); date approx"),

    e("국토교통부", "유일호", "Yu Il-ho",
      "2014-07-16", "2016-01-13",
      "박근혜", "Conservative", False, "", "", "",
      True, "2014-07-16",
      "비겸직 (교수 출신); date approx; verify"),

    e("국토교통부", "강호인", "Kang Ho-in",
      "2016-01-13", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2016-01-13",
      "비겸직 (관료 출신); date approx"),

    # 해양수산부 (비겸직)
    e("해양수산부", "윤진숙", "Yun Jin-suk",
      "2013-03-22", "2013-10-28",
      "박근혜", "Conservative", False, "", "", "",
      True, "2013-03-22",
      "비겸직 (관료 출신); date approx"),

    e("해양수산부", "김영석", "Kim Yeong-seok",
      "2015-09-24", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2015-09-24",
      "비겸직 (관료 출신); date approx"),

    # 국민안전처 (비겸직, 2014-11 신설)
    e("국민안전처", "박인용", "Park In-yong",
      "2014-11-19", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2014-11-19",
      "비겸직 (군인 출신, 해병대); date approx"),

    # 기재부 (비겸직)
    e("기획재정부", "유일호", "Yu Il-ho",
      "2016-01-13", "2017-03-10",
      "박근혜", "Conservative", False, "", "", "",
      True, "2016-01-13",
      "비겸직 (교수 출신); 국토부 후임 기재부 부총리; date approx"),

    # =========================================================================
    # 문재인 정부 (Moon Jae-in) 2017-05-10 ~ 2022-05-09
    # Progressive / 더불어민주당
    # 20대 MP: 2016-05-30 ~ 2020-05-29
    # 21대 MP: 2020-05-30 ~ 2024-05-29
    # =========================================================================

    # --- 겸직 ministers (missing from manual panel) ---

    # 정세균: 국무총리 (20대 의원, 전북 전주 덕진)
    # Already in manual panel

    # 이낙연: 국무총리 (20대 의원, 전남 순천)
    # Already in manual panel

    # 김부겸: 행정안전부 장관 (20대 의원, 대구 수성갑)
    # Already in manual panel

    # 김영춘: 해양수산부 장관 (20대 의원)
    # Already in manual panel

    # 도종환: 문화체육관광부 장관 (20대 의원)
    # Already in manual panel

    # 김영록: 농림축산식품부 장관 (20대 의원)
    # Already in manual panel

    # 김영주: 고용노동부 장관 (20대 의원)
    # Added in v1 new_entries

    # 김현미: 국토교통부 장관 (20대 의원)
    # Already in manual panel

    # 이개호: 농림부 장관 (20대 의원)
    # Added in v1 new_entries

    # 진선미: 여성가족부 장관 (20대 의원)
    # Added in v1 new_entries

    # 유은혜: 교육부 장관 (20대 의원)
    # Already in manual panel

    # 박영선: 중소벤처기업부 장관 (20대 의원)
    # Already in manual panel

    # 진영: 행정안전부 장관 (20대 의원)
    # Already in manual panel

    # 추미애: 법무부 장관 (21대 의원)
    # Already in manual panel

    # 이인영: 통일부 장관 (21대 의원)
    # Added in v1 new_entries

    # 황희: 문체부 장관 (21대 의원)
    # Added in v1 new_entries

    # 전해철: 행안부 장관 (21대 의원)
    # Already in manual panel

    # 한정애: 환경부 장관 (21대 의원)
    # Added in v1 new_entries

    # 박범계: 법무부 장관 (21대 의원)
    # Added in v1 new_entries

    # 권칠승: 중기부 장관 (21대 의원)
    # Added in v1 new_entries

    # 김영주: 고용노동부 장관 (20대 의원, 서울 영등포을)
    e("고용노동부", "김영주", "Kim Yeong-ju",
      "2017-06-14", "2018-11-08",
      "문재인", "Progressive", True,
      "더불어민주당", "서울 영등포구 을", 20,
      True, "2017-06-14",
      "겸직 장관 (20대); 노동운동 출신"),

    # 이개호: 농림축산식품부 장관 (20대 의원, 전남 담양·함평·영광·장성)
    e("농림축산식품부", "이개호", "Lee Gae-ho",
      "2018-04-27", "2019-04-08",
      "문재인", "Progressive", True,
      "더불어민주당", "전남 담양·함평·영광·장성", 20,
      True, "2018-04-27",
      "겸직 장관 (20대)"),

    # 진선미: 여성가족부 장관 (20대 의원, 서울 강동을)
    e("여성가족부", "진선미", "Jin Seon-mi",
      "2018-09-06", "2019-04-05",
      "문재인", "Progressive", True,
      "더불어민주당", "서울 강동구 을", 20,
      True, "2018-09-06",
      "겸직 장관 (20대)"),

    # 이인영: 통일부 장관 (21대 의원, 서울 구로갑)
    e("통일부", "이인영", "Lee In-yeong",
      "2020-07-27", "2021-11-03",
      "문재인", "Progressive", True,
      "더불어민주당", "서울 구로구 갑", 21,
      True, "2020-07-27",
      "겸직 장관 (21대)"),

    # 황희: 문화체육관광부 장관 (21대 의원, 경기 김포을)
    e("문화체육관광부", "황희", "Hwang Hee",
      "2020-12-29", "2022-05-09",
      "문재인", "Progressive", True,
      "더불어민주당", "경기 김포시 을", 21,
      True, "2020-12-29",
      "겸직 장관 (21대)"),

    # 한정애: 환경부 장관 (21대 의원, 서울 강서갑)
    e("환경부", "한정애", "Han Jeong-ae",
      "2021-01-20", "2022-05-09",
      "문재인", "Progressive", True,
      "더불어민주당", "서울 강서구 갑", 21,
      True, "2021-01-20",
      "겸직 장관 (21대)"),

    # 박범계: 법무부 장관 (21대 의원, 대전 서구을)
    e("법무부", "박범계", "Park Beom-gye",
      "2021-01-20", "2022-05-10",
      "문재인", "Progressive", True,
      "더불어민주당", "대전 서구 을", 21,
      True, "2021-01-20",
      "겸직 장관 (21대)"),

    # 권칠승: 중소벤처기업부 장관 (21대 의원, 경기 화성을)
    e("중소벤처기업부", "권칠승", "Gwon Chil-seung",
      "2021-04-08", "2022-05-09",
      "문재인", "Progressive", True,
      "더불어민주당", "경기 화성시 을", 21,
      True, "2021-04-08",
      "겸직 장관 (21대)"),

    # 임혜숙: 과학기술정보통신부 장관 (21대 비례 의원)
    e("과학기술정보통신부", "임혜숙", "Im Hye-suk",
      "2021-05-14", "2022-05-09",
      "문재인", "Progressive", True,
      "더불어민주당", "비례대표", 21,
      True, "2021-05-14",
      "겸직 장관 (21대 비례의원); 공학자 출신"),

    # --- 비겸직 ministers (문재인 정부) ---

    # 기획재정부 (비겸직)
    e("기획재정부", "김동연", "Kim Dong-yeon",
      "2017-06-09", "2018-12-07",
      "문재인", "Progressive", False, "", "", "",
      True, "2017-06-09",
      "비겸직 (관료 출신, 한국개발연구원장)"),

    e("기획재정부", "홍남기", "Hong Nam-gi",
      "2018-12-07", "2022-05-09",
      "문재인", "Progressive", False, "", "", "",
      True, "2018-12-07",
      "비겸직 (관료 출신)"),

    # 교육부 (비겸직)
    e("교육부", "김상곤", "Kim Sang-gon",
      "2017-07-03", "2018-10-02",
      "문재인", "Progressive", False, "", "", "",
      True, "2017-07-03",
      "비겸직 (교육감 출신)"),

    # 과학기술정보통신부 (비겸직)
    e("과학기술정보통신부", "유영민", "Yu Yeong-min",
      "2017-07-03", "2020-01-14",
      "문재인", "Progressive", False, "", "", "",
      True, "2017-07-03",
      "비겸직 (기업인 출신)"),

    e("과학기술정보통신부", "최기영", "Choe Gi-yeong",
      "2019-08-09", "2021-05-14",
      "문재인", "Progressive", False, "", "", "",
      True, "2019-08-09",
      "비겸직 (교수 출신)"),

    # 외교부 (비겸직)
    # 강경화: already in manual panel

    e("외교부", "정의용", "Jeong Ui-yong",
      "2021-02-09", "2022-05-09",
      "문재인", "Progressive", False, "", "", "",
      True, "2021-02-09",
      "비겸직 (외교관 출신)"),

    # 통일부 (비겸직)
    e("통일부", "조명균", "Jo Myeong-gyun",
      "2017-07-03", "2019-04-08",
      "문재인", "Progressive", False, "", "", "",
      True, "2017-07-03",
      "비겸직 (관료 출신); agent confirmed NOT 겸직"),

    e("통일부", "김연철", "Kim Yeon-cheol",
      "2019-04-08", "2020-07-27",
      "문재인", "Progressive", False, "", "", "",
      True, "2019-04-08",
      "비겸직 (교수 출신)"),

    # 국방부 (비겸직)
    e("국방부", "송영무", "Song Yeong-mu",
      "2017-07-03", "2019-01-14",
      "문재인", "Progressive", False, "", "", "",
      True, "2017-07-03",
      "비겸직 (군인 출신)"),

    e("국방부", "정경두", "Jeong Gyeong-du",
      "2019-01-14", "2020-09-18",
      "문재인", "Progressive", False, "", "", "",
      True, "2019-01-14",
      "비겸직 (군인 출신)"),

    e("국방부", "서욱", "Seo Wook",
      "2020-09-18", "2022-05-09",
      "문재인", "Progressive", False, "", "", "",
      True, "2020-09-18",
      "비겸직 (군인 출신)"),

    # 법무부 (비겸직)
    # 박상기: already in manual panel
    # 조국: already in manual panel

    # 문화체육관광부 (비겸직)
    e("문화체육관광부", "박양우", "Park Yang-u",
      "2019-04-08", "2020-12-29",
      "문재인", "Progressive", False, "", "", "",
      True, "2019-04-08",
      "비겸직 (관료 출신)"),

    # 농림축산식품부 (비겸직)
    e("농림축산식품부", "김현수", "Kim Hyeon-su",
      "2019-04-08", "2022-05-09",
      "문재인", "Progressive", False, "", "", "",
      True, "2019-04-08",
      "비겸직 (관료 출신)"),

    # 산업통상자원부 (비겸직)
    e("산업통상자원부", "백운규", "Baek Un-gyu",
      "2017-07-03", "2019-03-08",
      "문재인", "Progressive", False, "", "", "",
      True, "2017-07-03",
      "비겸직 (교수 출신)"),

    e("산업통상자원부", "성윤모", "Seong Yun-mo",
      "2019-03-08", "2021-02-19",
      "문재인", "Progressive", False, "", "", "",
      True, "2019-03-08",
      "비겸직 (관료 출신)"),

    e("산업통상자원부", "문승욱", "Mun Seung-uk",
      "2021-02-19", "2022-05-09",
      "문재인", "Progressive", False, "", "", "",
      True, "2021-02-19",
      "비겸직 (관료 출신)"),

    # 보건복지부 (비겸직)
    e("보건복지부", "박능후", "Park Neung-hu",
      "2017-07-03", "2021-01-20",
      "문재인", "Progressive", False, "", "", "",
      True, "2017-07-03",
      "비겸직 (교수 출신)"),

    e("보건복지부", "권덕철", "Gwon Deok-cheol",
      "2021-01-20", "2022-05-09",
      "문재인", "Progressive", False, "", "", "",
      True, "2021-01-20",
      "비겸직 (관료 출신)"),

    # 환경부 (비겸직)
    e("환경부", "김은경", "Kim Eun-gyeong",
      "2017-07-03", "2019-01-14",
      "문재인", "Progressive", False, "", "", "",
      True, "2017-07-03",
      "비겸직 (환경운동가 출신)"),

    e("환경부", "조명래", "Jo Myeong-rae",
      "2019-01-14", "2021-01-20",
      "문재인", "Progressive", False, "", "", "",
      True, "2019-01-14",
      "비겸직 (교수 출신)"),

    # 고용노동부 (비겸직)
    e("고용노동부", "이재갑", "Lee Jae-gap",
      "2018-11-08", "2021-01-20",
      "문재인", "Progressive", False, "", "", "",
      True, "2018-11-08",
      "비겸직 (관료 출신)"),

    e("고용노동부", "안경덕", "Ahn Gyeong-deok",
      "2021-01-20", "2022-05-09",
      "문재인", "Progressive", False, "", "", "",
      True, "2021-01-20",
      "비겸직 (관료 출신)"),

    # 여성가족부 (비겸직)
    e("여성가족부", "정현백", "Jeong Hyeon-baek",
      "2017-07-03", "2018-09-06",
      "문재인", "Progressive", False, "", "", "",
      True, "2017-07-03",
      "비겸직 (교수 출신)"),

    e("여성가족부", "이정옥", "Lee Jeong-ok",
      "2019-04-05", "2020-12-29",
      "문재인", "Progressive", False, "", "", "",
      True, "2019-04-05",
      "비겸직 (교수 출신)"),

    e("여성가족부", "정영애", "Jeong Yeong-ae",
      "2021-01-20", "2022-05-09",
      "문재인", "Progressive", False, "", "", "",
      True, "2021-01-20",
      "비겸직 (활동가 출신)"),

    # 국토교통부 (비겸직)
    e("국토교통부", "변창흠", "Byeon Chang-heum",
      "2020-12-29", "2021-04-16",
      "문재인", "Progressive", False, "", "", "",
      True, "2020-12-29",
      "비겸직 (교수 출신)"),

    e("국토교통부", "노형욱", "No Hyeong-uk",
      "2021-04-16", "2022-05-09",
      "문재인", "Progressive", False, "", "", "",
      True, "2021-04-16",
      "비겸직 (관료 출신)"),

    # 해양수산부 (비겸직)
    e("해양수산부", "문성혁", "Mun Seong-hyeok",
      "2018-09-21", "2022-05-09",
      "문재인", "Progressive", False, "", "", "",
      True, "2018-09-21",
      "비겸직 (교수 출신)"),

    # 중소벤처기업부 (비겸직)
    e("중소벤처기업부", "홍종학", "Hong Jong-hak",
      "2017-11-17", "2019-04-08",
      "문재인", "Progressive", False, "", "", "",
      True, "2017-11-17",
      "비겸직 (19대 비례 후 의원직 사임, 교수 출신)"),

    # =========================================================================
    # 윤석열 정부 (Yoon Suk-yeol) 2022-05-10 ~ 2025-06-03
    # Conservative / 국민의힘
    # 21대 MP: 2020-05-30 ~ 2024-05-29
    # 22대 MP: 2024-05-30 ~
    # =========================================================================

    # --- 겸직 ministers ---

    # 원희룡: 국토교통부 (21대 의원, 제주 제주갑)
    e("국토교통부", "원희룡", "Won Hee-ryong",
      "2022-05-10", "2023-12-28",
      "윤석열", "Conservative", True,
      "국민의힘", "제주 제주시 갑", 21,
      True, "2022-05-10",
      "겸직 장관 (21대); 제주도지사 출신"),

    # 이영: 중소벤처기업부 (21대 의원, 대전 중구)
    e("중소벤처기업부", "이영", "Lee Yeong",
      "2022-05-10", "2023-12-27",
      "윤석열", "Conservative", True,
      "국민의힘", "대전 중구", 21,
      True, "2022-05-10",
      "겸직 장관 (21대)"),

    # 권영세: 통일부 (21대 의원, 서울 용산)
    # Already in manual panel

    # 추경호: 기획재정부 부총리 (21대 의원, 대구 달성군)
    # Already in manual panel

    # 박진: 외교부 (21대 의원, 서울 강남갑)
    # Already in manual panel

    # 박민식: 국가보훈부 (21대 의원, 부산 북강서갑)
    e("국가보훈부", "박민식", "Park Min-sik",
      "2023-06-01", "2024-09-01",
      "윤석열", "Conservative", True,
      "국민의힘", "부산 북구·강서구 갑", 21,
      True, "2023-06-01",
      "겸직 장관 (21대 의원); date approx; verify"),

    # --- 비겸직 ministers (윤석열 정부) ---

    # 교육부 (비겸직)
    e("교육부", "박순애", "Park Sun-ae",
      "2022-07-29", "2022-08-09",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-07-29",
      "비겸직 (교수 출신); 단기 재임"),

    e("교육부", "이주호", "Lee Ju-ho",
      "2022-11-09", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-11-09",
      "비겸직 (18대 의원이었으나 21대/22대 아님; 교수 출신); date approx"),

    # 과학기술정보통신부 (비겸직)
    e("과학기술정보통신부", "이종호", "Lee Jong-ho",
      "2022-05-10", "2024-08-01",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-05-10",
      "비겸직 (교수 출신)"),

    e("과학기술정보통신부", "유상임", "Yu Sang-im",
      "2024-08-01", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2024-08-01",
      "비겸직 (교수 출신); date approx"),

    # 법무부 (비겸직)
    # 한동훈: added in v1

    e("법무부", "박성재", "Park Seong-jae",
      "2024-01-22", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2024-01-22",
      "비겸직 (검사 출신); date approx"),

    # 국방부 (비겸직)
    # 이종섭: added in v1

    e("국방부", "신원식", "Sin Won-sik",
      "2023-09-22", "2024-11-22",
      "윤석열", "Conservative", False, "", "", "",
      True, "2023-09-22",
      "비겸직 (군인 출신)"),

    e("국방부", "김용현", "Kim Yong-hyeon",
      "2024-11-22", "2024-12-06",
      "윤석열", "Conservative", False, "", "", "",
      True, "2024-11-22",
      "비겸직 (군인 출신); 12.3 계엄 관련 구속"),

    # 행정안전부 (비겸직)
    # 이상민: already in manual panel (FALSE)

    # 국가보훈부 (비겸직)
    e("국가보훈부", "강정애", "Kang Jeong-ae",
      "2023-09-01", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2023-09-01",
      "비겸직; date approx"),

    # 문화체육관광부 (비겸직)
    e("문화체육관광부", "박보균", "Park Bo-gyun",
      "2022-05-10", "2023-09-22",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-05-10",
      "비겸직 (18대 의원이었으나 21대/22대 아님; 언론인 출신)"),

    e("문화체육관광부", "유인촌", "Yu In-chon",
      "2023-09-22", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2023-09-22",
      "비겸직 (연예인 출신; 이명박 정부에도 동일 직위)"),

    # 농림축산식품부 (비겸직)
    e("농림축산식품부", "정황근", "Jeong Hwang-geun",
      "2022-05-10", "2023-01-10",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-05-10",
      "비겸직 (20대 비례의원이었으나 21대 아님; 농업전문가); date approx"),

    # 산업통상자원부 (비겸직)
    e("산업통상자원부", "이창양", "Lee Chang-yang",
      "2022-05-10", "2023-10-01",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-05-10",
      "비겸직 (교수 출신)"),

    e("산업통상자원부", "방문규", "Bang Mun-gyu",
      "2023-10-01", "2024-08-01",
      "윤석열", "Conservative", False, "", "", "",
      True, "2023-10-01",
      "비겸직 (관료 출신); date approx"),

    e("산업통상자원부", "안덕근", "Ahn Deok-geun",
      "2024-01-22", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2024-01-22",
      "비겸직 (교수/관료 출신); date approx"),

    # 보건복지부 (비겸직)
    e("보건복지부", "조규홍", "Jo Gyu-hong",
      "2022-05-10", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-05-10",
      "비겸직 (관료 출신)"),

    # 환경부 (비겸직)
    e("환경부", "한화진", "Han Hwa-jin",
      "2022-05-10", "2024-08-01",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-05-10",
      "비겸직 (교수 출신)"),

    e("환경부", "김완섭", "Kim Wan-seop",
      "2024-08-01", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2024-08-01",
      "비겸직 (관료 출신); date approx"),

    # 고용노동부 (비겸직)
    e("고용노동부", "이정식", "Lee Jeong-sik",
      "2022-05-10", "2024-07-01",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-05-10",
      "비겸직 (관료 출신)"),

    e("고용노동부", "김문수", "Kim Moon-su",
      "2024-07-01", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2024-07-01",
      "비겸직 (15·16대 의원이었으나 22대 아님; 경기도지사 출신); date approx"),

    # 여성가족부 (비겸직)
    e("여성가족부", "김현숙", "Kim Hyeon-suk",
      "2022-05-10", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-05-10",
      "비겸직 (20대 비례의원이었으나 21대 아님); date approx"),

    # 해양수산부 (비겸직)
    e("해양수산부", "조승환", "Jo Seung-hwan",
      "2022-05-10", "2023-12-29",
      "윤석열", "Conservative", False, "", "", "",
      True, "2022-05-10",
      "비겸직 (관료 출신)"),

    e("해양수산부", "강도형", "Kang Do-hyeong",
      "2023-12-29", "2025-06-03",
      "윤석열", "Conservative", False, "", "", "",
      True, "2023-12-29",
      "비겸직; date approx"),

    # =========================================================================
    # 이재명 정부 (Lee Jae-myung) 2025-06-04 ~
    # Progressive / 더불어민주당
    # 22대 MP: 2024-05-30 ~
    # =========================================================================

    # PM (겸직)
    e("국무총리", "김민석", "Kim Min-seok",
      "2025-07-03", "",
      "이재명", "Progressive", True,
      "더불어민주당", "인천 계양구 을", 22,
      True, "2025-07-03",
      "겸직 총리 (22대)"),

    # 겸직 장관
    e("통일부", "정동영", "Jeong Dong-yeong",
      "2025-07-25", "",
      "이재명", "Progressive", True,
      "더불어민주당", "전북 전주시 완산구 갑", 22,
      True, "2025-07-25",
      "겸직 장관 (22대)"),

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
      "겸직 장관 (22대); 신설 부처"),

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
      "겸직 장관 (22대); date approx"),

    # 비겸직 장관 (이재명 정부)
    e("기획재정부", "구윤철", "Gu Yun-cheol",
      "2026-01-02", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2026-01-02",
      "비겸직; 부총리 겸 기재부장관"),

    e("과학기술정보통신부", "배경훈", "Bae Gyeong-hun",
      "2025-10-01", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2025-10-01",
      "비겸직; 과기부총리"),

    e("교육부", "최교진", "Choi Gyo-jin",
      "2025-10-01", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2025-10-01",
      "비겸직"),

    e("외교부", "조현", "Jo Hyeon",
      "2025-07-18", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2025-07-18",
      "비겸직 (외교관 출신)"),

    e("국가보훈부", "권오을", "Gwon O-eul",
      "2025-07-25", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2025-07-25",
      "비겸직"),

    e("문화체육관광부", "최휘영", "Choi Hwi-yeong",
      "2025-07-31", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2025-07-31",
      "비겸직"),

    e("농림축산식품부", "송미령", "Song Mi-ryeong",
      "2025-06-04", "",
      "이재명", "Progressive", False, "", "", "",
      False, "",
      "비겸직; 윤석열 정부에서 유임"),

    e("산업통상자원부", "김정관", "Kim Jeong-gwan",
      "2025-10-01", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2025-10-01",
      "비겸직"),

    e("보건복지부", "정은경", "Jeong Eun-gyeong",
      "2025-07-21", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2025-07-21",
      "비겸직 (전 질병관리청장)"),

    e("고용노동부", "김영훈", "Kim Yeong-hun",
      "2025-07-21", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2025-07-21",
      "비겸직"),

    e("성평등가족부", "원민경", "Won Min-gyeong",
      "2025-10-01", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2025-10-01",
      "비겸직; 신설 부처"),

    e("중소벤처기업부", "한성숙", "Han Seong-suk",
      "2025-07-23", "",
      "이재명", "Progressive", False, "", "", "",
      True, "2025-07-23",
      "비겸직 (네이버 대표 출신)"),

]

# ---------------------------------------------------------------------------
# Build comprehensive dataframe
# ---------------------------------------------------------------------------

# Standardize existing df columns
for col in COLS:
    if col not in existing.columns:
        existing[col] = ""

existing_clean = existing[COLS].copy()

new_df = pd.DataFrame(new_entries, columns=COLS)

comprehensive = pd.concat([existing_clean, new_df], ignore_index=True)

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

# Normalize dual_office to True/False bool
def normalize_dual(val):
    if isinstance(val, bool):
        return val
    if str(val).strip().lower() in ("true", "1", "yes"):
        return True
    return False

comprehensive["dual_office"] = comprehensive["dual_office"].apply(normalize_dual)

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

print("=== Entries flagged as 'verify' ===")
verify_entries = comprehensive[comprehensive["notes"].str.contains("verify", na=False)]
print(f"Count: {len(verify_entries)}")
for _, row in verify_entries.iterrows():
    d = "T" if row["dual_office"] else "F"
    print(f"  [{d}] {row['admin']} | {row['ministry']} | {row['name']} | {row['start'][:7]}")

print()
print("=== 겸직 entries by admin ===")
dual_entries = comprehensive[comprehensive["dual_office"] == True]
for admin in ["김대중", "노무현", "이명박", "박근혜", "문재인", "윤석열", "이재명"]:
    rows = dual_entries[dual_entries["admin"] == admin]
    print(f"  {admin}: {len(rows)}건")
    for _, r in rows.iterrows():
        print(f"    {r['ministry']} | {r['name']} | {r['start'][:7]}")
