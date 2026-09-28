# Korean Cabinet Minister Dataset
## 한국 국무총리·국무위원 데이터셋 (1988-2026)

[![Data: CC BY 4.0](https://img.shields.io/badge/Data-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Code: MIT](https://img.shields.io/badge/Code-MIT-blue.svg)](LICENSE)

Every South Korean prime minister and cabinet minister (국무위원) in office between the start of the current constitution (1988-02-25) and 2026-09-24. Each tenure has its appointment and exit dates with sources, the minister's nomination and confirmation-hearing record, and whether the minister was also a sitting member of the National Assembly (dual office, 국회의원 겸직), coded day by day.

**Interactive explorer:** https://kyusik-yang.github.io/minister-data/

Version 2.0.0 replaces the first release (2026-03), which had serious errors. See [CHANGELOG.md](CHANGELOG.md) for what was wrong and what changed.

---

## Coverage

| Administration | Rows | Persons | Dual-office rows | Carried over from the previous government |
|---|---:|---:|---:|---:|
| 노태우 Roh Tae-woo (1988-02-25) | 141 | 120 | 24 | 22 |
| 김영삼 Kim Young-sam (1993-02-25) | 152 | 127 | 28 | 25 |
| 김대중 Kim Dae-jung (1998-02-25) | 124 | 115 | 23 | 22 |
| 노무현 Roh Moo-hyun (2003-02-25) | 101 | 92 | 11 | 20 |
| 이명박 Lee Myung-bak (2008-02-25) | 71 | 67 | 13 | 16 |
| 박근혜 Park Geun-hye (2013-02-25) | 72 | 60 | 13 | 17 |
| 문재인 Moon Jae-in (2017-05-10) | 73 | 70 | 19 | 17 |
| 윤석열 Yoon Suk Yeol (2022-05-10) | 54 | 54 | 9 | 16 |
| 이재명 Lee Jae-myung (2025-06-04) | 46 | 39 | 11 | 14 |
| **Total** | **834** | **565** | **151** | |

A row is one continuous tenure within one administration. The same data at the tenure level has 687 spells. There are also 686 nominations, including 35 that were withdrawn or rejected.

**Offices in scope.** The prime minister (including acting-before-consent 서리 periods) and every office whose head held 국무위원 status under the Government Organization Act, 30 office lineages in all. A lineage follows one office through its renamings, for example 재무부, 재정경제원, 재정경제부, 기획재정부 and 재정경제부 again. The legal basis for every office period is in `evidence/offices/`.

---

## Files (`data/v2/`)

| File | Rows | One row per | Use it for |
|---|---:|---|---|
| `spells.csv` | 687 | continuous tenure in one ministry name | the main tenure table |
| `panel_admin.csv` | 834 | tenure x administration | analysis by government. Keeps the column names of the first release |
| `nominations.csv` | 686 | nomination (appointed, withdrawn or rejected) | confirmation hearings, report adoption, failed nominations |
| `persons.csv` | 565 | person | person ids, Hanja names, National Assembly member codes |
| `acting_heads.csv` | 130 | acting head (직무대행) | acting prime ministers (complete) and acting ministers (partial) |
| `offices.csv` | 118 | office period | legal office periods and deputy-PM titles |
| `ministry_alias.csv` | 778 | spelling of an office title | normalizing titles found in transcripts and news |
| `person_name_variants.csv` | 23 | transcript variant of a name | linking transcripts with Hanja variants or typos |
| `spell_disputes.csv` | 925 | competing date | alternative start and end dates found in sources |
| `MANIFEST.json` | | | version, build time, row counts, sha256 of every file |

The column definitions and coding rules are in [docs/codebook.md](docs/codebook.md).

The first release's `data/minister_panel_comprehensive.csv` is still in place because downstream projects read it. It is deprecated and should not be used for new work.

---

## Quick start

```python
import pandas as pd

spells = pd.read_csv("data/v2/spells.csv")

# Share of new appointments that went to sitting National Assembly members, by appointing president
new = spells[~spells["reorg_continuation"].fillna(False).astype(bool)]
order = ["노태우", "김영삼", "김대중", "노무현", "이명박", "박근혜", "문재인", "윤석열", "이재명"]
print(new.groupby("appointing_president")["dual_office_at_start"].mean().reindex(order).round(3))
```

Output with v2.0.0:

```
노태우    0.202
김영삼    0.220
김대중    0.220
노무현    0.139
이명박    0.212
박근혜    0.239
문재인    0.333
윤석열    0.135
이재명    0.385
```

Who held an office on a given date:

```python
d = "2019-10-21"
on = spells[(spells.spell_start <= d) & (spells.spell_end.fillna("9999-12-31") >= d) & (spells.lineage == "sme")]
print(on[["name", "ministry", "spell_start", "spell_end", "dual_office_at_start"]])
#  name  ministry        spell_start  spell_end   dual_office_at_start
#  박영선  중소벤처기업부   2019-04-08   2021-01-20  True
```

**Dual office varies within a tenure.** A minister's seat can end in the middle of a tenure, for example at the end of an Assembly term or on resignation from the Assembly. For any analysis at the level of a date, such as linking parliamentary speeches, use `dual_office_start` and `dual_office_end`, not the row-level flag.

**Linking to transcripts.** [kr-hearings-data](https://github.com/kyusik-yang/kr-hearings-data) links National Assembly speeches to this dataset. The recommended rule is person name (or Hanja, or an entry in `person_name_variants.csv`) plus the speech date inside `[spell_start, spell_end]`, with the ministry resolved through `ministry_alias.csv`. Speeches by acting prime ministers link to `acting_heads.csv`.

### Linked datasets

| Dataset | Version used | Role |
|---|---|---|
| [kna](https://github.com/kyusik-yang/kna) | 0.7.1 | National Assembly member lists (terms 17-22) and resignation motions used for dual-office coding |
| [kr-hearings-data](https://github.com/kyusik-yang/kr-hearings-data) | v10 build | Parliamentary speeches linked to this dataset. Its full-build check (2026-09-28) linked all but 66 of 1.15 million minister turns, and those 66 are label errors in the minutes |

The versions and check results are recorded in `data/v2/MANIFEST.json` under `linked_datasets`. When kna publishes a new release, run `python3 pipeline/build/check_linked_datasets.py`. It compares the local kna version with the recorded one and lists the steps to rebuild the National Assembly member table and the panel.

---

## How the data were built and checked

**Sources, in order of authority**
1. The Official Gazette (관보). Appointment notices from 2001 onward were read in full text, and 2,709 personnel items were harvested.
2. National Assembly records: bill records of confirmation-hearing requests and prime-minister consent motions (의안정보시스템), and member histories from the Open Assembly API.
3. Official pages: ministries' lists of past ministers, the Presidential Archives (대통령기록관) and 정책브리핑.
4. News on the day of the appointment or exit, from BigKinds, Naver News and, before 1990, the Naver News Library.

Wikipedia and Namu Wiki were used only to find candidates, never as the sole source for a date. Every start and end date has at least two independent sources, at least one of them outside the wikis. The sources are cited with access times in `spells.csv` and in the roster files under `evidence/roster/`.

**Verification.** Each office lineage was compiled by one agent and then re-checked by a second agent working from different sources, whose instructions were to look for errors and omissions. Of 687 spells, 566 were confirmed, 75 corrected and 46 remain disputed. A disputed spell keeps the better-supported date and lists the alternative in `spell_disputes.csv`. Party membership on the appointment date was re-verified for all 151 dual-office rows. The panel was also checked against every minister's appearances in the National Assembly transcripts from 2000 to 2026. Apart from label errors in the minutes, every appearance falls inside a tenure of the same person.

**Blind audit.** A stratified random sample was re-collected from scratch by auditors who saw only names and years, and each disagreement was then adjudicated with sources.

| Period | Sample | Fields compared | Exact agreement | Errors found in the data |
|---|---|---:|---:|---|
| 1998-2026 | 72 tenures (dates) | 144 | 133 | 3, all one day, corrected |
| 1998-2026 | 24 nominations | 120 | 118 | 2, corrected |
| 1998-2026 | 24 dual-office rows | 96 | 95 | 0 |
| 1988-1997 | 24 tenures (dates) | 48 | 44 | 1, corrected |

No date in either sample was off by more than one day. The remaining one-day differences are convention questions, described in the codebook, not errors. The samples, the auditors' answers and the adjudications are in `evidence/blind_audit/`.

**Use of AI.** The collection, verification and audit were carried out by large-language-model agents (Anthropic's Claude) working under the source rules above, directed and checked by the author. Every value in the data can be traced to a cited source.

**Known limits**
- Acting heads are complete for the prime minister and partial for other ministries.
- There are no digital Gazette files before 2001. For 1988-2000, start dates are the day the appointment certificate (임명장) was given, unless an official record gives the legal appointment date. The announcement day is kept as an alternative.
- Party labels are the party on the appointment date, including renamings and mergers.
- The data stop at 2026-09-24.

---

## Reproducing the dataset

The collection and build scripts are in [pipeline/](pipeline/README.md). The raw source snapshots (web pages, Gazette PDFs, news articles, about 2 GB) are archived by the author and are available on request. The verified rosters and review tables that the build reads are in `evidence/`.

---

## Citation

```bibtex
@misc{yang2026ministerdata,
  author       = {Yang, Kyusik},
  title        = {Korean Cabinet Minister Dataset, 1988-2026},
  year         = {2026},
  version      = {2.0.0},
  publisher    = {GitHub},
  url          = {https://github.com/kyusik-yang/minister-data}
}
```

## License

Data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Code: [MIT](LICENSE).

## Contact

Kyusik Yang, NYU Department of Politics (kyusik.yang@nyu.edu). Please report errors through [issues](https://github.com/kyusik-yang/minister-data/issues).
