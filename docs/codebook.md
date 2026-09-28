# Codebook (v2.0.0)

This codebook covers the files in `data/v2/`. Dates are `YYYY-MM-DD`. A blank end date means the person was in office on the data cutoff, 2026-09-24. Boolean columns are `True` or `False`.

## Scope and units

**Offices.** The prime minister (국무총리), including 서리 periods before the Assembly's consent, and every office whose head held 국무위원 status under the Government Organization Act (정부조직법) in force on the date. The legal inventory, with law numbers and effective dates, is in `evidence/offices/` (`offices.json` from 1998, `offices_1988.json` for 1988-1998) and summarized in `offices.csv`. Heads of offices without 국무위원 status are out of scope, for example 국가보훈처 before 2023, 기획예산위원회, 금융위원회 and 방송통신위원회. Acting heads (직무대행) are not tenures. They are listed in `acting_heads.csv`.

**Window.** Every tenure with at least one day in office between 1988-02-25 and 2026-09-24. Tenures that began earlier are included with their true start date. `panel_admin.csv` clips rows to the window.

**Units.**
- A **spell** (`spells.csv`) is one continuous period of one person in one ministry name.
- When a ministry is renamed by law during a tenure, a new spell starts on the effective date with `reorg_continuation = True`.
- An **appointment** (`appointment_id`) joins such spells into one continuous tenure in the lineage.
- A **row** of `panel_admin.csv` is a spell split at presidential inaugurations. The inauguration day belongs to the new administration.

## Identifiers

Identifiers are derived from content, so rebuilding the data does not renumber them, and a date correction does not change an id.

| Id | Construction |
|---|---|
| `person_id` | `P` + first 8 hex digits of sha1 of name, Hanja and, for namesakes only, birth year |
| `spell_id` | `person_id` + `-` + lineage + `-` + ordinal of the person's spells in that lineage, for example `Pf9642325-education-1` |
| `appointment_id` | `A` + the `spell_id` of the appointment's first spell, without the leading `P` |
| `row_id` | `spell_id` + `-g` + two-digit administration index (00 전두환 to 08 이재명) |
| `nomination_id` | `N` + first 8 hex digits of sha1 of nominee, office title and nomination date |
| `acting_id` | `H` + first 8 hex digits of sha1 of name, lineage and start date |

## Lineages

| Key | Offices (in order) |
|---|---|
| `pm` | 국무총리 |
| `epb` | 경제기획원 (to 1994-12-22) |
| `finance` | 재무부, 재정경제원, 재정경제부, 기획재정부, 재정경제부 (from 2026-01-02) |
| `budget` | 기획예산처 (1999-2008 and from 2026-01-02) |
| `unification` | 국토통일원, 통일원, 통일부 |
| `foreign` | 외무부, 외교통상부, 외교부 |
| `defense` | 국방부 |
| `justice` | 법무부 |
| `interior` | 내무부, 행정자치부, 행정안전부, 안전행정부, 행정자치부, 행정안전부 |
| `general_affairs` | 총무처 (to 1998-02-27) |
| `safety` | 국민안전처 (2014-2017) |
| `education` | 문교부, 교육부, 교육인적자원부, 교육과학기술부, 교육부 |
| `science` | 과학기술처, 과학기술부, 미래창조과학부, 과학기술정보통신부 |
| `ict` | 체신부, 정보통신부 (to 2008-02-28) |
| `culture` | 문화공보부, 문화부, 문화체육부, 문화관광부, 문화체육관광부 |
| `public_info` | 공보처 (1990-1998) |
| `sports` | 체육부, 체육청소년부 (to 1993-03-05) |
| `agriculture` | 농림수산부, 농림부, 농림수산식품부, 농림축산식품부 |
| `industry` | 상공부, 상공자원부, 통상산업부, 산업자원부, 지식경제부, 산업통상자원부, 산업통상부 |
| `energy` | 동력자원부 (to 1993-03-05) |
| `land` | 건설부, 건설교통부, 국토해양부, 국토교통부 |
| `transport` | 교통부 (to 1994-12-22) |
| `oceans` | 해양수산부 (1996-2008 and from 2013) |
| `health` | 보건사회부, 보건복지부, 보건복지가족부, 보건복지부 |
| `labor` | 노동부, 고용노동부 |
| `gender` | 정무장관(제2) to 1998-02-27, 여성부, 여성가족부, 여성부, 여성가족부, 성평등가족부 |
| `environment` | 환경처, 환경부, 기후에너지환경부 |
| `sme` | 중소벤처기업부 (from 2017) |
| `veterans` | 국가보훈부 (from 2023) |
| `special` | 정무장관(제1), 특임장관 (optional posts, vacancies are normal) |

Two offices that existed at the same time never share a lineage. When ministries merged, the lineage follows the branch whose functions continued, for example 재무부 into 재정경제원 and 상공부 into 상공자원부. The reasons are recorded in `offices_1988.json`.

## Date conventions

- **Start.** The legal appointment date (임명일). From 2001 this is the date printed in the Gazette notice. For 1988-2000, where no digital Gazette exists, it is the day the appointment certificate (임명장) was given, unless an official record gives the legal date. The announcement day is kept in `spell_disputes.csv`.
- **End.** The last day in office, meaning the day a resignation was accepted or a dismissal took effect. If a successor's term began at 00:00 on day X, the end is X-1. If sources give only the successor's appointment, the end is that date and `end_confidence = inferred_from_successor`. Same-day handovers are allowed.
- **Renaming by law.** The spell under the old name ends the day before the law takes effect. The spell under the new name starts on that day.
- **Suspension.** Impeachment suspensions do not end a spell. They are recorded in `suspended_from` and `suspended_to`.
- **Precision.** Independent re-collection agreed to the day on 92 percent of sampled dates, and every difference was one day. Allow a one-day buffer when linking by date.

## `spells.csv`

| Column | Description |
|---|---|
| `spell_id`, `appointment_id`, `person_id`, `nomination_id` | Identifiers, see above. `nomination_id` links the nomination that produced the appointment |
| `name`, `name_hanja`, `name_en` | Name in Hangul, Hanja, and romanization from an official or NA source where available |
| `mona_cd` | National Assembly member code (NAAS_CD) if the person ever held a seat in terms 12-22 or appears in the NA member register |
| `lineage` | Office lineage key |
| `ministry`, `office_title` | Ministry name in force during the spell, and the full title (e.g. 부총리 겸 기획재정부장관, 국무총리서리) |
| `deputy_pm` | The title carried 부총리 (deputy prime minister) during the spell |
| `pm_status`, `pm_acting_until` | PM only. `서리` or `정식`, and the last day of 서리 status for a 서리 later confirmed |
| `spell_start`, `spell_end` | Tenure dates (conventions above) |
| `suspended_from`, `suspended_to`, `suspensions` | Impeachment or other suspension within the spell (the last as JSON) |
| `dual_office_at_start` | Held a National Assembly seat on the first day of the spell |
| `dual_office_start`, `dual_office_end` | First and last day of the spell on which the person held a seat |
| `mp_assembly_term`, `mp_party_at_appt`, `mp_district` | Assembly term, party on the first dual-office day (re-verified per row) and district or 비례대표. The party is the name the party used on that day, including provisional names. For example, 나웅배 (1995-12-21) is coded 신한국당, the name in use from 1995-12-06, although it was formally adopted only on 1996-02-06 |
| `disputed`, `alternative_dates` | The verifier could not settle a date. Alternatives are summarized here and detailed in `spell_disputes.csv` |
| `start_confidence`, `end_confidence` | `high`, `medium`, `low` or `inferred_from_successor` |
| `verification_status` | `confirmed`, `corrected` (changed by the verifier or a later audit) or `disputed` |
| `birth_date`, `gender` | From NA records or sources where available |
| `end_reason` | `replaced`, `resigned`, `resigned_to_run` (to run in an election), `dismissed`, `ministry_reorganized`, `consent_rejected`, `in_office`, `other` |
| `appointing_president`, `appointed_by_acting_president` | Who appointed, and whether an acting president did |
| `reorg_continuation`, `reappointed_on_reorg` | The spell continues a tenure across a legal renaming, and whether a new appointment was issued then |
| `start_sources`, `end_sources` | Cited sources with access times, separated by ` ;; ` |
| `transcript_check`, `transcript_notes` | Check against National Assembly transcripts (2000 on) |
| `notes` | Free text, including corrections applied after verification |

## `panel_admin.csv`

The columns of the first release keep their names: `ministry`, `name`, `name_en`, `start`, `end`, `admin`, `admin_ideology`, `dual_office`, `mp_party_at_appt`, `mp_district`, `assembly_num_at_appt`, `confirmation_hearing`, `confirmation_date`, `notes`. Their meanings are now as follows.

| Column | Description |
|---|---|
| `start`, `end` | Row period, clipped to the administration and the window. `end` is blank if in office at the cutoff |
| `admin`, `admin_ideology` | Serving administration and its broad orientation (Conservative for 노태우, 김영삼, 이명박, 박근혜, 윤석열; Progressive for 김대중, 노무현, 문재인, 이재명) |
| `dual_office` | Held a seat on at least one day of the row. See `dual_office_start`, `dual_office_end`, `dual_office_share` and `dual_office_full_row` |
| `confirmation_hearing`, `confirmation_date` | A hearing was held for the nomination behind the appointment, and its first day. Never the appointment date |
| `holdover`, `holdover_type` | The row belongs to an administration other than the appointing one. `retained` means the new president kept the minister. `caretaker` means the minister served until a successor was named |
| `appointing_president`, `appointment_start`, `appointment_end`, `spell_start`, `spell_end` | Tenure context of the row |
| `hearing_report_adopted`, `nomination_date`, `na_consent_vote` | From the linked nomination |
| `mp_election_type`, `mp_party_at_election`, `mp_party_sources` | Seat type, party at the election, and the sources for `mp_party_at_appt` |
| `former_mp`, `mp_terms_before` | Had held a seat before the row, and how many terms |

All `spells.csv` columns with the same name have the same meaning.

## `nominations.csv`

| Column | Description |
|---|---|
| `nominee`, `office_title`, `lineage` | Who was nominated for what |
| `nomination_date`, `request_date` | Announcement of the nomination, and the date the hearing request or consent motion reached the Assembly |
| `likms_bill_id` | Bill id in the National Assembly bill system (의안정보시스템) |
| `hearing_dates`, `hearing_committee` | Hearing days, separated by `;` |
| `hearing_required` | A hearing was legally required. The PM required one from 2000-05-30, and 국무위원 from 2005-07-28 |
| `report_adopted` | `yes`, `no` or `not_applicable`. A nomination that ended before any hearing is `not_applicable` |
| `na_consent_vote` | PM only. `passed`, `rejected` or `not_applicable` |
| `outcome`, `outcome_date` | `appointed`, `withdrawn` (by the president), `nominee_withdrew` or `rejected` (by the Assembly) |
| `spell_id` | The spell that the nomination produced |

## Other tables

- **`persons.csv`.** `person_id`, `name`, `name_hanja`, `birth_date`, `mona_cd`, `na_match_method`, `na_terms`. The match method is `hanja`, `birth`, `distinct_namesake` (a namesake exists but is a different person), `no_member_with_name`, `hanja_only_no_roster_birth` or `override`. Linking requires consistent birth years, because namesakes can share Hanja.
- **`acting_heads.csv`.** `acting_id`, `person_id` (when the acting head also appears as a minister), `acting_for_lineage`, `role`, `from`, `to`, `coverage`, `sources`, `added_by`. Coverage is complete for acting prime ministers and incidental for other offices. One row, marked `transcript_observation`, has dates observed in the minutes, not appointment dates.
- **`offices.csv`.** Office periods with 국무위원 status, deputy-PM titles and legal basis.
- **`ministry_alias.csv`.** `alias_string`, `canonical_ministry`, `lineage`, `valid_from`, `valid_to`, `alias_type` (`official`, `short`, `hanja`, `title_form`, `deputy_pm_prefix`, `acting_form`, `typo`, `ambiguous_short`, `printed_anachronism`, `out_of_scope`), `person_id`, `spell_id`. Rows with a `person_id` apply only to that person on those dates.
- **`person_name_variants.csv`.** Transcript spellings of a minister's name (`hanja_variant`, `compat_ideograph`, `typo`), each scoped to a spell and dated, with the meeting ids where they occur.
- **`spell_disputes.csv`.** Competing start or end dates found in sources, with the kept value, the alternative, sources for both and the reason for the choice.
- **`lineage_family_crosswalk.csv`.** Mapping between these lineages and the ministry families used by kr-hearings-data.

## Known issues

- Birth dates are missing for some ministers without an NA record.
- Before 2001, start dates can differ by one or two days from the announcement date reported in the press. Both dates are recorded.
