"""
인사청문회 회의록 수집 스크립트 (v2)
Confirmation Hearing Transcript Collector

Collects 인사청문회 transcripts for ministers in minister_panel_manual.csv.
Outputs structured meeting metadata and transcript text for Q-A dyad extraction.

Usage:
    # Stage 1: Discover meetings for all ministers in panel
    python collect_hearing_transcripts.py --stage discover --api-key KEY

    # Stage 2: Download transcripts (PDF for 16-19대, HTML for 20-22대)
    python collect_hearing_transcripts.py --stage transcripts --api-key KEY

    # Stage 3: Parse Q-A dyads from collected transcripts
    python collect_hearing_transcripts.py --stage dyads

    # Run all stages sequentially
    python collect_hearing_transcripts.py --stage all --api-key KEY

Output:
    data/raw/hearing_meetings.json          -- meeting metadata (all ministers)
    data/raw/transcripts/{MNTS_ID}.{ext}    -- raw transcript files
    data/processed/dyads_hearing.csv        -- Q-A dyad dataset

API:
    - Pharos: https://record.assembly.go.kr/assembly/mnts/search/search.do
    - Viewer: https://record.assembly.go.kr/assembly/viewer/minutes/

Data structure:
    - 16-19대: document-level records, MNTS_FILE_EXT=PDF
    - 20-22대: speech-level records, MNTS_FILE_EXT=xml (HTML viewer available)
"""

import requests
import json
import time
import csv
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

DATA_DIR      = Path(__file__).parent.parent / "data"
RAW_DIR       = DATA_DIR / "raw"
TRANSCRIPTS   = RAW_DIR / "transcripts"
PROCESSED_DIR = DATA_DIR / "processed"
for d in [RAW_DIR, TRANSCRIPTS, PROCESSED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

MINISTER_PANEL = DATA_DIR / "minister_panel_manual.csv"
MEETINGS_FILE  = RAW_DIR / "hearing_meetings.json"

# ── API configuration ────────────────────────────────────────────────────────

PHAROS_URL    = "https://record.assembly.go.kr/assembly/mnts/search/search.do"
VIEWER_BASE   = "https://record.assembly.go.kr/assembly"
PHAROS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DualOfficeResearch/2.0; Academic)",
    "Referer":    "https://record.assembly.go.kr/",
}

# Pharos TH (term) = assembly_num + 2
TH_MAP = {16: 18, 17: 19, 18: 20, 19: 21, 20: 22, 21: 23, 22: 24}

# ── Known CMIT_CDs for PM 인사청문특별위원회 ─────────────────────────────────
# Discovered through systematic Pharos API enumeration (2026-03-01)
# Format: CMIT_CD -> {name, assembly_num, minister_name}
PM_HEARING_CMIT_CODES = {
    # 16대 (2000-2004) -- 김대중 정부
    "16-3-S2-0": {"name": "국무총리(이한동)임명동의에관한인사청문특별위원회",      "assembly": 16, "minister": "이한동"},
    "16-3-S7-0": {"name": "국무총리(장상)임명동의에관한인사청문특별위원회",        "assembly": 16, "minister": "장상"},
    "16-3-S8-0": {"name": "국무총리(장대환)임명동의에관한인사청문특별위원회",      "assembly": 16, "minister": "장대환"},
    "16-3-S9-0": {"name": "국무총리(김석수)임명동의에관한인사청문특별위원회",      "assembly": 16, "minister": "김석수"},
    "16-3-SB-0": {"name": "국무총리후보자(고건)에관한인사청문특별위원회",          "assembly": 16, "minister": "고건"},
    # 17대 (2004-2008) -- 노무현 정부
    "17-3-SH-0": {"name": "국무총리(이해찬)임명동의에관한인사청문특별위원회",      "assembly": 17, "minister": "이해찬"},
    "17-3-SP-0": {"name": "국무총리(한명숙)임명동의에관한인사청문특별위원회",      "assembly": 17, "minister": "한명숙"},
    "17-3-ST-0": {"name": "국무총리(한덕수)임명동의에관한인사청문특별위원회",      "assembly": 17, "minister": "한덕수_노무현"},
    "17-3-SV-0": {"name": "국무총리후보자(한승수)에관한인사청문특별위원회",        "assembly": 17, "minister": "한승수"},
    # 18대 (2008-2012) -- 이명박 정부
    # 한승수 hearing was in 17대 assembly (2008-02), NOT 18대
    "18-3-TE-0": {"name": "국무총리(정운찬)임명동의에관한인사청문특별위원회",      "assembly": 18, "minister": "정운찬"},
    # 19대 (2012-2016) -- 박근혜 정부
    "19-3-T4-0": {"name": "국무총리후보자(정홍원)에관한인사청문특별위원회",        "assembly": 19, "minister": "정홍원"},
    "19-3-AG-0": {"name": "국무총리(이완구)임명동의에관한인사청문특별위원회",      "assembly": 19, "minister": "이완구"},
    "19-3-AA-0": {"name": "국무총리(황교안)임명동의에관한인사청문특별위원회",      "assembly": 19, "minister": "황교안"},
    # 20대 (2016-2020) -- 문재인 정부
    "20-3-AK-0": {"name": "국무총리(이낙연)임명동의에관한인사청문특별위원회",      "assembly": 20, "minister": "이낙연"},
    # 이해찬 총리 (2018): 인사청문회 진행 여부 불확실 -- 위원회 미확인
    "20-3-BE-0": {"name": "국무총리(정세균)임명동의에관한인사청문특별위원회",      "assembly": 20, "minister": "정세균_총리"},
    # 21대 (2020-2024) -- 문재인/윤석열 정부
    "21-3-AF-0": {"name": "국무총리(김부겸)임명동의에관한인사청문특별위원회",      "assembly": 21, "minister": "김부겸_총리"},
    "21-3-AM-0": {"name": "국무총리후보자(한덕수)에관한인사청문특별위원회",        "assembly": 21, "minister": "한덕수"},
}

# ── Pharos API helpers ───────────────────────────────────────────────────────

def pharos_post(session: requests.Session, body: dict, collection: str = "record3") -> dict:
    """POST to Pharos search API. Returns parsed result dict."""
    try:
        resp = session.post(PHAROS_URL, data=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get(collection, {})
    except Exception as e:
        logger.warning(f"Pharos error: {e}")
        return {}


def get_meetings_by_cmit(
    session: requests.Session,
    cmit_cd: str,
    assembly_num: int,
    collection: str = "record3",
) -> list:
    """
    Get all meeting records for a given CMIT_CD.

    For 16-19대 (document-level): each record = one meeting document.
    For 20-22대 (speech-level): each record = one speech; deduplicate by MNTS_ID.
    """
    th = TH_MAP[assembly_num]
    all_items = []
    seen_mnts = set()
    unique_meetings = []
    start = 1

    while True:
        body = {
            "S_TH":      str(th),
            "E_TH":      str(th),
            "collection": collection,
            "CMIT_CD":   cmit_cd,
            "startCount": str(start),
        }
        rc = pharos_post(session, body, collection)
        total = int(rc.get("totalCount", 0) or 0)
        items = rc.get("resultList", [])
        if not items:
            break

        for item in items:
            mnts_id = item.get("MNTS_ID", "")
            if mnts_id and mnts_id not in seen_mnts:
                seen_mnts.add(mnts_id)
                unique_meetings.append({
                    "mnts_id":   mnts_id,
                    "cmit_cd":   item.get("CMIT_CD", cmit_cd),
                    "cmit_nm":   item.get("CMIT_NM", ""),
                    "date":      item.get("DATE", "")[:8],
                    "file_ext":  item.get("MNTS_FILE_EXT", "").upper(),
                    "docid":     item.get("DOCID", ""),
                    "confer_num": item.get("CONFER_NUM", ""),
                    "assembly":  assembly_num,
                    "collection": collection,
                })

        all_items.extend(items)
        if len(all_items) >= total:
            break
        start += len(items)
        time.sleep(0.3)

    logger.info(f"  {cmit_cd}: {len(unique_meetings)} unique meetings from {len(all_items)} records")
    return unique_meetings


def search_minister_hearings_record2(
    session: requests.Session,
    minister_name: str,
    assembly_num: int,
    confirmation_date: str,
) -> list:
    """
    Search for 장관 인사청문회 in record2 (상임위원회) by minister name.

    For ministers confirmed through standing committees (post-2012 개정 이후),
    the hearing appears in the relevant 상임위 with ITEM_NM referencing 인사청문.
    """
    th = TH_MAP.get(assembly_num)
    if th is None:
        return []

    all_meetings = []
    seen_mnts = set()

    for start in range(1, 200, 10):
        body = {
            "S_TH":       str(th),
            "E_TH":       str(th),
            "collection": "record2",
            "schword":    minister_name,
            "startCount": str(start),
        }
        rc = pharos_post(session, body, "record2")
        total = int(rc.get("totalCount", 0) or 0)
        items = rc.get("resultList", [])
        if not items:
            break

        for item in items:
            item_nm  = item.get("ITEM_NM", "")
            cmit_nm  = item.get("CMIT_NM", "")
            spk_cnts = item.get("SPK_CNTS", "")
            mnts_id  = item.get("MNTS_ID", "")

            # Filter: item name or speaker content must reference 인사청문
            is_hearing = (
                "인사청문" in item_nm
                or "인사청문" in cmit_nm
                or (minister_name in spk_cnts and "청문" in spk_cnts)
            )
            if is_hearing and mnts_id and mnts_id not in seen_mnts:
                seen_mnts.add(mnts_id)
                all_meetings.append({
                    "mnts_id":   mnts_id,
                    "cmit_cd":   item.get("CMIT_CD", ""),
                    "cmit_nm":   cmit_nm,
                    "item_nm":   item_nm,
                    "date":      item.get("DATE", "")[:8],
                    "file_ext":  item.get("MNTS_FILE_EXT", "").upper(),
                    "docid":     item.get("DOCID", ""),
                    "assembly":  assembly_num,
                    "collection": "record2",
                })

        if start + 9 >= total:
            break
        time.sleep(0.3)

    return all_meetings


# ── Transcript retrieval ─────────────────────────────────────────────────────

def download_pdf(session: requests.Session, mnts_id: str) -> Optional[bytes]:
    """Download PDF transcript for 16-19대 meetings."""
    url = f"{VIEWER_BASE}/viewer/minutes/download/pdf.do?id={mnts_id}"
    try:
        resp = session.get(url, timeout=60)
        if resp.status_code == 200 and b"%PDF" in resp.content[:10]:
            return resp.content
        logger.warning(f"PDF download failed for {mnts_id}: status={resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"PDF download error {mnts_id}: {e}")
        return None


def fetch_html_viewer(session: requests.Session, mnts_id: str) -> Optional[str]:
    """Fetch HTML viewer page for 20-22대 meetings (XML format)."""
    url = f"{VIEWER_BASE}/viewer/minutes/xml.do?id={mnts_id}&type=view"
    try:
        resp = session.get(url, timeout=60)
        if resp.status_code == 200 and len(resp.text) > 1000:
            if "spk_sub" in resp.text or "위원장" in resp.text:
                return resp.text
            else:
                logger.warning(f"HTML viewer for {mnts_id}: no speech content found")
                return None
        logger.warning(f"HTML viewer failed for {mnts_id}: status={resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"HTML viewer error {mnts_id}: {e}")
        return None


# ── Speech extraction from HTML ──────────────────────────────────────────────

def parse_speeches_from_html(html: str) -> list:
    """
    Parse speech turns from the Pharos HTML viewer page.

    Structure (20-22대 XML format):
        <strong class="name">발언자이름</strong>
        <span class="position">직책</span>
        <span class="area">지역구</span>
        ...
        <div class="talk">
          <div class="txt">
            <span class="spk_sub" id="spk_sub{N}-{M}">&nbsp;발언내용</span>
            <br/>...
          </div>
        </div>

    Returns:
        list of {"speaker_name": str, "position": str, "area": str, "text": str}
    """
    speeches = []

    # Extract speaker blocks: name + position + area + talk content
    # Pattern: speaker info div followed by talk div
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

        # Extract text from spk_sub spans
        texts = re.findall(r'<span class="spk_sub"[^>]*>([^<]*(?:<br/>[^<]*)*)</span>', raw_text, re.DOTALL)
        if not texts:
            # Fallback: strip all tags
            texts = [re.sub(r"<[^>]+>", " ", raw_text)]

        # Clean: remove &nbsp;, <br/>, extra whitespace
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


# ── Q-A Dyad parsing ─────────────────────────────────────────────────────────

def parse_qa_dyads(speeches: list, meeting_meta: dict) -> list:
    """
    Build Q-A dyads from an ordered list of speech turns.

    Rules:
    - Questioner (질문자): a 위원/의원 who is NOT the candidate/minister
    - Respondent (답변자): identified by candidate_name or position containing 후보자/장관
    - A dyad = (questioner_speech, immediate_respondent_speech)
    - Follow-up questions extend the dyad sequence.

    Args:
        speeches:     List of {"speaker_name", "position", "text", ...}
        meeting_meta: Context dict with "candidate_name", "minister", "assembly", etc.

    Returns:
        List of dyad dicts.
    """
    candidate = meeting_meta.get("minister", "")
    dyads = []
    q_buffer   = None
    q_name     = None
    q_position = None
    q_order    = 0

    for i, sp in enumerate(speeches):
        name     = sp["speaker_name"]
        position = sp.get("position", "")
        text     = sp["text"]

        # Identify if this speaker is the candidate/minister respondent
        is_candidate = (
            candidate and (candidate in name or name in candidate)
        ) or "후보자" in position or "장관" in position

        # Identify questioner (committee member = 위원)
        is_questioner = (
            "위원" in position or "의원" in position
            or ("위원장" in name and "위원장" in position)
        ) and not is_candidate

        if is_questioner and text and len(text) > 10:
            # Start or continue a question buffer
            q_buffer   = text
            q_name     = name
            q_position = position
            q_order   += 1

        elif is_candidate and q_buffer and text and len(text) > 10:
            # Candidate responded -- form a dyad
            dyad = {
                "dyad_id":       None,  # assigned later
                "hearing_id":    meeting_meta.get("mnts_id", ""),
                "assembly":      meeting_meta.get("assembly", ""),
                "date":          meeting_meta.get("date", ""),
                "cmit_nm":       meeting_meta.get("cmit_nm", ""),
                "minister":      candidate,
                "dual_office":   meeting_meta.get("dual_office"),
                "q_speaker":     q_name,
                "q_position":    q_position,
                "q_text":        q_buffer,
                "q_word_count":  len(q_buffer.split()),
                "r_speaker":     name,
                "r_position":    position,
                "r_text":        text,
                "r_word_count":  len(text.split()),
                "q_order":       q_order,
            }
            dyads.append(dyad)
            q_buffer   = None
            q_name     = None
            q_position = None

    return dyads


# ── Stage 1: Discover meetings ───────────────────────────────────────────────

def stage_discover(session: requests.Session) -> list:
    """
    Discover all 인사청문회 meetings for ministers in the panel.

    Returns list of meeting metadata dicts, saved to MEETINGS_FILE.
    """
    # Load minister panel
    ministers = []
    with open(MINISTER_PANEL, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        ministers = [row for row in reader if row.get("confirmation_hearing") == "TRUE"]

    logger.info(f"Minister panel: {len(ministers)} ministers with confirmation hearings")

    all_meetings = []

    # --- PM hearings via hardcoded CMIT_CDs (record3) ---
    logger.info("=== Stage 1a: PM 인사청문특별위원회 ===")
    for cmit_cd, info in PM_HEARING_CMIT_CODES.items():
        assembly = info["assembly"]
        minister = info["minister"]
        logger.info(f"  {cmit_cd}: {info['name'][:50]}")
        meetings = get_meetings_by_cmit(session, cmit_cd, assembly, "record3")
        for mtg in meetings:
            mtg["minister"]   = minister
            mtg["hearing_type"] = "PM_SPECIAL"
            # Lookup dual_office from minister panel
            match = [m for m in ministers if m.get("name") == minister.split("_")[0]]
            if match:
                mtg["dual_office"] = match[0].get("dual_office", "")
                mtg["confirmation_date"] = match[0].get("confirmation_date", "")
            else:
                mtg["dual_office"] = ""
                mtg["confirmation_date"] = ""
        all_meetings.extend(meetings)
        time.sleep(0.5)

    # --- Minister hearings via record2 search ---
    logger.info("=== Stage 1b: 장관 인사청문 (record2 search) ===")
    for m in ministers:
        name     = m["name"]
        ministry = m["ministry"]
        assembly = m.get("assembly_num_at_appt", "")

        # Skip PM (already handled above)
        if ministry == "국무총리":
            continue
        if not assembly:
            continue

        try:
            assembly_int = int(assembly)
        except ValueError:
            continue

        # Skip if assembly not in range
        if assembly_int < 16 or assembly_int > 22:
            continue

        logger.info(f"  Searching: {name} ({ministry}, {assembly}대)")
        meetings = search_minister_hearings_record2(session, name, assembly_int,
                                                    m.get("confirmation_date", ""))
        for mtg in meetings:
            mtg["minister"]     = name
            mtg["ministry"]     = ministry
            mtg["dual_office"]  = m.get("dual_office", "")
            mtg["hearing_type"] = "MINISTER_STANDING"
            mtg["confirmation_date"] = m.get("confirmation_date", "")
        all_meetings.extend(meetings)
        time.sleep(0.3)

    # Save checkpoint
    with open(MEETINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_meetings, f, ensure_ascii=False, indent=2)

    logger.info(f"Discovery complete: {len(all_meetings)} meetings saved to {MEETINGS_FILE}")
    return all_meetings


# ── Stage 2: Download transcripts ────────────────────────────────────────────

def stage_transcripts(session: requests.Session) -> None:
    """
    Download transcript files for all discovered meetings.

    - 16-19대 (PDF): saves to data/raw/transcripts/{MNTS_ID}.pdf
    - 20-22대 (XML/HTML): saves to data/raw/transcripts/{MNTS_ID}.html
    """
    if not MEETINGS_FILE.exists():
        logger.error(f"Meetings file not found: {MEETINGS_FILE}. Run --stage discover first.")
        return

    with open(MEETINGS_FILE, encoding="utf-8") as f:
        meetings = json.load(f)

    logger.info(f"Downloading transcripts for {len(meetings)} meetings")

    ok = 0
    skip = 0
    fail = 0

    for mtg in meetings:
        mnts_id  = mtg.get("mnts_id", "")
        file_ext = mtg.get("file_ext", "").upper()
        assembly = mtg.get("assembly", 0)

        if not mnts_id:
            continue

        # Determine output path
        if assembly <= 19 or file_ext == "PDF":
            out_path = TRANSCRIPTS / f"{mnts_id}.pdf"
        else:
            out_path = TRANSCRIPTS / f"{mnts_id}.html"

        if out_path.exists():
            skip += 1
            continue

        if assembly <= 19 or file_ext == "PDF":
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

        time.sleep(0.5)

    logger.info(f"Transcripts: {ok} downloaded, {skip} skipped, {fail} failed")


# ── Stage 3: Parse Q-A dyads ─────────────────────────────────────────────────

def stage_dyads() -> None:
    """
    Parse Q-A dyads from downloaded transcripts.

    Currently handles HTML viewer format (20-22대).
    PDF parsing (16-19대) requires pdfplumber -- flagged for later.
    """
    if not MEETINGS_FILE.exists():
        logger.error("Meetings file not found. Run --stage discover first.")
        return

    with open(MEETINGS_FILE, encoding="utf-8") as f:
        meetings = json.load(f)

    all_dyads = []

    for mtg in meetings:
        mnts_id  = mtg.get("mnts_id", "")
        assembly = mtg.get("assembly", 0)

        if not mnts_id:
            continue

        # Identify transcript file
        html_path = TRANSCRIPTS / f"{mnts_id}.html"
        pdf_path  = TRANSCRIPTS / f"{mnts_id}.pdf"

        if html_path.exists():
            html = html_path.read_text(encoding="utf-8")
            speeches = parse_speeches_from_html(html)
            if speeches:
                dyads = parse_qa_dyads(speeches, mtg)
                all_dyads.extend(dyads)
                logger.info(f"  {mnts_id}: {len(speeches)} speeches -> {len(dyads)} dyads")
            else:
                logger.warning(f"  {mnts_id}: no speeches parsed from HTML")

        elif pdf_path.exists():
            # PDF parsing: requires pdfplumber
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                if text:
                    # Simple pattern-based parsing for PDF text
                    speeches = parse_pdf_text(text, mtg)
                    dyads = parse_qa_dyads(speeches, mtg)
                    all_dyads.extend(dyads)
                    logger.info(f"  {mnts_id}: {len(speeches)} speeches -> {len(dyads)} dyads (PDF)")
                else:
                    logger.warning(f"  {mnts_id}: no text extracted from PDF")
            except ImportError:
                logger.warning(f"  {mnts_id}: pdfplumber not installed, skipping PDF")
            except Exception as e:
                logger.error(f"  {mnts_id}: PDF parse error: {e}")
        else:
            logger.warning(f"  {mnts_id}: no transcript file found")

    # Assign dyad IDs and save
    for i, d in enumerate(all_dyads):
        d["dyad_id"] = i

    out_path = PROCESSED_DIR / "dyads_hearing.csv"
    if all_dyads:
        import csv as csv_mod
        fieldnames = list(all_dyads[0].keys())
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv_mod.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_dyads)

        dual_count   = sum(1 for d in all_dyads if str(d.get("dual_office")).upper() == "TRUE")
        nodual_count = sum(1 for d in all_dyads if str(d.get("dual_office")).upper() == "FALSE")
        logger.info(f"Dyads saved: {len(all_dyads)} total -> {out_path}")
        logger.info(f"  dual_office=TRUE:  {dual_count}")
        logger.info(f"  dual_office=FALSE: {nodual_count}")
    else:
        logger.warning("No dyads extracted. Check transcript files.")


def parse_pdf_text(text: str, meeting_meta: dict) -> list:
    """
    Parse speech turns from Korean National Assembly transcript PDF text.

    Handles:
    - 17대+ Korean-only transcripts (2004+)
    - 16대 Chinese-character names (2000-2004): 委員長 金德圭, 後補者 李漢東

    Due to pdfplumber 2-column merging, the first "line" of a block may contain
    both speaker identifier AND speech content on the same line. We match the
    speaker from the START of the block (no $ anchor) and treat the rest as speech.

    Patterns (at start of block):
        "위원장 홍길동 의석을..."   -> position="위원장", name="홍길동"
        "홍길동 위원 시간이..."     -> name="홍길동", position="위원"
        "위원장 金德圭 의석을..."   -> position="위원장", name="金德圭" (16대 mixed)
        "委員長 金德圭 의석을..."   -> position="委員長", name="金德圭" (16대 Chinese)
    """
    speeches = []

    # Hangul name pattern (2-5 chars)
    KO = r"[가-힣]{2,5}"
    # Chinese character pattern (2-5 chars, for 16대 names)
    ZH = r"[\u4e00-\u9fff]{1,5}"
    # Either Hangul or Chinese for names
    NAME = rf"(?:{KO}|{ZH})"
    # Position words (may include Chinese or Korean)
    POS  = rf"[가-힣\u4e00-\u9fff]{{2,15}}"

    # Pattern A: position first, Korean name -- e.g., "위원장 홍길동 ..."
    # Pattern B: name first, Korean position  -- e.g., "홍길동 위원 ..."
    # Pattern C: position first, Chinese name -- e.g., "委員長 金德圭 ..."
    # Pattern D: Chinese position + Korean name (mixed) -- e.g., "後補者 이해찬 ..."
    speaker_re = re.compile(
        rf"^({POS}(?:\s+{POS})?)\s+({NAME})\s"  # position-first (A/C/D)
    )
    speaker_re_name_first = re.compile(
        rf"^({KO})\s+({POS})\s"  # name-first (B)
    )

    # Split by the ○ marker
    blocks = re.split(r"\n\s*[○◯◉]\s*", text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Try position-first pattern at start of block
        m = speaker_re.match(block)
        if m:
            position  = m.group(1).strip()
            name      = m.group(2).strip()
            speech_text = block[m.end():].strip()
        else:
            # Try name-first pattern
            m2 = speaker_re_name_first.match(block)
            if m2:
                name      = m2.group(1).strip()
                position  = m2.group(2).strip()
                speech_text = block[m2.end():].strip()
            else:
                continue  # Skip unrecognized blocks

        # Combine any remaining lines as speech text
        if not speech_text:
            lines = block.split("\n")
            speech_text = "\n".join(lines[1:]).strip()

        # Clean up column-bleed artifacts: remove embedded ○ markers
        speech_text = re.sub(r"[○◯◉]\s*[가-힣\u4e00-\u9fff]+\s+[가-힣\u4e00-\u9fff]+\s*", " ", speech_text)
        speech_text = re.sub(r"\s+", " ", speech_text).strip()

        if name and len(speech_text) > 5:
            speeches.append({
                "speaker_name": name,
                "position":     position,
                "area":         "",
                "text":         speech_text,
            })

    return speeches


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="인사청문회 회의록 수집 및 Q-A dyad 구축 (v2)")
    parser.add_argument("--api-key",  default="d74b52f3a3d340969a16879df76c1496",
                        help="국회 Open API 키 (현재 미사용 -- Pharos 기반)")
    parser.add_argument("--stage",    choices=["discover", "transcripts", "dyads", "all"],
                        default="all",  help="실행 단계")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(PHAROS_HEADERS)

    if args.stage in ("discover", "all"):
        meetings = stage_discover(session)
        logger.info(f"Discovered {len(meetings)} meetings")

    if args.stage in ("transcripts", "all"):
        stage_transcripts(session)

    if args.stage in ("dyads", "all"):
        stage_dyads()


if __name__ == "__main__":
    main()
