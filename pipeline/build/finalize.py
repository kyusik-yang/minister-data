"""Write release CSVs and a validation report from the pickles made by build_panel.py.

Outputs in build/out/:
  minister_panel_comprehensive.csv  main table, one row per spell x administration
  spells.csv                        one row per spell (continuous tenure in one ministry name)
  nominations.csv                   one row per nomination (appointed, withdrawn, rejected)
  persons.csv                       one row per person
  acting_heads.csv                  acting heads recorded incidentally by the roster builders (not exhaustive)
  validation.md                     automated checks
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "out"
CUTOFF = pd.Timestamp("2026-09-24")
VALID_HTYPES = {"상임위원회", "국정감사", "인사청문특별위원회"}
NOT_MINISTER = ["실장", "처장", "청장", "위원장", "차관", "후보", "대행", "정책관", "국장", "과장"]

MAIN_COLS = [
    # backward-compatible columns (same names as the 2026-03 release)
    "ministry", "name", "name_en", "start", "end", "admin", "admin_ideology", "dual_office",
    "mp_party_at_appt", "mp_district", "assembly_num_at_appt", "confirmation_hearing", "confirmation_date", "notes",
    # identifiers
    "row_id", "spell_id", "appointment_id", "person_id", "nomination_id", "lineage",
    # person
    "name_hanja", "birth_date", "gender",
    # office and tenure
    "office_title", "deputy_pm", "spell_start", "spell_end", "appointment_start", "appointment_end",
    "in_office_at_cutoff", "end_reason", "appointing_president", "holdover", "holdover_type", "appointed_by_acting_president",
    "reorg_continuation", "reappointed_on_reorg", "pm_status", "pm_acting_until",
    "suspended_from", "suspended_to", "suspension_reason",
    # dual office (National Assembly seat) detail
    "dual_office_start", "dual_office_end", "dual_office_full_row", "dual_office_share", "mp_election_type", "mp_party_at_election",
    "mona_cd", "former_mp", "mp_terms_before", "mp_party_sources",
    # hearing
    "nomination_date", "hearing_report_adopted", "na_consent_vote",
    # provenance
    "start_confidence", "end_confidence", "start_sources", "end_sources", "verification_status", "roster_status",
]


def d(x):
    if x is None or (isinstance(x, float) and pd.isna(x)) or (hasattr(pd, "isna") and pd.isna(x) if not isinstance(x, (list, dict, str)) else False):
        return ""
    if isinstance(x, pd.Timestamp):
        return x.strftime("%Y-%m-%d")
    return x


def joinlist(x):
    if isinstance(x, list):
        return " ;; ".join(map(str, x))
    return x if isinstance(x, str) else ""


def main():
    pan = pd.read_pickle(OUT / "panel.pkl")
    sp = pd.read_pickle(OUT / "spells.pkl")
    nm = pd.read_pickle(OUT / "nominations.pkl")
    persons = pd.read_pickle(OUT / "persons.pkl")
    acting = pd.read_pickle(OUT / "acting.pkl")

    pan = pan.copy()
    pan["start"] = pan["row_start"]
    pan["end"] = pan.apply(lambda r: pd.NaT if r["in_office_at_cutoff"] else r["row_end"], axis=1)
    pan["spell_start"] = pan["start_ts"]
    pan["spell_end"] = pan["end_ts"]
    for c in ["suspended_from", "suspended_to", "suspension_reason"]:
        pan[c] = None
    for i, r in pan.iterrows():
        sus = r.get("suspensions") or []
        if isinstance(sus, list) and sus:
            ins = [s for s in sus if s.get("from") and pd.Timestamp(s["from"]) <= r["row_end"]
                   and (not s.get("to") or pd.Timestamp(s["to"]) >= r["row_start"])]
            if ins:
                pan.at[i, "suspended_from"] = ins[0].get("from")
                pan.at[i, "suspended_to"] = ins[0].get("to")
                pan.at[i, "suspension_reason"] = ins[0].get("reason")
    # party at appointment: verified value if the dual-office review supplied one, else the election party
    if "mp_party_at_appt" not in pan:
        pan["mp_party_at_appt"] = None
    ovf = ROOT / "build" / "dual_party_overrides.csv"
    if ovf.exists():
        ov = pd.read_csv(ovf, dtype=str)
        key = lambda n, m, st: f"{n}|{m}|{st}"
        omap = {key(r["name"], r["ministry"], r["row_start"]): r for _, r in ov.iterrows()}
        pan["_k"] = [key(r["name"], r["ministry"], r["row_start"].strftime("%Y-%m-%d")) for _, r in pan.iterrows()]
        rmap = {r["row_id"]: r for _, r in ov.iterrows() if isinstance(r.get("row_id"), str)}
        def pick(rid, k):
            r = rmap.get(rid)
            return r if r is not None else omap.get(k)
        picked = [pick(rid, k) for rid, k in zip(pan["row_id"], pan["_k"])]
        pan["mp_party_at_appt"] = [r["party_on_date"] if r is not None else None for r in picked]
        pan["mp_party_sources"] = [r["party_sources"] if r is not None else None for r in picked]
        missing = pan[pan["dual_office"].astype(bool) & pan["mp_party_sources"].isna()]
        if len(missing):
            print("WARNING dual rows without a party review:", missing[["name", "ministry", "row_start"]].to_string())
    pan["mp_party_at_appt"] = pan["mp_party_at_appt"].where(pan["mp_party_at_appt"].notna(), pan["mp_party_at_election"])
    pan.loc[~pan["dual_office"].astype(bool), "mp_party_at_appt"] = None
    pan["start_sources"] = pan["start_sources"].map(joinlist)
    pan["end_sources"] = pan["end_sources"].map(joinlist)
    pan["notes"] = pan["notes"].fillna("")
    for c in MAIN_COLS:
        if c not in pan:
            pan[c] = None
    out = pan[MAIN_COLS].copy()
    for c in out.columns:
        out[c] = out[c].map(d)
    out.to_csv(OUT / "minister_panel_comprehensive.csv", index=False)

    spc = sp.copy()
    spc["start_sources"] = spc["start_sources"].map(joinlist)
    spc["end_sources"] = spc["end_sources"].map(joinlist)
    spc["suspensions"] = spc["suspensions"].map(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, list) and x else "")
    keep = ["spell_id", "appointment_id", "person_id", "nomination_id", "lineage", "ministry", "office_title", "deputy_pm",
            "name", "name_hanja", "name_en", "birth_date", "gender", "start", "end", "end_reason", "appointing_president",
            "appointed_by_acting_president", "reorg_continuation", "reappointed_on_reorg", "pm_status", "pm_acting_until",
            "suspensions", "start_confidence", "end_confidence", "start_sources", "end_sources", "transcript_check",
            "transcript_notes", "verification_status", "roster_status", "notes"]
    for c in keep:
        if c not in spc:
            spc[c] = None
    spc[keep].to_csv(OUT / "spells.csv", index=False)

    if len(nm):
        nmc = nm.copy()
        nmc["hearing_dates"] = nmc["hearing_dates"].map(lambda x: ";".join(x) if isinstance(x, list) else (x or ""))
        nmc["sources"] = nmc["sources"].map(joinlist)
        nkeep = ["nomination_id", "spell_id", "lineage", "nominee", "office_title", "nomination_date", "request_date",
                 "likms_bill_id", "hearing_dates", "hearing_committee", "hearing_required", "report_adopted",
                 "na_consent_vote", "outcome", "outcome_date", "sources", "notes"]
        for c in nkeep:
            if c not in nmc:
                nmc[c] = None
        nmc[nkeep].to_csv(OUT / "nominations.csv", index=False)

    persons.to_csv(OUT / "persons.csv", index=False)
    if len(acting):
        import hashlib
        a = acting.copy()
        a["sources"] = a["sources"].map(joinlist)
        # the 1998 holdover acting records appear in both the main and the ext88 roster: keep one
        # add acting heads observed in the NA minutes inside documented vacancies (build/acting_from_transcripts.csv)
        tf = ROOT / "build" / "acting_from_transcripts.csv"
        if tf.exists():
            t = pd.read_csv(tf, dtype=str).rename(columns={"acting_for_lineage": "lineage"})
            a = pd.concat([a, t], ignore_index=True)
        # drop informational rows that are not acting heads of the lineage (e.g. a minister's concurrent acting-president role)
        a = a[~a["role"].astype(str).str.contains("not an acting head", case=False)]
        a = a.sort_values(["name", "lineage", "from", "to"]).drop_duplicates(subset=["name", "lineage", "from", "to"], keep="first").reset_index(drop=True)
        # stable id, link to a roster person when the acting head also held a cabinet post
        a["acting_id"] = ["H" + hashlib.sha1(f"{r['name']}|{r['lineage']}|{r['from']}".encode("utf-8")).hexdigest()[:8] for _, r in a.iterrows()]
        by_name = persons.groupby("name")["person_id"].apply(list).to_dict()
        hmap = dict(zip(persons["name"] + "|" + persons["hanja_n"].fillna(""), persons["person_id"]))
        def pid(r):
            h = r.get("name_hanja") if isinstance(r.get("name_hanja"), str) else ""
            if h and f"{r['name']}|{h}" in hmap:
                return hmap[f"{r['name']}|{h}"]
            c = by_name.get(r["name"], [])
            return c[0] if len(c) == 1 else None
        a["person_id"] = a.apply(pid, axis=1)
        a["acting_for_lineage"] = a["lineage"]
        a["coverage"] = a["lineage"].map(lambda l: "complete for PM vacancies and suspensions" if l == "pm" else "incidental, not exhaustive")
        a["added_by"] = a["added_by"].fillna("roster_builder") if "added_by" in a else "roster_builder"
        first = ["acting_id", "person_id", "name", "name_hanja", "acting_for_lineage", "role", "from", "to", "coverage", "sources"]
        a = a[first + [c for c in a.columns if c not in first and c != "lineage"]]
        a.to_csv(OUT / "acting_heads.csv", index=False)

    # ------------------------------------------------------------ validation
    lines = ["# Validation report", ""]
    lines.append(f"Rows {len(pan)}, spells {len(sp)}, appointments {sp['appointment_id'].nunique()}, persons {len(persons)}, nominations {len(nm)}")
    lines.append("")
    lines.append("## Rows by administration")
    t = pan.groupby("admin").agg(rows=("row_id", "size"), persons=("person_id", "nunique"), dual=("dual_office", "sum"), holdover=("holdover", "sum"))
    lines.append(t.to_markdown())
    lines.append("")
    # start <= end
    bad = sp[(sp["end_ts"].notna()) & (sp["end_ts"] < sp["start_ts"])]
    lines.append(f"## end before start: {len(bad)}")
    for _, r in bad.iterrows():
        lines.append(f"- {r['name']} {r['ministry']} {r['start']} {r['end']}")
    # overlaps and vacancies per lineage, only while an in-scope office of the lineage existed
    offices = json.loads((ROOT / "offices.json").read_text())["offices"]
    if (ROOT / "offices_1988.json").exists():
        offices = offices + [o for o in json.loads((ROOT / "offices_1988.json").read_text())["offices"] if o.get("from", "") < "1998-02-28"]
    exist = {}
    for o in offices:
        if o.get("in_scope") and o.get("lineage_key") in set(sp["lineage"]):
            exist.setdefault(o["lineage_key"], []).append((pd.Timestamp(o["from"]), pd.Timestamp(o["to"] or "2026-09-24")))
    lines.append("")
    lines.append("## Overlaps (>1 day) and vacancies (>1 day) within a lineage while its office existed")
    ov, gp = [], []
    for lin, g in sp.groupby("lineage"):
        if lin in ("special",):
            continue  # optional posts: vacancies are normal
        g = g.sort_values("start_ts")
        rows = list(g.itertuples())
        for a, b in zip(rows, rows[1:]):
            ae = a.end_ts if pd.notna(a.end_ts) else CUTOFF
            if b.start_ts < ae and a.person_id != b.person_id:
                ov.append(f"- {lin}: {a.name} {a.ministry} ({a.start}..{a.end}) overlaps {b.name} {b.ministry} ({b.start}..{b.end})")
            gs, ge = ae + pd.Timedelta(days=1), b.start_ts - pd.Timedelta(days=1)
            if ge >= gs:
                # days in the gap when some office of the lineage legally existed
                days = sum(max(0, (min(ge, t) - max(gs, f)).days + 1) for f, t in exist.get(lin, []))
                if days > 1:
                    gp.append(f"- {lin}: vacancy {d(gs)}..{d(ge)} ({days} days with the office in existence) between {a.name} and {b.name}")
    # leading and trailing vacancies: office existed but nobody held it before the first or after the last spell
    for lin, g in sp.groupby("lineage"):
        if lin in ("special",) or lin not in exist:
            continue
        first_exist = min(f for f, _ in exist[lin])
        last_exist = max(t for _, t in exist[lin])
        g = g.sort_values("start_ts")
        fs = g["start_ts"].min()
        le = g["end_ts"].max() if g["end_ts"].notna().all() else None
        win = pd.Timestamp("1988-02-25")
        if fs > max(first_exist, win) + pd.Timedelta(days=1):
            gp.append(f"- {lin}: leading vacancy {d(max(first_exist, win))}..{d(fs - pd.Timedelta(days=1))} before {g.iloc[0]['name']}")
        if le is not None and le < min(last_exist, CUTOFF):
            gp.append(f"- {lin}: trailing vacancy {d(le + pd.Timedelta(days=1))}..{d(min(last_exist, CUTOFF))} after {g.sort_values('end_ts').iloc[-1]['name']} (nobody in office at the cutoff)")
    lines.append(f"Overlaps: {len(ov)}")
    lines += ov
    lines.append(f"Vacancies: {len(gp)}")
    lines += gp
    # transcript bounds
    lines.append("")
    SCOPE_KEYS = sorted({o["office"].replace(" ", "").replace("(제1)", "").replace("(제2)", "") for o in offices if o.get("in_scope")} | {"총리", "특임"})
    SCOPE_KEYS = [k.replace("부", "") if k.endswith("부") else k for k in SCOPE_KEYS]
    tr = pd.read_csv(ROOT / "inputs" / "minister_role_meetings.csv", dtype=str)
    tr = tr[tr["role"].isin(["minister", "prime_minister"]) & tr["hearing_type"].isin(VALID_HTYPES)].copy()
    tr["date"] = pd.to_datetime(tr["date"], errors="coerce")
    tr["pname"] = tr["person_name"].fillna("")
    outside = []
    for (nm_, aff), g in tr.groupby(["pname", "affiliation_raw"]):
        if not nm_:
            continue
        s = sp[sp["name"] == nm_]
        if s.empty:
            continue
        affn = aff.replace(" ", "") if isinstance(aff, str) else ""
        if not any(k in affn for k in SCOPE_KEYS) or any(k in affn for k in NOT_MINISTER):
            continue  # affiliation is not an in-scope cabinet post (e.g. 국무총리실장)
        s2 = s
        for _, row in g.iterrows():
            ok = ((s2["start_ts"] <= row["date"]) & (s2["end_ts"].fillna(CUTOFF) >= row["date"])).any()
            if not ok:
                outside.append((nm_, aff, row["date"], row["meeting_id"], row["hearing_type"]))
    lines.append(f"## Transcript appearances as minister outside any spell of that person (valid hearing types): {len(outside)}")
    for o in outside[:300]:
        lines.append(f"- {o[0]} [{o[1]}] {d(o[2])} meeting {o[3]} ({o[4]})")
    # nominations
    lines.append("")
    if len(nm):
        un = nm[(nm["outcome"] == "appointed") & (nm["spell_id"].isna())]
        lines.append(f"## Appointed nominations without a linked spell: {len(un)}")
        for _, r in un.iterrows():
            lines.append(f"- {r['nominee']} {r['office_title']} {r.get('nomination_date')}")
    nohear = pan[(pan["row_start"] >= pd.Timestamp("2005-07-28")) & (~pan["holdover"].astype(bool)) & (~pan["reorg_continuation"].fillna(False).astype(bool)) & (~pan["confirmation_hearing"].astype(bool))]
    lines.append(f"## Non-holdover rows starting after 2005-07-28 without a hearing: {len(nohear)}")
    for _, r in nohear.iterrows():
        lines.append(f"- {r['name']} {r['ministry']} {d(r['row_start'])} ({r['lineage']})")
    # NA match quality
    lines.append("")
    lines.append("## NA member linkage")
    lines.append(persons["na_match_method"].value_counts().to_markdown())
    (OUT / "validation.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:40]))


if __name__ == "__main__":
    main()
