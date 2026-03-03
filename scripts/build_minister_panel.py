"""
겸직 장관 패널 구축 스크립트
Build Dual-Office Minister Panel

Step 1: 역대 국무위원 목록 수집 (from 관보 / e-나라지표)
Step 2: 각 임명 시점에 현직 국회의원인지 확인
Step 3: minister_panel.csv 완성

Usage:
    python build_minister_panel.py

Output:
    data/minister_panel.csv  -- 겸직/비겸직 여부 포함 장관 패널
    data/mp_history.csv      -- 역대 의원 재임 이력 (검증용)
"""

import pandas as pd
import requests
import json
import time
import logging
from pathlib import Path
from datetime import datetime, date

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

OPEN_ASSEMBLY_API = "https://open.assembly.go.kr/portal/openapi"

# 분석 대상 기간: 16대~22대 (2000-2024)
# 인사청문회 제도 도입: 2000년 (국무총리), 2005년 (전 국무위원 확대)
ASSEMBLY_TERMS = {
    "16": ("2000-05-30", "2004-05-29"),
    "17": ("2004-05-30", "2008-05-29"),
    "18": ("2008-05-30", "2012-05-29"),
    "19": ("2012-05-30", "2016-05-29"),
    "20": ("2016-05-30", "2020-05-29"),
    "21": ("2020-05-30", "2024-05-29"),
    "22": ("2024-05-30", "2028-05-29"),
}


def get_mp_history(api_key: str) -> pd.DataFrame:
    """
    국회 Open API에서 역대 의원 재임 이력을 수집.
    endpoint: ALLNAMEMBER (역대 국회의원)
    """
    url = f"{OPEN_ASSEMBLY_API}/ALLNAMEMBER"
    all_records = []
    page = 1
    page_size = 100

    while True:
        params = {
            "KEY": api_key,
            "Type": "json",
            "pIndex": page,
            "pSize": page_size,
        }
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # API 응답 구조에 따라 파싱
            if "ALLNAMEMBER" not in data:
                logger.warning(f"예상 외 응답 구조: {list(data.keys())}")
                break

            records = data["ALLNAMEMBER"][1].get("row", [])
            if not records:
                break

            all_records.extend(records)
            logger.info(f"p{page}: {len(records)}건 수집 (누적 {len(all_records)})")
            page += 1
            time.sleep(0.3)

        except Exception as e:
            logger.error(f"p{page} 수집 실패: {e}")
            break

    df = pd.DataFrame(all_records)
    logger.info(f"역대 의원 총 {len(df)}명 수집")
    return df


def load_minister_list(csv_path: Path) -> pd.DataFrame:
    """
    수기 작성된 장관 목록 로드.
    필수 컬럼: name, ministry, start, end, admin
    """
    df = pd.read_csv(csv_path)
    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    return df


def check_dual_office(minister_row: pd.Series, mp_df: pd.DataFrame) -> dict:
    """
    특정 장관 임명 시점에 현직 국회의원인지 확인.

    Args:
        minister_row: 장관 정보 (name, start, end)
        mp_df: 역대 의원 이력 DataFrame

    Returns:
        dict: {dual_office: bool, mp_party: str, mp_district: str, assembly_num: str}
    """
    name = minister_row["name"]
    appt_date = minister_row["start"]

    if pd.isna(appt_date):
        return {"dual_office": False, "mp_party_at_appt": "", "mp_district": "", "assembly_num_at_appt": ""}

    # 이름으로 의원 후보 검색 (HG_NM 컬럼)
    name_col = "HG_NM" if "HG_NM" in mp_df.columns else mp_df.columns[0]
    candidates = mp_df[mp_df[name_col] == name].copy()

    if candidates.empty:
        return {"dual_office": False, "mp_party_at_appt": "", "mp_district": "", "assembly_num_at_appt": ""}

    # 임명일이 의원 재임 기간과 겹치는지 확인
    # 컬럼명은 API 응답 구조에 따라 조정 필요
    # 예상 컬럼: UNITS (대수), POLY_NM (정당), CMIT_NM (위원회)
    result = {"dual_office": False, "mp_party_at_appt": "", "mp_district": "", "assembly_num_at_appt": ""}

    for _, mp in candidates.iterrows():
        # 대수별 재임 기간으로 날짜 추정
        units = str(mp.get("UNITS", ""))
        for term_num, (term_start, term_end) in ASSEMBLY_TERMS.items():
            if term_num in units.split(","):
                ts = datetime.strptime(term_start, "%Y-%m-%d").date()
                te = datetime.strptime(term_end, "%Y-%m-%d").date()
                if ts <= appt_date.date() <= te:
                    result["dual_office"] = True
                    result["mp_party_at_appt"] = mp.get("POLY_NM", "")
                    result["mp_district"] = mp.get("ORIG_NM", "")
                    result["assembly_num_at_appt"] = term_num
                    break
        if result["dual_office"]:
            break

    return result


def build_panel(api_key: str, minister_csv: Path) -> pd.DataFrame:
    """전체 패널 구축 파이프라인."""

    logger.info("Step 1: 역대 의원 이력 수집")
    mp_df = get_mp_history(api_key)
    mp_df.to_csv(RAW_DIR / "mp_history_raw.csv", index=False, encoding="utf-8-sig")

    logger.info("Step 2: 장관 목록 로드")
    minister_df = load_minister_list(minister_csv)

    logger.info("Step 3: 겸직 여부 확인")
    dual_info = minister_df.apply(lambda row: check_dual_office(row, mp_df), axis=1)
    dual_df = pd.DataFrame(dual_info.tolist())
    panel = pd.concat([minister_df, dual_df], axis=1)

    # 파생 변수 계산
    panel["tenure_days"] = (panel["end"] - panel["start"]).dt.days
    panel["tenure_months"] = panel["tenure_days"] / 30.44

    out_path = DATA_DIR / "minister_panel.csv"
    panel.to_csv(out_path, index=False, encoding="utf-8-sig")
    logger.info(f"패널 저장: {out_path} ({len(panel)}명)")
    logger.info(f"겸직: {panel['dual_office'].sum()}명, 비겸직: {(~panel['dual_office']).sum()}명")

    return panel


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="겸직 장관 패널 구축")
    parser.add_argument("--api-key", required=True, help="국회 Open API 키")
    parser.add_argument(
        "--minister-csv",
        default=str(DATA_DIR / "minister_panel_manual.csv"),
        help="수기 작성 장관 목록 CSV 경로",
    )
    args = parser.parse_args()

    panel = build_panel(args.api_key, Path(args.minister_csv))
    print(panel[["name", "ministry", "start", "dual_office", "mp_party_at_appt"]].to_string())
