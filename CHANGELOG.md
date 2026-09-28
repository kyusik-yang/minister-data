# Changelog

## Metadata update after v2.0.0 (2026-09-28)

- The kr-hearings-data entry of `linked_datasets` in `data/v2/MANIFEST.json` and the linked-datasets table of the README now report the link check on the released kr-hearings-data v10. The data files and their checksums are unchanged.

## v2.0.0 (2026-09-28)

The dataset was rebuilt from primary sources. The first release is kept for reference only (see below).

### What changed
- **Coverage.** The data now run from 1988-02-25 to 2026-09-24, from the start of the current constitution to the cutoff, and cover every office with 국무위원 status plus the prime minister. The first release covered 2000-2025 and had only 2 rows for the 김대중 government. The new release has 834 rows (687 tenures, 565 persons), against 296.
- **Sources and verification.** Every date is backed by at least two independent sources, with the Official Gazette as the first authority from 2001. Each lineage was independently re-verified, and a blind random audit was run (see the README).
- **Dual office.** Dual office is now coded day by day from the National Assembly's member histories, with the party on the appointment date re-verified for every dual-office row.
- **Nominations.** A nominations table was added, covering 686 nominations with hearing dates, report adoption and outcome, including 35 withdrawn or rejected nominations.
- **New tables.** Acting heads, the legal office inventory, title aliases, name variants and competing dates were added.
- **Identifiers.** Stable, content-derived identifiers were added.
- **Files.** New files are in `data/v2/`. `panel_admin.csv` keeps the column names of the first release.

### Errors found in the first release (v1, 296 rows)
Of the 292 v1 rows that match a row in the rebuilt panel:
- 166 had a wrong start date. In 69 of them the error was a month or more, and in 30 it was six months or more.
- 192 had a wrong end date. In 103 the error was a month or more. The v1 builder had filled 77 end dates with presidential transition dates.
- 205 had a wrong `confirmation_date`. 172 of all v1 hearing dates were copies of the appointment date, not hearing dates.
- 3 had a wrong `dual_office` value. 김화중, 박홍수 and 이달곤 held seats when appointed but were coded as non-members.
- 5 had a ministry name that was not in force on the date.

The other 4 rows were not ministers. 정호영, 김행, 강선우 and 이진숙 were nominees whose nominations were withdrawn.

The v1 documentation also had problems:
- The README printed analysis results and transcript quotes that no file in the repository produces. The five quoted questions do not occur in the transcripts.
- The documented scripts could not regenerate the released file.
- A National Assembly API key was hard-coded in a script. It has been removed from the working copy, but it remains in the git history.

The row-by-row comparison is produced by `pipeline/build/diff_old_new.py`.

### Retired files
The following files moved to `legacy/` with an explanation in `legacy/README.md`:
- `data/losi_mp_metadata.csv`
- `data/sample_dyads.csv`
- the v1 scripts
- `docs/SCRIPTS.md`
- the v1 figure and screenshot

For transcripts and question-answer data, use [kr-hearings-data](https://github.com/kyusik-yang/kr-hearings-data).

`data/minister_panel_comprehensive.csv` (v1) remains in place for downstream projects that still read it. It is deprecated.

## v1 (2026-03)

The first release. It had 296 appointments from 2000 to 2025, with hand and script coding of dual office.
