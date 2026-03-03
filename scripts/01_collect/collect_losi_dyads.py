"""
collect_losi_dyads.py

Parse LOSI xlsx files (16-22대) and extract Q-A dyads for:
  1. 인사청문회 -- from 상임위원회 files (안건 contains "국무위원후보자" + "인사청문")
  2. 국정감사   -- from 국정감사 files  (minister name appears as speaker)

Format differences:
  16-20대: folder of per-committee xlsx files (one sheet, header row=0, 안건 column)
  21-22대: single xlsx with multiple sheets named {회의번호}_발언내용
           (header row=2, 안건1 + 안건2 columns, committee from 위원회 column)

Usage:
    cd projects/dual-office
    python scripts/collect_losi_dyads.py --type all --assemblies 17 18 19 20 21 22
    python scripts/collect_losi_dyads.py --type audit --assemblies 21 22
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterator, Optional, Tuple

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE       = Path(__file__).parent.parent
DATA_DIR   = BASE / "data"
LOSI_BASE  = Path("/Volumes/kyusik-ssd/kyusik-research/data-national-assembly-meetings")
PANEL_FILE = DATA_DIR / "minister_panel_comprehensive.csv"
OUT_DIR    = DATA_DIR / "raw" / "losi"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Assembly config ────────────────────────────────────────────────────────────
ASSEMBLY_MAP = {
    16: "제16대 국회",
    17: "제17대 국회",
    18: "제18대 국회",
    19: "제19대 국회",
    20: "제20대 국회",
    21: "제21대 국회",
    22: "제22대 국회",
}

# 21-22대: single xlsx with multiple sheets (one sheet per session)
MULTI_SHEET_ASSEMBLIES = {21, 22}

# ── Minister panel ─────────────────────────────────────────────────────────────
def load_panel() -> pd.DataFrame:
    panel = pd.read_csv(PANEL_FILE)
    panel["start_dt"] = pd.to_datetime(panel["start"], errors="coerce")
    panel["end_dt"]   = pd.to_datetime(panel["end"],   errors="coerce")
    return panel

# ── Helpers ────────────────────────────────────────────────────────────────────
def concat_content(row) -> str:
    """Concatenate 발언내용1-7 into a single string."""
    parts = []
    for i in range(1, 8):
        col = f"발언내용{i}"
        if col in row.index:
            val = row[col]
            if pd.notna(val) and str(val).strip() not in ("", "nan"):
                parts.append(str(val).strip())
    return " ".join(parts)

def parse_date(date_str) -> Optional[str]:
    """Parse LOSI date formats -> 'YYYY-MM-DD'."""
    if pd.isna(date_str):
        return None
    s = str(date_str)
    # '2009年7月13日(月)'
    m = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # '2009년06월16일' or '2020년10월7일(수)'
    m2 = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", s)
    if m2:
        return f"{m2.group(1)}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
    return s[:10] if len(s) >= 10 else None

def is_questioner(speaker: str) -> bool:
    """True if speaker is a committee member (questioner)."""
    if pd.isna(speaker):
        return False
    s = str(speaker).strip()
    if re.search(r"위원$", s):
        return True
    if re.search(r"위원장$", s) or re.search(r"위원장대리$", s):
        return True
    return False

def minister_in_speaker(speaker: str, minister_name: str) -> bool:
    """True if speaker is the minister (name followed by space or end of string)."""
    if pd.isna(speaker):
        return False
    s = str(speaker).strip()
    idx = s.find(minister_name)
    if idx == -1:
        return False
    # Ensure name is not a prefix of a longer name (substring guard)
    end_pos = idx + len(minister_name)
    if end_pos < len(s):
        next_char = s[end_pos]
        if "\uAC00" <= next_char <= "\uD7A3" or "\u3131" <= next_char <= "\u314E":
            return False
    return True

def normalize_agenda(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure df has a unified '안건' column.
    For 21-22대 which have 안건1 + 안건2, combine them."""
    if "안건" not in df.columns:
        df = df.copy()
        parts = []
        for col in ["안건1", "안건2"]:
            if col in df.columns:
                parts.append(df[col].fillna(""))
        if parts:
            df["안건"] = parts[0] if len(parts) == 1 else parts[0].str.cat(parts[1], sep=" ")
        else:
            df["안건"] = ""
    return df

# ── File loading ───────────────────────────────────────────────────────────────
def load_xlsx(path: str) -> Optional[pd.DataFrame]:
    """Load single-sheet xlsx (16-20대). Returns None on error."""
    try:
        df = pd.read_excel(path, dtype=str)
        required = {"회의번호", "발언자", "발언순번"}
        if not required.issubset(set(df.columns)):
            return None
        df = normalize_agenda(df)
        df["발언순번"] = pd.to_numeric(df["발언순번"], errors="coerce")
        return df
    except Exception as e:
        print(f"  [WARN] Failed to load {path}: {e}", file=sys.stderr)
        return None

def iter_meeting_sheets(path: str) -> Iterator[Tuple[str, str, pd.DataFrame]]:
    """Iterate over sessions in a multi-sheet xlsx (21-22대).
    Yields (meeting_id, committee, df) for each speech sheet."""
    try:
        xl = pd.ExcelFile(path)
    except Exception as e:
        print(f"  [WARN] Cannot open {path}: {e}", file=sys.stderr)
        return

    for sheet_name in xl.sheet_names:
        if not sheet_name.endswith("_발언내용"):
            continue
        meeting_id = sheet_name.split("_")[0]
        try:
            df = xl.parse(sheet_name, dtype=str, header=2)
        except Exception:
            continue

        required = {"회의번호", "발언자", "발언순번"}
        if not required.issubset(set(df.columns)):
            continue

        df = normalize_agenda(df)
        df["발언순번"] = pd.to_numeric(df["발언순번"], errors="coerce")

        committee = ""
        if "위원회" in df.columns and len(df) > 0:
            committee = str(df["위원회"].dropna().iloc[0]) if df["위원회"].notna().any() else ""

        yield meeting_id, committee, df

def get_committee_path(assembly_num: int, kind: str):
    """Return file/folder path for the given assembly and kind."""
    prefix = ASSEMBLY_MAP.get(assembly_num)
    if not prefix:
        return None
    if assembly_num in MULTI_SHEET_ASSEMBLIES:
        if kind == "hearing":
            return LOSI_BASE / f"{prefix} 상임위원회 회의록 데이터셋" / f"{prefix} 상임위원회 회의록 데이터셋.xlsx"
        else:
            return LOSI_BASE / f"{prefix} 국정감사 회의록 데이터셋.xlsx"
    else:
        if kind == "hearing":
            return LOSI_BASE / f"{prefix} 상임위원회 회의록 데이터셋"
        else:
            return LOSI_BASE / f"{prefix} 국정감사 회의록 데이터셋"

def get_committee_files(assembly_num: int, kind: str) -> list:
    """Return list of xlsx paths for 16-20대 (single-sheet per file)."""
    path = get_committee_path(assembly_num, kind)
    if path is None or not path.exists():
        print(f"  [WARN] Not found: {path}", file=sys.stderr)
        return []
    return sorted([str(path / f) for f in os.listdir(path) if f.endswith(".xlsx")])

# ── Core: extract Q-A dyads from a meeting ────────────────────────────────────
def extract_dyads_from_meeting(
    rows: pd.DataFrame,
    minister_name: str,
    meeting_id: str,
    date_str: str,
    committee: str,
    ministry: str,
    admin: str,
    dual_office: bool,
    hearing_type: str,
) -> list:
    """Extract Q-A dyads where Q = 위원/위원장 speech, A = minister speech."""
    rows = rows.sort_values("발언순번").reset_index(drop=True)

    dyads = []
    dyad_counter = 0
    i = 0
    while i < len(rows):
        row = rows.iloc[i]
        speaker = str(row["발언자"]).strip() if pd.notna(row["발언자"]) else ""

        if is_questioner(speaker):
            q_text = concat_content(row)
            q_speaker = speaker
            q_id = str(row.get("의원ID", "")) if pd.notna(row.get("의원ID", "")) else ""

            j = i + 1
            while j < len(rows):
                next_row = rows.iloc[j]
                next_speaker = str(next_row["발언자"]).strip() if pd.notna(next_row["발언자"]) else ""

                if minister_in_speaker(next_speaker, minister_name):
                    a_text = concat_content(next_row)
                    dyad_counter += 1
                    dyad_id = f"LOSI_{hearing_type[:3].upper()}_{meeting_id}_{minister_name}_{dyad_counter:04d}"
                    dyads.append({
                        "dyad_id":       dyad_id,
                        "hearing_id":    meeting_id,
                        "date":          date_str,
                        "committee":     committee,
                        "minister":      minister_name,
                        "ministry":      ministry,
                        "admin":         admin,
                        "dual_office":   dual_office,
                        "hearing_type":  hearing_type,
                        "q_speaker":     q_speaker,
                        "q_mp_id":       q_id,
                        "q_text":        q_text,
                        "q_word_count":  len(q_text.split()),
                        "r_speaker":     next_speaker,
                        "r_text":        a_text,
                        "source":        "losi",
                    })
                    i = j
                    break
                elif is_questioner(next_speaker):
                    break
                else:
                    j += 1
        i += 1

    return dyads

# ── Hearing pipeline ───────────────────────────────────────────────────────────
def _process_hearing_meeting(grp, meeting_id, committee, ministers, date_str, all_dyads):
    """Common logic for processing one hearing meeting group."""
    agenda_texts = " ".join(grp["안건"].dropna().unique())
    speakers_str = " ".join(grp["발언자"].dropna().unique())

    for _, m in ministers.iterrows():
        m_name = str(m["name"]).strip()
        if m_name not in agenda_texts and m_name not in speakers_str:
            continue

        if pd.notna(m.get("confirmation_date")):
            try:
                conf_dt = pd.to_datetime(m["confirmation_date"])
                hearing_dt = pd.to_datetime(date_str, errors="coerce")
                if hearing_dt is not pd.NaT:
                    if abs((hearing_dt - conf_dt).days) > 180:
                        continue
            except Exception:
                pass

        dyads = extract_dyads_from_meeting(
            rows=grp,
            minister_name=m_name,
            meeting_id=str(meeting_id),
            date_str=date_str,
            committee=committee,
            ministry=str(m["ministry"]),
            admin=str(m["admin"]),
            dual_office=bool(m["dual_office"]),
            hearing_type="HEARING",
        )
        if dyads:
            print(f"  {m_name} ({committee}, {date_str}): {len(dyads)} dyads")
            all_dyads.extend(dyads)

def collect_hearings(assemblies: list, panel: pd.DataFrame) -> pd.DataFrame:
    """From 상임위원회 files: find 인사청문회 rows and match to panel."""
    all_dyads = []
    ministers = panel[panel["confirmation_hearing"] == True].copy()

    for asm in assemblies:
        if asm in MULTI_SHEET_ASSEMBLIES:
            path = get_committee_path(asm, "hearing")
            if not path or not path.exists():
                print(f"  [WARN] Not found: {path}", file=sys.stderr)
                continue
            sheets_total = 0
            for meeting_id, committee, df in iter_meeting_sheets(str(path)):
                sheets_total += 1
                mask_h = df["안건"].str.contains("인사청문", na=False, regex=False)
                mask_m = df["안건"].str.contains("국무위원후보자", na=False, regex=False)
                grp = df[mask_h & mask_m]
                if len(grp) == 0:
                    continue
                date_raw = grp["회의일자"].iloc[0] if len(grp) > 0 else ""
                date_str = parse_date(date_raw) or str(date_raw)
                _process_hearing_meeting(grp, meeting_id, committee, ministers, date_str, all_dyads)
            print(f"\n=== {asm}대 청문회 ({sheets_total} sessions scanned) ===")
        else:
            files = get_committee_files(asm, "hearing")
            print(f"\n=== {asm}대 청문회 ({len(files)} files) ===")
            for fpath in files:
                df = load_xlsx(fpath)
                if df is None:
                    continue
                mask_h = df["안건"].str.contains("인사청문", na=False, regex=False)
                mask_m = df["안건"].str.contains("국무위원후보자", na=False, regex=False)
                df_h = df[mask_h & mask_m]
                if len(df_h) == 0:
                    continue
                fname = os.path.basename(fpath)
                committee = re.sub(r"제\d+대 국회 상임위원회 (.+) 회의록 데이터셋\.xlsx", r"\1", fname)
                for meeting_id, grp in df_h.groupby("회의번호"):
                    date_raw = grp["회의일자"].iloc[0] if len(grp) > 0 else ""
                    date_str = parse_date(date_raw) or str(date_raw)
                    _process_hearing_meeting(grp, meeting_id, committee, ministers, date_str, all_dyads)

    return pd.DataFrame(all_dyads)

# ── Audit pipeline ─────────────────────────────────────────────────────────────
def _check_minister_date(m, date_str: str) -> bool:
    """Return True if minister was serving on date_str (with tolerance)."""
    if not pd.notna(m.get("start_dt")) or not date_str:
        return True
    try:
        audit_dt = pd.to_datetime(date_str, errors="coerce")
        if audit_dt is pd.NaT:
            return True
        start_dt = pd.to_datetime(m["start_dt"], errors="coerce")
        end_raw   = m.get("end_dt")
        end_dt    = pd.to_datetime(end_raw, errors="coerce") if pd.notna(end_raw) else pd.Timestamp("2030-01-01")
        if audit_dt < start_dt - pd.Timedelta(days=30):
            return False
        if audit_dt > end_dt + pd.Timedelta(days=60):
            return False
    except Exception:
        pass
    return True

def collect_audits(assemblies: list, panel: pd.DataFrame) -> pd.DataFrame:
    """From 국정감사 files: find sessions where panel minister appears as speaker."""
    all_dyads = []

    for asm in assemblies:
        if asm in MULTI_SHEET_ASSEMBLIES:
            path = get_committee_path(asm, "audit")
            if not path or not path.exists():
                print(f"  [WARN] Not found: {path}", file=sys.stderr)
                continue
            sheets_total = 0
            for meeting_id, committee, df in iter_meeting_sheets(str(path)):
                sheets_total += 1
                all_speakers = " ".join(df["발언자"].dropna().unique())
                for _, m in panel.iterrows():
                    m_name = str(m["name"]).strip()
                    if m_name not in all_speakers:
                        continue
                    date_raw = df["회의일자"].iloc[0] if len(df) > 0 else ""
                    date_str = parse_date(date_raw) or str(date_raw)
                    if not _check_minister_date(m, date_str):
                        continue
                    dyads = extract_dyads_from_meeting(
                        rows=df,
                        minister_name=m_name,
                        meeting_id=meeting_id,
                        date_str=date_str,
                        committee=committee,
                        ministry=str(m["ministry"]),
                        admin=str(m["admin"]),
                        dual_office=bool(m["dual_office"]),
                        hearing_type="AUDIT",
                    )
                    if dyads:
                        print(f"  {m_name} ({committee}, {date_str}): {len(dyads)} dyads")
                        all_dyads.extend(dyads)
            print(f"\n=== {asm}대 국정감사 ({sheets_total} sessions scanned) ===")
        else:
            files = get_committee_files(asm, "audit")
            print(f"\n=== {asm}대 국정감사 ({len(files)} files) ===")
            for fpath in files:
                df = load_xlsx(fpath)
                if df is None:
                    continue
                fname = os.path.basename(fpath)
                committee = re.sub(r"제\d+대 국회 국정감사 (.+) 회의록 데이터셋\.xlsx", r"\1", fname)
                all_speakers = " ".join(df["발언자"].dropna().unique())
                for _, m in panel.iterrows():
                    m_name = str(m["name"]).strip()
                    if m_name not in all_speakers:
                        continue
                    mask = df["발언자"].str.contains(m_name, na=False, regex=False)
                    for meeting_id in df[mask]["회의번호"].unique():
                        grp = df[df["회의번호"] == meeting_id].copy()
                        date_raw = grp["회의일자"].iloc[0] if len(grp) > 0 else ""
                        date_str = parse_date(date_raw) or str(date_raw)
                        if not _check_minister_date(m, date_str):
                            continue
                        dyads = extract_dyads_from_meeting(
                            rows=grp,
                            minister_name=m_name,
                            meeting_id=str(meeting_id),
                            date_str=date_str,
                            committee=committee,
                            ministry=str(m["ministry"]),
                            admin=str(m["admin"]),
                            dual_office=bool(m["dual_office"]),
                            hearing_type="AUDIT",
                        )
                        if dyads:
                            print(f"  {m_name} ({committee}, {date_str}): {len(dyads)} dyads")
                            all_dyads.extend(dyads)

    return pd.DataFrame(all_dyads)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["hearing", "audit", "all"], default="all")
    parser.add_argument("--assemblies", nargs="+", type=int, default=[17, 18, 19, 20, 21, 22])
    args = parser.parse_args()

    panel = load_panel()
    print(f"Panel loaded: {len(panel)} ministers")

    dfs = []

    if args.type in ("hearing", "all"):
        df_h = collect_hearings(args.assemblies, panel)
        if len(df_h) > 0:
            out = OUT_DIR / "losi_hearing_dyads.csv"
            df_h.to_csv(out, index=False, encoding="utf-8-sig")
            print(f"\n[Hearing] Saved {len(df_h)} dyads -> {out}")
            dfs.append(df_h)

    if args.type in ("audit", "all"):
        df_a = collect_audits(args.assemblies, panel)
        if len(df_a) > 0:
            out = OUT_DIR / "losi_audit_dyads.csv"
            df_a.to_csv(out, index=False, encoding="utf-8-sig")
            print(f"\n[Audit] Saved {len(df_a)} dyads -> {out}")
            dfs.append(df_a)

    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        # Deduplicate: same meeting + minister + q_text + r_text
        before = len(combined)
        combined = combined.drop_duplicates(subset=["hearing_id", "minister", "admin", "ministry", "q_text", "r_text"])
        # Drop false positives: r_speaker must contain minister title
        title_mask = combined["r_speaker"].str.contains("장관|국무위원|부총리", na=False, regex=True)
        combined = combined[title_mask]
        print(f"\n[Combined] {before} raw -> {len(combined)} after dedup+title filter")

        out_all = OUT_DIR / "losi_all_dyads.csv"
        combined.to_csv(out_all, index=False, encoding="utf-8-sig")
        print(f"Saved -> {out_all}")
        print("\nBreakdown:")
        print(combined.groupby(["admin", "hearing_type", "dual_office"]).size().to_string())

if __name__ == "__main__":
    main()
