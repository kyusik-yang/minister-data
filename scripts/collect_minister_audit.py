"""
Collect 국정감사 (annual audit) transcripts for ministers.
Separate from collect_minister_hearings.py (which handles 인사청문회).

Strategy:
  1. For each minister, identify their committee and tenure period
  2. Scan MNTS_IDs for October of each year during their tenure
  3. Find meetings with "국정감사" in title AND committee match
  4. Check minister's name appears in transcript
  5. Download full transcript and extract Q-A dyads

Output:
  data/raw/minister_audit_meetings.json   -- discovered meeting list
  data/raw/transcripts_audit/             -- HTML transcript files
  data/processed/minister_audit_dyads.csv -- extracted Q-A pairs

Usage:
  python collect_minister_audit.py [--stage discover|transcripts|dyads|all]
  python collect_minister_audit.py --stage discover --year 2025
  python collect_minister_audit.py --stage discover --minister 구윤철
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ============================================================
# Paths
# ============================================================
BASE = Path(__file__).parent.parent
PANEL_FILE = BASE / "data" / "minister_panel_comprehensive.csv"
HEARINGS_JSON = BASE / "data" / "raw" / "minister_hearing_meetings.json"
AUDIT_JSON = BASE / "data" / "raw" / "minister_audit_meetings.json"
TRANSCRIPT_DIR = BASE / "data" / "raw" / "transcripts_audit"
DYADS_FILE = BASE / "data" / "processed" / "minister_audit_dyads.csv"

TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Committee keyword mapping: ministry -> committee short name
# ============================================================
MINISTRY_COMMITTEE = {
    # Current names (21-22대)
    "기획재정부": "기획재정위원회",
    "교육부": "교육위원회",
    "과학기술정보통신부": "과학기술정보방송통신위원회",
    "외교부": "외교통일위원회",
    "통일부": "외교통일위원회",
    "법무부": "법제사법위원회",
    "국방부": "국방위원회",
    "행정안전부": "행정안전위원회",
    "문화체육관광부": "문화체육관광위원회",
    "농림축산식품부": "농림축산식품해양수산위원회",
    "해양수산부": "농림축산식품해양수산위원회",
    "산업통상자원부": "산업통상자원중소벤처기업위원회",
    "중소벤처기업부": "산업통상자원중소벤처기업위원회",
    "보건복지부": "보건복지위원회",
    "환경부": "환경노동위원회",
    "고용노동부": "환경노동위원회",
    "여성가족부": "여성가족위원회",
    "성평등가족부": "여성가족위원회",
    "국토교통부": "국토교통위원회",
    "국가보훈부": "정무위원회",
    "국가보훈처": "정무위원회",
    "기후에너지환경부": "환경노동위원회",
    # 박근혜 era names (19대)
    "미래창조과학부": "미래창조과학방송통신위원회",
    "안전행정부": "안전행정위원회",
    # 이명박 era names (18대)
    "지식경제부": "지식경제위원회",
    "국토해양부": "국토해양위원회",
    "행정자치부": "행정안전위원회",
    # 노무현 era names (17대)
    "재정경제부": "재정경제위원회",
    "기획예산처": "재정경제위원회",
    "교육인적자원부": "교육위원회",
    "과학기술부": "과학기술정보통신위원회",
    "정보통신부": "과학기술정보통신위원회",
    "외교통상부": "통일외교통상위원회",
    "농림부": "농림해양수산위원회",
    "산업자원부": "산업자원위원회",
    "노동부": "환경노동위원회",
    "건설교통부": "건설교통위원회",
    "문화관광부": "문화관광위원회",
}

# Approximate MNTS_ID scan windows for October 국감 by year
# Based on known ID-date mappings from hearing data + rate estimation
# 17대 (노무현): anchor (27430, 2004-09-23), (30192, 2007-01-15) -> ~3.3 IDs/day
# 20대+ (박근혜/문재인/윤석열/이재명): confirmed ranges from collected data
AUDIT_WINDOWS = {
    # 17대 국회 국감 (노무현 정부) -- collected 2004-2006
    2004: (27430, 27700),   # confirmed 27504-27696
    2005: (28300, 28900),   # confirmed 28696-28815
    2006: (29400, 30671),   # confirmed 29893-30671
    2007: (31100, 31200),   # confirmed 31121-31151 (minimal)
    # 20대 국회 국감 -- 국정감사 labeled full transcripts in 40000-42000 range
    2016: (40550, 40830),   # confirmed 40661-40803 (Sep 26 - Oct 18, 2016)
    2017: (40600, 41100),   # confirmed 40827-41001 (Oct 12 - Nov 10, 2017)
    2018: (40990, 41300),   # confirmed 41005-41176 (Oct 10 - Oct 30, 2018)
    2019: (41200, 41500),   # confirmed 41203-41348 (Oct 4 - Oct 24, 2019)
    2020: (44480, 44600),   # confirmed 44480-44565 (Oct 15 - Oct 30, 2020)
    # 21대 국회 국감 -- confirmed ranges
    2021: (44550, 44780),   # confirmed 44569-44714 (Oct 5 - Oct 21, 2021)
    2022: (44700, 44900),   # confirmed 44719-44876 (Oct 4 - Oct 24, 2022)
    # 21대 국회 마지막 국감 (2023)
    2023: (44850, 45400),   # confirmed 44890-45036 (Oct 10 - Nov 2, 2023)
    # 22대 국회 국감 (2024)
    2024: (52000, 52600),   # confirmed 52000-52049 (Oct 21 - Oct 31, 2024)
    2025: (55200, 55800),   # confirmed 55481-55755 (Oct 13 - Nov 4, 2025)
}

# ============================================================
# HTTP Session
# ============================================================
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; research)"})

LIST_URL = "https://likms.assembly.go.kr/record/new/ApiSearch.do"
VIEWER_URL = "https://record.assembly.go.kr/assembly/viewer/minutes/xml.do"


def fetch_title_only(mnts_id: int):
    """Fetch header of page (20KB) to extract meeting title and audit keyword.
    Returns (title, has_audit_keyword) or None on failure.
    """
    try:
        resp = SESSION.get(
            VIEWER_URL,
            params={"id": mnts_id, "type": "view"},
            timeout=15,
            stream=True,
        )
        if resp.status_code != 200:
            resp.close()
            return None
        chunk = resp.raw.read(20480)  # 20KB to catch audit keyword in table of contents
        resp.close()
        if not chunk:
            return None
        html = chunk.decode("utf-8", errors="replace")
        if "회의록 정보를 찾을 수 없습니다" in html:
            return None
        soup = BeautifulSoup(html, "html.parser")
        h2 = soup.find("h2")
        if not h2:
            return None
        title = h2.get_text(strip=True)
        # Also check if the raw chunk mentions 국정감사 (for 정기회-titled sessions pre-2025)
        has_audit = "국정감사" in html
        return (title, has_audit)
    except Exception:
        return None


def scan_audit_sessions(mnts_range, target_committees, year):
    """
    One-pass concurrent scan: collect all 국정감사 sessions matching any target committee.
    Returns list of {mnts_id, title, committee} dicts.
    Does NOT check minister name (done in second pass with full download).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    lo, hi = mnts_range
    all_ids = list(range(lo, hi + 1))
    found = []
    print(f"  Scanning {lo}-{hi} ({len(all_ids)} IDs) for {year}국감 [{len(target_committees)} committees]...")

    def check_one(mnts_id):
        result = fetch_title_only(mnts_id)
        if result is None:
            return None
        title, has_audit = result
        # Accept if: (a) title explicitly says 국정감사 (2025+ format)
        #            (b) content mentions 국정감사 AND date is in October (pre-2025 format)
        oct_str = f"({year}.10."
        is_audit = "국정감사" in title or (has_audit and oct_str in title)
        if not is_audit:
            return None
        for cmit in target_committees:
            if cmit in title or cmit[:6] in title:
                return {"mnts_id": mnts_id, "title": title, "committee": cmit}
        return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(check_one, mid): mid for mid in all_ids}
        for future in as_completed(futures):
            result = future.result()
            if result:
                print(f"    {result['mnts_id']}: [{result['committee'][:15]}] {result['title'][16:55]}")
                found.append(result)

    found.sort(key=lambda x: x["mnts_id"])
    print(f"  => Found {len(found)} matching 국감 sessions")
    return found


def check_minister_in_session(mnts_id: int, minister_name: str) -> bool:
    """Download full transcript and check if minister name appears."""
    try:
        resp = SESSION.get(
            VIEWER_URL,
            params={"id": mnts_id, "type": "view"},
            timeout=60,
        )
        return minister_name in resp.text
    except Exception:
        return False


def discover_stage(args):
    """
    Committee-first discover:
    1. One pass to find all 국감 sessions in the year's window
    2. For each session, check which ministers from target list appear
    """
    panel = pd.read_csv(PANEL_FILE)
    panel["start"] = pd.to_datetime(panel["start"], errors="coerce")
    panel["end"] = pd.to_datetime(panel["end"], errors="coerce")
    panel["confirmation_date"] = pd.to_datetime(panel["confirmation_date"], errors="coerce")

    # Load existing results
    if AUDIT_JSON.exists():
        with open(AUDIT_JSON) as f:
            existing = json.load(f)
        existing_keys = {(e["minister"], e["mnts_id"]) for e in existing}
    else:
        existing = []
        existing_keys = set()

    # For 국감, include ALL ministers (not limited to confirmation_hearing=True)
    # 국감 covers all ministers in office, regardless of hearing status
    target = panel.copy()

    if hasattr(args, "minister") and args.minister:
        target = target[target["name"] == args.minister]

    years_filter = [int(args.year)] if (hasattr(args, "year") and args.year) else None

    # Build minister-year list
    minister_records = []
    for _, row in target.iterrows():
        name = row["name"]
        ministry = row["ministry"]
        start = row["start"]
        conf_ts = row["confirmation_date"]
        end = row["end"]

        # Effective start
        if pd.isna(start):
            if pd.isna(conf_ts):
                continue
            start = conf_ts
        elif not pd.isna(conf_ts):
            start = min(start, conf_ts)

        committee = MINISTRY_COMMITTEE.get(ministry)
        if not committee:
            continue

        if pd.isna(end):
            end = pd.Timestamp("2026-12-31")

        # Which October years during tenure?
        for y in range(start.year, end.year + 1):
            if years_filter and y not in years_filter:
                continue
            if y not in AUDIT_WINDOWS:
                continue
            oct_start = pd.Timestamp(f"{y}-10-01")
            oct_end = pd.Timestamp(f"{y}-10-31")
            if oct_start <= end and oct_end >= start:
                minister_records.append({
                    "name": name,
                    "ministry": ministry,
                    "admin": row["admin"],
                    "dual_office": str(row["dual_office"]),
                    "committee": committee,
                    "year": y,
                })

    if not minister_records:
        print("No qualifying minister-year combinations found.")
        return

    print(f"Qualifying minister-year pairs: {len(minister_records)}")

    # Group by year and collect all needed committees
    from collections import defaultdict
    by_year = defaultdict(list)
    for rec in minister_records:
        by_year[rec["year"]].append(rec)

    new_results = list(existing)

    for year, year_recs in sorted(by_year.items()):
        committees = {r["committee"] for r in year_recs}
        window = AUDIT_WINDOWS[year]

        print(f"\nYear {year}: {len(year_recs)} minister-committee pairs, {len(committees)} unique committees")

        # One-pass scan for all audit sessions
        audit_sessions = scan_audit_sessions(window, committees, year)

        if not audit_sessions:
            print(f"  No 국감 sessions found for {year}")
            continue

        # For each session, check which ministers appear
        print(f"\n  Checking {len(audit_sessions)} sessions for minister presence...")
        for session in audit_sessions:
            mnts_id = session["mnts_id"]
            session_cmit = session["committee"]

            # Find ministers who should appear in this committee
            relevant = [r for r in year_recs if r["committee"] == session_cmit]
            if not relevant:
                continue

            # Download full transcript once
            try:
                resp = SESSION.get(
                    VIEWER_URL,
                    params={"id": mnts_id, "type": "view"},
                    timeout=60,
                )
                html = resp.text
            except Exception as e:
                print(f"    ERROR downloading {mnts_id}: {e}")
                continue

            for rec in relevant:
                if rec["name"] not in html:
                    continue
                key = (rec["name"], str(mnts_id))
                if key in existing_keys:
                    print(f"    SKIP {rec['name']} @ {mnts_id}: already found")
                    continue

                print(f"    FOUND {rec['name']} ({rec['ministry']}) @ {mnts_id}: {session['title'][:50]}")
                entry = {
                    "mnts_id": str(mnts_id),
                    "cmit_nm": session["title"],
                    "year": year,
                    "minister": rec["name"],
                    "ministry": rec["ministry"],
                    "admin": rec["admin"],
                    "dual_office": rec["dual_office"],
                    "hearing_type": "AUDIT",
                }
                new_results.append(entry)
                existing_keys.add(key)

            time.sleep(0.3)

    with open(AUDIT_JSON, "w", encoding="utf-8") as f:
        json.dump(new_results, f, ensure_ascii=False, indent=2)

    added = len(new_results) - len(existing)
    print(f"\nDiscover: {added} new entries added")
    print(f"Total in {AUDIT_JSON}: {len(new_results)}")
    return


def transcripts_stage(args):
    """Download full transcripts for discovered audit meetings."""
    if not AUDIT_JSON.exists():
        print("No audit meetings found. Run --stage discover first.")
        return

    with open(AUDIT_JSON) as f:
        meetings = json.load(f)

    downloaded = 0
    skipped = 0

    for m in meetings:
        mnts_id = m["mnts_id"]
        out_path = TRANSCRIPT_DIR / f"{mnts_id}.html"

        if out_path.exists() and out_path.stat().st_size > 100000:
            skipped += 1
            continue

        url = VIEWER_URL
        try:
            resp = SESSION.get(url, params={"id": mnts_id, "type": "view"}, timeout=60)
            if resp.status_code == 200:
                out_path.write_bytes(resp.content)
                print(f"  Downloaded {mnts_id}: {len(resp.content)//1024}KB")
                downloaded += 1
            else:
                print(f"  FAIL {mnts_id}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  ERROR {mnts_id}: {e}")

        time.sleep(0.5)

    print(f"\nDownloaded: {downloaded}, Skipped (already ok): {skipped}")


def parse_html_speeches(html: str, candidate: str) -> list[dict]:
    """Parse speeches from HTML transcript. Reuses logic from collect_minister_hearings.py."""
    speeches = []

    pattern = re.compile(
        r'<strong class="name">([^<]+)</strong>'
        r'(?:.*?<span class="position">([^<]*)</span>)?'
        r'(.*?)(?=<strong class="name">|$)',
        re.DOTALL,
    )

    for m in pattern.finditer(html):
        name = m.group(1).strip()
        position = (m.group(2) or "").strip()
        raw_text = m.group(3)

        text = re.sub(r"<[^>]+>", " ", raw_text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue

        is_candidate = "후보자" in position or candidate in name or "장관" in position
        is_questioner = "위원" in position or "의원" in position

        speeches.append(
            {
                "name": name,
                "position": position,
                "text": text,
                "is_candidate": is_candidate,
                "is_questioner": is_questioner,
            }
        )

    return speeches


def parse_qa_dyads(speeches: list[dict], candidate: str, minister_entry: dict) -> list[dict]:
    """Extract Q-A dyads from speech list."""
    dyads = []
    i = 0
    order = 0

    while i < len(speeches):
        sp = speeches[i]

        if sp["is_questioner"] and not sp["is_candidate"]:
            q_sp = sp
            # Find next minister response
            j = i + 1
            while j < len(speeches) and not speeches[j]["is_candidate"]:
                j += 1

            if j < len(speeches):
                r_sp = speeches[j]
                q_words = len(q_sp["text"].split())
                r_words = len(r_sp["text"].split())

                if q_words >= 3 and r_words >= 3:
                    order += 1
                    dyads.append(
                        {
                            "hearing_id": minister_entry["mnts_id"],
                            "year": minister_entry["year"],
                            "minister": minister_entry["minister"],
                            "ministry": minister_entry["ministry"],
                            "admin": minister_entry["admin"],
                            "dual_office": minister_entry["dual_office"],
                            "hearing_type": "AUDIT",
                            "q_speaker": q_sp["name"],
                            "q_position": q_sp["position"],
                            "q_text": q_sp["text"],
                            "q_word_count": q_words,
                            "r_speaker": r_sp["name"],
                            "r_position": r_sp["position"],
                            "r_text": r_sp["text"],
                            "r_word_count": r_words,
                            "q_order": order,
                        }
                    )
                i = j + 1
            else:
                i += 1
        else:
            i += 1

    return dyads


def dyads_stage(args):
    """Extract Q-A dyads from downloaded transcripts."""
    if not AUDIT_JSON.exists():
        print("No audit meetings. Run --stage discover first.")
        return

    with open(AUDIT_JSON) as f:
        meetings = json.load(f)

    all_dyads = []

    for m in meetings:
        mnts_id = m["mnts_id"]
        html_path = TRANSCRIPT_DIR / f"{mnts_id}.html"

        if not html_path.exists():
            print(f"  SKIP {mnts_id}: no transcript downloaded")
            continue

        html = html_path.read_text(encoding="utf-8", errors="replace")
        speeches = parse_html_speeches(html, m["minister"])
        dyads = parse_qa_dyads(speeches, m["minister"], m)

        print(f"  {mnts_id} ({m['minister']} {m['year']}국감): {len(speeches)} speeches, {len(dyads)} dyads")
        all_dyads.extend(dyads)

    if all_dyads:
        df = pd.DataFrame(all_dyads)
        df.insert(0, "dyad_id", [f"AUD{i+1:05d}" for i in range(len(df))])
        df.to_csv(DYADS_FILE, index=False, encoding="utf-8")
        print(f"\nSaved {len(df)} dyads to {DYADS_FILE}")
        print(f"dual_office=True: {(df['dual_office']=='True').sum()}")
        print(f"dual_office=False: {(df['dual_office']=='False').sum()}")
    else:
        print("No dyads extracted.")


def main():
    parser = argparse.ArgumentParser(description="Collect 국정감사 transcripts and Q-A dyads")
    parser.add_argument(
        "--stage",
        choices=["discover", "transcripts", "dyads", "all"],
        default="all",
        help="Which stage to run",
    )
    parser.add_argument("--year", type=int, help="Only scan this year (for discover stage)")
    parser.add_argument("--minister", type=str, help="Only process this minister")
    args = parser.parse_args()

    if args.stage in ("discover", "all"):
        print("=== DISCOVER STAGE ===")
        discover_stage(args)

    if args.stage in ("transcripts", "all"):
        print("\n=== TRANSCRIPTS STAGE ===")
        transcripts_stage(args)

    if args.stage in ("dyads", "all"):
        print("\n=== DYADS STAGE ===")
        dyads_stage(args)


if __name__ == "__main__":
    main()
