"""Export compact JSON for the dashboard and inline it into dashboard/index.html.

Reads build/out/*.csv (after build_panel.py and finalize.py) and writes
  dashboard/data.json      compact data (also useful on its own)
  dashboard/index.html     template.html with the data inlined
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "out"
DASH = ROOT.parent / "dashboard"
CUTOFF = "2026-09-24"

LINEAGES = [
    # key, Korean label, English label, group
    ("pm", "국무총리", "Prime Minister", "총리"),
    ("epb", "경제기획원", "Economic Planning Board", "경제"),
    ("finance", "재무·재정경제", "Finance", "경제"),
    ("budget", "기획예산", "Budget", "경제"),
    ("unification", "통일", "Unification", "외교안보"),
    ("foreign", "외교", "Foreign Affairs", "외교안보"),
    ("defense", "국방", "Defense", "외교안보"),
    ("justice", "법무", "Justice", "외교안보"),
    ("interior", "내무·행정안전", "Interior and Safety", "행정"),
    ("general_affairs", "총무처", "Government Administration", "행정"),
    ("safety", "국민안전처", "Public Safety", "행정"),
    ("education", "교육", "Education", "사회"),
    ("culture", "문화", "Culture", "사회"),
    ("public_info", "공보처", "Public Information", "사회"),
    ("sports", "체육·청소년", "Sports and Youth", "사회"),
    ("health", "보건복지", "Health and Welfare", "사회"),
    ("labor", "노동", "Labor", "사회"),
    ("gender", "여성·가족", "Gender Equality and Family", "사회"),
    ("environment", "환경", "Environment", "사회"),
    ("industry", "상공·산업", "Trade and Industry", "산업"),
    ("energy", "동력자원", "Energy and Resources", "산업"),
    ("science", "과학기술", "Science and ICT", "산업"),
    ("ict", "체신·정보통신", "Communications", "산업"),
    ("agriculture", "농림", "Agriculture", "산업"),
    ("land", "건설·국토", "Land and Transport", "산업"),
    ("transport", "교통", "Transportation", "산업"),
    ("oceans", "해양수산", "Oceans and Fisheries", "산업"),
    ("sme", "중소벤처기업", "SMEs and Startups", "산업"),
    ("veterans", "국가보훈", "Patriots and Veterans", "기타"),
    ("special", "정무·특임", "Minister without Portfolio", "기타"),
]
ADMINS = [
    ("노태우", "Roh Tae-woo", "1988-02-25", "1993-02-24", "Conservative"),
    ("김영삼", "Kim Young-sam", "1993-02-25", "1998-02-24", "Conservative"),
    ("김대중", "Kim Dae-jung", "1998-02-25", "2003-02-24", "Progressive"),
    ("노무현", "Roh Moo-hyun", "2003-02-25", "2008-02-24", "Progressive"),
    ("이명박", "Lee Myung-bak", "2008-02-25", "2013-02-24", "Conservative"),
    ("박근혜", "Park Geun-hye", "2013-02-25", "2017-05-09", "Conservative"),
    ("문재인", "Moon Jae-in", "2017-05-10", "2022-05-09", "Progressive"),
    ("윤석열", "Yoon Suk Yeol", "2022-05-10", "2025-06-03", "Conservative"),
    ("이재명", "Lee Jae-myung", "2025-06-04", CUTOFF, "Progressive"),
]


def first_url(s):
    if not isinstance(s, str):
        return None
    m = re.search(r"https?://[^\s)\]]+", s)
    return m.group(0).rstrip(".,;") if m else None


def short_src(s):
    if not isinstance(s, str) or not s:
        return None
    first = re.sub(r"/(?:Users|Volumes|private)/\S*", "", s.split(" ;; ")[0])
    first = re.sub(r"\(accessed[^)]*\)", "", first)
    first = re.sub(r"https?://\S+", "", first)
    return re.sub(r"\s+", " ", first).strip()[:140] or None


def nz(x):
    if x is None:
        return None
    if isinstance(x, float) and pd.isna(x):
        return None
    return x


def main():
    DASH.mkdir(parents=True, exist_ok=True)
    sp = pd.read_csv(OUT / "spells.csv", dtype=str)
    pan = pd.read_csv(OUT / "minister_panel_comprehensive.csv", dtype=str)
    nm = pd.read_csv(OUT / "nominations.csv", dtype=str)
    pe = pd.read_csv(OUT / "persons.csv", dtype=str)

    # spell-level dual office: from the admin-split rows (first row decides "at appointment")
    pan["_s"] = pan["start"]
    first_row = pan.sort_values("_s").groupby("spell_id").first()
    any_dual = pan.groupby("spell_id")["dual_office"].apply(lambda s: (s == "True").any())
    rows = []
    for _, r in sp.iterrows():
        fr = first_row.loc[r["spell_id"]] if r["spell_id"] in first_row.index else None
        start = r["start"]
        end = nz(r["end"])
        e = end or CUTOFF
        days = (pd.Timestamp(e) - pd.Timestamp(start)).days + 1
        dual_start = fr is not None and fr["dual_office"] == "True"
        rows.append({
            "id": r["spell_id"], "pid": r["person_id"], "n": r["name"], "h": nz(r.get("name_hanja")),
            "en": nz(r.get("name_en")), "l": r["lineage"], "m": r["ministry"], "t": nz(r.get("office_title")),
            "dpm": r.get("deputy_pm") == "True", "s": start, "e": end, "d": int(days),
            "ap": nz(r.get("appointing_president")), "er": nz(r.get("end_reason")),
            "reorg": r.get("reorg_continuation") == "True", "pms": nz(r.get("pm_status")),
            "dual": bool(dual_start), "dualAny": bool(any_dual.get(r["spell_id"], False)),
            "party": nz(fr["mp_party_at_appt"]) if fr is not None and dual_start else None,
            "dist": nz(fr["mp_district"]) if fr is not None and dual_start else None,
            "term": nz(fr["assembly_num_at_appt"]) if fr is not None and dual_start else None,
            "fmp": fr is not None and fr.get("former_mp") == "True",
            "conf": nz(r.get("start_confidence")), "econf": nz(r.get("end_confidence")),
            "ver": nz(r.get("verification_status")) or ("unverified" if r.get("roster_status") == "unverified" else None), "nom": nz(r.get("nomination_id")),
            "src": short_src(r.get("start_sources")), "url": first_url(r.get("start_sources")),
            "esrc": short_src(r.get("end_sources")), "eurl": first_url(r.get("end_sources")),
        })
    noms = []
    for _, r in nm.iterrows():
        hd = [x for x in str(r.get("hearing_dates") or "").split(";") if re.match(r"\d{4}-\d{2}-\d{2}", x)]
        noms.append({"id": r["nomination_id"], "sid": nz(r.get("spell_id")), "n": r["nominee"], "l": r["lineage"],
                     "t": nz(r.get("office_title")), "nd": nz(r.get("nomination_date")), "rd": nz(r.get("request_date")),
                     "hd": hd, "rep": nz(r.get("report_adopted")), "vote": nz(r.get("na_consent_vote")),
                     "o": nz(r.get("outcome")), "od": nz(r.get("outcome_date"))})
    persons = []
    for _, r in pe.iterrows():
        persons.append({"pid": r["person_id"], "n": r["name"], "h": nz(r.get("hanja_n")), "b": nz(r.get("birth_n")),
                        "mona": nz(r.get("mona_cd")), "na": nz(r.get("na_terms_all"))})
    present = set(sp["lineage"])
    lin = [{"k": k, "ko": ko, "en": en, "g": g} for k, ko, en, g in LINEAGES if k in present]
    lin += [{"k": k, "ko": k, "en": k, "g": "기타"} for k in sorted(present - {x[0] for x in LINEAGES})]
    ver = sp["verification_status"].where(sp["verification_status"].notna(), sp["roster_status"].map({"unverified": "unverified"})).fillna("unverified").value_counts().to_dict()
    meta = {"cutoff": CUTOFF, "window_start": "1988-02-25", "n_spells": len(sp), "n_rows": len(pan),
            "n_persons": len(pe), "n_noms": len(nm), "verification": ver}
    audit_f = ROOT / "blind_audit" / "summary.json"
    if audit_f.exists():
        meta["audit"] = json.loads(audit_f.read_text())
    data = {"meta": meta, "admins": [{"k": a, "en": e, "s": s, "e": t, "ideo": i} for a, e, s, t, i in ADMINS],
            "lineages": lin, "spells": rows, "noms": noms, "persons": persons}
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (DASH / "data.json").write_text(js, encoding="utf-8")
    tpl = (DASH / "template.html").read_text(encoding="utf-8")
    html = tpl.replace("/*__DATA__*/null", js.replace("</", "<\\/"))
    (DASH / "index.html").write_text(html, encoding="utf-8")
    print("spells", len(rows), "noms", len(noms), "persons", len(persons), "bytes", len(html.encode()))


if __name__ == "__main__":
    main()
