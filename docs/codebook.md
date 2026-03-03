# Codebook: minister_panel_comprehensive.csv

## Unit of Observation

One row = one ministerial appointment (minister × administration × ministry).

A minister who served in two different ministries within the same administration appears as two separate rows. A minister who served under two different presidents appears as two rows.

## Variables

### Identification

| Variable | Type | Description |
|----------|------|-------------|
| `ministry` | String | Ministry name in Korean (e.g., 교육부, 법무부, 기획재정부) |
| `name` | String | Minister's name in Korean |
| `name_en` | String | Minister's name romanized (McCune-Reischauer or official romanization) |

### Appointment Period

| Variable | Type | Description |
|----------|------|-------------|
| `start` | Date | Appointment start date (YYYY-MM-DD). Source: Korean Official Gazette (관보) |
| `end` | Date | Appointment end date (YYYY-MM-DD). Source: Korean Official Gazette. Missing if still in office at time of data collection. |

### Administration

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `admin` | String | 김대중, 노무현, 이명박, 박근혜, 문재인, 윤석열, 이재명, 한덕수 | President's name (Korean). "한덕수" refers to the caretaker period. |
| `admin_ideology` | String | Progressive, Conservative | Broad ideological orientation of the administration |

### Dual-Office Status (Key Variable)

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `dual_office` | Boolean | True, False | **True** if the minister simultaneously held a seat in the National Assembly (국회의원) during the appointment period. Coded based on National Assembly member records, Wikipedia cross-validation, and official appointment documents. |
| `mp_party_at_appt` | String | Party name or empty | The minister's political party at the time of appointment (if dual_office = True). Empty if not a dual-office minister. |
| `mp_district` | String | District name or empty | The minister's electoral district (지역구) or "비례대표" (proportional representation) at time of appointment. Empty if not dual-office. |
| `assembly_num_at_appt` | Float | 16.0, 17.0, ..., 22.0 | The National Assembly term (대수) during which the minister held their legislative seat. Empty if not dual-office. |

**Coding rules for dual_office:**
- A minister is coded `True` if they held their National Assembly seat AT THE TIME of their ministerial appointment AND retained that seat (even temporarily) during their ministerial tenure.
- Ministers who had previously served in the Assembly but resigned or whose term had expired before the ministerial appointment are coded `False`.
- Sources: National Assembly membership records (국회의원 현황), Official Gazette, Wikipedia, Namu Wiki.

### Confirmation Hearing

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `confirmation_hearing` | Boolean | True, False | True if the minister went through a National Assembly confirmation hearing (인사청문회). Since the 인사청문회법 (Confirmation Hearing Act) was enacted in 2000, all prime ministers and most senior ministers have been subject to these hearings. |
| `confirmation_date` | Date | YYYY-MM-DD or empty | Date of the confirmation hearing. Source: National Assembly records, Namu Wiki (인사청문회 목록). |

**Note on confirmation hearings:** The 인사청문회 system was gradually expanded. Initially (2000), only the Prime Minister and a few senior positions required hearings. Coverage expanded significantly in 2005 and again in 2014. Some ministers in the 김대중 era have `confirmation_hearing = False` for this reason.

### Notes

| Variable | Type | Description |
|----------|------|-------------|
| `notes` | String | Free-text notes documenting data sources, corrections applied, edge cases, or verification details. Often records the specific correction script that modified this entry. |

---

## Administration Breakdown

| Admin | N ministers | Dual-office (True) | Coverage |
|-------|-------------|-------------------|----------|
| 김대중 | 2 | 1 | Partial (2000-2003 not yet complete) |
| 노무현 | 80 | 9 | Complete (2003-2008) |
| 이명박 | 52 | 10 | Complete (2008-2013) |
| 박근혜 | 46 | 11 | Complete (2013-2017) |
| 문재인 | 54 | 18 | Complete (2017-2022) |
| 윤석열 | 30 | 5 | Through 2024-12 |
| 이재명 | 22 | 9 | Through 2025-03 (data collection ongoing) |
| 한덕수 (caretaker) | 1 | 0 | Caretaker PM only |
| **Total** | **287** | **63** | |

---

## Known Data Issues

1. **김대중 era incomplete:** The dataset was primarily constructed for the 노무현-이재명 period (17th-21st Assemblies, 2004-2024). The 김대중 entries are partial.

2. **Caretaker prime minister:** 한덕수 (2024-12-03 onward, following Yoon's impeachment) is listed separately.

3. **Date accuracy:** Start/end dates are sourced from the Official Gazette and are generally accurate to the day. Occasional discrepancies exist where the Official Gazette date and the actual service commencement date differ by 1-2 days.

4. **Dual-office edge cases:** A handful of ministers who were appointed on the exact last day of their Assembly term may be borderline cases. The coding follows the principle: was the minister simultaneously an Assembly member for any substantive period during their ministerial tenure?
