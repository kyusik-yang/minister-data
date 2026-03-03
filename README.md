# Korean Cabinet Minister Dataset
## 한국 국무위원 겸직 데이터셋

A panel dataset of South Korean cabinet ministers (2000-2025) with hand-coded dual-office status -- recording whether each minister simultaneously held a seat in the National Assembly (국회의원-국무위원 겸직).

---

## At a Glance

| | |
|--|--|
| **Coverage** | 2000-2025 (Kim Dae-jung through Lee Jae-myung) |
| **Administrations** | 7 (김대중, 노무현, 이명박, 박근혜, 문재인, 윤석열, 이재명) |
| **Ministers** | 287 appointments |
| **Dual-office rate** | 63 / 287 (~22%) |
| **Unit** | One row per ministerial appointment |

**What is dual-office?** South Korea's constitution uniquely permits sitting National Assembly members to simultaneously serve as cabinet ministers, retaining both their legislative seat and executive appointment. No other established presidential democracy has an equivalent provision. This dataset enables study of how this executive-legislative personnel overlap shapes parliamentary oversight.

---

## Files

```
minister-data/
├── data/
│   ├── minister_panel_comprehensive.csv   # Main dataset (287 ministers)
│   └── losi_mp_metadata.csv              # MP party coding (1,931 pairs, 17th-21st Assembly)
├── docs/
│   ├── codebook.md                        # Variable definitions and coding rules
│   └── SCRIPTS.md                         # Pipeline: how to reproduce the dataset
└── scripts/
    ├── 01_collect/                         # Raw transcript and dyad collection
    ├── 02_build/                           # Panel construction
    ├── 03_validate/                        # Correction patches (v1-v6)
    └── 04_metadata/                        # MP party metadata
```

---

## Main Dataset: `minister_panel_comprehensive.csv`

**Key variables:**

| Variable | Type | Description |
|----------|------|-------------|
| `ministry` | String | Ministry name (Korean) |
| `name` | String | Minister's name (Korean) |
| `name_en` | String | Minister's name (romanized) |
| `start` | Date | Appointment start (YYYY-MM-DD) |
| `end` | Date | Appointment end (YYYY-MM-DD) |
| `admin` | String | Administration (e.g., 노무현, 이명박) |
| `admin_ideology` | String | Progressive / Conservative |
| `dual_office` | Boolean | **True** = simultaneous National Assembly member |
| `mp_party_at_appt` | String | Minister's party at appointment (if dual) |
| `mp_district` | String | Electoral district or 비례대표 (if dual) |
| `assembly_num_at_appt` | Float | National Assembly term number (if dual) |
| `confirmation_hearing` | Boolean | Had a confirmation hearing (인사청문회)? |
| `confirmation_date` | Date | Date of confirmation hearing |
| `notes` | String | Source notes and corrections |

See `docs/codebook.md` for full documentation and coding rules.

**Administration breakdown:**

| Administration | N | Dual-office |
|---------------|---|-------------|
| 김대중 | 2 | 1 |
| 노무현 | 80 | 9 |
| 이명박 | 52 | 10 |
| 박근혜 | 46 | 11 |
| 문재인 | 54 | 18 |
| 윤석열 | 30 | 5 |
| 이재명 | 22 | 9 |
| 한덕수 (caretaker) | 1 | 0 |
| **Total** | **287** | **63** |

---

## Supplementary: `losi_mp_metadata.csv`

Party coding for National Assembly members appearing as questioners in parliamentary transcripts. Covers the 17th-21st Assemblies (2004-2024). Used to code questioner ruling/opposition status in Q-A dyad analysis.

Variables: `q_speaker`, `assembly`, `q_party`, `q_sex`, `q_elect_type`, `q_birth`, `q_term_count`, `q_mona_cd`

---

## Reproducing the Dataset

See `docs/SCRIPTS.md` for the full pipeline. In brief:

```
01_collect/   →   02_build/   →   03_validate/ (v1→v6)   →   04_metadata/
```

Dependencies: `pip install pandas requests openpyxl beautifulsoup4`

---

## Related Paper

This dataset was constructed for:

> Yang, Kyusik. "Dual Office, Divided Loyalty? Executive-Legislative Personnel Overlap and Parliamentary Oversight in South Korea." Under review, *Comparative Political Studies*.

If you use this dataset, please cite the paper (citation will be updated upon publication).

---

## Known Gaps

- **Kim Dae-jung era (2000-2003):** Only 2 entries currently. Full collection is ongoing.
- **22nd Assembly (2024-present):** Not yet fully archived in LOSI.
- **Interim ministers (직무대행):** Not included.
- **Prime ministers:** Included in the panel; PM confirmation hearings were collected separately and are not part of the LOSI Q-A dyad dataset.

---

## License

Data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
Code: MIT

## Contact

Kyusik Yang -- kyusik.yang@nyu.edu -- PhD Candidate, NYU Department of Politics
