# National Assembly member reference table, terms 15-22

Built 2026-09-25 (UTC) for dual-office coding in the minister-data rebuild. Data cutoff is 2026-09-24.
Everything here lives in `_rebuild/na_members/` and is not committed to git.

## Files

| File | Content |
|------|---------|
| `na_members_15_22.csv` | Main table. One row per member x term (2,595 rows, 1,501 distinct `mona_cd`). |
| `na_member_spells_15_22.csv` | One row per seat spell (2,600 rows). Five members held two separate spells in one term. |
| `manual_checks.csv` | 23 hand-verified corrections with the evidence (URL, access time, quoted text). Applied by the build script. |
| `validation/` | Validation tables written by the build script (listed below). |
| `sources/` | Raw snapshots of every page and API response used (about 12 MB). |
| `scripts/` | Fetch, parse and build scripts. |
| `work/` | Parsed Wikipedia intermediates. `work/obsolete/` holds outputs of an early run that the current build no longer writes. |

## Columns of `na_members_15_22.csv`

Required columns first.

| Column | Definition |
|--------|------------|
| `term` | Assembly term (15-22). |
| `name` | Korean name as recorded by the National Assembly (NA). |
| `name_hanja` | Name in hanja (NA `ALLNAMEMBER`). Three rows are blank in the NA record. |
| `birth_date` | Birth date as recorded by the NA. See the note on lunar dates under Known gaps. |
| `gender` | `남` or `여` as recorded by the NA. |
| `party_at_election` | Party under which the member won the seat (Wikipedia list column 당선시 정당, with the year suffix of the Wikipedia party key removed). For PR successors this is the party at succession, which can differ from the list party (see `pr_list_party`). |
| `district` | NA district name for the first spell of the term, province names shortened (서울특별시 becomes 서울). PR seats read `비례대표`, or `전국구` in term 15. |
| `election_type` | `지역구` or `비례대표` (term 15 전국구 is coded `비례대표`). First spell of the term. |
| `seat_start` | First day in the seat in this term. |
| `seat_end` | Last day in the seat in this term (last spell). Blank for members sitting on 2026-09-24. |
| `exit_reason` | `term_end`, `resigned`, `died`, `disqualified`, `elected_other_office`, or blank (sitting, or reason not established). |
| `entered_via` | `general`, `by_election` or `succession_pr` (first spell). |
| `mona_cd` | NA member code (NAAS_CD / MONA_CD). Known for every row. |
| `source` | Sources that contributed to the row. |

Extra columns.

| Column | Definition |
|--------|------------|
| `n_spells`, `spells` | Number of seat spells in the term, and a text list of all spells when there are two. |
| `exit_detail` | Finer exit code. Values are `term_end`, `resigned_to_run_for_other_office`, `resigned_on_appointment`, `resigned_other`, `died`, `court_ruling_election_law`, `court_ruling_other_or_unspecified`, `election_voided_by_court`, `pr_seat_lost_on_leaving_party`, `took_office_as_elected_local_head`, `elected_president`, `unknown`. |
| `exit_reason_text` | Raw reason wording from the Wikipedia seat-change table and list notes. |
| `start_status`, `end_status` | How well the boundary is corroborated (definitions below). |
| `start_check`, `end_check` | The competing dates behind the status. |
| `district_wiki` | Region and district as written in the Wikipedia list. |
| `pr_list_party`, `pr_list_rank` | PR list (Wikipedia section) and list rank. |
| `party_at_seat_end_wiki` | Party at the end of the seat or today (Wikipedia 종료시 정당 or 현재 정당). |
| `party_api_profile` | Party written in the NA 의원이력 record for the spell. |
| `wiki_article` | Wikipedia article title of the member, useful to separate namesakes. |
| `in_kna_build` | Terms 17-22 only. Whether the member is in the kna `members_{term}.parquet` build. |
| `notes` | Corrections applied and API anomalies. |
| `same_name_other_person` | True when another person with the same name appears anywhere in terms 15-22 (37 names, 135 rows). |

`na_member_spells_15_22.csv` carries the same fields per spell plus the raw API period (`api_frto`, `api_profile`), the Wikipedia dates (`wiki_start`, `wiki_end`, `wikiseat_start`, `wikiseat_end`), the NA bill record of the resignation motion (`nabill_resign_date`, `nabill_id`), and the Wikipedia revision ids.

## How the table was built

1. The NA open API table 의원이력 gives one record per member per term spell, with the activity period (`FRTO_DATE`). Former members come from endpoint `nfzegpkvaclgtscxt` and sitting members from `nexgtxtmaamffofof`. These periods are the seat dates. In the cases checked, the NA date is the day the change took legal effect. For 임태희 (term 18) the resignation motion was filed on 2010-07-16 and approved on 2010-10-01, and the NA end date is 2010-10-01. For the 2014 local-election candidates the NA end date is 2014-05-15, which the Wikipedia seat table describes as 후보자로 등록에 따른 퇴직.
2. Person attributes (name, hanja, birth date, gender) come from `ALLNAMEMBER`. Birth dates agree exactly with the per-term 인적사항 table (`npffdutiapkzbfyvr`) for all 2,296 member-terms that table covers. Hanja, birth dates and gender also agree with the kna build for every member of terms 17-22.
3. For terms 17-22 the kna files `members_17..22.parquet` were read as the base list (read only). Since 2026-09-27 the build reads kna 0.7.1 (GitHub tag v0.7.1, released 2026-09-27, which fixed 5 member rows reported from this build). Its member sets match the NA API exactly for terms 17-22, including the 15 members who entered the 22nd Assembly in 2026 (14 winners of the 2026-06-03 by-elections and 김형연), so `in_kna_build` is True for every row of terms 17-22. The earlier build read kna 0.6.0 (March 2026), which lacked those 15 members.
4. The Korean Wikipedia pages 대한민국 제N대 국회의원 목록 (N = 15..22) were parsed with a rowspan-aware table parser. They supply party at election, PR list and rank, and dated notes (의원직 사퇴, 의원직 상실, 의원직 승계, 재보궐선거 당선, 사망). The seat-change tables (의석 변동) of the pages 대한민국 제N대 국회 supply a second, differently worded record of each seat change with a reason.
5. The API spells and Wikipedia rows were matched within term by name, then by seat type, district similarity and start date. All 2,600 API spells and all 2,600 Wikipedia rows matched one to one. The row counts per term are identical in the two sources.
6. The NA bill records of 국회의원(○○○) 사직의 건 (terms 17-22, copied from the kna bill masters) give plenary approval dates for resignations. Only motions with the result 원안가결 are used. With kna 0.7.0 the extract (`sources/na_bills/resignation_motions_17_22.csv`, which records `kna_version`) holds 86 motions, 52 of them approved, against 77 and 43 with kna 0.6.0. The 9 additions are the 22nd-Assembly resignations approved on 2026-04-29 by members running in the 2026-06-03 local elections.
7. Every boundary that is not a regular term start or term end was compared across the sources and given a status. Conflicts that mattered were checked against news reports. The accepted corrections are in `manual_checks.csv`.

### Boundary status values

| Status | Meaning |
|--------|---------|
| `term_start`, `term_end`, `sitting` | Regular term boundary, or still in office at the cutoff. |
| `confirmed` | The NA date matches at least one independent source (Wikipedia list, Wikipedia seat table, or NA bill record). |
| `confirmed_pollday_plus1` | By-election entrant whose NA start is the day after polling (the NA records the moment the winner is determined). Wikipedia gives the polling day. |
| `api_later_than_wiki` | Every other source is 1-70 days earlier than the NA date. The NA date was kept. The checks below show that Wikipedia often records the announcement, submission, nomination or predecessor-exit date. |
| `api_earlier_than_wiki` | Every other source is 1-70 days later than the NA date. The NA date was kept. |
| `conflict` | Other sources disagree in both directions or by more than 70 days. The NA date was kept. |
| `single_source` | Only the NA reports the boundary. |
| `verified_manual` | Set from `manual_checks.csv` after a news check. |

Counts over all 2,600 spells. Starts are 2,370 term starts, 167 confirmed, 19 confirmed_pollday_plus1, 38 api_later_than_wiki, 2 api_earlier_than_wiki and 4 conflict. Ends are 2,023 term ends, 299 sitting, 225 confirmed, 8 verified_manual, 31 api_later_than_wiki, 6 api_earlier_than_wiki, 2 conflict and 6 single_source.

Why the NA date wins in `api_later_than_wiki` cases. News checks show the Wikipedia date to be an earlier step in each of these examples.

- 정상천 (term 15) handed in his resignation on 1999-03-30 during a session, and the Hankook Ilbo of 1999-03-31 reports that it would go to a plenary vote in early April. The NA end date is 1999-04-02.
- The five PR members who left 새천년민주당 for 열린우리당 announced it on 2003-10-26 and left the party "27일자로" (Hankook Ilbo 2003-10-27). The NA end date is 2003-10-27.
- 강은희 (term 19) was named minister on 2015-12-21, the date on the Wikipedia list (edaily 2015-12-21). Her NA end date is 2016-01-18.
- After 김한길's resignation in 2000, the NEC named his successor on 2000-10-12 (Hankook Ilbo 2000-10-13), weeks after the 2000-09-20 date on Wikipedia.
- 이찬진's succession took place in December 1997 according to the Hankook Ilbo of 1998-05-06, which matches the NA start of 1997-12-20 and not the Wikipedia date of 1997-11-26.

### Corrections applied (`manual_checks.csv`)

| Term | Member | Field | NA API value | Value used | Evidence |
|------|--------|-------|--------------|------------|----------|
| 15 | 서상목 | seat_end | 2000-05-29 (full term) | 1999-09-06, resigned | Hankook Ilbo 1999-09-07, Wikipedia list and seat table |
| 15 | 한광옥 | seat_end | 2000-05-29 (full term) | 1999-11-24, resigned on appointment as presidential chief of staff | Wikipedia list gives the day. News confirms the November 1999 appointment only to the month. Weak. |
| 15 | 이회창 (PR spell) | seat_end | 1997-12-29 | 1997-11-26 | The NA end is impossible because the NA seats his successor from 1997-12-20, which puts 300 members in a 299-seat house. Wikipedia gives 11-26, the registration day announced in advance (Hankook Ilbo 1997-11-15). Weak. The true date lies between 11-26 and 12-20. |
| 15 | 김용갑 | district | 경남 마산시 회원군 | 경남 밀양시 | 헌정회 record (NA API `nprlapfmaufmqytet`) and Wikipedia |
| 16 | 김학원 | district | 충남 당진군 (same as 송영진) | 충남 부여군 | 헌정회 record and Wikipedia |
| 16 | 이미경, 허운나, 이재정, 박양수, 오영식 | exit_detail | 의원직 상실, no reason | pr_seat_lost_on_leaving_party, end 2003-10-27 confirmed | Hankook Ilbo 2003-10-27 |
| 19 | 안종범 | exit_reason | disqualified (from 의원직 상실) | resigned on appointment | Wikipedia seat table reason text |
| 22 | 임광현 | exit_reason | none | resigned on appointment as NTS commissioner | News1 2025-07-23 (also on fnnews) |

Two automatic fixes are in `notes`. 김홍일 (term 15) has an NA end of 2000-05-30, one day after the term, which is set to the term end. 백선희 (term 22) has an NA end of 2028-05-29, the future term end, which is treated as sitting.

## Row counts and validation

| Term | Seats | Member rows | Spells | General | By-election | PR succession | Wikipedia by-election events | Wikipedia succession events | Term end | Resigned | Died | Disqualified | Elected other office | Exit unknown | Sitting at cutoff |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 | 299 | 334 | 335 | 299 | 21 | 15 | 21 | 15 | 296 | 14 | 8 | 17 | 0 | 0 | |
| 16 | 273 | 313 | 315 | 273 | 20 | 22 | 20 | 22 | 268 | 9 | 4 | 28 | 3 | 3 | |
| 17 | 299 | 322 | 324 | 299 | 19 | 6 | 19 | 6 | 291 | 8 | 1 | 22 | 0 | 2 | |
| 18 | 299 | 331 | 331 | 299 | 21 | 11 | 21 | 11 | 291 | 14 | 2 | 24 | 0 | 0 | |
| 19 | 300 | 332 | 332 | 300 | 24 | 8 | 24 | 8 | 291 | 17 | 1 | 23 | 0 | 0 | |
| 20 | 300 | 320 | 320 | 300 | 15 | 5 | 15 | 5 | 290 | 10 | 1 | 19 | 0 | 0 | |
| 21 | 300 | 322 | 322 | 300 | 13 | 9 | 13 | 9 | 296 | 16 | 0 | 10 | 0 | 0 | |
| 22 | 300 | 321 | 321 | 300 | 14 | 7 | 14 | 7 | 0 | 16 | 0 | 5 | 1 | 0 | 299 |

Exit counts are per spell. Seat counts are the 의원정수 values of the NA table `nokivirranikoinnk` (term 16 had 273 seats). General-election entrants equal the seat count in every term, and by-election and succession entrants equal the number of such events in Wikipedia. In term 22 one seat (강원 강릉시) is vacant after 권성동 lost it on 2026-07-16, so 299 members sit at the cutoff.

Checks in `validation/`:

- `counts_per_term.csv` has the table above plus corroboration counts per term.
- `duplicates_term_mona.csv` is empty. Each (term, `mona_cd`) appears once.
- Missing birth dates are zero. Missing hanja are two in term 17 and one in term 18.
- `name_birth_multi_mona.csv` is empty. No name and birth date pair maps to two codes, so the same person keeps one `mona_cd` across terms.
- `mona_multi_name_birth.csv` is empty. No code carries two names or two birth dates.
- `same_name_different_persons.csv` lists the 37 names shared by different people (for example two 최경환 in term 20 and two 김병욱 in term 21, each kept apart by code, birth date and district). A term-15 이재명 (born 1948, 인천 부평구을) is a different person from the later 이재명.
- `person_terms.csv` lists the terms of each code.
- `daily_headcount.csv` shows that the number of sitting members never exceeds the seat count on any day after the corrections. Before the 이회창 correction it exceeded 299 on 7 days from 1997-12-20.
- `district_overlaps.csv` is empty. No two spells overlap in the same district after the 김학원 correction (same-day handovers allowed).
- `deaths_vs_hunjunghoe.csv` compares the 17 deaths in office with the 헌정회 death dates. Fifteen agree to the day. 심규섭 differs (2002-01-27 in the NA record and Wikipedia, 2002-01-29 in 헌정회) and 구논회 has no 헌정회 death date. No 헌정회 death date falls inside a spell that is not coded as a death.
- `party_wiki_vs_api.csv` lists 17 spells where the Wikipedia party at election differs from the party in the NA 의원이력 record. Most are cases where the NA record carries a later party name (Wikipedia 통합민주당, NA 민주당 in term 18) or PR members elected on a satellite list whom the NA records under their later party (three 더불어시민당 members in term 21).
- `kna_vs_this_table.csv` lists differences from the kna build (below).
- `date_conflicts_and_single_source.csv` lists every spell with a boundary that is not confirmed.

## Problems found in the kna build (read only, not changed)

The kna files split the slash-separated `ALLNAMEMBER` fields by position, which misassigns the district when a member held a PR seat in some terms. In `kna/data/processed/members_17..22.parquet` this gives wrong districts for 김한길 (17, shows 광진구갑), 김영선 (17 and 18), 박지원 (20, shows 해남군완도군진도군), and wrong `election_type` (지역구 instead of 비례대표) for 신용현 and 권미혁 (20). Term 22 also lacks the 15 members who entered after March 2026. The per-term 의원이력 records used here do not have this problem.

## Known gaps

- Five exits rest on the NA date alone and have no established reason. They are 하순봉 (16, 2004-05-03), 송석찬 and 천용택 (16, 2004-05-14), 박재완 and 이주호 (17, 2008-03-01). Their `exit_reason` is blank and `exit_detail` is `unknown`. 임광현's end date (22, 2025-07-22) also rests on the NA only, although news confirms the reason.
- PR successor start dates in terms 15-17 are the NA dates. Wikipedia usually gives the predecessor's exit date instead, and the news reports checked rarely state the NEC decision date. Treat these starts (status `api_later_than_wiki`) as accurate to within about two weeks.
- The 2026 resignations to run for local office carry the NA date 2026-04-30, while Wikipedia and a Money Today report of 2026-04-28 give 2026-04-29 as the planned day. The one-day gap was not resolved. The 2002 local-election resignations (김민석) and the 16th-term 이회창 resignation (NA 2002-12-11, Hankook Ilbo 2002-11-27 reporting 11-26) are also kept at the NA dates.
- 한광옥 (15) and 이회창 (15, PR spell) end dates are weakly verified (see the corrections table).
- The resignation motion records cover terms 17-22 only and end with the kna build in March 2026. Terms 15-16 have no bill-record check.
- `ALLNAMEMBER` and the 인적사항 table disagree on the lunar or solar flag of the birth date for every member (one says 음 where the other says 양). The flag is therefore left out, and `birth_date` is the recorded date without a calendar flag.
- The NA table of term dates (`nokivirranikoinnk`) has an error for term 15 (it repeats the term-14 dates). Term 15 is 1996-05-30 to 2000-05-29, as in the 의원이력 records and the Wikipedia page.
- The Wikipedia seat-change table for term 22 names 박수현 (국민의힘) as the 2026 winner in 공주시·부여군·청양군. The NA and the Wikipedia list give 윤용근. The NA and list value is used.
- `party_at_election` for PR successors follows Wikipedia, which is not consistent across terms (list party in some cases, party at succession in others). Use `pr_list_party` for the list.
- The 헌정회 table has no term-22 records.

## Sources and access times (UTC)

National Assembly open API (열린국회정보, https://open.assembly.go.kr/portal/openapi/), key omitted from all saved files.

| Endpoint | Table | Accessed | Snapshot |
|----------|-------|----------|----------|
| `ALLNAMEMBER` | 국회의원 정보 통합 (3,296 members, all terms) | 2026-09-25T02:15:00Z to 02:16:34Z | `sources/api/allnamember/` with `manifest.json` |
| `nfzegpkvaclgtscxt` | 역대 국회의원 의원이력 (former members), terms 15-22 | 2026-09-25T02:19:39Z to 02:21:03Z | `sources/api/nfzegpkvaclgtscxt/` |
| `nexgtxtmaamffofof` | 국회의원 의원이력 (sitting members, 610 records) | same window | `sources/api/nexgtxtmaamffofof/` |
| `npffdutiapkzbfyvr` | 역대 국회의원 인적사항, terms 15-22 | same window | `sources/api/npffdutiapkzbfyvr/` |
| `nprlapfmaufmqytet` | 역대 국회의원 현황 (헌정회 data), terms 15-21 | same window | `sources/api/nprlapfmaufmqytet/` |
| `nokivirranikoinnk` | 역대 국회 선거일, 의원정수, 임기정보 | same window | `sources/api/nokivirranikoinnk/` |
| `OPENSRVAPI` | API catalog, used to find the endpoints | 2026-09-25T02:18:12Z | `sources/api/opensrvapi_catalog.json` |
| spec sheets | official spec files naming the endpoint codes | 2026-09-25T02:18:48Z to 02:18:56Z | `sources/api/specs/` |

Per-page request times are in `sources/api/history_manifest.json` and `sources/api/allnamember/manifest.json`.

Korean Wikipedia (MediaWiki API, `action=parse`), revision ids fixed in the snapshots. The full log with URLs is `sources/wiki/access_log.tsv`.

| Page | Revision | Accessed |
|------|----------|----------|
| 대한민국 제15대 국회의원 목록 | 41996917 | 2026-09-25T02:17:07Z |
| 대한민국 제16대 국회의원 목록 | 42446179 | 2026-09-25T02:17:08Z |
| 대한민국 제17대 국회의원 목록 | 41080768 | 2026-09-25T02:17:09Z |
| 대한민국 제18대 국회의원 목록 | 40331558 | 2026-09-25T02:17:10Z |
| 대한민국 제19대 국회의원 목록 | 40914874 | 2026-09-25T02:17:11Z |
| 대한민국 제20대 국회의원 목록 | 40331548 | 2026-09-25T02:17:12Z |
| 대한민국 제21대 국회의원 목록 | 42148778 | 2026-09-25T02:17:13Z |
| 대한민국 제22대 국회의원 목록 | 42421192 | 2026-09-25T02:17:14Z |
| 대한민국 제15대 국회 to 제22대 국회 (의석 변동) | 41996916, 42446181, 41820105, 41820092, 42216872, 41820069, 41820079, 42540220 | 2026-09-25T02:17:41Z to 02:17:49Z |

Revision URLs take the form `https://ko.wikipedia.org/w/index.php?title=<title>&oldid=<revision>`.

NA bill records. `sources/na_bills/resignation_motions_17_22.csv` holds 77 motions titled 국회의원(○○○) 사직의 건, of which 43 were approved. They were copied on 2026-09-25T02:28:48Z from `kna/data/processed/master_bills_17..22.parquet` (kna build of March 2026), and each row keeps its `likms.assembly.go.kr` bill link.

kna release (read only). `kna/data/processed/members_17.parquet` to `members_22.parquet` (file dates 2026-03-30). `member_info_17_22.parquet` holds the same records and was not used separately.

News checks. Snapshots are in `sources/news/`, and `sources/news/access_log.tsv` records each URL with its access time. Articles used as evidence:

| Article | URL | Accessed |
|---------|-----|----------|
| Hankook Ilbo 1997-10-29, 탈당 이만섭씨 의원직/김찬진 변호사가 승계 | https://www.hankookilbo.com/news/article/199710290024060805 | 2026-09-25T02:33:20Z |
| Hankook Ilbo 1997-11-15, 이회창 후보 TV토론 (resignation planned for the 26th) | https://www.hankookilbo.com/news/article/199711150053494051 | 2026-09-25T02:33:45Z |
| Hankook Ilbo 1997-11-22, 이 후보 오늘 회견/의원직 사퇴 선언/이찬진씨 승계 | https://www.hankookilbo.com/news/article/199711220090178917 | 2026-09-25T02:33:18Z |
| Hankook Ilbo 1998-05-05, 李燦振 의원직 사퇴서 | https://www.hankookilbo.com/news/article/199805050040949393 | 2026-09-25T02:33:22Z |
| Hankook Ilbo 1998-05-06, 이찬진 왜 금배지 포기했나 | https://www.hankookilbo.com/news/article/199805060096431137 | 2026-09-25T02:35:22Z |
| Hankook Ilbo 1999-03-24, 송업교 전국구 의원직 승계 | https://www.hankookilbo.com/news/article/199903240071167562 | 2026-09-25T02:34:16Z |
| Hankook Ilbo 1999-03-31, 정상천 전국구의원직 사퇴서 제출 | https://www.hankookilbo.com/news/article/199903310079817416 | 2026-09-25T02:34:14Z |
| Hankook Ilbo 1999-09-07, [세풍여파] 서상목 의원직 사퇴 | https://www.hankookilbo.com/news/article/199909070047739038 | 2026-09-25T02:31:49Z |
| Hankook Ilbo 1999-12-28, 99 정치권 뜬 별 진 별 | https://www.hankookilbo.com/news/article/199912280059118280 | 2026-09-25T02:31:36Z |
| Hankook Ilbo 2000-10-13, 선관위, 김화중씨 전국구 결정 | https://www.hankookilbo.com/news/article/200010130035613989 | 2026-09-25T02:34:18Z |
| Hankook Ilbo 2002-11-27, 이회창후보 의원직 사퇴/유한열씨 승계 | https://www.hankookilbo.com/news/article/200211270031086567 | 2026-09-25T02:33:43Z |
| Hankook Ilbo 2003-03-05, 오영식·구종태씨 議員승계 | https://www.hankookilbo.com/news/article/200303050054183334 | 2026-09-25T02:34:19Z |
| Hankook Ilbo 2003-10-27, 민주 전국구5명 우리당行 | https://www.hankookilbo.com/news/article/200310270047461686 | 2026-09-25T02:35:44Z |
| edaily 2015-12-21, 새누리 비례대표 정윤숙 승계 | https://edaily.co.kr/News/Read?mediaCodeNo=257&newsId=04060646609600816 | 2026-09-25T02:37:09Z |
| Seoul Shinmun 2016-11-03, 17년만에 靑비서실장 컴백한 한광옥 | https://www.seoul.co.kr/news/politics/2016/11/03/20161103800073 | 2026-09-25T02:31:33Z |
| News1 2025-07-23 (also on fnnews), 임광현 국세청장 임명…이주희 변호사 비례대표 의원직 승계 | https://www.news1.kr/politics/assembly/5856667 and https://www.fnnews.com/news/202507231947455574 | 2026-09-25T02:36:40Z and 02:36:39Z |
| Money Today 2026-04-28, 추미애·박찬대·전재수 '마지막 본회의' | https://www.mt.co.kr/politics/2026/04/28/2026042813272976958 | 2026-09-25T02:37:31Z |

Other snapshots in `sources/news/` were read but gave no usable date (for example the 1999-04-03 plenary reports and the 2003 비화 series).

## Reproduce

Run from `_rebuild/na_members/`, with the NA key exported as `ASSEMBLY_API_KEY`.

```bash
python3 scripts/01_fetch_allnamember.py          # ALLNAMEMBER pages
python3 scripts/03_fetch_na_history_apis.py      # 의원이력, 인적사항, 헌정회, term dates
python3 scripts/02_fetch_wiki.py "대한민국 제15대 국회의원 목록" ... "대한민국 제22대 국회"   # 16 pages
python3 scripts/00_extract_kna_resignation_motions.py
python3 scripts/04_parse_wiki_lists.py           # work/wiki_list_rows.csv
python3 scripts/05_parse_wiki_seatchanges.py     # work/wiki_seat_changes.csv
python3 scripts/06_build_table.py                # outputs and validation/
python3 scripts/07_snapshot_url.py <label> <url> [pattern]   # news snapshot for a manual check
```

A fresh fetch will pick up later edits of the NA records and of Wikipedia. The saved snapshots reproduce this build exactly when the fetch steps are skipped.

## Extension to terms 12, 13 and 14

Added 2026-09-26 (UTC) to code dual office for the 1988-1998 ministers. The 12th Assembly is included because its term ran until 1988-05-29, so members elected in 1985 were still sitting when 노태우 took office on 1988-02-25.

### Files

| File | Content |
|------|---------|
| `na_members_12_22.csv` | Same columns as `na_members_15_22.csv`. The 937 rows for terms 12-14 come first. The 2,595 rows for terms 15-22 follow and are byte-identical to the data lines of `na_members_15_22.csv`. Total 3,532 rows and 1,982 distinct `mona_cd`. |
| `na_member_spells_12_22.csv` | Same columns as `na_member_spells_15_22.csv`. 938 spells for terms 12-14, then the 2,600 spells of the 15-22 file unchanged. Total 3,538. |
| `manual_checks_12_14.csv` | 29 hand checks for terms 12-14 with URLs, access times and quoted text. Same columns as `manual_checks.csv`. |
| `validation/t12_14/` | Validation tables for terms 12-14 (listed below). The 15-22 validation files are untouched. |
| `sources/api/term12/`, `term13/`, `term14/` | Raw NA API pages with a `manifest.json` each. |
| `sources/wiki/` | Six new page snapshots (member lists and 국회 pages for terms 12-14) and five member articles, all logged in `access_log.tsv`. |
| `sources/na_bills/likms_12_14/`, `sources/na_bills/resignation_motions_12_14.csv` | The 124 likms records titled 국회의원(○○○)사직의건 for terms 12-14, each detail page saved as HTML and text. |
| `sources/news/t12_14/` | BigKinds search responses (JSON with `.meta.json`) and `digest.tsv`, a readable list of every hit. |
| `scripts/11_*.py` to `scripts/15_*.py` | Fetch, parse and build scripts for this extension. Scripts 00-08 were not changed. |
| `work/wiki_list_rows_12_14.csv`, `work/wiki_seat_changes_12_14.csv` | Parsed Wikipedia intermediates. |

Two columns need care in the combined files.

- `same_name_other_person` for terms 12-14 is computed over terms 12-22. The 15-22 rows keep the flag of the 15-22 build, which looked at terms 15-22 only. Recomputed over 12-22, 29 of those rows would turn True (11 names, among them 강경식, 김영선, 이상민 and 이원형). Use `validation/t12_14/same_name_different_persons_12_22.csv` for the full list.
- `in_kna_build` is blank for terms 12-14, since the kna build starts with term 17.

### Terms, seats and electoral rules

| Term | Election | Term start | Term end | Seats (NA table `nokivirranikoinnk`) | District seats | PR (전국구) seats |
|---:|---|---|---|---:|---:|---:|
| 12 | 1985-02-12 | 1985-04-11 | 1988-05-29 | 276 | 184 (92 districts with two members each) | 92 |
| 13 | 1988-04-26 | 1988-05-30 | 1992-05-29 | 299 | 224 | 75 |
| 14 | 1992-03-24 | 1992-05-30 | 1996-05-29 | 299 | 237 | 62 |

The NA table notes that the 12th term, set at four years, ended on 1988-05-29 under 부칙 제3조 of the ninth constitutional amendment (1988-02-25). The seat numbers by type are the section headings of the Wikipedia lists. The 인적사항 table counts 184 district and 104 PR member rows in term 12, 228 and 79 in term 13, and 249 and 93 in term 14. These counts include by-election winners and PR successors.

### How the 12-14 rows were built

The method is that of the 15-22 build, with these differences.

1. The seat spells come from 의원이력 (`nfzegpkvaclgtscxt`, per term, fetched 2026-09-26) plus the sitting-member table saved on 2026-09-25 (`nexgtxtmaamffofof`), which holds one 12-14 record, 박지원's term-14 spell. `ALLNAMEMBER` from the 2026-09-25 pull gives the person attributes, so both parts of the combined file rest on the same person table. There is no kna base list for these terms.
2. The 의원이력 records name no district for most PR members (a few read 전국구). The seat type is set to PR when the record has no district, and it agrees with the 인적사항 election type and with the Wikipedia section for all 938 spells (`seat_type_api_vs_pi_vs_wiki.csv` is empty). PR seats read `전국구` in `district`.
3. Wikipedia rows were matched to API spells by name within term, with a key that ignores the initial-sound rule (라/나, 류/유, 렬/열) and spacing. This matched six spellings that differ between Wikipedia and the NA, which are (Wikipedia first) 류상호/유상호, 유갑종/류갑종, 김종렬/김종열, 류준상/유준상, 류제연/유제연 and 나병선/라병선. Two term-12 PR rows carry other names on Wikipedia. 한석봉 was matched through its article link (한효섭), and 김형호 (NA 김형효) as the only unmatched pair in the same list. Both cases carry a note. For namesakes, the birth year in the Wikipedia article title (for example 서정화 (1933년)) breaks ties. All 938 spells and all 938 Wikipedia rows matched one to one.
4. The seat-change tables of the pages 대한민국 제N대 국회 list several people in one row (for example `강영훈 / 최창윤 → 심기섭 / 안찬희`). These rows were split into one exit or entry per person. Rows reading 승계 불가 are exits.
5. NA bill records. `likms_search("사직", age)` gave 124 bills titled 국회의원(○○○)사직의건 for terms 12-14 (13 in term 12, 88 in term 13 and 23 in term 14). Each detail page was rendered and saved. 41 were approved (원안가결), 79 were refused (불허가, all filed on 1990-07-13 or 1990-07-23 and refused on 1990-09-07), 2 were withdrawn and 2 were discarded. For all 40 approved bills with a usable date, the decision date equals the NA end date of the member's spell. The one exception is 김동주 (term 13), whose record gives a decision date of 1991-10-16, before the proposal on 1992-02-26, and the end date rests on the NA and both Wikipedia tables. None of the 79 refused and 2 withdrawn bills is followed by an exit within 40 days. Of the two discarded bills, 서경원's was dropped because the seat had been lost by a conviction (remark 有罪確定으로 議員職 喪失), and 김양배's (term 12) carries the remark `1986.11.1 退職`, which is the NA end date. `validation/t12_14/resignation_bills_vs_spells.csv` lists every bill with its status.
6. An approved resignation bill decides the exit code. Where Wikipedia gives a different reason, the bill wins and the note says so. This changed 임철순 (term 12, Wikipedia seat table 사망, but the bill was approved on 1987-08-24 and the 헌정회 record gives a death date in 2017) and four term-14 PR members whom the seat table lists as losing the seat on leaving the party (박지원, 남궁진, 김옥두 and 이우정, whose resignations were approved on the NA end date).
7. BigKinds (bigkinds.or.kr) metadata covers the dailies from 1990. Its search API returns the title and lead of each article without login. It was used for the checks in `manual_checks_12_14.csv` (`scripts/15_news_checks_12_14.py`, 35 queries, every quoted lead compared with the saved response). Terms 12 and early 13 fall before 1990, where the checks rest on the bill records and the two Wikipedia tables.

Two new codes were needed.

| Column | Value | Meaning |
|--------|-------|---------|
| `entered_via` | `declared_winner_by_court` | Took the seat when a court voided the declared winner and named the member elected. One case, 임채정 (term 14, 서울 노원구을, 1992-09-08). |
| `exit_detail` | `winner_declaration_voided_by_court` | The reverse case, 김용채 (exit_reason `disqualified`). |

### Row counts and validation

| Term | Seats | Member rows | Spells | General | By-election | PR succession | By court | Wikipedia by-election events | Wikipedia succession events | Term end | Resigned | Died | Disqualified | Elected other office |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 | 276 | 288 | 288 | 276 | 0 | 12 | 0 | 0 | 12 | 271 | 12 | 4 | 0 | 1 |
| 13 | 299 | 307 | 308 | 299 | 5 | 4 | 0 | 5 | 4 | 292 | 6 | 2 | 8 | 0 |
| 14 | 299 | 342 | 342 | 299 | 11 | 31 | 1 | 11 | 31 | 285 | 24 | 7 | 26 | 0 |

General-election entrants equal the seat count in every term, and the by-election and succession entrants equal the Wikipedia events. Neither the NA nor Wikipedia records a by-election in the 12th term, and the five district seats vacated in that term stayed empty. Every exit has a reason. 홍희표 (term 13) holds two spells, one ending on 1989-03-14 (당선무효 in the Wikipedia seat table) and one won in the 동해시 re-election of 1989-04-14. 676 persons sat in terms 12-14, and 195 of them also sat in terms 15-22 under the same code.

Boundary status over the 938 spells. Starts are 874 term starts, 7 confirmed, 15 confirmed_pollday_plus1, 6 verified_manual, 35 api_later_than_wiki and 1 conflict. Ends are 848 term ends, 85 confirmed, 1 verified_manual, 2 api_earlier_than_wiki, 1 conflict and 1 single_source.

The api_later_than_wiki starts are all PR successions (34) except one. Wikipedia usually gives the day the predecessor left or announced leaving, and the NA date falls 1 to 20 days later. For six successions the news reports the 중앙선관위 decision on the NA date (권오석 1990-03-26, 유성환 and 강부자 1993-03-03, 김찬두 1994-11-04, 배기선 1995-09-04, 배길랑 1995-11-07), which supports reading the NA start as the NEC decision day. The exception is 이수인, who won the 1990-11-09 by-election in 영광·함평. The 서울신문 of 1990-11-11 reports the count of 114 of the 117 ballot boxes on the morning of 1990-11-10, and the NA start is 1990-11-11.

Checks in `validation/t12_14/`:

- `counts_per_term.csv` holds the table above with corroboration counts.
- `duplicates_term_mona.csv`, `mona_not_in_allnamember.csv`, `seat_type_api_vs_pi_vs_wiki.csv`, `district_overlaps.csv` and `age_outliers.csv` are empty.
- `name_birth_multi_mona_12_22.csv` and `mona_multi_name_birth_12_22.csv` are empty over terms 12-22. The same person keeps one code from term 12 to term 22, and no code carries two names or two birth dates.
- `same_name_different_persons_12_22.csv` lists the 25 names in terms 12-14 that belong to more than one person in terms 12-22 (124 rows). Four names were shared by two people sitting in the same term. They are 강경식 (term 12, 1936 PR and 1940 부산 진구), 서정화 (terms 12-14, 1933 and 1939, both PR in term 12 at ranks 7 and 50, then 서울 용산구 and 인천 중·동구), 김정길 (term 13, 1935 PR and 1945 부산 영도구) and 김영진 (term 14, 1940 PR and 1947 전남 강진·완도). There are three 박지원 in terms 12-22. The term-13 박지원 (born 1934, 경기 화성) is not the later 박지원 (born 1942, PR in term 14).
- `wiki_article_year_vs_birth.csv` lists nine rows where the year in the Wikipedia article title differs from the NA birth year. One is 김태수, whose NA year 2037 is corrected below. In the other eight the gap is one to four years (for example 박준병 (1933년), NA 1934), and the NA birth date is kept. Only 김영진 (term 14) has a namesake in the same term, and the two are told apart by seat type.
- `person_attrs_vs_injeoksahang.csv` lists the five birth dates corrected by hand (below). Otherwise the per-term 인적사항 table agrees with this table on name, hanja and birth date for every member.
- `daily_headcount.csv` never exceeds the seat count except on 1992-09-08, when 김용채 and 임채정 both hold the 노원구을 seat for the day of the ruling (a same-day handover, as in the NA record).
- `deaths_vs_hunjunghoe.csv` compares the 13 deaths in office with the 헌정회 table. Seven agree to the day, five have no 헌정회 death date, and 구자춘 differs (NA and Wikipedia 1996-02-10, 헌정회 1996-02-11). News reports the death on the evening of 1996-02-10.
- `party_wiki_vs_api.csv` lists 54 spells where the Wikipedia party at election differs from the NA 의원이력 party. 35 are term-12 members elected for other parties (29 of them for 민주한국당) whom the NA records under 신한민주당. Each of them appears in the Wikipedia seat-change table or member notes as joining 신한민주당. Of the other 19, fifteen are PR successors of 1996 for whom the NA gives 신한국당 or 민주당 where Wikipedia gives 민주자유당 or 통합민주당, and four are district members elected as independents whom the NA records under the party they joined later.
- `resignation_bills_vs_spells.csv` is described in step 5 above.
- `date_conflicts_and_single_source.csv` lists the 38 spells with a boundary that is not confirmed.

### Corrections and checks applied (`manual_checks_12_14.csv`)

| Term | Member | Field | NA value | Value used | Evidence |
|---:|---|---|---|---|---|
| 12 | 김옥선, 고한준, 김태수 | birth_date | 1834-04-02, 1830-07-30, 2037-01-07 | 1934-04-02, 1930-07-30, 1937-01-07 | 헌정회 table (NA API) and Wikipedia article |
| 13 | 이돈만, 이행구 | birth_date | 1848-08-09, 1821-09-29 | 1948-08-09, 1921-09-29 | 헌정회 table and Wikipedia article |
| 14 | 서석재 | exit_detail | court_ruling_other_or_unspecified | court_ruling_election_law | 경향신문 and 세계일보 1993-01-30 (conviction for buying off a candidate) |
| 14 | 이부영 | end_status | api_later_than_wiki | conflict | 국제신문 1995-11-04 and 경인일보 1995-11-08 place the loss of the seat on 1995-11-10. The NA end 1995-11-11 is kept. |
| 13 | 권오석 | seat_start | 1990-03-26 | same, verified | 경향신문 and 국민일보 1990-03-27 |
| 14 | 유성환, 강부자 | seat_start | 1993-03-03 | same, verified | 경인일보 and 부산일보 1993-03-04 |
| 14 | 김찬두 | seat_start | 1994-11-04 | same, verified | 서울신문 1994-11-05 |
| 14 | 배기선 | seat_start | 1995-09-04 | same, verified | 강원도민일보 1995-09-05 |
| 14 | 배길랑 | seat_start | 1995-11-07 | same, verified | 경향신문 and 한국일보 1995-11-08 |
| 14 | 김광수 | seat_end | 1996-03-04 | same, verified (Wikipedia 1996-03-05) | 한국일보 1996-03-05 |

Fifteen more rows are evidence notes that change no value. They cover the 수서 convictions of 1992-02-28 (이태섭, 오용운, 이원배), the convictions of 1992-03-10 (이학봉, 박재규), the 1992-09-08 ruling (김용채, 임채정), 김대중's resignation accepted on 1993-01-06 (Wikipedia gives the 1992-12-19 announcement), 구자춘's death, 이수인's by-election count, and the one-day disagreements for 조용직 and 신진욱. The notes for 박지원 and 이우정 quote the news on the day of resignation, and the note for 이민헌 records what was and was not found.

Automatic fixes, recorded in `notes`:

- 강삼재 (term 12) has an NA start of 1984-05-30, before the 1985 election. It is set to the term start. The Wikipedia list shows 강삼재 as elected for 마산시 with no succession or by-election event, and with this fix the general-election entrants equal the 276 seats.
- 현경대 (term 12) has an NA end of 1988-05-30, one day after the term. It is set to the term end.
- 이웅희 (term 14) has a blank party cell on Wikipedia. `party_at_election` is taken from the NA 의원이력 record (민주자유당).

### Known gaps for terms 12-14

- PR successor starts rest on the NA date alone in 34 cases (status api_later_than_wiki). The six news checks above all agree with the NA, but the other dates were not checked one by one.
- 이부영's last day (term 14) is 1995-11-09 or 1995-11-10 by the news and 1995-11-11 by the NA. 신진욱 (NA 1996-03-21, news and Wikipedia 1996-03-22) and 조용직 (NA 1996-02-22, one report and Wikipedia 1996-02-23) differ by one day. The 한국일보 of 1992-10-16 dates 조용직's succession to 1992-10-15, the NA to 1992-10-16. NA dates are kept in all four.
- 이민헌 (term 14) lost the seat on 1996-03-25 by the NA. Wikipedia gives only the year, and the news searched gives no reason. The reason is coded `court_ruling_other_or_unspecified` from the Wikipedia wording 의원직 상실. The member had been refused the 신한국당 nomination and was reported to be running as an independent, which suggests a loss on leaving the party, but no source says so.
- `court_ruling_other_or_unspecified` also covers 김종인 (1994-09-09, a bribery conviction confirmed by the Supreme Court according to 서울신문 1994-09-10), 박철언 (1994-06-28) and 서경원 (1990-08-24, whose bill remark reports a conviction).
- Before 1990 there is no news check. Boundaries before 1990, among them all of term 12 and the December 1988 successions of 심기섭 and 안찬희, rest on the NA, the bill records and Wikipedia.
- The Wikipedia tables contain errors that were not used. The seat-change table gives 사망 for 임철순 and 1986-11-14 for 김종철's death (the NA, the member list and 헌정회 give 1986-11-04). The member list gives 1985-10-13 for 김양배's resignation (the bill was filed on 1986-10-13). The seat-change table also writes 이연석, 박승웅 and 주양자 as 이년석, 박승옹 and 주앙자.
- The NA birth dates carry no calendar flag, as in the 15-22 build. The five century errors above were the only impossible dates found by the age check.

### Sources and access times (UTC)

| Source | Detail | Accessed |
|--------|--------|----------|
| NA open API `nfzegpkvaclgtscxt`, `npffdutiapkzbfyvr`, `nprlapfmaufmqytet` | terms 12, 13, 14 (`PROFILE_UNIT_CD`/`UNIT_CD` 100012-100014, `DAESU` 12-14), key omitted, `sources/api/term1N/manifest.json` | 2026-09-26T12:32:22Z to 12:32:52Z |
| NA open API `nexgtxtmaamffofof`, `ALLNAMEMBER`, `nokivirranikoinnk` | reused from the 15-22 pull | 2026-09-25 (see above) |
| kowiki 대한민국 제12대 국회의원 목록 | oldid 40892103 | 2026-09-26T12:33:19Z |
| kowiki 대한민국 제13대 국회의원 목록 | oldid 40892102 | 2026-09-26T12:33:20Z |
| kowiki 대한민국 제14대 국회의원 목록 | oldid 40331547 | 2026-09-26T12:33:21Z |
| kowiki 대한민국 제12대, 제13대, 제14대 국회 (의석 변동) | oldid 40637230, 41819983, 41819802 | 2026-09-26T12:33:22Z to 12:33:24Z |
| kowiki articles 김옥선, 고한준, 김태수 (1937년), 이돈만, 이행구 | oldid 42374620, 39789633, 39789614, 39727142, 39790234 | 2026-09-26T12:54:01Z to 12:54:05Z |
| likms.assembly.go.kr bill search and 124 detail pages | `https://likms.assembly.go.kr/bill/bi/billDetailPage.do?billId=<bill_id>`, rendered with Playwright | 2026-09-26T12:35:42Z to 13:00:23Z |
| BigKinds news search API | `https://www.bigkinds.or.kr/api/news/search.do` (POST), 35 queries, each saved with its request body | 2026-09-26T12:44:02Z to 12:48:44Z |

### Reproduce terms 12-14

Run from `_rebuild/na_members/`, with the NA key exported as `ASSEMBLY_API_KEY` for the first step only.

```bash
python3 scripts/11_fetch_na_history_12_14.py     # NA API pages for terms 12-14
python3 scripts/02_fetch_wiki.py "대한민국 제12대 국회의원 목록" "대한민국 제13대 국회의원 목록" "대한민국 제14대 국회의원 목록" "대한민국 제12대 국회" "대한민국 제13대 국회" "대한민국 제14대 국회"
python3 scripts/12_parse_wiki_12_14.py           # work/wiki_list_rows_12_14.csv, work/wiki_seat_changes_12_14.csv
python3 scripts/13_fetch_likms_resignations_12_14.py   # likms 사직의건 records (resumable)
python3 scripts/15_news_checks_12_14.py          # BigKinds snapshots behind manual_checks_12_14.csv
python3 scripts/14_build_table_12_22.py          # na_members_12_22.csv, na_member_spells_12_22.csv, validation/t12_14/
```

Script 14 imports its helper functions from `06_build_table.py` and reads the 15-22 outputs, which it copies without change. With the saved snapshots it reproduces this build exactly.


## kna 0.7.0 rebuild (2026-09-27)

Scripts `00_extract_kna_resignation_motions.py`, `06_build_table.py` and `14_build_table_12_22.py` were rerun against kna 0.7.0. The 0.6.0-based outputs are kept in `archive_kna0.6.0/`.

| Item | kna 0.6.0 | kna 0.7.0 |
|------|-----------|-----------|
| Resignation motions (approved) | 77 (43) | 86 (52) |
| Member-term rows, terms 12-22 | 3,532 | 3,532 |
| Seat spells, terms 12-22 | 3,538 | 3,538 |
| Rows with a changed seat_start or seat_end | | 0 |
| Rows with `in_kna_build` newly True | | 15 |
| Seat ends whose status became `confirmed` (new NA bill record) | | 9 |
| Disagreements with the kna member files (`validation/kna_vs_this_table.csv`) | 24 | 5 (0 with kna 0.7.1) |

Seat dates come from the NA open API, not from kna, so no seat date and no dual-office coding changed.
