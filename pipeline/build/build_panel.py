"""Assemble the minister panel from the verified lineage rosters.

Inputs (all under _rebuild/):
  roster/<lineage>.verified.json   verified roster per ministry lineage (falls back to <lineage>.json)
  offices.json                     legal inventory of in-scope offices
  na_members/na_member_spells_15_22.csv, na_members/na_members_15_22.csv
  na_members/sources/api/allnamember/page_*.json   NA ALLNAMEMBER (all terms, for earlier seats)
  build/person_overrides.csv       optional manual person merges/splits (name, key, person_key)
  build/na_match_overrides.csv     optional manual person -> mona_cd links

Outputs (build/out/):
  minister_panel.csv   one row per spell x administration (clipped to the window)
  spells.csv           one row per spell (no administration split)
  nominations.csv      one row per nomination
  persons.csv          one row per person
  offices.csv          office-name periods
  validation.md        checks and counts
"""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "out"
WINDOW_START = pd.Timestamp("1988-02-25")
CUTOFF = pd.Timestamp("2026-09-24")

# Inauguration day belongs to the incoming administration.
ADMINS = [
    ("전두환", pd.Timestamp("1980-09-01"), "Conservative"),
    ("노태우", pd.Timestamp("1988-02-25"), "Conservative"),
    ("김영삼", pd.Timestamp("1993-02-25"), "Conservative"),
    ("김대중", pd.Timestamp("1998-02-25"), "Progressive"),
    ("노무현", pd.Timestamp("2003-02-25"), "Progressive"),
    ("이명박", pd.Timestamp("2008-02-25"), "Conservative"),
    ("박근혜", pd.Timestamp("2013-02-25"), "Conservative"),
    ("문재인", pd.Timestamp("2017-05-10"), "Progressive"),
    ("윤석열", pd.Timestamp("2022-05-10"), "Conservative"),
    ("이재명", pd.Timestamp("2025-06-04"), "Progressive"),
]
IDEOLOGY = {a: i for a, _, i in ADMINS}

LINEAGE_ORDER = ["pm", "finance", "budget", "unification", "foreign", "justice", "defense",
                 "interior", "safety", "education", "science", "ict", "culture", "agriculture",
                 "industry", "health", "environment", "labor", "gender", "land", "oceans",
                 "sme", "veterans", "special"]


def admin_on(d: pd.Timestamp) -> str:
    cur = None
    for name, start, _ in ADMINS:
        if d >= start:
            cur = name
    return cur


def to_ts(x):
    if x is None or (isinstance(x, float) and pd.isna(x)) or x == "":
        return pd.NaT
    s = str(x).strip()
    if re.fullmatch(r"\d{4}", s):
        return pd.NaT
    return pd.to_datetime(s[:10], errors="coerce")


def norm_hanja(s):
    if not isinstance(s, str):
        return None
    s = re.sub(r"\s+", "", s)
    return s or None


def birth_key(b):
    if not isinstance(b, str) or not b.strip():
        return None
    return b.strip()[:10]


# ---------------------------------------------------------------- load rosters

def roster_files():
    """(lineage, path, status, part) for every lineage file: main (1998+) and ext88 (1988-1998)."""
    keys = sorted({p.name.split(".")[0] for p in (ROOT / "roster").glob("*.json") if not p.name.endswith("partial.json")})
    order = [k for k in LINEAGE_ORDER if k in keys] + [k for k in keys if k not in LINEAGE_ORDER]
    out = []
    for lin in order:
        for part in ("main", "ext88"):
            suf = "" if part == "main" else ".ext88"
            f = ROOT / "roster" / f"{lin}{suf}.verified.json"
            status = "verified"
            if not f.exists():
                f = ROOT / "roster" / f"{lin}{suf}.json"
                status = "unverified"
            if f.exists():
                out.append((lin, f, status, part))
    return out


def ministry_overrides():
    """Ministry -> lineage overrides from the 1988 inventory (offices that ran in parallel
    with another office of the same old lineage, e.g. 공보처, 총무처)."""
    f = ROOT / "offices_1988.json"
    ov = {}
    if f.exists():
        d = json.loads(f.read_text())
        for x in d.get("ministry_to_lineage_overrides", []) or []:
            if isinstance(x, str) and "->" in x:
                a, b = [t.strip() for t in x.split("->", 1)]
                ov[a] = b
            elif isinstance(x, dict):
                ov[x.get("ministry")] = x.get("lineage")
    return ov


def load_rosters():
    spells, noms, acting, issues, sources = [], [], [], [], {}
    ovr = ministry_overrides()
    seen_spells = set()
    for lin, f, status, part in roster_files():
        d = json.loads(f.read_text())
        sources[f"{lin}:{part}"] = f"{f.name} ({status})"
        ver = (d.get("verification") or {})
        per = ver.get("per_spell") or ver.get("spell_status") or ver.get("spells") or ver.get("spell_statuses") or {}
        # verifiers wrote per-spell status in several layouts, normalise to (key, index, status)
        entries = []
        if isinstance(per, dict):
            for k, v in per.items():
                st = v.get("status") if isinstance(v, dict) else v
                m = re.match(r"^(\d+)\b", str(k))
                entries.append((str(k), int(m.group(1)) if m else None, st))
        elif isinstance(per, list):
            for j, v in enumerate(per):
                if isinstance(v, dict):
                    k = "|".join(str(v.get(x, "")) for x in ("name", "ministry", "start"))
                    entries.append((k, v.get("index", j), v.get("status")))
        for i, s in enumerate(d.get("spells", [])):
            s = dict(s)
            if part == "ext88" and (s.get("from_main") or str(s.get("start", "")) >= "1998-02-25"):
                continue  # 1998 holdovers are taken from the main (1998+) file
            key = (s.get("name"), s.get("ministry"), str(s.get("start")))
            if key in seen_spells:
                continue
            seen_spells.add(key)
            s["lineage"] = ovr.get(s.get("ministry"), lin)
            s["roster_part"] = part
            s["roster_file"] = f.name
            s["roster_status"] = status
            s["roster_index"] = i
            vs = s.get("verification_status") or s.get("verification")
            if isinstance(vs, dict):
                vs = vs.get("status")
            if not vs:
                for k, idx, st in entries:
                    if (s.get("name") in k and str(s.get("start")) in k) or (idx == i and s.get("name") in k):
                        vs = st
                        break
            if not vs:
                for k, idx, st in entries:
                    if idx == i:
                        vs = st
                        break
            s["verification_status"] = vs
            spells.append(s)
        for n in d.get("nominations", []):
            n = dict(n)
            nd = str(n.get("nomination_date") or n.get("outcome_date") or n.get("request_date") or "")
            if part == "ext88" and nd >= "1998-02-25":
                continue
            n["lineage"] = lin
            noms.append(n)
        for a in d.get("acting", []):
            a = dict(a)
            a["lineage"] = lin
            acting.append(a)
        for it in d.get("issues", []):
            it = dict(it) if isinstance(it, dict) else {"desc": str(it)}
            it["lineage"] = lin
            issues.append(it)
    return spells, noms, acting, issues, sources


# ---------------------------------------------------------------- corrections

def apply_corrections(spells, noms):
    """Apply build/corrections.csv (documented fixes found after verification, e.g. by the
    blind audit) and general coding rules. Returns the corrected lists and a log."""
    applied = []
    f = ROOT / "build" / "corrections.csv"
    cor = pd.read_csv(f, dtype=str) if f.exists() else pd.DataFrame()
    for _, c in cor.iterrows():
        hit = 0
        if c["kind"] == "spell":
            for s in spells:
                if s.get("name") == c["name"] and s.get("ministry") == c["ministry_or_office"] and str(s.get("start")) == c["start_or_date"]:
                    old = s.get(c["field"])
                    s[c["field"]] = c["new_value"]
                    s["notes"] = (str(s.get("notes") or "") + f" [correction {c['field']} {old} -> {c['new_value']}: {c['source']}]").strip()
                    s["verification_status"] = "corrected"
                    hit += 1
        else:
            for n in noms:
                if n.get("nominee") == c["name"] and n.get("office_title") == c["ministry_or_office"] and str(n.get("nomination_date")) == c["start_or_date"]:
                    old = n.get(c["field"])
                    n[c["field"]] = c["new_value"]
                    n["notes"] = (str(n.get("notes") or "") + f" [correction {c['field']} {old} -> {c['new_value']}: {c['source']}]").strip()
                    hit += 1
        applied.append((c["kind"], c["name"], c["field"], hit))
        if hit != 1:
            print("WARNING correction matched", hit, "records:", c["kind"], c["name"], c["ministry_or_office"], c["start_or_date"])
    # rule: a nomination that ended before any hearing has no hearing report to adopt
    for n in noms:
        if n.get("outcome") in ("withdrawn", "nominee_withdrew") and not n.get("hearing_dates") and n.get("report_adopted") in ("no", "unknown", None):
            n["report_adopted"] = "not_applicable"
            applied.append(("rule", n.get("nominee"), "report_adopted", 1))
    return spells, noms, applied


# ---------------------------------------------------------------- persons

def assign_persons(sp: pd.DataFrame) -> pd.DataFrame:
    """Same person = same Korean name and (same hanja or same birth date), or same name
    with no conflicting hanja/birth information anywhere. Conflicts are flagged."""
    sp = sp.copy()
    sp["hanja_n"] = sp["name_hanja"].map(norm_hanja)
    sp["birth_n"] = sp["birth_date"].map(birth_key)
    overrides = ROOT / "build" / "person_overrides.csv"
    ov = pd.read_csv(overrides) if overrides.exists() else pd.DataFrame(columns=["name", "hanja", "birth", "person_key"])
    keys = []
    flags = []
    for name, g in sp.groupby("name"):
        hanjas = set(g["hanja_n"].dropna())
        births = set(b[:4] for b in g["birth_n"].dropna())
        if len(hanjas) <= 1 and len(births) <= 1:
            for idx in g.index:
                keys.append((idx, f"{name}|{next(iter(hanjas), '')}|{next(iter(births), '')}"))
            continue
        # Several people share the name: cluster by hanja, then birth year.
        for idx, r in g.iterrows():
            hit = ov[(ov["name"] == name) & ((ov["hanja"] == r["hanja_n"]) | (ov["birth"].astype(str).str[:4] == (r["birth_n"] or "")[:4]))]
            if len(hit):
                keys.append((idx, hit.iloc[0]["person_key"]))
                continue
            if r["hanja_n"] or r["birth_n"]:
                keys.append((idx, f"{name}|{r['hanja_n'] or ''}|{(r['birth_n'] or '')[:4]}"))
            else:
                keys.append((idx, f"{name}|?"))
                flags.append(f"{name}: spell {r['ministry']} {r['start']} has no hanja/birth while the name is shared")
    sp["person_key"] = pd.Series(dict(keys))
    # Merge keys that differ only by a missing component (hanja known in one, birth in other).
    firsts = sp.sort_values("start_ts").groupby("person_key")["start_ts"].min().sort_values()
    import hashlib
    pid = {k: "P" + hashlib.sha1(k.encode("utf-8")).hexdigest()[:8] for k in firsts.index}
    assert len(set(pid.values())) == len(pid), "person id collision"
    sp["person_id"] = sp["person_key"].map(pid)
    sp.attrs["person_flags"] = flags
    return sp


# ---------------------------------------------------------------- NA seats

def load_na():
    ext = (ROOT / "na_members" / "na_member_spells_12_22.csv").exists()
    tag = "12_22" if ext else "15_22"
    spells = pd.read_csv(ROOT / "na_members" / f"na_member_spells_{tag}.csv", dtype=str)
    members = pd.read_csv(ROOT / "na_members" / f"na_members_{tag}.csv", dtype=str)
    rows = []
    for f in sorted(glob.glob(str(ROOT / "na_members" / "sources" / "api" / "allnamember" / "page_*.json"))):
        d = json.loads(Path(f).read_text())
        for blk in d["ALLNAMEMBER"]:
            rows += blk.get("row", [])
    alln = pd.DataFrame(rows)
    spells["seat_start_ts"] = pd.to_datetime(spells["seat_start"], errors="coerce")
    spells["seat_end_ts"] = pd.to_datetime(spells["seat_end"], errors="coerce").fillna(CUTOFF + pd.Timedelta(days=1))
    return spells, members, alln


def eraco_terms(s):
    return sorted(int(x) for x in re.findall(r"제(\d+)대", s or ""))


def match_na(persons: pd.DataFrame, members: pd.DataFrame, alln: pd.DataFrame):
    """Link each person to an NA member code (NAAS_CD/mona_cd). Name must match; hanja or
    birth date must match when the name is shared by several members."""
    ov_f = ROOT / "build" / "na_match_overrides.csv"
    ov = pd.read_csv(ov_f, dtype=str) if ov_f.exists() else pd.DataFrame(columns=["person_id", "mona_cd"])
    ovm = dict(zip(ov["person_id"], ov["mona_cd"]))
    alln = alln.copy()
    alln["hanja_n"] = alln["NAAS_CH_NM"].map(norm_hanja)
    out, notes = {}, []
    for _, p in persons.iterrows():
        if p["person_id"] in ovm:
            out[p["person_id"]] = (ovm[p["person_id"]] if ovm[p["person_id"]] != "none" else None, "override")
            continue
        c = alln[alln["NAAS_NM"] == p["name"]]
        if c.empty:
            out[p["person_id"]] = (None, "no_member_with_name")
            continue
        exact = c
        if p.get("hanja_n"):
            exact = c[c["hanja_n"] == p["hanja_n"]]
        if p.get("birth_n") and len(exact) != 1:
            b = p["birth_n"]
            e2 = c[c["BIRDY_DT"].astype(str).str[: len(b)] == b]
            if len(e2) == 1:
                exact = e2
        # a Hanja match is not enough: namesakes share Hanja (e.g. 김성환 金星煥 1953 and 1965).
        # Reject a candidate whose NA birth year differs by more than one year from the roster's.
        if p.get("birth_n") and len(exact):
            by = int(str(p["birth_n"])[:4])
            exact = exact[exact["BIRDY_DT"].astype(str).str[:4].map(lambda x: x.isdigit() and abs(int(x) - by) <= 1)]
        if len(exact) == 1 and not p.get("birth_n"):
            out[p["person_id"]] = (exact.iloc[0]["NAAS_CD"], "hanja_only_no_roster_birth")
            notes.append(f"{p['person_id']} {p['name']} {p.get('hanja_n')}: linked by Hanja only, roster has no birth date, NA birth {exact.iloc[0]['BIRDY_DT']}")
            continue
        if len(exact) == 1 and (p.get("hanja_n") or p.get("birth_n") or len(c) == 1):
            how = "hanja" if p.get("hanja_n") and exact.iloc[0]["hanja_n"] == p["hanja_n"] else ("birth" if p.get("birth_n") else "unique_name")
            out[p["person_id"]] = (exact.iloc[0]["NAAS_CD"], how)
        elif len(c) == 1 and not p.get("hanja_n") and not p.get("birth_n"):
            out[p["person_id"]] = (c.iloc[0]["NAAS_CD"], "unique_name_unconfirmed")
        else:
            if (p.get("hanja_n") or p.get("birth_n")) and len(exact) == 0:
                # namesakes exist but neither hanja nor birth date matches any of them
                out[p["person_id"]] = (None, "distinct_namesake")
                continue
            out[p["person_id"]] = (None, f"ambiguous_{len(c)}_members")
            notes.append(f"{p['person_id']} {p['name']} hanja={p.get('hanja_n')} birth={p.get('birth_n')}: {len(c)} NA members with the name, none matched uniquely")
    return out, notes


# ---------------------------------------------------------------- nominations

def link_nominations(sp: pd.DataFrame, nm: pd.DataFrame):
    """Link each appointed nomination to the spell it produced: same lineage, same name,
    spell start on or after the nomination (or request) date and within 400 days, the
    first such spell that is not a reorganization continuation."""
    sp_nom, nm_spell = {}, {}
    if not len(nm):
        return sp_nom, nm_spell
    cand = nm[nm["outcome"].astype(str) == "appointed"]
    for _, n in cand.iterrows():
        t = n["_ts"]
        s = sp[(sp["lineage"] == n["lineage"]) & (sp["name"] == n["nominee"]) & (~sp["reorg_continuation"].fillna(False).astype(bool))]
        if pd.notna(t):
            s = s[(s["start_ts"] >= t - pd.Timedelta(days=3)) & (s["start_ts"] <= t + pd.Timedelta(days=400))]
        s = s[~s["spell_id"].isin(sp_nom.keys())].sort_values("start_ts")
        if s.empty:
            # reorganization continuations, reappointments and deputy-PM elevations inside a running
            # spell: link to the spell (any) of this person in the lineage that contains the outcome date
            od = to_ts(n.get("outcome_date")) if pd.notna(to_ts(n.get("outcome_date"))) else t
            s = sp[(sp["lineage"] == n["lineage"]) & (sp["name"] == n["nominee"])]
            if pd.notna(od):
                s = s[(s["start_ts"] <= od + pd.Timedelta(days=3)) & (s["end_ts"].fillna(CUTOFF) >= od - pd.Timedelta(days=3))]
            s = s.sort_values("start_ts")
            if len(s):
                sid = s.iloc[0]["spell_id"]
                nm_spell[n["nomination_id"]] = sid
                sp_nom.setdefault(sid, n["nomination_id"])
            continue
        sid = s.iloc[0]["spell_id"]
        sp_nom[sid] = n["nomination_id"]
        nm_spell[n["nomination_id"]] = sid
    return sp_nom, nm_spell


# ---------------------------------------------------------------- main build

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spells, noms, acting, issues, sources = load_rosters()
    spells, noms, applied = apply_corrections(spells, noms)
    sp = pd.DataFrame(spells)
    sp["start_ts"] = sp["start"].map(to_ts)
    sp["end_ts"] = sp["end"].map(to_ts)
    sp = sp[sp["start_ts"].notna()].copy()
    sp = sp[(sp["end_ts"].isna()) | (sp["end_ts"] >= WINDOW_START)].copy()
    sp = sp.sort_values(["start_ts", "lineage", "name"]).reset_index(drop=True)
    sp = assign_persons(sp)

    # appointment_id: consecutive spells of one person in one lineage joined by reorganization
    sp = sp.sort_values(["person_id", "lineage", "start_ts"]).reset_index(drop=True)
    app, last = [], {}
    n = 0
    for i, r in sp.iterrows():
        k = (r["person_id"], r["lineage"])
        prev = last.get(k)
        cont = bool(r.get("reorg_continuation")) and prev is not None and \
            pd.notna(prev["end_ts"]) and (r["start_ts"] - prev["end_ts"]).days <= 1
        if not cont:
            n += 1
        app.append(n)
        last[k] = r
    sp["_app"] = app
    first = sp.groupby("_app")["start_ts"].min().sort_values()
    sp = sp.sort_values(["person_id", "lineage", "start_ts"]).reset_index(drop=True)
    sp["_ord"] = sp.groupby(["person_id", "lineage"]).cumcount() + 1
    sp["spell_id"] = sp["person_id"] + "-" + sp["lineage"] + "-" + sp["_ord"].astype(str)
    head = sp.sort_values("start_ts").groupby("_app")["spell_id"].first()
    sp["appointment_id"] = sp["_app"].map(lambda a: "A" + head[a][1:])
    ag = sp.groupby("appointment_id").agg(appointment_start=("start_ts", "min"), appointment_end=("end_ts", lambda s: s.max() if s.notna().all() else pd.NaT))
    sp = sp.join(ag, on="appointment_id")
    sp = sp.sort_values(["start_ts", "lineage", "name"]).reset_index(drop=True)
    # spell_id was assigned above (stable: person, lineage, ordinal)

    # NA linkage
    na_spells, members, alln = load_na()
    persons = sp.sort_values("start_ts").groupby("person_id").agg(
        name=("name", "first"), hanja_n=("hanja_n", lambda s: next((x for x in s if x), None)),
        birth_n=("birth_n", lambda s: next((x for x in s if x), None))).reset_index()
    match, match_notes = match_na(persons, members, alln)
    persons["mona_cd"] = persons["person_id"].map(lambda p: match[p][0])
    persons["na_match_method"] = persons["person_id"].map(lambda p: match[p][1])
    eraco = dict(zip(alln["NAAS_CD"], alln["GTELT_ERACO"]))
    persons["na_terms_all"] = persons["mona_cd"].map(lambda m: ",".join(map(str, eraco_terms(eraco.get(m)))) if m else "")

    # administration split
    rows = []
    for _, r in sp.iterrows():
        s = max(r["start_ts"], WINDOW_START)
        e = r["end_ts"] if pd.notna(r["end_ts"]) else CUTOFF
        cuts = [s] + [a for _, a, _ in ADMINS if s < a <= e] + [e + pd.Timedelta(days=1)]
        for j in range(len(cuts) - 1):
            rs, re_ = cuts[j], cuts[j + 1] - pd.Timedelta(days=1)
            if re_ < rs:
                continue
            row = r.to_dict()
            row["row_start"], row["row_end"] = rs, re_
            row["admin"] = admin_on(rs)
            row["holdover"] = row["admin"] != admin_on(r["start_ts"]) if r["start_ts"] >= ADMINS[0][1] else True
            row["in_office_at_cutoff"] = pd.isna(r["end_ts"]) and j == len(cuts) - 2
            rows.append(row)
    pan = pd.DataFrame(rows)

    # dual office per row
    pmona = dict(zip(persons["person_id"], persons["mona_cd"]))
    dual_cols = {k: [] for k in ["dual_office", "dual_office_start", "dual_office_end", "dual_office_full_row",
                                 "assembly_num_at_appt", "mp_district", "mp_election_type", "mp_party_at_election",
                                 "mp_party_api_profile", "former_mp", "mp_terms_before", "mona_cd"]}
    for _, r in pan.iterrows():
        m = pmona.get(r["person_id"])
        seats = na_spells[na_spells["mona_cd"] == m] if m else na_spells.iloc[0:0]
        ov = seats[(seats["seat_start_ts"] <= r["row_end"]) & (seats["seat_end_ts"] >= r["row_start"])].sort_values("seat_start_ts")
        before_terms = set(int(t) for t in seats[seats["seat_start_ts"] < r["row_start"]]["term"])
        if m:
            before_terms |= {t for t in eraco_terms(eraco.get(m)) if t < 15}
        dual_cols["mona_cd"].append(m)
        dual_cols["mp_terms_before"].append(len(before_terms))
        if len(ov):
            f0, fl = ov.iloc[0], ov.iloc[-1]
            ds, de = max(f0["seat_start_ts"], r["row_start"]), min(fl["seat_end_ts"], r["row_end"])
            dual_cols["dual_office"].append(True)
            dual_cols["dual_office_start"].append(ds)
            dual_cols["dual_office_end"].append(de)
            dual_cols["dual_office_full_row"].append(ds == r["row_start"] and de == r["row_end"])
            dual_cols["assembly_num_at_appt"].append(int(f0["term"]))
            dual_cols["mp_district"].append(f0["district"])
            dual_cols["mp_election_type"].append(f0["election_type"])
            dual_cols["mp_party_at_election"].append(f0["party_at_election"])
            dual_cols["mp_party_api_profile"].append(f0["party_api_profile"])
            dual_cols["former_mp"].append(len(before_terms - {int(f0['term'])}) > 0)
        else:
            dual_cols["dual_office"].append(False)
            for k in ["dual_office_start", "dual_office_end", "dual_office_full_row", "assembly_num_at_appt",
                      "mp_district", "mp_election_type", "mp_party_at_election", "mp_party_api_profile"]:
                dual_cols[k].append(None)
            dual_cols["former_mp"].append(len(before_terms) > 0)
    for k, v in dual_cols.items():
        pan[k] = v

    # dual-office share of the row, and retained vs caretaker holdovers
    pan["dual_office_share"] = [
        round(((r["dual_office_end"] - r["dual_office_start"]).days + 1) / ((r["row_end"] - r["row_start"]).days + 1), 4)
        if r["dual_office"] else 0.0 for _, r in pan.iterrows()]
    ret_pat = re.compile(r"유임|retain|reappoint|재임명|kept on|kept by", re.I)

    def holdover_type(r):
        if not r["holdover"]:
            return None
        days = (r["row_end"] - r["row_start"]).days + 1
        if days > 90 and ret_pat.search(str(r.get("notes") or "")):
            return "retained"
        return "caretaker"
    pan["holdover_type"] = pan.apply(holdover_type, axis=1)
    pan["admin_ideology"] = pan["admin"].map(IDEOLOGY)
    pan = pan.sort_values(["row_start", "lineage", "name"]).reset_index(drop=True)
    adm_no = {name: i for i, (name, _, _) in enumerate(ADMINS)}
    pan["row_id"] = pan["spell_id"] + "-" + pan["admin"].map(lambda a: f"g{adm_no[a]:02d}")

    # nominations and their link to spells
    nm = pd.DataFrame(noms)
    if len(nm):
        for c in ["nomination_date", "request_date", "outcome_date"]:
            if c not in nm:
                nm[c] = None
        nm["_ts"] = nm["nomination_date"].map(to_ts).fillna(nm["request_date"].map(to_ts)).fillna(nm["outcome_date"].map(to_ts))
        nm = nm.sort_values(["_ts", "lineage", "nominee"], na_position="last").reset_index(drop=True)
        import hashlib
        nkey = nm["nominee"].astype(str) + "|" + nm["office_title"].astype(str) + "|" + nm["nomination_date"].fillna(nm["request_date"]).fillna(nm["outcome_date"]).astype(str)
        nm["nomination_id"] = ["N" + hashlib.sha1(k.encode("utf-8")).hexdigest()[:8] for k in nkey]
        dup = nm["nomination_id"].duplicated(keep=False)
        if dup.any():
            nm.loc[dup, "nomination_id"] = nm.loc[dup, "nomination_id"] + "-" + (nm[dup].groupby("nomination_id").cumcount() + 1).astype(str)
    sp_nom, nm_spell = link_nominations(sp, nm)
    sp["nomination_id"] = sp["spell_id"].map(sp_nom)
    if len(nm):
        nm["spell_id"] = nm["nomination_id"].map(nm_spell)
    nom_by_id = nm.set_index("nomination_id") if len(nm) else pd.DataFrame()
    # hearing attributes belong to the appointment (inherited by reorg continuations and holdover rows)
    app_nom = sp.dropna(subset=["nomination_id"]).sort_values("start_ts").groupby("appointment_id")["nomination_id"].first()
    pan["nomination_id"] = pan["appointment_id"].map(app_nom)

    def nget(nid, col):
        if not isinstance(nid, str) or nid not in nom_by_id.index:
            return None
        return nom_by_id.at[nid, col] if col in nom_by_id.columns else None

    pan["confirmation_hearing"] = pan["nomination_id"].map(lambda n: bool(nget(n, "hearing_dates")) if isinstance(n, str) else False)
    pan["confirmation_date"] = pan["nomination_id"].map(lambda n: (sorted(nget(n, "hearing_dates"))[0] if nget(n, "hearing_dates") else None))
    pan["hearing_report_adopted"] = pan["nomination_id"].map(lambda n: nget(n, "report_adopted"))
    pan["nomination_date"] = pan["nomination_id"].map(lambda n: nget(n, "nomination_date"))
    pan["na_consent_vote"] = pan["nomination_id"].map(lambda n: nget(n, "na_consent_vote"))
    pan.to_pickle(OUT / "panel.pkl")
    sp.to_pickle(OUT / "spells.pkl")
    nm.to_pickle(OUT / "nominations.pkl")
    persons.to_pickle(OUT / "persons.pkl")
    pd.DataFrame(acting).to_pickle(OUT / "acting.pkl")
    pd.DataFrame(issues).to_pickle(OUT / "issues.pkl")
    (OUT / "build_log.json").write_text(json.dumps({"sources": sources, "person_flags": sp.attrs.get("person_flags", []),
                                                    "na_match_notes": match_notes}, ensure_ascii=False, indent=1))
    print("spells", len(sp), "rows", len(pan), "persons", len(persons), "nominations", len(nm))
    print(json.dumps(sources, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
