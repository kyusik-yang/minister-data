"""Write a versioned release candidate from build/out/ into _rebuild/release/<version>/.

Files (new names, the old data/minister_panel_comprehensive.csv is never touched):
  spells.csv            one row per spell (kr-hearings-data interface columns first)
  panel_admin.csv       one row per spell x administration (v1-compatible column names kept)
  nominations.csv, persons.csv, acting_heads.csv, offices.csv
  ministry_alias.csv, person_name_variants.csv, spell_disputes.csv   (interface tables)
  MANIFEST.json         version, build time, row counts and sha256 of every file
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "out"
VERSION = sys.argv[1] if len(sys.argv) > 1 else "v2.0.0-rc1"
REL = ROOT / "release" / VERSION
CUTOFF = "2026-09-24"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    REL.mkdir(parents=True, exist_ok=True)
    sp = pd.read_csv(OUT / "spells.csv", dtype=str)
    pan = pd.read_csv(OUT / "minister_panel_comprehensive.csv", dtype=str)
    pe = pd.read_csv(OUT / "persons.csv", dtype=str)

    # spell-level dual office and suspension from the admin-split rows
    pan["_dual"] = pan["dual_office"] == "True"
    dual = pan[pan["_dual"]].groupby("spell_id").agg(dual_office_start=("dual_office_start", "min"),
                                                     dual_office_end=("dual_office_end", "max"),
                                                     mp_assembly_term=("assembly_num_at_appt", "first"),
                                                     mp_party_at_appt=("mp_party_at_appt", "first"),
                                                     mp_district=("mp_district", "first"))
    sus = pan.dropna(subset=["suspended_from"]).groupby("spell_id").agg(suspended_from=("suspended_from", "first"),
                                                                         suspended_to=("suspended_to", "first"))
    mona = dict(zip(pe["person_id"], pe["mona_cd"]))
    s = sp.copy()
    s["mona_cd"] = s["person_id"].map(mona)
    s = s.join(dual, on="spell_id").join(sus, on="spell_id")
    s["dual_office_at_start"] = s["spell_id"].isin(pan[pan["_dual"] & (pan["start"] == pan["spell_start"])]["spell_id"])
    s["disputed"] = s["verification_status"] == "disputed"
    dparts = [pd.read_csv(f, dtype=str) for f in [ROOT / "interface" / "spell_disputes.csv", ROOT / "interface" / "spell_disputes_1988.csv"] if f.exists()]
    dsp = pd.concat(dparts, ignore_index=True) if dparts else pd.DataFrame(columns=["name", "ministry", "spell_start", "field", "alternative_value"])
    alt = {}
    for _, r in dsp.iterrows():
        k = (r["name"], r["ministry"], r["spell_start"])
        alt.setdefault(k, []).append(f"{r['field']}={r['alternative_value']}")
    s["alternative_dates"] = [";".join(alt.get((r["name"], r["ministry"], r["start"]), [])) for _, r in s.iterrows()]
    s = s.rename(columns={"start": "spell_start", "end": "spell_end"})
    first = ["spell_id", "appointment_id", "person_id", "name", "name_hanja", "mona_cd", "lineage", "ministry", "office_title",
             "deputy_pm", "pm_status", "pm_acting_until", "spell_start", "spell_end", "suspended_from", "suspended_to",
             "dual_office_at_start", "dual_office_start", "dual_office_end", "mp_assembly_term", "mp_party_at_appt", "mp_district",
             "disputed", "alternative_dates", "start_confidence", "end_confidence", "verification_status"]
    rest = [c for c in s.columns if c not in first and c not in ("roster_status",)]
    s[first + rest].to_csv(REL / "spells.csv", index=False)

    pan.drop(columns=["_dual"]).to_csv(REL / "panel_admin.csv", index=False)
    pd.read_csv(OUT / "nominations.csv", dtype=str).to_csv(REL / "nominations.csv", index=False)
    pd.read_csv(OUT / "persons.csv", dtype=str).rename(columns={"hanja_n": "name_hanja", "birth_n": "birth_date", "na_terms_all": "na_terms"}).to_csv(REL / "persons.csv", index=False)
    ah = pd.read_csv(OUT / "acting_heads.csv", dtype=str)
    if "note" in ah.columns:
        ah["notes"] = ah["notes"].fillna("").str.cat(ah["note"].fillna(""), sep=" ").str.strip().replace("", None)
        ah = ah.drop(columns=["note"])
    ah.to_csv(REL / "acting_heads.csv", index=False)
    offs = []
    for fn in ["offices.json", "offices_1988.json"]:
        d = json.loads((ROOT / fn).read_text())
        for o in d["offices"]:
            if fn == "offices_1988.json" and o.get("from", "") >= "1998-02-28":
                continue
            offs.append({"office": o.get("office"), "lineage": o.get("lineage_key"), "from": o.get("from"), "to": o.get("to"),
                         "is_kukmuwiwon": o.get("is_kukmuwiwon"), "in_scope": o.get("in_scope"),
                         "deputy_pm_title": json.dumps(o.get("deputy_pm_title"), ensure_ascii=False) if o.get("deputy_pm_title") else "",
                         "legal_basis": "; ".join(f"{b.get('law_no', '')} ({b.get('effective', '')})" for b in (o.get("legal_basis") or []) if isinstance(b, dict)),
                         "source_inventory": fn})
    pd.DataFrame(offs).drop_duplicates(subset=["office", "from"]).sort_values(["from", "office"]).to_csv(REL / "offices.csv", index=False)
    dsp.to_csv(REL / "spell_disputes.csv", index=False)
    for f in ["ministry_alias.csv", "person_name_variants.csv", "lineage_family_crosswalk.csv"]:
        src = ROOT / "interface" / f
        if src.exists():
            (REL / f).write_bytes(src.read_bytes())
    built = subprocess.check_output(["date", "+%Y-%m-%dT%H:%M:%S%z"]).decode().strip()
    files = {}
    for p in sorted(REL.glob("*.csv")):
        files[p.name] = {"sha256": sha256(p), "rows": int(len(pd.read_csv(p, dtype=str))), "bytes": p.stat().st_size}
    linked = json.loads((ROOT / "build" / "linked_datasets.json").read_text()) if (ROOT / "build" / "linked_datasets.json").exists() else {}
    manifest = {"dataset": "minister-data (Korean cabinet ministers)", "version": VERSION, "built_at": built, "linked_datasets": linked,
                "window": ["1988-02-25", CUTOFF], "status": "release candidate, not yet published in the repository",
                "files": files}
    (REL / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v["rows"] for k, v in files.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
