"""
collect_minister_hearings.py

Stage 1b: Collect 장관 인사청문회 transcripts for all non-PM ministers
in minister_panel_comprehensive.csv.

Discovery strategy (unified MNTS_ID range scan, all 17-22대):
  - The Pharos HTML viewer (viewer/minutes/xml.do?id=MNTS_ID) works for ALL
    assembly terms including 17-19대, returning speech-level HTML with date,
    title, and agenda items.
  - We scan MNTS_ID ranges estimated by linear interpolation from known anchor
    points, stream the first 40 KB of each page, and filter for 인사청문 meetings.
  - For 22대 2024 윤석열 ministers (non-sequential MNTS_IDs), we use hardcoded
    scan ranges derived from probing.
  - HEARING_DATE_WINDOW=90 days handles extreme cases like 김용현 where the
    hearing was 81 days before the confirmation (appointment) date.

Usage:
    python collect_minister_hearings.py --stage discover
    python collect_minister_hearings.py --stage transcripts
    python collect_minister_hearings.py --stage dyads
    python collect_minister_hearings.py --stage all
"""

import requests
import json
import time
import re
import csv as csv_mod
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE          = Path(__file__).parent.parent
DATA_DIR      = BASE / "data"
RAW_DIR       = DATA_DIR / "raw"
TRANSCRIPTS   = RAW_DIR / "transcripts_minister"
PROCESSED_DIR = DATA_DIR / "processed"
for d in [RAW_DIR, TRANSCRIPTS, PROCESSED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

PANEL_CSV     = DATA_DIR / "minister_panel_comprehensive.csv"
MEETINGS_FILE = RAW_DIR / "minister_hearing_meetings.json"

# ── API configuration ─────────────────────────────────────────────────────────

PHAROS_URL  = "https://record.assembly.go.kr/assembly/mnts/search/search.do"
VIEWER_BASE = "https://record.assembly.go.kr/assembly"
PHAROS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DualOfficeResearch/2.0; Academic)",
    "Referer":    "https://record.assembly.go.kr/",
}

# Pharos TH (term) = assembly_num + 2
TH_MAP = {16: 18, 17: 19, 18: 20, 19: 21, 20: 22, 21: 23, 22: 24}

# Assembly term date ranges (for deriving assembly from confirmation_date)
ASSEMBLY_TERMS = [
    (16, "2000-05-30", "2004-05-29"),
    (17, "2004-05-30", "2008-05-29"),
    (18, "2008-05-30", "2012-05-29"),
    (19, "2012-05-30", "2016-05-29"),
    (20, "2016-05-30", "2020-05-29"),
    (21, "2020-05-30", "2024-05-29"),
    (22, "2024-05-30", "2099-12-31"),
]

# ── MNTS_ID anchors for 17-22대 range scanning ────────────────────────────────
#
# Each entry: (mnts_id, "YYYYMMDD") -- verified from the HTML viewer.
# Used for linear interpolation to estimate center of a target-date scan.
# All assemblies 17-22대 use the same HTML viewer URL format; 17-19대 have
# full speech-level content just like 20-22대.
#
ANCHORS = sorted([
    (27430, "20040923"),   # 17대 일자리창출특별위원회 (confirmed via viewer)
    (30192, "20070115"),   # 17대 헌법재판소장 인사청문특별위원회 (confirmed)
    (42135, "20170518"),   # 20대 PM 이낙연 hearing day 1
    (42202, "20170531"),   # 20대 PM 이낙연 hearing day 4
    (44275, "20191230"),   # 20대 PM 정세균 hearing day 1
    (45868, "20210430"),   # 21대 PM 김부겸 hearing day 1
    (52117, "20240716"),   # 22대 기재위 강민수 hearing (confirmed)
    (55008, "20250714"),   # 22대 농해수위 전재수 hearing (confirmed)
    (55025, "20250715"),   # 22대 국방위 안규백 hearing (confirmed)
    (55090, "20250729"),   # 22대 (probed)
    (55270, "20250901"),   # 22대 (probed)
], key=lambda x: x[1])

SCAN_WORKERS = 5     # parallel HTML viewer requests
HEADER_BYTES = 40960 # bytes to stream per HTML viewer page (some pages need >32KB)

# Max days between minister's confirmation_date and actual hearing date.
# confirmation_date can be the nomination date (hearing after), appointment date
# (hearing before), or exact hearing date -- varies by minister/government.
# Set to 90 to handle extreme cases like 김용현 (hearing 81 days before appointment).
HEARING_DATE_WINDOW = 90  # days on either side


def derive_assembly(date_str: str) -> Optional[int]:
    """Derive National Assembly term number from a date string (YYYY-MM-DD)."""
    if not date_str:
        return None
    for asm, start, end in ASSEMBLY_TERMS:
        if start <= date_str <= end:
            return asm
    return None


# ── Data loading ──────────────────────────────────────────────────────────────

def load_ministers() -> list:
    """
    Load minister panel: confirmation_hearing=TRUE, not PM.
    Fills missing assembly_num_at_appt from confirmation_date.
    """
    ministers = []
    derived = 0

    with open(PANEL_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv_mod.DictReader(f)
        for row in reader:
            if str(row.get("confirmation_hearing", "")).strip().upper() != "TRUE":
                continue
            if str(row.get("ministry", "")).strip() == "국무총리":
                continue

            asm_raw = str(row.get("assembly_num_at_appt", "")).strip()
            if not asm_raw or asm_raw in ("nan", ""):
                conf_date = str(row.get("confirmation_date", "")).strip()
                inferred = derive_assembly(conf_date)
                if inferred:
                    row = dict(row)
                    row["assembly_num_at_appt"] = str(inferred)
                    derived += 1
                else:
                    row = dict(row)
                    row["assembly_num_at_appt"] = ""

            ministers.append(row)

    logger.info(
        f"Loaded {len(ministers)} ministers with confirmation hearings (PM excluded); "
        f"{derived} assembly numbers derived from date"
    )
    return ministers


# ── MNTS_ID estimation and HTML-header scanning ───────────────────────────────

def _days_between(d1: str, d2: str) -> float:
    """Days from compact date d1 to d2 (YYYYMMDD strings). Positive = d2 is later."""
    fmt = "%Y%m%d"
    return (datetime.strptime(d2, fmt) - datetime.strptime(d1, fmt)).days


def estimate_mnts_id_center(target_date_compact: str) -> int:
    """
    Estimate the MNTS_ID for a target date using linear interpolation
    between the two nearest anchor points.
    """
    anchors = ANCHORS  # sorted ascending by date

    before = None
    after  = None
    for mnts_id, date_str in anchors:
        if date_str <= target_date_compact:
            before = (mnts_id, date_str)
        elif after is None:
            after = (mnts_id, date_str)

    if before is None and after is None:
        return 40000  # fallback

    if before is None:
        # Extrapolate backward from earliest anchor
        mid, dstr = after
        days_offset = _days_between(target_date_compact, dstr)  # positive = target is earlier
        rate = 3.0  # conservative default IDs/day
        return max(1, mid - int(days_offset * rate))

    if after is None:
        # Extrapolate forward from latest anchor.
        # Use LONG-RUN average rate to avoid hearing-week density spikes.
        mid, dstr = before
        days_offset = _days_between(dstr, target_date_compact)
        if len(anchors) >= 3:
            m_first, d_first = anchors[0]
            m_last,  d_last  = anchors[-1]
            total_days = _days_between(d_first, d_last)
            rate = (m_last - m_first) / total_days if total_days > 0 else 3.0
        else:
            rate = 3.0
        return mid + int(days_offset * rate)

    # Interpolate between before and after
    m1, d1 = before
    m2, d2 = after
    total_days = _days_between(d1, d2)
    target_days = _days_between(d1, target_date_compact)
    fraction = target_days / total_days if total_days > 0 else 0.5
    return int(m1 + fraction * (m2 - m1))


def fetch_mnts_header(session: requests.Session, mnts_id: int) -> dict:
    """
    Fetch the first HEADER_BYTES bytes of an HTML viewer page and extract:
      - date     : "YYYYMMDD" (empty string if not found)
      - title    : meeting title from <h2><strong>...</strong>
      - is_hearing: bool - True if "인사청문" appears in the header
      - candidates: list of (ministry, name) extracted from hearing agenda items
    """
    url = f"{VIEWER_BASE}/viewer/minutes/xml.do?id={mnts_id}&type=view"
    try:
        resp = session.get(url, timeout=12, stream=True)
        content = b""
        for chunk in resp.iter_content(4096):
            content += chunk
            if len(content) >= HEADER_BYTES:
                break
        resp.close()

        html = content.decode("utf-8", errors="ignore")

        # Date: <span class="date">(2025.07.14.)</span>
        date_m = re.search(
            r'<span class="date">\((\d{4})\.(\d{2})\.(\d{2})\.\)',
            html
        )
        date_str = "".join(date_m.groups()) if date_m else ""

        # Meeting title: <h2><strong>제22대국회 ...</strong>
        title_m = re.search(r'<h2><strong>([^<]+)</strong>', html)
        title = title_m.group(1).strip() if title_m else ""

        # Candidate names: "국무위원후보자(해양수산부장관 전재수) 인사청문"
        candidates = []
        if "인사청문" in html:
            cand_pattern = re.finditer(
                r'국무위원후보자\(([^)]+장관[^)]*)\s+([^)]{2,5})\)\s*인사청문',
                html
            )
            for m in cand_pattern:
                position = m.group(1).strip()
                name     = m.group(2).strip()
                if (position, name) not in candidates:
                    candidates.append((position, name))

        return {
            "mnts_id":     mnts_id,
            "date":        date_str,
            "title":       title,
            "is_hearing":  "인사청문" in html,
            "candidates":  candidates,
        }

    except Exception as e:
        logger.debug(f"fetch_mnts_header({mnts_id}): {e}")
        return {
            "mnts_id":    mnts_id,
            "date":       "",
            "title":      "",
            "is_hearing": False,
            "candidates": [],
        }


def scan_mnts_range(session: requests.Session, lo: int, hi: int) -> list:
    """
    Scan MNTS_IDs [lo, hi] in parallel.
    Returns all headers where is_hearing=True and date is non-empty.
    """
    mnts_ids = list(range(lo, hi + 1))
    results = []

    def _fetch(mid):
        return fetch_mnts_header(session, mid)

    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as executor:
        futures = {executor.submit(_fetch, mid): mid for mid in mnts_ids}
        for future in as_completed(futures):
            meta = future.result()
            if meta["date"] and meta["is_hearing"]:
                results.append(meta)

    return sorted(results, key=lambda x: (x["date"], x["mnts_id"]))


# ── Discovery via MNTS_ID range scan (all 17-22대) ────────────────────────────

def discover_via_mnts_scan(session: requests.Session, ministers: list) -> list:
    """
    Discover 인사청문회 meeting IDs for 17-22대 ministers using MNTS_ID range scan.

    The HTML viewer works for all assembly terms (17-22대), returning speech-level
    HTML with date, title, and agenda items.

    confirmation_date in the panel may be the nomination, appointment, OR hearing
    date depending on the government/period.  We match any hearing whose HTML date
    is within HEARING_DATE_WINDOW days of the confirmation_date.

    Special scans (hardcoded ranges to avoid interpolation errors):
      22대 2025 (Jul-Sep 2025): one big scan 54950-55400
      22대 2024 윤석열 ministers (non-sequential IDs):
            52080-52250 covers Jun-Aug 2024 (김문수, 유상임, 김완섭)
            52350-52450 covers Sep-Dec 2024 (김용현 MNTS_ID=52390 confirmed)

    All other dates (17-21대 and any remaining 22대): interpolation ± window.
    Window size scales with assembly era: larger for older assemblies where the
    MNTS_ID rate estimate is less reliable.
    """
    # HTML viewer coverage:
    #   17대 (2004-2008): MNTS_IDs ~27000-31000 -- viewer works, speech-level HTML
    #   18대 (2008-2012): MNTS_IDs ~31000-36000 -- viewer returns empty (PDF-only)
    #   19대 (2012-2016): MNTS_IDs ~36000-41000 -- viewer returns empty (PDF-only)
    #   20-22대 (2016+):  MNTS_IDs ~41000+      -- viewer works, speech-level HTML
    # 18대 and 19대 ministers are logged as NOT_FOUND and handled separately via
    # the Pharos PDF pipeline (record2 download + pdfplumber parsing).
    PDF_ONLY_ASSEMBLIES = {18, 19}

    # Collect ministers grouped by confirmation_date (17대 + 20-22대 only)
    targets_by_date: dict[str, list] = {}
    pdf_only_ministers: list[dict] = []
    for m in ministers:
        try:
            asm = int(float(m.get("assembly_num_at_appt", 0) or 0))
        except (ValueError, TypeError):
            continue
        if asm < 17:
            continue
        if asm in PDF_ONLY_ASSEMBLIES:
            pdf_only_ministers.append(m)
            continue
        conf_date = m.get("confirmation_date", "").strip().replace("-", "")
        if not conf_date:
            continue
        targets_by_date.setdefault(conf_date, []).append(m)

    if pdf_only_ministers:
        logger.warning(
            f"Skipping {len(pdf_only_ministers)} ministers from 18-19대 "
            f"(PDF-only, HTML viewer not supported). "
            f"Use Pharos record2 search + pdfplumber pipeline separately."
        )
        for m in pdf_only_ministers:
            logger.warning(f"  PDF_ONLY: {m.get('name','')} ({m.get('ministry','')} "
                           f"{m.get('admin','')} {m.get('assembly_num_at_appt','')}대)")

    if not targets_by_date:
        return []

    scan_ranges: list[tuple[int, int, set]] = []  # (lo, hi, {dates covered by this scan})

    # ── 22대 2025 hearing season (Jul-Sep 2025) ──────────────────────────────
    SEASON25_DATES = {d for d in targets_by_date if "20250714" <= d <= "20251231"}
    if SEASON25_DATES:
        scan_ranges.append((54950, 55400, SEASON25_DATES))
        logger.info(
            f"22대 2025 season: single scan 54950-55400 covers {sorted(SEASON25_DATES)}"
        )

    # ── 22대 2024 윤석열 ministers ────────────────────────────────────────────
    # Probed: Jun-Aug 2024 is in 52080-52210; Sep-Nov 2024 (김용현) is ~52350-52450.
    WIN2024_DATES_EARLY = {d for d in targets_by_date if "20240601" <= d <= "20240831"}
    WIN2024_DATES_LATE  = {d for d in targets_by_date if "20240901" <= d <= "20241231"}
    if WIN2024_DATES_EARLY:
        scan_ranges.append((52080, 52250, WIN2024_DATES_EARLY))
        logger.info(
            f"22대 2024 early (Jun-Aug): scan 52080-52250 covers {sorted(WIN2024_DATES_EARLY)}"
        )
    if WIN2024_DATES_LATE:
        scan_ranges.append((52350, 52450, WIN2024_DATES_LATE))
        logger.info(
            f"22대 2024 late (Sep-Dec): scan 52350-52450 covers {sorted(WIN2024_DATES_LATE)}"
        )

    # ── All other dates: interpolation-based scan ─────────────────────────────
    # Covers: 17대, 20대, 21대, and any remaining 22대 dates.
    # 18대 and 19대 are excluded (PDF-only, handled separately).
    covered = SEASON25_DATES | WIN2024_DATES_EARLY | WIN2024_DATES_LATE
    for date_compact in sorted(targets_by_date.keys()):
        if date_compact in covered:
            continue
        center = estimate_mnts_id_center(date_compact)
        try:
            asm = int(float(targets_by_date[date_compact][0].get("assembly_num_at_appt", 0) or 0))
        except (ValueError, TypeError):
            asm = 20
        # Larger window for older assemblies where anchor density is lower
        if asm >= 21:
            window = 100
        elif asm == 20:
            window = 80
        else:
            window = 130   # 17대: sparser anchors, higher interpolation error
        lo = max(1, center - window)
        hi = center + window
        scan_ranges.append((lo, hi, {date_compact}))

    # ── Merge overlapping scan ranges to avoid redundant fetching ────────────
    # Sort by lo; merge adjacent/overlapping ranges.
    scan_ranges.sort(key=lambda x: x[0])
    merged: list[tuple[int, int, set]] = []
    for lo, hi, dates in scan_ranges:
        if merged and lo <= merged[-1][1] + 1:
            prev_lo, prev_hi, prev_dates = merged[-1]
            merged[-1] = (prev_lo, max(prev_hi, hi), prev_dates | dates)
        else:
            merged.append((lo, hi, dates.copy()))
    scan_ranges = merged
    logger.info(f"Scan plan: {len(scan_ranges)} ranges after merging")

    # ── Execute scans ─────────────────────────────────────────────────────────
    all_hearings: dict[int, dict] = {}  # mnts_id -> header dict

    for lo, hi, dates in scan_ranges:
        logger.info(f"Scanning MNTS_IDs {lo}-{hi} for dates {sorted(dates)}")
        t0 = time.time()
        found = scan_mnts_range(session, lo, hi)
        elapsed = time.time() - t0
        logger.info(f"  {len(found)} hearing meetings in {elapsed:.0f}s")
        for h in found:
            all_hearings[h["mnts_id"]] = h

    # ── Match hearings to ministers ───────────────────────────────────────────
    # Key: confirmation_date may differ from hearing date by up to HEARING_DATE_WINDOW
    # days.  We use candidate-name match as the primary signal.

    all_meetings = []
    not_found:  list[dict] = []

    for date_compact, date_ministers in sorted(targets_by_date.items()):
        # Collect all hearings within ±HEARING_DATE_WINDOW of this confirmation_date
        target_dt = datetime.strptime(date_compact, "%Y%m%d")
        nearby_hearings = [
            h for h in all_hearings.values()
            if h["date"] and abs((datetime.strptime(h["date"], "%Y%m%d") - target_dt).days)
               <= HEARING_DATE_WINDOW
        ]

        if not nearby_hearings:
            logger.warning(f"  {date_compact}: NO hearings found within ±{HEARING_DATE_WINDOW} days")
            for m in date_ministers:
                not_found.append(m)
            continue

        logger.info(f"  {date_compact}: {len(nearby_hearings)} candidate hearing(s)")
        for h in nearby_hearings:
            logger.info(
                f"    MNTS_ID={h['mnts_id']}: {h['date']} {h['title'][:60]} cands={h['candidates']}"
            )

        for m in date_ministers:
            minister_name = m.get("name", "").strip()
            ministry      = m.get("ministry", "").strip()

            # Primary: match by candidate name extracted from agenda
            matched_list = []
            for h in nearby_hearings:
                for pos, cand_name in h["candidates"]:
                    if cand_name == minister_name or minister_name in cand_name:
                        if h not in matched_list:
                            matched_list.append(h)

            # Fallback: single hearing in window → assign it
            if not matched_list and len(nearby_hearings) == 1:
                matched_list = nearby_hearings[:]

            # Fallback: title keyword match on ministry
            if not matched_list:
                ministry_kw = re.sub(r"[부처청]$", "", ministry)
                for h in nearby_hearings:
                    if ministry_kw and ministry_kw in h["title"]:
                        matched_list.append(h)

            if not matched_list:
                logger.warning(
                    f"    {minister_name} ({ministry}): no match among "
                    f"{len(nearby_hearings)} hearings"
                )
                not_found.append(m)
                continue

            asm = int(float(m.get("assembly_num_at_appt", 0) or 0))
            # Record ALL matched hearing days (minister may span 2-3 hearing days)
            for matched in matched_list:
                all_meetings.append({
                    "mnts_id":           str(matched["mnts_id"]),
                    "cmit_nm":           matched["title"],
                    "item_nm":           "",
                    "date":              matched["date"],
                    "file_ext":          "XML",
                    "assembly":          asm,
                    "collection":        "record2",
                    "minister":          minister_name,
                    "ministry":          ministry,
                    "admin":             m.get("admin", ""),
                    "dual_office":       m.get("dual_office", ""),
                    "confirmation_date": m.get("confirmation_date", ""),
                    "hearing_type":      "MINISTER_STANDING",
                })
            logger.info(
                f"    Matched {minister_name} -> "
                f"{[str(h['mnts_id']) for h in matched_list]}"
            )

    if not_found:
        logger.warning(
            f"NOT FOUND in MNTS_ID scan ({len(not_found)} ministers):"
        )
        for m in not_found:
            logger.warning(
                f"  {m.get('name','')} ({m.get('ministry','')} {m.get('admin','')})"
                f" conf={m.get('confirmation_date','').replace('-','')}"
            )

    return all_meetings


# ── 17-19대 discovery via name-based Pharos search ────────────────────────────

def pharos_post(session: requests.Session, body: dict, collection: str) -> dict:
    """POST to Pharos search API. Returns result dict for the given collection."""
    try:
        resp = session.post(PHAROS_URL, data=body, timeout=30)
        resp.raise_for_status()
        return resp.json().get(collection, {})
    except Exception as e:
        logger.warning(f"Pharos API error: {e}")
        return {}


def find_hearing_meetings_17_19(session: requests.Session,
                                name: str,
                                assembly_num: int,
                                confirmation_date: str) -> list:
    """
    Search Pharos by minister name + 인사청문 (record2 + record3), filter by a
    symmetric ±14-day window around confirmation_date.

    Works for 17-19대 (document-level records) where schword properly filters results.
    For 20-22대 schword returns the full corpus regardless of keyword -- use
    discover_20_22() instead.

    Uses compound schword "{name} 인사청문" to avoid paginating through thousands
    of regular committee meetings that merely mention the minister's name.
    Caps pagination at MAX_PHAROS_PAGES per collection as a safety limit.

    Returns list of unique meeting metadata dicts (keyed by MNTS_ID).
    """
    MAX_PHAROS_PAGES = 10  # safety cap -- 인사청문 results should appear in page 1-2

    th = TH_MAP.get(assembly_num)
    if th is None:
        return []

    # Symmetric date window: ±14 days around confirmation_date
    # For 17-19대, confirmation_date is typically the appointment date; the actual
    # hearing usually happens 1-7 days BEFORE, so symmetric window is important.
    date_window: set[str] = set()
    compact = confirmation_date.replace("-", "")
    if len(compact) == 8:
        try:
            d0 = datetime.strptime(compact, "%Y%m%d")
            for i in range(-14, 15):  # ±14 days
                date_window.add((d0 + timedelta(days=i)).strftime("%Y%m%d"))
        except ValueError:
            pass

    found: dict[str, dict] = {}

    for collection in ["record2", "record3"]:
        start = 1
        page  = 0
        while True:
            body = {
                "S_TH":       str(th),
                "E_TH":       str(th),
                "collection": collection,
                "schword":    f"{name} 인사청문",  # compound search: much narrower
                "startCount": str(start),
            }
            rc = pharos_post(session, body, collection)
            total = int(rc.get("totalCount", 0) or 0)
            items = rc.get("resultList", [])

            if not items:
                break
            page += 1

            for item in items:
                mnts_id = (item.get("MNTS_ID", "") or "").strip()
                date    = (item.get("DATE", "") or "")[:8]
                item_nm = item.get("ITEM_NM", "") or ""
                cmit_nm = item.get("CMIT_NM", "") or ""

                if not mnts_id:
                    continue
                if date_window and date not in date_window:
                    continue
                if "인사청문" not in item_nm and "인사청문" not in cmit_nm:
                    continue

                if mnts_id not in found:
                    found[mnts_id] = {
                        "mnts_id":    mnts_id,
                        "cmit_cd":    item.get("CMIT_CD", ""),
                        "cmit_nm":    cmit_nm,
                        "item_nm":    item_nm,
                        "date":       date,
                        "file_ext":   (item.get("MNTS_FILE_EXT", "") or "").upper() or "PDF",
                        "assembly":   assembly_num,
                        "collection": collection,
                    }

            if start + len(items) > total or page >= MAX_PHAROS_PAGES:
                break
            start += len(items)
            time.sleep(0.25)

        time.sleep(0.3)

    return list(found.values())


def discover_17_19(session: requests.Session, ministers: list) -> list:
    """
    Discover 인사청문회 meetings for 17-19대 ministers using name-based Pharos search.
    """
    all_meetings = []
    not_found    = []

    relevant = [
        m for m in ministers
        if int(float(m.get("assembly_num_at_appt", 0) or 0)) in (17, 18, 19)
    ]
    logger.info(f"17-19대 ministers to discover: {len(relevant)}")

    for i, m in enumerate(relevant):
        name      = m.get("name", "").strip()
        ministry  = m.get("ministry", "").strip()
        admin     = m.get("admin", "").strip()
        conf_date = m.get("confirmation_date", "").strip()
        asm       = int(float(m.get("assembly_num_at_appt", 0) or 0))
        dual      = m.get("dual_office", "").strip()

        logger.info(f"  [{i+1}/{len(relevant)}] {name} ({ministry}, {admin}, "
                    f"{asm}대, {conf_date})")

        meetings = find_hearing_meetings_17_19(session, name, asm, conf_date)

        if not meetings:
            logger.warning(f"    -> NOT FOUND in Pharos")
            not_found.append(m)
        else:
            logger.info(f"    -> {len(meetings)} meeting(s): {[mg['date'] for mg in meetings]}")
            for mtg in meetings:
                mtg["minister"]          = name
                mtg["ministry"]          = ministry
                mtg["admin"]             = admin
                mtg["dual_office"]       = dual
                mtg["confirmation_date"] = conf_date
                mtg["hearing_type"]      = "MINISTER_STANDING"
            all_meetings.extend(meetings)

        time.sleep(0.5)

    if not_found:
        logger.warning(f"17-19대 NOT FOUND ({len(not_found)}):")
        for m in not_found:
            logger.warning(f"  {m.get('name','')} ({m.get('ministry','')} {m.get('admin','')})"
                           f" {m.get('confirmation_date','')}")

    return all_meetings


# ── Stage 1: Discover ─────────────────────────────────────────────────────────

def stage_discover(session: requests.Session) -> list:
    """
    Discover 인사청문회 meeting metadata for all non-PM ministers.
    Uses unified MNTS_ID range scan for all 17-22대.
    Saves results to MEETINGS_FILE as a checkpoint.
    """
    ministers = load_ministers()

    # Unified MNTS_ID range scan covers all 17-22대 (HTML viewer works for all terms)
    all_meetings = discover_via_mnts_scan(session, ministers)

    # Deduplicate by (mnts_id, minister)
    seen: set[tuple] = set()
    deduped = []
    for mtg in all_meetings:
        key = (mtg.get("mnts_id", ""), mtg.get("minister", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(mtg)
    all_meetings = deduped

    with open(MEETINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_meetings, f, ensure_ascii=False, indent=2)

    # Summary
    found   = [m for m in all_meetings if m.get("mnts_id")]
    print(f"\n{'='*60}")
    print(f"Discovery complete: {len(found)} meetings found for {len(found)} minister-hearings")
    print(f"Saved to {MEETINGS_FILE}")
    print(f"\nBy assembly:")
    from collections import Counter
    by_asm = Counter(str(m.get("assembly", "?")) for m in found)
    for asm, cnt in sorted(by_asm.items()):
        print(f"  {asm}대: {cnt}")

    return all_meetings


# ── Stage 2: Download transcripts ─────────────────────────────────────────────

def download_pdf(session: requests.Session, mnts_id: str) -> Optional[bytes]:
    """Download PDF transcript for 16-19대 meetings."""
    url = f"{VIEWER_BASE}/viewer/minutes/download/pdf.do?id={mnts_id}"
    try:
        resp = session.get(url, timeout=60)
        if resp.status_code == 200 and b"%PDF" in resp.content[:10]:
            return resp.content
        logger.warning(f"PDF download failed {mnts_id}: status={resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"PDF download error {mnts_id}: {e}")
        return None


def fetch_html_viewer(session: requests.Session, mnts_id: str) -> Optional[str]:
    """Fetch full HTML viewer page for 20-22대 meetings."""
    url = f"{VIEWER_BASE}/viewer/minutes/xml.do?id={mnts_id}&type=view"
    try:
        resp = session.get(url, timeout=60)
        if resp.status_code == 200 and len(resp.text) > 1000:
            if "spk_sub" in resp.text or "위원장" in resp.text:
                return resp.text
            logger.warning(f"HTML viewer {mnts_id}: no speech content")
            return None
        logger.warning(f"HTML viewer failed {mnts_id}: status={resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"HTML viewer error {mnts_id}: {e}")
        return None


def stage_transcripts(session: requests.Session) -> None:
    """
    Download transcript files for all discovered meetings.
    17-19대 -> PDF; 20-22대 -> HTML viewer.
    Skips already-downloaded files.
    """
    if not MEETINGS_FILE.exists():
        logger.error("Run --stage discover first.")
        return

    with open(MEETINGS_FILE, encoding="utf-8") as f:
        meetings = json.load(f)

    # Deduplicate by MNTS_ID for download (multiple ministers can share one meeting)
    seen_mnts: dict[str, dict] = {}
    for mtg in meetings:
        mid = mtg.get("mnts_id", "")
        if mid and mid not in seen_mnts:
            seen_mnts[mid] = mtg

    logger.info(f"Downloading transcripts for {len(seen_mnts)} unique meetings")
    ok = fail = skip = 0

    for mnts_id, mtg in seen_mnts.items():
        asm      = int(mtg.get("assembly", 0) or 0)
        file_ext = (mtg.get("file_ext", "") or "").upper()
        is_pdf   = (file_ext == "PDF")  # 17대 HTML viewer works; 18/19대 excluded from discovery

        out_path = TRANSCRIPTS / (f"{mnts_id}.pdf" if is_pdf else f"{mnts_id}.html")
        if out_path.exists():
            skip += 1
            continue

        if is_pdf:
            content = download_pdf(session, mnts_id)
            if content:
                out_path.write_bytes(content)
                ok += 1
                logger.info(f"  PDF saved: {mnts_id} ({len(content)//1024}KB)")
            else:
                fail += 1
        else:
            html = fetch_html_viewer(session, mnts_id)
            if html:
                out_path.write_text(html, encoding="utf-8")
                ok += 1
                logger.info(f"  HTML saved: {mnts_id} ({len(html)//1024}KB)")
            else:
                fail += 1

        time.sleep(0.4)

    logger.info(f"Transcripts: {ok} saved, {skip} already existed, {fail} failed")


# ── Speech and Q-A dyad parsing ───────────────────────────────────────────────

def parse_speeches_from_html(html: str) -> list:
    """
    Parse speech turns from the Pharos HTML viewer page (20-22대 XML format).

    Structure:
        <strong class="name">발언자이름</strong>
        <span class="position">직책</span>
        <span class="area">지역구</span>
        <div class="talk"><div class="txt">
            <span class="spk_sub" id="spk_sub{N}-{M}">발언내용</span>
        </div></div>
    """
    speeches = []
    speaker_pattern = re.compile(
        r'<strong class="name">([^<]+)</strong>'
        r'(?:.*?<span class="position">([^<]*)</span>)?'
        r'(?:.*?<span class="area">([^<]*)</span>)?'
        r'.*?<div class="talk">.*?<div class="txt">(.*?)</div>\s*</div>\s*</div>',
        re.DOTALL,
    )
    for m in speaker_pattern.finditer(html):
        name     = m.group(1).strip()
        position = (m.group(2) or "").strip()
        area     = (m.group(3) or "").strip()
        raw_text = m.group(4)

        texts = re.findall(
            r'<span class="spk_sub"[^>]*>([^<]*(?:<br/>[^<]*)*)</span>',
            raw_text, re.DOTALL,
        )
        if not texts:
            texts = [re.sub(r"<[^>]+>", " ", raw_text)]

        full_text = " ".join(
            re.sub(r"\s+", " ", t.replace("&nbsp;", " ").replace("<br/>", " ").strip())
            for t in texts
        ).strip()

        if name and full_text:
            speeches.append({
                "speaker_name": name,
                "position":     position,
                "area":         area,
                "text":         full_text,
            })
    return speeches


def parse_qa_dyads(speeches: list, meeting_meta: dict) -> list:
    """
    Build Q-A dyads from an ordered list of speech turns.

    Questioner: 위원/의원 who is NOT the candidate (후보자).
    Respondent: the candidate (identified by name or 후보자 in position).
    """
    candidate = meeting_meta.get("minister", "")
    dyads      = []
    q_buffer   = None
    q_name     = None
    q_position = None
    q_area     = None
    q_order    = 0

    for sp in speeches:
        name     = sp["speaker_name"]
        position = sp.get("position", "")
        text     = sp["text"]
        area     = sp.get("area", "")

        is_candidate = (
            (candidate and (candidate in name or name in candidate))
            or "후보자" in position
            or "장관후보자" in position
            or ("장관" in position and candidate and candidate in name)
        )
        is_questioner = (
            ("위원" in position or "의원" in position)
            and not is_candidate
        )

        if is_questioner and text and len(text) > 10:
            q_buffer   = text
            q_name     = name
            q_position = position
            q_area     = area
            q_order   += 1

        elif is_candidate and q_buffer and text and len(text) > 10:
            dyads.append({
                "dyad_id":       None,
                "hearing_id":    meeting_meta.get("mnts_id", ""),
                "assembly":      meeting_meta.get("assembly", ""),
                "date":          meeting_meta.get("date", ""),
                "cmit_nm":       meeting_meta.get("cmit_nm", ""),
                "minister":      candidate,
                "ministry":      meeting_meta.get("ministry", ""),
                "admin":         meeting_meta.get("admin", ""),
                "dual_office":   meeting_meta.get("dual_office", ""),
                "q_speaker":     q_name,
                "q_position":    q_position,
                "q_area":        q_area,
                "q_text":        q_buffer,
                "q_word_count":  len(q_buffer.split()),
                "r_speaker":     name,
                "r_position":    position,
                "r_text":        text,
                "r_word_count":  len(text.split()),
                "q_order":       q_order,
            })
            q_buffer   = None
            q_name     = None
            q_position = None
            q_area     = None

    return dyads


# ── Stage 3: Parse Q-A dyads ──────────────────────────────────────────────────

def stage_dyads() -> None:
    """
    Parse Q-A dyads from downloaded HTML transcripts.
    PDF transcripts (17-19대) are flagged for separate pdfplumber parsing.
    """
    if not MEETINGS_FILE.exists():
        logger.error("Run --stage discover first.")
        return

    with open(MEETINGS_FILE, encoding="utf-8") as f:
        meetings = json.load(f)

    all_dyads = []

    for mtg in meetings:
        mnts_id = mtg.get("mnts_id", "")
        if not mnts_id:
            continue

        html_path = TRANSCRIPTS / f"{mnts_id}.html"
        pdf_path  = TRANSCRIPTS / f"{mnts_id}.pdf"

        if html_path.exists():
            html     = html_path.read_text(encoding="utf-8")
            speeches = parse_speeches_from_html(html)
            if speeches:
                dyads = parse_qa_dyads(speeches, mtg)
                all_dyads.extend(dyads)
                logger.info(f"  {mnts_id} ({mtg.get('minister','')}): "
                            f"{len(speeches)} speeches -> {len(dyads)} dyads")
            else:
                logger.warning(f"  {mnts_id}: no speeches parsed from HTML")

        elif pdf_path.exists():
            logger.info(f"  {mnts_id}: PDF flagged for separate pdfplumber parsing")

        else:
            logger.warning(f"  {mnts_id}: no transcript file found")

    # Assign dyad IDs
    for i, d in enumerate(all_dyads):
        d["dyad_id"] = i

    out_path = PROCESSED_DIR / "minister_dyads.csv"
    if all_dyads:
        fieldnames = list(all_dyads[0].keys())
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv_mod.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_dyads)

        dual   = sum(1 for d in all_dyads if str(d.get("dual_office", "")).upper() == "TRUE")
        nodual = sum(1 for d in all_dyads if str(d.get("dual_office", "")).upper() == "FALSE")
        logger.info(f"Dyads saved: {len(all_dyads)} total -> {out_path}")
        logger.info(f"  dual_office=TRUE:  {dual}")
        logger.info(f"  dual_office=FALSE: {nodual}")
    else:
        logger.warning("No HTML dyads extracted; run PDF parsing separately for 17-19대")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Stage 1b: Collect 장관 인사청문 transcripts and parse Q-A dyads"
    )
    parser.add_argument(
        "--stage",
        choices=["discover", "transcripts", "dyads", "all"],
        default="all",
        help="Stage to run",
    )
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(PHAROS_HEADERS)

    if args.stage in ("discover", "all"):
        meetings = stage_discover(session)
        logger.info(f"Discovered {len(meetings)} minister-hearing pairs total")

    if args.stage in ("transcripts", "all"):
        stage_transcripts(session)

    if args.stage in ("dyads", "all"):
        stage_dyads()


if __name__ == "__main__":
    main()
