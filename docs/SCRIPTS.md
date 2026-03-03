# Scripts: Execution Order and Purpose

The scripts are organized into four stages that reflect the data construction pipeline.
Run them in the order listed below to reproduce `data/minister_panel_comprehensive.csv`
from scratch.

---

## Stage 1 -- Collect (`scripts/01_collect/`)

Fetch raw parliamentary transcripts and dyad data from the National Assembly APIs.

| Script | Purpose |
|--------|---------|
| `collect_minister_hearings.py` | Downloads minister confirmation hearing transcripts via the Pharos API (`record.assembly.go.kr`) |
| `collect_hearing_transcripts.py` | Downloads prime minister confirmation hearing transcripts (Pharos) |
| `collect_minister_audit.py` | Downloads national audit session (국정감사) transcripts for ministers (Pharos) |
| `collect_losi_dyads.py` | Parses LOSI (국회의사록정보시스템) Excel files into Q-A dyads for the 17th-21st Assemblies |

**API notes:**
- Pharos endpoint: `POST record.assembly.go.kr/assembly/mnts/search/search.do`
- 18th-19th Assembly Pharos returns empty (PDF-only era) -- those sessions are not recoverable via this API
- LOSI requires downloading xlsx files from the National Assembly; the script expects them in `data/raw/losi/`

---

## Stage 2 -- Build Panel (`scripts/02_build/`)

Construct the minister panel from the National Assembly Open API and manual sources.

| Script | Purpose |
|--------|---------|
| `build_minister_panel.py` | Fetches minister appointment records from the National Assembly Open API; auto-matches Assembly membership to detect dual-office candidates |
| `build_comprehensive_panel.py` | First version of the comprehensive panel builder (reference only) |
| `build_comprehensive_panel_v2.py` | Current version: merges API data, manual coding, and Wikipedia cross-validation into `minister_panel_comprehensive.csv` |

**Run order:** `build_minister_panel.py` → `build_comprehensive_panel_v2.py`

---

## Stage 3 -- Validate and Correct (`scripts/03_validate/`)

Sequential correction patches applied to the minister panel after manual verification.
Each script applies targeted fixes and saves an updated CSV.

| Script | What it fixes |
|--------|--------------|
| `apply_corrections_v1.py` | Wikipedia cross-validation: corrects `dual_office` status for 23 entries (20 TRUE→FALSE, 3 FALSE→TRUE) |
| `apply_corrections_v2.py` | `mp_district` and `assembly_num_at_appt` corrections for dual-office entries |
| `apply_corrections_v3.py` | FALSE NEGATIVE recovery: 3 entries missed in v1 (유일호 ×2, 신원식) |
| `apply_corrections_v4.py` | `confirmation_date` backfill from National Assembly and Namu Wiki records; resolves all NaN dates |
| `apply_corrections_v5.py` | Lee Jae-myung administration (이재명, 2025) additions and date corrections for 19 entries |
| `apply_corrections_v6.py` | Final deduplication and cleanup |

**Run in order v1 → v6.** Each script reads the output of the previous.

Helper scripts:

| Script | Purpose |
|--------|---------|
| `lookup_confirmation_dates.py` | Queries the National Assembly API for confirmation hearing dates to backfill missing values |
| `search_missing_ministers.py` | Searches for ministers not yet in the panel (name fuzzy matching against API records) |

---

## Stage 4 -- MP Metadata (`scripts/04_metadata/`)

Constructs `data/losi_mp_metadata.csv`: the party coding table that maps each LOSI questioner to ruling/opposition status.

| Script | Purpose |
|--------|---------|
| `collect_mp_metadata.py` | Fetches MP metadata (name, party, district, term) from the National Assembly Open API for each Assembly term |
| `collect_audit_mp_metadata.py` | Supplements MP metadata specifically for national audit session questioners |
| `merge_mp_metadata.py` | Merges all metadata sources, resolves party changes mid-term, and outputs `losi_mp_metadata.csv` |

**Run order:** `collect_mp_metadata.py` + `collect_audit_mp_metadata.py` → `merge_mp_metadata.py`

---

## Dependencies

```
pip install pandas requests openpyxl beautifulsoup4
```

Python 3.9+ required. Scripts use `python3` (system Python on macOS).
