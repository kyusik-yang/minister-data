"""Build the National Assembly member reference table, terms 15-22.

Inputs (saved under sources/, or read-only elsewhere):
  sources/api/nfzegpkvaclgtscxt, nexgtxtmaamffofof   NA API 의원이력 (seat spells with dates)
  sources/api/allnamember                            NA API 국회의원 정보 통합 (person attributes)
  sources/api/npffdutiapkzbfyvr                      NA API 역대 국회의원 인적사항 (per term)
  sources/na_bills/resignation_motions_17_22.csv     NA bill records, 국회의원 사직의 건
  work/wiki_list_rows.csv                            parsed ko.wikipedia member lists (script 04)
  work/wiki_seat_changes.csv                         parsed ko.wikipedia 의석 변동 tables (script 05)
  manual_checks.csv                                  hand-verified dates with news/official URLs
  kna/data/processed/members_17..22.parquet          kna release (read only), base list for 17-22

Outputs:
  na_members_15_22.csv         one row per member x term
  na_member_spells_15_22.csv   one row per seat spell (a member can hold two spells in one term)
  validation/*.csv             validation tables
"""

import glob
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import os
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "sources" / "api"
WORK = ROOT / "work"
VAL = ROOT / "validation"
KNA = Path(os.environ.get("KNA_DATA", str(Path(__file__).resolve().parents[4] / "kna" / "data" / "processed")))  # kna repo checked out next to minister-data, or set KNA_DATA

TERM_START = {15: "1996-05-30", 16: "2000-05-30", 17: "2004-05-30", 18: "2008-05-30",
              19: "2012-05-30", 20: "2016-05-30", 21: "2020-05-30", 22: "2024-05-30"}
TERM_END = {15: "2000-05-29", 16: "2004-05-29", 17: "2008-05-29", 18: "2012-05-29",
            19: "2016-05-29", 20: "2020-05-29", 21: "2024-05-29", 22: "2028-05-29"}
SEATS = {15: 299, 16: 273, 17: 299, 18: 299, 19: 300, 20: 300, 21: 300, 22: 300}
CUTOFF = "2026-09-24"

PROVINCE = [("서울특별시", "서울"), ("부산광역시", "부산"), ("대구광역시", "대구"), ("인천광역시", "인천"),
            ("광주광역시", "광주"), ("대전광역시", "대전"), ("울산광역시", "울산"),
            ("세종특별자치시", "세종"), ("경기도", "경기"), ("강원도", "강원"), ("강원특별자치도", "강원"),
            ("충청북도", "충북"), ("충청남도", "충남"), ("전라북도", "전북"), ("전북특별자치도", "전북"),
            ("전라남도", "전남"), ("경상북도", "경북"), ("경상남도", "경남"), ("제주특별자치도", "제주"),
            ("제주도", "제주")]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def load_api(ep):
    rows = []
    for f in sorted(glob.glob(str(API / ep / "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        if ep in d:
            rows += d[ep][1]["row"]
    return rows


def dot2iso(s):
    s = (s or "").strip()
    if not s:
        return ""
    y, m, d = s.split(".")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def norm_name(s):
    s = re.sub(r"\s*\(.*?\)\s*", "", str(s or ""))
    return s.replace(" ", "").strip()


def norm_dist(s):
    s = str(s or "")
    for a, b in PROVINCE:
        s = s.replace(a, b)
    return re.sub(r"[\s·,()]", "", s)


def clean_district(s):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    for a, b in PROVINCE:
        if s.startswith(a + " "):
            s = b + s[len(a):]
    return s


def party_display(raw):
    return re.sub(r"\d{4}$", "", raw or "").strip()


def days(a, b):
    if not a or not b or len(a) != 10 or len(b) != 10:
        return None
    return (pd.Timestamp(a) - pd.Timestamp(b)).days


def now_utc():
    import subprocess
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip()


# ---------------------------------------------------------------------------
# 1. seat spells from the NA API
# ---------------------------------------------------------------------------
def api_spells():
    rows = []
    for r in load_api("nfzegpkvaclgtscxt"):
        rows.append({**r, "api_table": "nfzegpkvaclgtscxt", "term": int(r["PROFILE_UNIT_CD"][-2:])})
    for r in load_api("nexgtxtmaamffofof"):
        m = re.match(r"제(\d+)대", r["PROFILE_SJ"])
        rows.append({**r, "api_table": "nexgtxtmaamffofof", "term": int(m.group(1))})
    out = []
    for r in rows:
        t = r["term"]
        if t < 15 or t > 22:
            continue
        a, _, b = r["FRTO_DATE"].partition("~")
        sj = re.sub(r"\s+", " ", r["PROFILE_SJ"]).strip()
        toks = sj.split(" ", 2)
        party = toks[1] if len(toks) > 1 else ""
        dist = toks[2].strip() if len(toks) > 2 else ""
        is_pr = (dist == "") or ("비례" in dist) or ("전국구" in dist)
        out.append({
            "term": t, "mona_cd": r["MONA_CD"], "api_name": r["HG_NM"].strip(),
            "api_hanja": (r.get("HJ_NM") or "").strip(), "api_start": dot2iso(a), "api_end": dot2iso(b),
            "api_frto": r["FRTO_DATE"].strip(), "api_party": party, "api_district": dist,
            "api_type": "비례대표" if is_pr else "지역구", "api_profile": sj, "api_table": r["api_table"],
        })
    df = pd.DataFrame(out).sort_values(["term", "mona_cd", "api_start"]).reset_index(drop=True)
    df["spell_seq"] = df.groupby(["term", "mona_cd"]).cumcount() + 1
    return df


def person_attrs():
    P = {}
    rows = []
    for f in sorted(glob.glob(str(API / "allnamember" / "page_*.json"))):
        rows += json.load(open(f, encoding="utf-8"))["ALLNAMEMBER"][1]["row"]
    for r in rows:
        P[r["NAAS_CD"]] = {
            "name": (r.get("NAAS_NM") or "").strip(), "hanja": (r.get("NAAS_CH_NM") or "").strip(),
            "birth": r.get("BIRDY_DT") or "", "gender": r.get("NTR_DIV") or "",
            "eras": r.get("GTELT_ERACO") or "",
        }
    T = {}
    for r in load_api("npffdutiapkzbfyvr"):
        T[(r["MONA_CD"], int(r["UNIT_CD"][-2:]))] = {
            "pi_party": r.get("POLY_NM") or "", "pi_district": (r.get("ORIG_NM") or "").strip(),
            "pi_elect": r.get("ELECT_GBN_NM") or "", "pi_birth": r.get("BTH_DATE") or "",
        }
    return P, T


# ---------------------------------------------------------------------------
# 2. wiki list rows and matching
# ---------------------------------------------------------------------------
SEAT_START_PAT = re.compile(r"재보궐선거 당선|보궐선거 당선|재선거 당선|의원직 승계")
SEAT_END_PAT = re.compile(r"의원직 사퇴|의원직 상실|사망|선거무효|당선무효|의원직 사직|퇴직")


def wiki_rows():
    wk = pd.read_csv(WORK / "wiki_list_rows.csv", keep_default_na=False)
    wk = wk[wk.name != ""].copy()
    s_d, s_t, e_d, e_t = [], [], [], []
    for ev in wk.events:
        ev = json.loads(ev)
        s = [(d, t) for d, t in ev if SEAT_START_PAT.search(t)]
        e = [(d, t) for d, t in ev if SEAT_END_PAT.search(t) and "제명무효" not in t]
        # a date glitch such as "1996.12. 30 사망" leaves the day in the text
        e = [(d if not re.match(r"^\d{1,2} ", t) or len(d) != 7 else f"{d}-{int(t.split()[0]):02d}", t) for d, t in e]
        s_d.append(s[0][0] if s else "")
        s_t.append(s[0][1] if s else "")
        e_d.append(e[-1][0] if e else "")
        e_t.append(e[-1][1] if e else "")
    wk["w_start"], wk["w_start_event"], wk["w_end"], wk["w_end_event"] = s_d, s_t, e_d, e_t
    wk["w_type"] = wk.section.map({"district": "지역구", "pr": "비례대표"})
    wk["nname"] = wk.name.map(norm_name)
    wk["region"] = wk.subsection.str.replace(r"\(.*?\)", "", regex=True).str.strip()
    return wk.reset_index(drop=True)


def dist_sim(api_dist, wk_row):
    a = norm_dist(api_dist)
    b = norm_dist(wk_row.district_or_rank)
    if not a or not b:
        return 0.0
    if b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def match_wiki(api, wk):
    api = api.copy()
    api["nname"] = api.api_name.map(norm_name)
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
                s = 0.0
                s += 2.0 if w.w_type == r.api_type else 0.0
                if r.api_type == "지역구" and w.w_type == "지역구":
                    s += dist_sim(r.api_district, w)
                ws = w.w_start or TERM_START[t]
                dd = days(ws, r.api_start)
                s += 1.0 / (1 + abs(dd)) if dd is not None else 0.0
                return s
            j = max(c.index, key=score)
            api.at[i, "wiki_idx"] = j
            used.add(j)
    return api, used


# ---------------------------------------------------------------------------
# 3. seat change table events, resignation motions, manual checks
# ---------------------------------------------------------------------------
def seat_change_events():
    sc = pd.read_csv(WORK / "wiki_seat_changes.csv", keep_default_na=False)
    out = []
    for _, r in sc.iterrows():
        names = [x.strip() for x in r["name"].split("→")]
        if len(names) == 2:
            out.append({**r, "name": names[0], "role": "exit"})
            out.append({**r, "name": names[1], "role": "enter"})
        else:
            enter = bool(re.search(r"승계|재보궐선거 당선|보궐선거 당선|재선거 당선", r["reason"])) and "대통령 당선" not in r["reason"]
            out.append({**r, "name": names[0], "role": "enter" if enter else "exit"})
    df = pd.DataFrame(out)
    df["nname"] = df.name.map(norm_name)
    return df


def resignation_motions():
    f = ROOT / "sources" / "na_bills" / "resignation_motions_17_22.csv"
    df = pd.read_csv(f, keep_default_na=False)
    df = df[df.proc_rslt == "원안가결"].copy()
    df["nname"] = df.member_name.map(norm_name)
    df["date"] = df.rgs_rsln_dt.str[:10]
    return df


def manual_checks():
    f = ROOT / "manual_checks.csv"
    if not f.exists():
        return pd.DataFrame(columns=["term", "mona_cd", "spell_seq", "field", "value"])
    return pd.read_csv(f, keep_default_na=False, dtype={"term": int, "spell_seq": int})


# ---------------------------------------------------------------------------
# 4. exit reason
# ---------------------------------------------------------------------------
def classify_exit(texts, etype):
    t = " | ".join(x for x in texts if x)
    if re.search(r"대통령 당선|대통령 취임", t):
        return "elected_other_office", "elected_president"
    if re.search(r"(지사|시장|교육감|구청장|군수).{0,4}취임", t):
        return "elected_other_office", "took_office_as_elected_local_head"
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
    if re.search(r"임명|취임|내정", t) and re.search(r"사퇴|사직", t):
        return "resigned", "resigned_on_appointment"
    if re.search(r"사퇴|사직", t):
        return "resigned", "resigned_other"
    return "", "unknown"


# ---------------------------------------------------------------------------
# 5. main build
# ---------------------------------------------------------------------------
def nearest(ev, ref, maxd=70):
    if len(ev) == 0 or not ref:
        return None
    dd = ev.date.map(lambda x: days(x, ref))
    ev = ev.assign(dd=dd.abs()).dropna(subset=["dd"]).sort_values("dd")
    if len(ev) == 0 or ev.iloc[0].dd > maxd:
        return None
    return ev.iloc[0]


def check(api_date, others, by_election=False):
    """Compare the API date with the other sources. Returns (status, detail).

    confirmed                 at least one other source gives the same day
    confirmed_pollday_plus1   by-election entrant, API = polling day + 1 (당선 결정 시점)
    api_later_than_wiki       every other source is 1-70 days earlier (announcement, submission,
                              nomination or predecessor-exit dates in Wikipedia)
    api_earlier_than_wiki     every other source is 1-70 days later
    conflict                  sources disagree in both directions or by more than 70 days
    single_source             no other source reports this boundary
    """
    have = [(l, d) for l, d in others if d]
    detail = "; ".join(f"{l}={d}" for l, d in have)
    if any(d == api_date for _, d in have):
        return "confirmed", "+".join(l for l, d in have if d == api_date)
    if by_election and any(days(api_date, d) == 1 for _, d in have):
        return "confirmed_pollday_plus1", detail
    full = [days(api_date, d) for _, d in have if len(d) == 10]
    if not have:
        return "single_source", ""
    if full and all(0 < x <= 70 for x in full):
        return "api_later_than_wiki", detail
    if full and all(-70 <= x < 0 for x in full):
        return "api_earlier_than_wiki", detail
    return "conflict", detail


def main():
    VAL.mkdir(exist_ok=True)
    api = api_spells()
    P, T = person_attrs()
    wk = wiki_rows()
    api, used = match_wiki(api, wk)
    assert (api.wiki_idx >= 0).all(), "unmatched API spell"
    assert len(used) == len(wk), "unmatched wiki row"
    sc = seat_change_events()
    bills = resignation_motions()
    man = manual_checks()

    spells = []
    for _, r in api.iterrows():
        t = r.term
        w = wk.loc[r.wiki_idx]
        start, end = r.api_start, r.api_end
        notes = []
        # API end anomalies
        if end and end > TERM_END[t]:
            notes.append(f"API end {end} is after the term end, set to term end or sitting")
            end = TERM_END[t] if t < 22 else ""
        if t == 22 and end == TERM_END[22]:
            end = ""
        sitting = (t == 22 and not end)
        full_start = start == TERM_START[t]
        full_end = (end == TERM_END[t]) and t < 22

        sc_p = sc[(sc.term == t) & (sc.nname == norm_name(r.api_name))]
        if sc_p.district.nunique() > 1 and r.api_type == "지역구":
            sims = sc_p.district.map(lambda d: SequenceMatcher(None, norm_dist(d), norm_dist(r.api_district)).ratio())
            sc_p = sc_p[sims >= 0.5] if (sims >= 0.5).any() else sc_p
        sc_in = None if full_start else nearest(sc_p[sc_p.role == "enter"], start)
        sc_out = None if (full_end or sitting) else nearest(sc_p[sc_p.role == "exit"], end)
        b_p = bills[(bills.age == t) & (bills.nname == norm_name(r.api_name))]
        bill = None if (full_end or sitting) else nearest(b_p, end, maxd=40)

        # entry
        if full_start:
            entered = "general"
        else:
            entered = "succession_pr" if r.api_type == "비례대표" else "by_election"
        # exit
        exit_texts = [sc_out.reason if sc_out is not None else "", w.w_end_event]
        if sitting:
            exit_reason, exit_detail = "", ""
        elif full_end:
            exit_reason, exit_detail = "term_end", "term_end"
        else:
            exit_reason, exit_detail = classify_exit([exit_texts[0]], r.api_type)
            if exit_reason == "" or exit_detail in ("resigned_other", "court_ruling_other_or_unspecified"):
                r2, d2 = classify_exit(exit_texts, r.api_type)
                if r2 and (exit_reason == "" or d2 not in ("resigned_other", "court_ruling_other_or_unspecified")):
                    exit_reason, exit_detail = r2, d2
            if bill is not None and exit_reason == "":
                exit_reason, exit_detail = "resigned", "resigned_other"

        # date checks
        if full_start:
            s_status, s_detail = "term_start", ""
        else:
            s_status, s_detail = check(start, [("wikilist", w.w_start), ("wikiseat", sc_in.date if sc_in is not None else "")],
                                       by_election=(entered == "by_election"))
        if sitting:
            e_status, e_detail = "sitting", ""
        elif full_end:
            if w.w_end:
                e_status, e_detail = "conflict", f"wikilist reports exit {w.w_end} ({w.w_end_event})"
            else:
                e_status, e_detail = "term_end", ""
        else:
            e_status, e_detail = check(end, [("wikilist", w.w_end), ("wikiseat", sc_out.date if sc_out is not None else ""),
                                             ("nabill", bill.date if bill is not None else "")])

        rec = {
            "term": t, "mona_cd": r.mona_cd, "spell_seq": r.spell_seq, "name": r.api_name,
            "election_type": r.api_type,
            "district": ("전국구" if t == 15 else "비례대표") if r.api_type == "비례대표" else clean_district(r.api_district),
            "district_wiki": "" if w.section == "pr" else f"{w.region} {w.district_or_rank}".strip(),
            "pr_list_party": party_display(re.sub(r"\(.*?\)", "", w.subsection).strip()) if w.section == "pr" else "",
            "pr_list_rank": w.district_or_rank.replace("번", "") if w.section == "pr" else "",
            "party_at_election": party_display(w.party_elected_raw),
            "party_at_election_wikikey": w.party_elected_raw,
            "party_at_seat_end_wiki": party_display(w.party_end_raw),
            "party_api_profile": r.api_party,
            "seat_start": start, "seat_end": end, "entered_via": entered,
            "exit_reason": exit_reason, "exit_detail": exit_detail,
            "exit_reason_text": " / ".join(x for x in exit_texts if x) if not (full_end or sitting) else "",
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
        }
        # manual checks override
        mm = man[(man.term == t) & (man.mona_cd == r.mona_cd) & (man.spell_seq == r.spell_seq)]
        for _, m in mm.iterrows():
            f = m.field
            old = rec.get(f, "")
            rec[f] = m.value
            if f in ("seat_start", "seat_end"):
                key = "start" if f == "seat_start" else "end"
                rec[f"{key}_status"] = "verified_manual"
                rec[f"{key}_check"] = f"api={r.api_start if key == 'start' else r.api_end}; chosen={m.value}; " + m.decision_basis
            else:
                rec["notes"] = "; ".join(x for x in [rec["notes"], f"{f} set by manual_checks.csv (was {old})"] if x)
            if f == "seat_end" and m.value == TERM_END[t]:
                rec["exit_reason"], rec["exit_detail"] = "term_end", "term_end"
        if len(mm):
            rec["manual_check"] = True
        spells.append(rec)
    S = pd.DataFrame(spells)

    S.to_csv(ROOT / "na_member_spells_15_22.csv", index=False)

    # -----------------------------------------------------------------------
    # member x term table
    # -----------------------------------------------------------------------
    kna_sets = {}
    for t in range(17, 23):
        k = pd.read_parquet(KNA / f"members_{t}.parquet")
        kna_sets[t] = set(k.mona_cd)
    rows = []
    for (t, m), g in S.groupby(["term", "mona_cd"], sort=False):
        g = g.sort_values("spell_seq")
        first, last = g.iloc[0], g.iloc[-1]
        p = P.get(m, {})
        n = len(g)
        spells_txt = " ; ".join(
            f"{x.seat_start}~{x.seat_end or 'sitting'} {x.election_type} {x.district} ({x.entered_via}->{x.exit_reason or 'sitting'})"
            for _, x in g.iterrows()) if n > 1 else ""
        src = ["NA-API 의원이력", "NA-API ALLNAMEMBER"]
        if t >= 17:
            src.insert(0, "kna members_%d.parquet" % t if m in kna_sets[t] else "NA-API (not in kna build)")
        src.append(f"kowiki list oldid={first.wiki_revid}")
        if (g.wikiseat_start != "").any() or (g.wikiseat_end != "").any():
            src.append(f"kowiki 의석변동 oldid={first.wikiseat_revid}")
        if (g.nabill_id != "").any():
            src.append("NA bill " + ",".join(x for x in g.nabill_id if x))
        if g.manual_check.any():
            src.append("manual_checks.csv")
        rows.append({
            "term": t, "name": p.get("name") or first["name"], "name_hanja": p.get("hanja", ""),
            "birth_date": p.get("birth", ""), "gender": p.get("gender", ""),
            "party_at_election": first.party_at_election, "district": first.district,
            "election_type": first.election_type, "seat_start": first.seat_start, "seat_end": last.seat_end,
            "exit_reason": last.exit_reason if last.exit_reason else "",
            "entered_via": first.entered_via, "mona_cd": m, "source": "; ".join(src),
            # extras
            "n_spells": n, "spells": spells_txt,
            "exit_detail": last.exit_detail, "exit_reason_text": last.exit_reason_text,
            "start_status": first.start_status, "end_status": last.end_status,
            "start_check": first.start_check, "end_check": last.end_check,
            "district_wiki": first.district_wiki, "pr_list_party": first.pr_list_party,
            "pr_list_rank": first.pr_list_rank, "party_at_seat_end_wiki": last.party_at_seat_end_wiki,
            "party_api_profile": first.party_api_profile, "wiki_article": first.wiki_article,
            "in_kna_build": (m in kna_sets[t]) if t >= 17 else "",
            "notes": "; ".join(x for x in g.notes if x),
        })
    M = pd.DataFrame(rows).sort_values(["term", "election_type", "district", "seat_start", "name"],
                                       ascending=[True, False, True, True, True]).reset_index(drop=True)
    # same-name flags
    nm = M.groupby("name").mona_cd.nunique()
    M["same_name_other_person"] = M.name.map(lambda x: nm.get(x, 1) > 1)
    M.to_csv(ROOT / "na_members_15_22.csv", index=False)
    validate(M, S, wk)
    print("rows", len(M), "spells", len(S))


def validate(M, S, wk):
    # counts per term
    out = []
    for t in range(15, 23):
        m, s = M[M.term == t], S[S.term == t]
        ev = wk[wk.term == t].events.map(json.loads)
        n_by = sum(1 for e in ev for d, x in e if "재보궐선거 당선" in x or "보궐선거 당선" in x or "재선거 당선" in x)
        n_suc = sum(1 for e in ev for d, x in e if "의원직 승계" in x)
        seated_at_cutoff = ((s.seat_end == "") | (s.seat_end >= min(CUTOFF, TERM_END[t]))).sum() if t == 22 else ""
        out.append({
            "term": t, "official_seats": SEATS[t], "member_rows": len(m), "unique_mona_cd": m.mona_cd.nunique(),
            "spells": len(s), "entered_general": (s.entered_via == "general").sum(),
            "entered_by_election": (s.entered_via == "by_election").sum(),
            "entered_succession_pr": (s.entered_via == "succession_pr").sum(),
            "wiki_by_election_events": n_by, "wiki_succession_events": n_suc,
            "general_minus_seats": (s.entered_via == "general").sum() - SEATS[t],
            "exits_term_end": (s.exit_reason == "term_end").sum(),
            "exits_resigned": (s.exit_reason == "resigned").sum(),
            "exits_died": (s.exit_reason == "died").sum(),
            "exits_disqualified": (s.exit_reason == "disqualified").sum(),
            "exits_elected_other_office": (s.exit_reason == "elected_other_office").sum(),
            "exits_unknown": ((s.exit_reason == "") & (s.seat_end != "")).sum(),
            "sitting_at_cutoff": seated_at_cutoff,
            "district_rows": (m.election_type == "지역구").sum(), "pr_rows": (m.election_type == "비례대표").sum(),
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
            "manual_checks_applied": s.manual_check.sum(),
        })
    pd.DataFrame(out).to_csv(VAL / "counts_per_term.csv", index=False)
    # duplicates
    d = M[M.duplicated(["term", "mona_cd"], keep=False)]
    d.to_csv(VAL / "duplicates_term_mona.csv", index=False)
    # name+birth collisions
    nb = M.groupby(["name", "birth_date"]).mona_cd.nunique()
    nb = nb[nb > 1].reset_index()
    nb.to_csv(VAL / "name_birth_multi_mona.csv", index=False)
    mb = M.groupby("mona_cd").agg(names=("name", lambda x: "|".join(sorted(set(x)))),
                                  births=("birth_date", lambda x: "|".join(sorted(set(x)))),
                                  terms=("term", lambda x: ",".join(str(i) for i in sorted(x))))
    mb[(mb.names.str.contains(r"\|")) | (mb.births.str.contains(r"\|"))].to_csv(VAL / "mona_multi_name_birth.csv")
    # same name different persons
    sn = M.groupby("name").filter(lambda g: g.mona_cd.nunique() > 1)
    sn = sn[["name", "mona_cd", "birth_date", "name_hanja", "term", "district", "party_at_election"]].sort_values(["name", "birth_date", "term"])
    sn.to_csv(VAL / "same_name_different_persons.csv", index=False)
    # persons across terms (same person) summary
    per = M.groupby("mona_cd").term.agg(lambda x: ",".join(str(i) for i in sorted(x)))
    per.reset_index().rename(columns={"term": "terms"}).to_csv(VAL / "person_terms.csv", index=False)
    # date conflicts list
    ok = ["term_start", "term_end", "sitting", "confirmed", "confirmed_pollday_plus1", "verified_manual"]
    S[(~S.start_status.isin(ok)) | (~S.end_status.isin(ok))].to_csv(
        VAL / "date_conflicts_and_single_source.csv", index=False)
    # daily headcount per term and district overlaps
    hc, ov = [], []
    SS = S.assign(end2=S.seat_end.replace("", CUTOFF))
    for t in range(15, 23):
        s_t = SS[SS.term == t]
        rng = pd.date_range(TERM_START[t], min(TERM_END[t], CUTOFF)).strftime("%Y-%m-%d")
        cnt = pd.Series(0, index=rng)
        for _, r in s_t.iterrows():
            cnt[(cnt.index >= r.seat_start) & (cnt.index <= r.end2)] += 1
        hc.append({"term": t, "seats": SEATS[t], "max_sitting": cnt.max(), "min_sitting": cnt.min(),
                   "days_over_seats": int((cnt > SEATS[t]).sum()),
                   "first_day_over": cnt[cnt > SEATS[t]].index[0] if (cnt > SEATS[t]).any() else ""})
        d = s_t[s_t.election_type == "지역구"].assign(dk=lambda x: x.district.map(norm_dist))
        for k, g in d.groupby("dk"):
            g = g.sort_values("seat_start")
            for i in range(1, len(g)):
                if g.iloc[i].seat_start < g.iloc[i - 1].end2:
                    ov.append({"term": t, "district": g.iloc[i].district, "a": g.iloc[i - 1]["name"],
                               "a_end": g.iloc[i - 1].end2, "b": g.iloc[i]["name"], "b_start": g.iloc[i].seat_start})
    pd.DataFrame(hc).to_csv(VAL / "daily_headcount.csv", index=False)
    pd.DataFrame(ov, columns=["term", "district", "a", "a_end", "b", "b_start"]).to_csv(VAL / "district_overlaps.csv", index=False)
    # deaths in office vs 헌정회 death dates (NA API nprlapfmaufmqytet)
    K = pd.DataFrame(load_api("nprlapfmaufmqytet"))
    iso = lambda x: (lambda m: f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else "")(
        re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", x or ""))
    K["nname"], K["dead"], K["birth"] = K.NAME.map(norm_name), K.DEAD.map(iso), K.BIRTH.map(iso)
    K = K[K.dead != ""].drop_duplicates(["nname", "birth", "dead"])
    SB = S.merge(M[["term", "mona_cd", "birth_date"]], on=["term", "mona_cd"])
    SB["nname"] = SB.name.map(norm_name)
    x = SB.merge(K[["nname", "birth", "dead"]], left_on=["nname", "birth_date"], right_on=["nname", "birth"], how="left")
    x["end2"] = x.seat_end.replace("", CUTOFF)
    x = x[(x.exit_reason == "died") | ((x.dead != "") & x.dead.notna() & (x.dead >= x.seat_start) & (x.dead <= x.end2))]
    x["death_check"] = x.apply(lambda r: "agree" if r.dead == r.seat_end else ("hunjunghoe_missing" if pd.isna(r.dead) else
                               ("died_in_office_not_coded" if r.exit_reason != "died" else f"differ({r.dead})")), axis=1)
    x[["term", "mona_cd", "name", "seat_start", "seat_end", "exit_reason", "dead", "death_check"]].to_csv(
        VAL / "deaths_vs_hunjunghoe.csv", index=False)
    # kna release (members_17..22.parquet) vs this table
    kd = []
    for t in range(17, 23):
        k = pd.read_parquet(KNA / f"members_{t}.parquet")
        mm = M[M.term == t].set_index("mona_cd")
        for _, r in k.iterrows():
            if r.mona_cd not in mm.index:
                kd.append({"term": t, "mona_cd": r.mona_cd, "name": r.member_name, "field": "membership",
                           "kna": "present", "this_table": "absent"})
                continue
            o = mm.loc[r.mona_cd]
            for f_k, f_o in [("district", "district"), ("election_type", "election_type"), ("birth_date", "birth_date"),
                             ("member_name_hanja", "name_hanja"), ("sex", "gender")]:
                a, b = str(r[f_k] or ""), str(o[f_o] or "")
                if f_k == "district":
                    if o.election_type == "비례대표" and "비례" in a:
                        continue
                    if norm_dist(a) == norm_dist(b):
                        continue
                if a != b:
                    kd.append({"term": t, "mona_cd": r.mona_cd, "name": r.member_name, "field": f_k,
                               "kna": a.replace("\n", " "), "this_table": b})
        for m in set(mm.index) - set(k.mona_cd):
            kd.append({"term": t, "mona_cd": m, "name": mm.loc[m, "name"], "field": "membership",
                       "kna": "absent", "this_table": f"present (seat_start {mm.loc[m, 'seat_start']})"})
    pd.DataFrame(kd).to_csv(VAL / "kna_vs_this_table.csv", index=False)
    # party at election vs API profile party
    pm = S[S.party_at_election != S.party_api_profile][["term", "mona_cd", "name", "election_type", "entered_via",
                                                          "party_at_election", "party_api_profile", "pr_list_party"]]
    pm.to_csv(VAL / "party_wiki_vs_api.csv", index=False)


if __name__ == "__main__":
    main()
