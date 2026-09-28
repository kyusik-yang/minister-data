"""Build the National Assembly member reference for terms 12-14 and combine it with terms 15-22.

The 12-14 rows are built with the same logic as 06_build_table.py (functions are imported from
that script, which is not changed). The 15-22 rows are copied line by line, unchanged, from
na_members_15_22.csv and na_member_spells_15_22.csv.

Inputs
  sources/api/term12..term14/nfzegpkvaclgtscxt_p01.json   NA API 의원이력 (former members)
  sources/api/nexgtxtmaamffofof/all_p01.json              NA API 의원이력 (sitting members, all terms)
  sources/api/term12..term14/npffdutiapkzbfyvr_p01.json   NA API 역대 국회의원 인적사항
  sources/api/term12..term14/nprlapfmaufmqytet_p01.json   NA API 헌정회 records (death dates)
  sources/api/allnamember/                                NA API ALLNAMEMBER (person attributes)
  sources/na_bills/resignation_motions_12_14.csv          likms 국회의원(○○○)사직의건 with results
  work/wiki_list_rows_12_14.csv, work/wiki_seat_changes_12_14.csv   (script 12)
  manual_checks_12_14.csv                                 hand-verified corrections with evidence

Outputs
  na_members_12_22.csv, na_member_spells_12_22.csv
  validation/t12_14/*.csv
"""

import glob
import importlib.util
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
API = ROOT / "sources" / "api"
WORK = ROOT / "work"
VAL = ROOT / "validation" / "t12_14"


def _load(fn, name):
    spec = importlib.util.spec_from_file_location(name, HERE / fn)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


b06 = _load("06_build_table.py", "b06")

TERMS = (12, 13, 14)
TS = {12: "1985-04-11", 13: "1988-05-30", 14: "1992-05-30"}
TE = {12: "1988-05-29", 13: "1992-05-29", 14: "1996-05-29"}
SEATS = {12: 276, 13: 299, 14: 299}          # 의원정수, NA table nokivirranikoinnk
SEATS_PER_DISTRICT = {12: 2, 13: 1, 14: 1}   # term 12 elected two members per district
b06.TERM_START.update(TS)
b06.TERM_END.update(TE)
b06.SEATS.update(SEATS)

days, norm_name, norm_dist = b06.days, b06.norm_name, b06.norm_dist
clean_district, party_display, check, nearest = b06.clean_district, b06.party_display, b06.check, b06.nearest

Y_VOWELS = {2, 3, 6, 7, 12, 17, 20}  # ㅑ ㅒ ㅕ ㅖ ㅛ ㅠ ㅣ


def dnorm(name):
    """Name key that ignores the initial-sound rule (두음법칙) and spacing.

    ㄹ becomes ㅇ before i/y vowels and ㄴ otherwise, and ㄴ becomes ㅇ before i/y vowels, in every
    syllable. This makes 라병선/나병선, 김종렬/김종열 and 이연석/이년석 the same key."""
    out = []
    for ch in norm_name(name):
        c = ord(ch) - 0xAC00
        if 0 <= c < 11172:
            ini, med, fin = c // 588, (c % 588) // 28, c % 28
            if ini == 5:
                ini = 11 if med in Y_VOWELS else 2
            if ini == 2 and med in Y_VOWELS:
                ini = 11
            ch = chr(0xAC00 + ini * 588 + med * 28 + fin)
        out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# NA API
# ---------------------------------------------------------------------------
def load_term(ep):
    rows = []
    for t in TERMS:
        for f in sorted(glob.glob(str(API / f"term{t}" / f"{ep}_p*.json"))):
            d = json.load(open(f, encoding="utf-8"))
            if ep in d:
                rows += d[ep][1]["row"]
    return rows


def person_info():
    T = {}
    for r in load_term("npffdutiapkzbfyvr"):
        T[(r["MONA_CD"], int(r["UNIT_CD"][-2:]))] = {
            "pi_name": (r.get("HG_NM") or "").strip(), "pi_party": r.get("POLY_NM") or "",
            "pi_district": (r.get("ORIG_NM") or "").strip(), "pi_elect": r.get("ELECT_GBN_NM") or "",
            "pi_birth": r.get("BTH_DATE") or "", "pi_hanja": (r.get("HJ_NM") or "").strip()}
    return T


def api_spells(T):
    rows = [{**r, "api_table": "nfzegpkvaclgtscxt", "term": int(r["PROFILE_UNIT_CD"][-2:])}
            for r in load_term("nfzegpkvaclgtscxt")]
    for r in b06.load_api("nexgtxtmaamffofof"):
        m = re.match(r"제(\d+)대", r["PROFILE_SJ"])
        if m and int(m.group(1)) in TERMS:
            rows.append({**r, "api_table": "nexgtxtmaamffofof", "term": int(m.group(1))})
    out = []
    for r in rows:
        t = r["term"]
        a, _, b = r["FRTO_DATE"].partition("~")
        sj = re.sub(r"\s+", " ", r["PROFILE_SJ"]).strip()
        toks = sj.split(" ", 2)
        party = toks[1] if len(toks) > 1 else ""
        dist = toks[2].strip() if len(toks) > 2 else ""
        pi = T.get((r["MONA_CD"], t), {})
        note = ""
        if dist and not ("비례" in dist or "전국구" in dist):
            typ = "지역구"
        elif dist:
            typ = "비례대표"
        elif pi.get("pi_elect") == "지역구":
            typ, dist = "지역구", pi["pi_district"]
            note = "의원이력 record has no district, district and seat type taken from the NA 인적사항 record"
        else:
            typ = "비례대표"
        out.append({
            "term": t, "mona_cd": r["MONA_CD"], "api_name": r["HG_NM"].strip(),
            "api_hanja": (r.get("HJ_NM") or "").strip(), "api_start": b06.dot2iso(a), "api_end": b06.dot2iso(b),
            "api_frto": r["FRTO_DATE"].strip(), "api_party": party, "api_district": dist,
            "api_type": typ, "api_profile": sj, "api_table": r["api_table"], "api_note": note,
        })
    df = pd.DataFrame(out).sort_values(["term", "mona_cd", "api_start"]).reset_index(drop=True)
    df["spell_seq"] = df.groupby(["term", "mona_cd"]).cumcount() + 1
    return df


# ---------------------------------------------------------------------------
# Wikipedia list rows
# ---------------------------------------------------------------------------
SEAT_START_PAT = re.compile(r"재보궐선거 당선|보궐선거 당선|재선거 당선|의원직 승계|재검표 결과 당선")
SEAT_END_PAT = re.compile(r"의원직 사퇴|의원직 상실|사망|선거무효|당선무효|의원직 사직|퇴직|재검표 결과 낙선")


def fix_event(d, t):
    """Repair dates that the list parser leaves broken.

    '1987.12.22 의원직 사퇴' (no final dot) is parsed as ('1987-12', '22 의원직 사퇴').
    '1992.3,10. 의원직 상실' (comma) and '1996. 의원직 상실' (year only) are left undated."""
    m = re.match(r"^(\d{1,2}) (.*)$", t)
    if len(d) == 7 and m:
        return f"{d}-{int(m.group(1)):02d}", m.group(2)
    m = re.match(r"^(\d{4})\.\s*(\d{1,2})[,.]\s*(\d{1,2})\.?\s*(.*)$", t)
    if d == "" and m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}", m.group(4)
    m = re.match(r"^(\d{4})\.\s*(\D.*)$", t)
    if d == "" and m:
        return m.group(1), m.group(2)
    return d, t


def wiki_rows():
    wk = pd.read_csv(WORK / "wiki_list_rows_12_14.csv", keep_default_na=False)
    wk = wk[wk.name != ""].copy()
    s_d, s_t, e_d, e_t = [], [], [], []
    for ev in wk.events:
        ev = [fix_event(d, t) for d, t in json.loads(ev)]
        s = [(d, t) for d, t in ev if SEAT_START_PAT.search(t)]
        e = [(d, t) for d, t in ev if SEAT_END_PAT.search(t) and "제명무효" not in t]
        s_d.append(s[0][0] if s else "")
        s_t.append(s[0][1] if s else "")
        e_d.append(e[-1][0] if e else "")
        e_t.append(e[-1][1] if e else "")
    wk["w_start"], wk["w_start_event"], wk["w_end"], wk["w_end_event"] = s_d, s_t, e_d, e_t
    wk["w_type"] = wk.section.map({"district": "지역구", "pr": "비례대표"})
    wk["nname"] = wk.name.map(dnorm)
    wk["region"] = wk.subsection.str.replace(r"\(.*?\)", "", regex=True).str.strip()
    return wk.reset_index(drop=True)


def match_wiki(api, wk):
    """06_build_table.match_wiki with the 두음법칙-insensitive name key."""
    api = api.copy()
    api["nname"] = api.api_name.map(dnorm)
    api["wiki_idx"] = -1
    used = set()
    for (t, n), g in api.groupby(["term", "nname"]):
        cand = wk[(wk.term == t) & (wk.nname == n)]
        if len(g) == 1 and len(cand) == 1:
            api.loc[g.index, "wiki_idx"] = cand.index[0]
            used.add(cand.index[0])
            continue
        for i, r in g.sort_values("api_start").iterrows():
            c = cand[~cand.index.isin(used)]
            if len(c) == 0:
                continue

            def score(j):
                w = wk.loc[j]
                s = 2.0 if w.w_type == r.api_type else 0.0
                # namesakes: Wikipedia article titles such as '서정화 (1933년)' carry the birth year
                y = re.search(r"\((\d{4})년\)", w.name_link or "")
                if y and r.birth_year:
                    s += 0.5 if y.group(1) == r.birth_year else -0.5
                if r.api_type == "지역구" and w.w_type == "지역구":
                    s += b06.dist_sim(r.api_district, w)
                dd = days(w.w_start or TS[t], r.api_start)
                s += 1.0 / (1 + abs(dd)) if dd is not None else 0.0
                return s
            j = max(c.index, key=score)
            api.at[i, "wiki_idx"] = j
            used.add(j)
    # fallbacks for names that the Wikipedia list writes differently: first the article link,
    # then a unique pair in the same term and seat type with name similarity of at least 0.6
    link_key = wk.name_link.map(lambda x: dnorm(re.sub(r"\s*\(.*?\)", "", x)) if x else "")
    for i, r in api[api.wiki_idx < 0].iterrows():
        c = wk[(wk.term == r.term) & (link_key == r.nname) & (~wk.index.isin(used))]
        if len(c) == 1:
            api.at[i, "wiki_idx"] = c.index[0]
            used.add(c.index[0])
    for i, r in api[api.wiki_idx < 0].iterrows():
        c = wk[(wk.term == r.term) & (wk.w_type == r.api_type) & (~wk.index.isin(used))]
        sims = c.nname.map(lambda x: SequenceMatcher(None, x, r.nname).ratio())
        c = c[sims >= 0.6]
        if len(c) == 1:
            api.at[i, "wiki_idx"] = c.index[0]
            used.add(c.index[0])
    return api, used


# ---------------------------------------------------------------------------
# seat-change table, bill records, 헌정회, manual checks
# ---------------------------------------------------------------------------
def seat_change_events():
    sc = pd.read_csv(WORK / "wiki_seat_changes_12_14.csv", keep_default_na=False)

    def split(s):
        return [n.strip() for n in re.split(r"\s*/\s*|,\s*", s) if n.strip()]
    out = []
    for _, r in sc.iterrows():
        parts = [x.strip() for x in r["name"].split("→")]
        if len(parts) == 2:
            out += [{**r, "name": n, "role": "exit"} for n in split(parts[0])]
            out += [{**r, "name": n, "role": "enter"} for n in split(parts[1])]
            continue
        if "재결정" in r["reason"]:
            roles = ["enter", "exit"]   # 당선자 재결정: the table does not say who won
        else:
            reason = r["reason"].replace("승계 불가", "")   # '전국구 후보 부족으로 승계 불가' is an exit
            enter = bool(re.search(r"승계|재보궐선거 당선|보궐선거 당선|재선거 당선", reason)) and "대통령 당선" not in reason
            roles = ["enter" if enter else "exit"]
        out += [{**r, "name": n, "role": ro} for n in split(parts[0]) for ro in roles]
    df = pd.DataFrame(out)
    df["nname"] = df.name.map(dnorm)
    return df


def resignation_motions():
    import os
    f = Path(os.environ.get("BILLS_CSV_12_14", ROOT / "sources" / "na_bills" / "resignation_motions_12_14.csv"))
    df = pd.read_csv(f, keep_default_na=False, dtype={"bill_id": str, "bill_no": str})
    df["nname"] = df.member_name.map(dnorm)

    def effective(r):
        # approved motion: the decision date. Discarded motion with a remark such as
        # '1986.11.1 退職': the member left the seat on that day before any decision.
        if "가결" in r.result and r.decided_date and r.decided_date < r.propose_date:
            return "", "approved_decision_date_before_proposal"   # 김동주 1992: record error in likms
        if "가결" in r.result:
            return r.decided_date, "approved"
        m = re.search(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?\s*退職", r.remark)
        if m:
            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}", "retired_before_decision"
        return "", ""
    eff = df.apply(effective, axis=1, result_type="expand")
    df["date"], df["bill_kind"] = eff[0], eff[1]
    return df


def hunjunghoe():
    K = pd.DataFrame(load_term("nprlapfmaufmqytet"))
    iso = lambda x: (lambda m: f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else "")(
        re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", x or ""))
    K["nname"], K["dead"], K["birth"] = K.NAME.map(norm_name), K.DEAD.map(iso), K.BIRTH.map(iso)
    K["term"] = K.DAESU.astype(int)
    return K


def manual_checks():
    f = ROOT / "manual_checks_12_14.csv"
    if not f.exists():
        return pd.DataFrame(columns=["term", "mona_cd", "spell_seq", "field", "value", "decision_basis"])
    return pd.read_csv(f, keep_default_na=False, dtype={"term": int, "spell_seq": int})


# ---------------------------------------------------------------------------
# exit reason (06 rules plus 지명, 정계 은퇴 and recount)
# ---------------------------------------------------------------------------
HANJA = {"任命": "임명", "當選": "당선", "辭職": "사직", "退職": "퇴직", "就任": "취임", "大統領": "대통령",
         "死亡": "사망", "出馬": "출마", "議長許可": "의장허가"}


def classify_exit(texts, etype):
    t = " | ".join(x for x in texts if x)
    for a, b in HANJA.items():
        t = t.replace(a, b)
    if re.search(r"재결정|재검표 결과 낙선", t):
        return "disqualified", "winner_declaration_voided_by_court"
    if re.search(r"대통령 ?당선|대통령 ?취임", t):
        return "elected_other_office", "elected_president"
    if re.search(r"사망|별세|서거", t):
        return "died", "died"
    if etype == "비례대표" and re.search(r"탈당|당적 이탈|당적이탈|출당|제명.{0,6}상실|합당 불참", t) and re.search(r"상실|퇴직", t):
        return "disqualified", "pr_seat_lost_on_leaving_party"
    if re.search(r"선거 무효|선거무효", t):
        return "disqualified", "election_voided_by_court"
    if re.search(r"당선무효|선거법|공직선거법|정치자금|선거사무장|회계책임자|재산 신고", t):
        return "disqualified", "court_ruling_election_law"
    if re.search(r"후보자로 등록|후보 등록|후보등록", t):
        return "resigned", "resigned_to_run_for_other_office"
    if re.search(r"의원직 상실|유죄|확정판결|확정|징역|금고", t):
        return "disqualified", "court_ruling_other_or_unspecified"
    if re.search(r"출마", t) and re.search(r"사퇴|사직|퇴직", t):
        return "resigned", "resigned_to_run_for_other_office"
    if re.search(r"임명|취임|내정|지명", t) and re.search(r"사퇴|사직", t):
        return "resigned", "resigned_on_appointment"
    if re.search(r"사퇴|사직|정계 ?은퇴", t):
        return "resigned", "resigned_other"
    return "", "unknown"


# ---------------------------------------------------------------------------
# main build of the 12-14 spells
# ---------------------------------------------------------------------------
def build_spells(P):
    T = person_info()
    api = api_spells(T)
    api["birth_year"] = api.mona_cd.map(lambda c: (P.get(c, {}).get("birth") or "")[:4])
    wk = wiki_rows()
    api, used = match_wiki(api, wk)
    unmatched_api = api[api.wiki_idx < 0]
    unmatched_wk = wk[~wk.index.isin(used)]
    if len(unmatched_api) or len(unmatched_wk):
        print(unmatched_api[["term", "api_name", "api_type", "api_district", "api_frto"]].to_string())
        print(unmatched_wk[["term", "section", "district_or_rank", "name", "note_raw"]].to_string())
        raise SystemExit("unmatched rows")
    sc = seat_change_events()
    bills_all = resignation_motions()
    bills = bills_all[bills_all.date != ""]
    man = manual_checks()

    spells = []
    for _, r in api.iterrows():
        t = r.term
        w = wk.loc[r.wiki_idx]
        start, end = r.api_start, r.api_end
        notes = [r.api_note] if r.api_note else []
        if end > TE[t]:
            notes.append(f"API end {end} is after the term end, set to the term end")
            end = TE[t]
        if start < TS[t]:
            notes.append(f"API start {start} is before the term start and the election, set to the term start")
            start = TS[t]
        full_start, full_end = start == TS[t], end == TE[t]
        party_elected = party_display(w.party_elected_raw)
        if not party_elected:
            party_elected = r.api_party
            notes.append("Wikipedia party cell is blank, party_at_election taken from the NA 의원이력 record")
        if dnorm(w["name"]) != dnorm(r.api_name):
            notes.append(f"Wikipedia list writes the name as {w['name']} (article link {w.name_link or 'none'})")

        key = dnorm(r.api_name)
        sc_p = sc[(sc.term == t) & (sc.nname == key)]
        fuzzy = False
        if len(sc_p) == 0:
            c = sc[sc.term == t]
            sims = c.nname.map(lambda x: SequenceMatcher(None, x, key).ratio())
            sc_p, fuzzy = c[sims >= 0.66], True
        if sc_p.district.nunique() > 1 and r.api_type == "지역구":
            sims = sc_p.district.map(lambda d: SequenceMatcher(None, norm_dist(d), norm_dist(r.api_district)).ratio())
            sc_p = sc_p[sims >= 0.5] if (sims >= 0.5).any() else sc_p
        maxd = 3 if fuzzy else 70
        sc_in = None if full_start else nearest(sc_p[sc_p.role == "enter"], start, maxd=maxd)
        sc_out = None if full_end else nearest(sc_p[sc_p.role == "exit"], end, maxd=maxd)
        for ev, lab in ((sc_in, "entry"), (sc_out, "exit")):
            if fuzzy and ev is not None:
                notes.append(f"seat-change table spells the name {ev['name']} ({lab} {ev.date})")
        b_p = bills[(bills.age == t) & (bills.nname == key)]
        bill = None if full_end else nearest(b_p, end, maxd=40)

        recount = bool(re.search(r"재검표", w.w_start_event)) or (sc_in is not None and "재결정" in sc_in.reason)
        if full_start:
            entered = "general"
        elif recount:
            entered = "declared_winner_by_court"
        else:
            entered = "succession_pr" if r.api_type == "비례대표" else "by_election"

        exit_texts = [sc_out.reason if sc_out is not None else "", w.w_end_event,
                      bill.remark if bill is not None else ""]
        if full_end:
            exit_reason, exit_detail = "term_end", "term_end"
        else:
            exit_reason, exit_detail = classify_exit([exit_texts[0]], r.api_type)
            if exit_reason == "" or exit_detail in ("resigned_other", "court_ruling_other_or_unspecified"):
                r2, d2 = classify_exit(exit_texts, r.api_type)
                if r2 and (exit_reason == "" or d2 not in ("resigned_other", "court_ruling_other_or_unspecified")):
                    exit_reason, exit_detail = r2, d2
            if bill is not None and bill.bill_kind == "retired_before_decision":
                notes.append(f"NA bill {bill.bill_no} (billId {bill.bill_id}) was {bill.result}, remark '{bill.remark}'")
            if bill is not None and bill.bill_kind == "approved" and exit_reason in ("", "disqualified", "died") \
                    and exit_detail != "winner_declaration_voided_by_court":
                # an approved 사직의건 means the member resigned, whatever the Wikipedia tables say
                r3, d3 = classify_exit([bill.remark, w.w_end_event if "사퇴" in w.w_end_event else "", "사직"], "지역구")
                if r3 != "resigned":
                    r3, d3 = "resigned", "resigned_other"
                if exit_reason:
                    notes.append(f"Wikipedia gives exit {exit_detail}, but NA bill {bill.bill_no} (billId {bill.bill_id}) "
                                 f"approved the resignation on {bill.date}")
                exit_reason, exit_detail = r3, d3

        if full_start:
            s_status, s_detail = "term_start", ""
        else:
            s_status, s_detail = check(start, [("wikilist", w.w_start if len(w.w_start) == 10 else ""),
                                               ("wikiseat", sc_in.date if sc_in is not None else "")],
                                       by_election=(entered == "by_election"))
        if full_end:
            if w.w_end:
                e_status, e_detail = "conflict", f"wikilist reports exit {w.w_end} ({w.w_end_event})"
            else:
                e_status, e_detail = "term_end", ""
        else:
            e_status, e_detail = check(end, [("wikilist", w.w_end if len(w.w_end) == 10 else ""),
                                             ("wikiseat", sc_out.date if sc_out is not None else ""),
                                             ("nabill", bill.date if bill is not None else "")])
            if len(w.w_end) in (4, 7):
                e_detail = "; ".join(x for x in [e_detail, f"wikilist gives only {w.w_end}"] if x)

        rec = {
            "term": t, "mona_cd": r.mona_cd, "spell_seq": r.spell_seq, "name": r.api_name,
            "election_type": r.api_type,
            "district": "전국구" if r.api_type == "비례대표" else clean_district(r.api_district),
            "district_wiki": "" if w.section == "pr" else f"{w.region} {w.district_or_rank}".strip(),
            "pr_list_party": party_display(re.sub(r"\(.*?\)", "", w.subsection).strip()) if w.section == "pr" else "",
            "pr_list_rank": w.district_or_rank.replace("번", "") if w.section == "pr" else "",
            "party_at_election": party_elected,
            "party_at_election_wikikey": w.party_elected_raw,
            "party_at_seat_end_wiki": party_display(w.party_end_raw),
            "party_api_profile": r.api_party,
            "seat_start": start, "seat_end": end, "entered_via": entered,
            "exit_reason": exit_reason, "exit_detail": exit_detail,
            "exit_reason_text": " / ".join(x for x in exit_texts if x) if not full_end else "",
            "start_status": s_status, "start_check": s_detail, "end_status": e_status, "end_check": e_detail,
            "wiki_start": w.w_start, "wiki_end": w.w_end,
            "wikiseat_start": sc_in.date if sc_in is not None else "",
            "wikiseat_end": sc_out.date if sc_out is not None else "",
            "nabill_resign_date": bill.date if bill is not None else "",
            "nabill_id": bill.bill_id if bill is not None else "",
            "api_frto": r.api_frto, "api_profile": r.api_profile, "api_table": r.api_table,
            "wiki_article": w.name_link, "wiki_revid": int(w.wiki_revid),
            "wikiseat_revid": int(sc_p.wiki_revid.iloc[0]) if len(sc_p) else "",
            "notes": "; ".join(notes),
            "manual_check": False,
            # helper columns, dropped before writing
            "_wiki_section": w.section, "_pi": T.get((r.mona_cd, t), {}), "_birth_year": r.birth_year,
        }
        mm = man[(man.term == t) & (man.mona_cd == r.mona_cd) & (man.spell_seq == r.spell_seq)
                 & ~man.field.isin(MEMBER_FIELDS)]
        for _, m in mm.iterrows():
            f = m.field
            if f == "note":
                rec["notes"] = "; ".join(x for x in [rec["notes"], f"manual check: {m.value}"] if x)
                continue
            old = rec.get(f, "")
            rec[f] = m.value
            if f in ("seat_start", "seat_end"):
                k = "start" if f == "seat_start" else "end"
                rec[f"{k}_status"] = "verified_manual"
                rec[f"{k}_check"] = f"api={r.api_start if k == 'start' else r.api_end}; chosen={m.value}; " + m.decision_basis
            else:
                rec["notes"] = "; ".join(x for x in [rec["notes"], f"{f} set by manual_checks_12_14.csv (was {old})"] if x)
            if m.note:
                rec["notes"] = "; ".join(x for x in [rec["notes"], f"manual check: {m.note}"] if x)
            if f == "seat_end" and m.value == TE[t]:
                rec["exit_reason"], rec["exit_detail"] = "term_end", "term_end"
        if len(mm):
            rec["manual_check"] = True
        spells.append(rec)
    return pd.DataFrame(spells), wk, sc, bills_all, T


MEMBER_FIELDS = {"birth_date", "name_hanja", "gender"}   # person attributes, applied to the member table


def member_rows(S, P, man):
    rows = []
    for (t, m), g in S.groupby(["term", "mona_cd"], sort=False):
        g = g.sort_values("spell_seq")
        first, last = g.iloc[0], g.iloc[-1]
        p = P.get(m, {})
        n = len(g)
        spells_txt = " ; ".join(
            f"{x.seat_start}~{x.seat_end} {x.election_type} {x.district} ({x.entered_via}->{x.exit_reason})"
            for _, x in g.iterrows()) if n > 1 else ""
        src = ["NA-API 의원이력", "NA-API ALLNAMEMBER", f"kowiki list oldid={first.wiki_revid}"]
        if (g.wikiseat_start != "").any() or (g.wikiseat_end != "").any():
            src.append(f"kowiki 의석변동 oldid={first.wikiseat_revid}")
        if (g.nabill_id != "").any():
            src.append("NA bill " + ",".join(x for x in g.nabill_id if x))
        if g.manual_check.any():
            src.append("manual_checks_12_14.csv")
        rows.append({
            "term": t, "name": p.get("name") or first["name"], "name_hanja": p.get("hanja", ""),
            "birth_date": p.get("birth", ""), "gender": p.get("gender", ""),
            "party_at_election": first.party_at_election, "district": first.district,
            "election_type": first.election_type, "seat_start": first.seat_start, "seat_end": last.seat_end,
            "exit_reason": last.exit_reason, "entered_via": first.entered_via, "mona_cd": m,
            "source": "; ".join(src), "n_spells": n, "spells": spells_txt,
            "exit_detail": last.exit_detail, "exit_reason_text": last.exit_reason_text,
            "start_status": first.start_status, "end_status": last.end_status,
            "start_check": first.start_check, "end_check": last.end_check,
            "district_wiki": first.district_wiki, "pr_list_party": first.pr_list_party,
            "pr_list_rank": first.pr_list_rank, "party_at_seat_end_wiki": last.party_at_seat_end_wiki,
            "party_api_profile": first.party_api_profile, "wiki_article": first.wiki_article,
            "in_kna_build": "", "notes": "; ".join(x for x in g.notes if x),
        })
        for _, mc in man[(man.term == t) & (man.mona_cd == m) & man.field.isin(MEMBER_FIELDS)].iterrows():
            rec = rows[-1]
            rec["notes"] = "; ".join(x for x in [rec["notes"], f"{mc.field} set by manual_checks_12_14.csv (NA value {rec[mc.field]})"] if x)
            rec[mc.field] = mc.value
            if "manual_checks_12_14.csv" not in rec["source"]:
                rec["source"] += "; manual_checks_12_14.csv"
    return pd.DataFrame(rows).sort_values(["term", "election_type", "district", "seat_start", "name"],
                                          ascending=[True, False, True, True, True]).reset_index(drop=True)


def write_combined(new_df, old_file, out_file):
    """Write the 12-14 rows, then the 15-22 file's data lines verbatim."""
    old_lines = old_file.read_text(encoding="utf-8").splitlines(keepends=True)
    header = old_lines[0].rstrip("\r\n").split(",")
    assert list(new_df.columns) == header, (list(new_df.columns), header)
    new_txt = new_df.to_csv(index=False, lineterminator="\n")
    new_lines = new_txt.splitlines(keepends=True)
    assert new_lines[0] == old_lines[0].rstrip("\r\n") + "\n"
    out_file.write_text("".join(new_lines) + "".join(old_lines[1:]), encoding="utf-8")


def main():
    VAL.mkdir(parents=True, exist_ok=True)
    P, _ = b06.person_attrs()
    S, wk, sc, bills_all, T = build_spells(P)
    M = member_rows(S, P, manual_checks())

    old_M = pd.read_csv(ROOT / "na_members_15_22.csv", keep_default_na=False, dtype=str)
    old_S = pd.read_csv(ROOT / "na_member_spells_15_22.csv", keep_default_na=False, dtype=str)
    # namesakes: for 12-14 rows, any other person with the same name in terms 12-22
    names = pd.concat([M[["name", "mona_cd"]], old_M[["name", "mona_cd"]]])
    nm = names.groupby("name").mona_cd.nunique()
    M["same_name_other_person"] = M.name.map(lambda x: nm.get(x, 1) > 1)
    M = M[list(old_M.columns)]
    S_out = S[list(old_S.columns)]
    write_combined(M, ROOT / "na_members_15_22.csv", ROOT / "na_members_12_22.csv")
    write_combined(S_out, ROOT / "na_member_spells_15_22.csv", ROOT / "na_member_spells_12_22.csv")
    validate(M, S, wk, sc, bills_all, T, P, old_M)
    print("rows 12-14", len(M), "spells 12-14", len(S))


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------
def validate(M, S, wk, sc, bills_all, T, P, old_M):
    out = []
    for t in TERMS:
        m, s = M[M.term == t], S[S.term == t]
        ev = wk[wk.term == t].events.map(json.loads)
        n_by = sum(1 for e in ev for d, x in e if re.search(r"보궐선거 당선|재선거 당선", x))
        n_suc = sum(1 for e in ev for d, x in e if "의원직 승계" in x)
        out.append({
            "term": t, "official_seats": SEATS[t], "member_rows": len(m), "unique_mona_cd": m.mona_cd.nunique(),
            "spells": len(s), "wiki_list_rows": int((wk.term == t).sum()),
            "entered_general": (s.entered_via == "general").sum(),
            "entered_by_election": (s.entered_via == "by_election").sum(),
            "entered_succession_pr": (s.entered_via == "succession_pr").sum(),
            "entered_declared_winner_by_court": (s.entered_via == "declared_winner_by_court").sum(),
            "wiki_by_election_events": n_by, "wiki_succession_events": n_suc,
            "general_minus_seats": (s.entered_via == "general").sum() - SEATS[t],
            "exits_term_end": (s.exit_reason == "term_end").sum(),
            "exits_resigned": (s.exit_reason == "resigned").sum(),
            "exits_died": (s.exit_reason == "died").sum(),
            "exits_disqualified": (s.exit_reason == "disqualified").sum(),
            "exits_elected_other_office": (s.exit_reason == "elected_other_office").sum(),
            "exits_unknown": (s.exit_reason == "").sum(),
            "district_rows": (m.election_type == "지역구").sum(), "pr_rows": (m.election_type == "비례대표").sum(),
            "pi_district_rows": sum(1 for (c, tt), v in T.items() if tt == t and v["pi_elect"] == "지역구"),
            "pi_pr_rows": sum(1 for (c, tt), v in T.items() if tt == t and v["pi_elect"] == "전국구"),
            "missing_birth": (m.birth_date == "").sum(), "missing_hanja": (m.name_hanja == "").sum(),
            "start_confirmed": s.start_status.isin(["confirmed", "confirmed_pollday_plus1", "verified_manual"]).sum(),
            "end_confirmed": s.end_status.isin(["confirmed", "verified_manual"]).sum(),
            "start_api_later": (s.start_status == "api_later_than_wiki").sum(),
            "end_api_later": (s.end_status == "api_later_than_wiki").sum(),
            "start_api_earlier": (s.start_status == "api_earlier_than_wiki").sum(),
            "end_api_earlier": (s.end_status == "api_earlier_than_wiki").sum(),
            "start_conflict": (s.start_status == "conflict").sum(), "end_conflict": (s.end_status == "conflict").sum(),
            "start_single_source": (s.start_status == "single_source").sum(),
            "end_single_source": (s.end_status == "single_source").sum(),
            "manual_checks_applied": int(s.manual_check.sum()),
        })
    pd.DataFrame(out).to_csv(VAL / "counts_per_term.csv", index=False)

    M[M.duplicated(["term", "mona_cd"], keep=False)].to_csv(VAL / "duplicates_term_mona.csv", index=False)
    # seat type and person attributes against the NA 인적사항 table
    tc = []
    for _, r in S.iterrows():
        pi = r["_pi"]
        pe = {"지역구": "지역구", "전국구": "비례대표"}.get(pi.get("pi_elect", ""), "")
        ws = {"district": "지역구", "pr": "비례대표"}[r["_wiki_section"]]
        if not (r.election_type == pe == ws):
            tc.append({"term": r.term, "mona_cd": r.mona_cd, "name": r["name"], "api_type": r.election_type,
                       "pi_type": pe, "wiki_section": ws})
    pd.DataFrame(tc, columns=["term", "mona_cd", "name", "api_type", "pi_type", "wiki_section"]).to_csv(
        VAL / "seat_type_api_vs_pi_vs_wiki.csv", index=False)
    pc = []
    for _, r in M.iterrows():
        pi = T.get((r.mona_cd, r.term), {})
        for f_m, f_p in (("birth_date", "pi_birth"), ("name_hanja", "pi_hanja"), ("name", "pi_name")):
            if (pi.get(f_p) or "") != (r[f_m] or ""):
                pc.append({"term": r.term, "mona_cd": r.mona_cd, "name": r["name"], "field": f_m,
                           "this_table": r[f_m], "injeoksahang": pi.get(f_p, "(no record)")})
    pd.DataFrame(pc, columns=["term", "mona_cd", "name", "field", "this_table", "injeoksahang"]).to_csv(
        VAL / "person_attrs_vs_injeoksahang.csv", index=False)

    # implausible ages (the NA records carry century errors in some birth dates)
    ag = M.assign(age=M.seat_start.str[:4].astype(int) - M.birth_date.str[:4].astype(int))
    ag[(ag.age < 25) | (ag.age > 90)][["term", "mona_cd", "name", "birth_date", "seat_start", "age", "notes"]].to_csv(
        VAL / "age_outliers.csv", index=False)

    # Wikipedia article title year against the NA birth year (namesake check)
    by = []
    for _, r in S.iterrows():
        y = re.search(r"\((\d{4})년\)", r.wiki_article or "")
        if y and y.group(1) != r["_birth_year"]:
            by.append({"term": r.term, "mona_cd": r.mona_cd, "name": r["name"], "wiki_article": r.wiki_article,
                       "na_birth_year": r["_birth_year"]})
    pd.DataFrame(by, columns=["term", "mona_cd", "name", "wiki_article", "na_birth_year"]).to_csv(
        VAL / "wiki_article_year_vs_birth.csv", index=False)

    # persons across 12-22
    A = pd.concat([M[["term", "name", "birth_date", "mona_cd", "name_hanja", "district", "party_at_election"]].astype(str),
                   old_M[["term", "name", "birth_date", "mona_cd", "name_hanja", "district", "party_at_election"]]])
    nb = A.groupby(["name", "birth_date"]).mona_cd.nunique()
    nb[nb > 1].reset_index().to_csv(VAL / "name_birth_multi_mona_12_22.csv", index=False)
    mb = A.groupby("mona_cd").agg(names=("name", lambda x: "|".join(sorted(set(x)))),
                                  births=("birth_date", lambda x: "|".join(sorted(set(x)))),
                                  terms=("term", lambda x: ",".join(sorted(set(x), key=int))))
    mb[(mb.names.str.contains(r"\|")) | (mb.births.str.contains(r"\|"))].to_csv(VAL / "mona_multi_name_birth_12_22.csv")
    sn = A.groupby("name").filter(lambda g: g.mona_cd.nunique() > 1)
    sn = sn[sn.name.isin(M.name)].assign(ti=lambda x: x.term.astype(int)).sort_values(["name", "birth_date", "ti"]).drop(columns="ti")
    sn.to_csv(VAL / "same_name_different_persons_12_22.csv", index=False)
    A.assign(ti=A.term.astype(int)).groupby("mona_cd").ti.agg(lambda x: ",".join(str(i) for i in sorted(x))).reset_index().rename(
        columns={"ti": "terms"}).to_csv(VAL / "person_terms_12_22.csv", index=False)
    # codes in ALLNAMEMBER
    miss = sorted(set(M.mona_cd) - set(P))
    pd.DataFrame({"mona_cd": miss}).to_csv(VAL / "mona_not_in_allnamember.csv", index=False)

    ok = ["term_start", "term_end", "confirmed", "confirmed_pollday_plus1", "verified_manual"]
    S[(~S.start_status.isin(ok)) | (~S.end_status.isin(ok))].drop(columns=["_pi", "_birth_year"]).to_csv(
        VAL / "date_conflicts_and_single_source.csv", index=False)

    # headcount and district overlaps
    hc, ov = [], []
    for t in TERMS:
        s_t = S[S.term == t]
        rng = pd.date_range(TS[t], TE[t]).strftime("%Y-%m-%d")
        cnt = pd.Series(0, index=rng)
        for _, r in s_t.iterrows():
            cnt[(cnt.index >= r.seat_start) & (cnt.index <= r.seat_end)] += 1
        hc.append({"term": t, "seats": SEATS[t], "max_sitting": cnt.max(), "min_sitting": cnt.min(),
                   "days_over_seats": int((cnt > SEATS[t]).sum()),
                   "first_day_over": cnt[cnt > SEATS[t]].index[0] if (cnt > SEATS[t]).any() else ""})
        d = s_t[s_t.election_type == "지역구"]
        cap = SEATS_PER_DISTRICT[t]
        for k, g in d.groupby("district_wiki"):
            c2 = pd.Series(0, index=rng)
            for _, r in g.iterrows():
                c2[(c2.index > r.seat_start) & (c2.index < r.seat_end)] += 1  # same-day handovers allowed
            if (c2 > cap).any():
                ov.append({"term": t, "district_wiki": k, "members": " / ".join(
                    f"{x['name']} {x.seat_start}~{x.seat_end}" for _, x in g.iterrows()),
                    "max_concurrent": int(c2.max()), "seats_in_district": cap})
            if t == 12 and len(g) < 2:
                ov.append({"term": t, "district_wiki": k, "members": " / ".join(g["name"]),
                           "max_concurrent": int(c2.max()), "seats_in_district": cap})
    pd.DataFrame(hc).to_csv(VAL / "daily_headcount.csv", index=False)
    pd.DataFrame(ov, columns=["term", "district_wiki", "members", "max_concurrent", "seats_in_district"]).to_csv(
        VAL / "district_overlaps.csv", index=False)

    # deaths vs 헌정회
    K = hunjunghoe()
    K = K[K.dead != ""].drop_duplicates(["nname", "birth", "dead"])
    SB = S.merge(M[["term", "mona_cd", "birth_date"]], on=["term", "mona_cd"])
    SB["nname"] = SB.name.map(norm_name)
    x = SB.merge(K[["nname", "birth", "dead"]], left_on=["nname", "birth_date"], right_on=["nname", "birth"], how="left")
    x = x[(x.exit_reason == "died") | (x.dead.notna() & (x.dead >= x.seat_start) & (x.dead <= x.seat_end))]
    x["death_check"] = x.apply(lambda r: "agree" if r.dead == r.seat_end else ("hunjunghoe_missing" if pd.isna(r.dead) else
                               ("died_in_office_not_coded" if r.exit_reason != "died" else f"differ({r.dead})")), axis=1)
    x[["term", "mona_cd", "name", "seat_start", "seat_end", "exit_reason", "dead", "death_check"]].to_csv(
        VAL / "deaths_vs_hunjunghoe.csv", index=False)

    S[S.party_at_election != S.party_api_profile][["term", "mona_cd", "name", "election_type", "entered_via",
                                                   "party_at_election", "party_api_profile", "pr_list_party"]].to_csv(
        VAL / "party_wiki_vs_api.csv", index=False)

    # every resignation motion against the spells
    rb = []
    for _, b in bills_all.iterrows():
        cand = S[(S.term == b.age) & (S.name.map(dnorm) == b.nname)]
        ends = "; ".join(f"{c.mona_cd} end {c.seat_end} ({c.exit_reason})" for _, c in cand.iterrows())
        hit = cand[cand.seat_end == b.date] if b.date else cand.iloc[0:0]
        near = any(abs(days(c.seat_end, b.propose_date) or 999) <= 40 for _, c in cand.iterrows())
        if b.bill_kind == "approved_decision_date_before_proposal":
            status = "approved_but_record_date_invalid"
        elif b.bill_kind == "approved":
            status = "approved_and_seat_ends_that_day" if len(hit) else "approved_but_no_seat_end_that_day"
        elif b.bill_kind == "retired_before_decision":
            status = "left_seat_before_decision_and_seat_ends_that_day" if len(hit) else "left_seat_before_decision_no_match"
        else:
            status = "not_approved_and_no_exit_within_40_days" if not near else "not_approved_but_exit_within_40_days"
        rb.append({"term": b.age, "bill_no": b.bill_no, "member_name": b.member_name, "propose_date": b.propose_date,
                   "decided_date": b.decided_date, "result": b.result, "remark": b.remark, "effective_date": b.date,
                   "spells": ends, "status": status, "detail_url": b.detail_url})
    pd.DataFrame(rb).to_csv(VAL / "resignation_bills_vs_spells.csv", index=False)


if __name__ == "__main__":
    main()
