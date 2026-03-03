# Korean Cabinet Minister Dataset
## 한국 국무위원 겸직 데이터셋

A comprehensive panel of South Korean cabinet ministers (2000-2025) with dual-office coding -- recording whether each minister simultaneously held a seat in the National Assembly (국회의원-국무위원 겸직 여부).

---

## Dataset Overview

| Item | Description |
|------|-------------|
| Coverage | 2000-2025 (Kim Dae-jung through Lee Jae-myung administrations) |
| Administrations | 7 (김대중, 노무현, 이명박, 박근혜, 문재인, 윤석열, 이재명) |
| Observations | 287 ministers |
| Key variable | `dual_office`: True if minister held a National Assembly seat simultaneously |
| Dual-office ministers | 63 (approximately 22%) |
| Unit | Minister-appointment (one row per ministerial appointment) |

**Why this matters:** South Korea is one of the very few presidential democracies that constitutionally permits sitting legislators to simultaneously serve as cabinet ministers. This dataset enables systematic study of how this executive-legislative personnel overlap affects parliamentary oversight, legislative behavior, and accountability.

---

## Files

### `data/minister_panel_comprehensive.csv`

The main dataset. 287 rows, one per ministerial appointment.

**Key variables:**

| Variable | Type | Description |
|----------|------|-------------|
| `ministry` | String | Ministry name (in Korean) |
| `name` | String | Minister name (Korean) |
| `name_en` | String | Minister name (romanized) |
| `start` | Date (YYYY-MM-DD) | Appointment start date |
| `end` | Date (YYYY-MM-DD) | Appointment end date |
| `admin` | String | Administration (e.g., 노무현, 이명박) |
| `admin_ideology` | String | Administration ideology (Progressive / Conservative) |
| `dual_office` | Boolean | True = simultaneous National Assembly member |
| `mp_party_at_appt` | String | Minister's party at time of appointment (if dual) |
| `mp_district` | String | Minister's electoral district (if dual) |
| `assembly_num_at_appt` | Float | National Assembly term number (if dual) |
| `confirmation_hearing` | Boolean | True = had a confirmation hearing (인사청문회) |
| `confirmation_date` | Date | Date of confirmation hearing |
| `notes` | String | Data sourcing notes, corrections applied |

See `docs/codebook.md` for full variable documentation.

### `data/losi_mp_metadata.csv`

Party coding metadata for National Assembly members, derived from the Legislative Oversight Session Index (LOSI, 국회의사록정보시스템). 1,931 MP-session pairs, covering the 17th-21st National Assemblies (2004-2024). Used to determine questioner ruling/opposition status in Q-A dyad analysis.

### `data/hearing_panel.csv`

Schedule of confirmation hearings associated with appointments in the minister panel.

---

## Scripts

### `scripts/build_*/` -- Panel Construction

- `build_minister_panel.py` -- Collects minister appointment records via the National Assembly Open API
- `build_comprehensive_panel.py`, `build_comprehensive_panel_v2.py` -- Merges API data with manual coding

### `scripts/apply_corrections_v1.py` through `v6.py` -- Manual Corrections

Sequential correction scripts applying targeted fixes identified through Wikipedia cross-validation and manual verification:
- v1: Wikipedia cross-validation (dual_office status correction for 23 entries)
- v2: District and assembly number corrections
- v3: FALSE NEGATIVE recovery (3 entries: Yoo Il-ho x2, Shin Won-sik)
- v4: Confirmation date backfill (from National Assembly records)
- v5: Lee Jae-myung administration (2025) additions
- v6: Final deduplication and cleanup

### `scripts/collect_*/` -- Data Collection

Collection scripts for parliamentary transcripts:
- `collect_hearing_transcripts.py` -- Confirmation hearing transcripts (Pharos API)
- `collect_minister_hearings.py` -- Minister confirmation hearings
- `collect_minister_audit.py` -- National audit session transcripts
- `collect_losi_dyads.py` -- LOSI Q-A dyad extraction
- `collect_mp_metadata.py`, `collect_audit_mp_metadata.py` -- MP metadata collection

---

## Data Sources

- **National Assembly Open API** (data.assembly.go.kr): Minister appointment records, MP metadata
- **Pharos** (record.assembly.go.kr): Full-text parliamentary transcripts
- **LOSI** (국회의사록정보시스템): Q-A dyad data for 17th-21st Assemblies
- **Wikipedia / Namu Wiki**: Cross-validation of dual-office coding
- **Korean Official Gazette (관보)**: Appointment dates, ministry assignments

---

## Related Paper

This dataset was constructed for:

> Yang, Kyusik. "Dual Office, Divided Loyalty? Executive-Legislative Personnel Overlap and Parliamentary Oversight in South Korea." Under review at *Comparative Political Studies*.

If you use this dataset, please cite the paper (citation to be updated upon publication).

---

## Data Gaps and Known Limitations

- **Kim Dae-jung era (2000-2003)**: Only 2 ministers currently included. Full collection of this period is ongoing.
- **LOSI coverage**: The 22nd Assembly (2024-present) is not yet fully archived in LOSI.
- **Prime ministers**: The dataset includes prime ministers (국무총리) who held simultaneous legislative seats. Note that prime minister confirmation hearings were not collected in the LOSI-based Q-A dyad analysis.
- **Interim ministers (직무대행)**: Not included.

---

## License

Data: CC BY 4.0 (attribution required)
Code: MIT License

---

## Contact

Kyusik Yang
PhD Candidate, Department of Politics, New York University
kyusik.yang@nyu.edu
