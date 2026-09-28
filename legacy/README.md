# Legacy files (retired 2026-09-26)

These files belong to the first release of this repository (commit `afdae91`, 2026-03). They are kept for transparency and are no longer maintained. An audit of that release found the problems summarized below. The rebuilt dataset replaces them.

## `data/losi_mp_metadata.csv`
Party and member attributes for legislators who ask questions in National Assembly transcripts.
- The columns `q_sex`, `q_birth` and `q_mona_cd` are empty in all 1,931 rows, because the builder read field names from a different API endpoint.
- 180 rows (9.3%) are keyed to an Assembly the person never served in, because the builder mapped calendar year to Assembly term.
- `q_term_count` is lifetime seniority as of the API query, not seniority in that Assembly.
- Party labels are election-ticket snapshots, not party membership at the time of the speech.
- Several keys conflate namesakes.

For legislator attributes linked to transcripts, use [kr-hearings-data](https://github.com/kyusik-yang/kr-hearings-data), which codes party membership by date.

## `data/sample_dyads.csv`
Ten question-answer pairs from the National Assembly Library transcript service (losi-open.nanet.go.kr). The rows are real. The question texts shown in the old README table were not taken from these rows and should be disregarded. Dyad data are maintained in kr-hearings-data.

## `scripts/`
The first build pipeline (`01_collect` to `04_metadata`). It cannot regenerate the first release.
- Paths resolve to a folder that no longer exists.
- A base input file was never committed.
- Several rows were edited by hand without a script.
- The builder passed the appointment date as the hearing date, so 172 `confirmation_date` values were copies of `start`.
- Presidential transition dates were used as end dates for 77 rows.

A National Assembly Open API key was hard-coded in `01_collect/collect_hearing_transcripts.py`. It has been removed from this copy, and the script now reads `ASSEMBLY_API_KEY` from the environment. The key remains in the git history and should be treated as revoked.

## `docs/SCRIPTS.md`, `docs/preview-interactive-page.png`
Documentation and a screenshot of the first pipeline and explorer.
