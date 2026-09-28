"""Compare the old release (data/minister_panel_comprehensive.csv at commit afdae91) with the rebuilt panel.

Every old row is matched to the new row with the same name, ministry and administration
(falling back to name + administration, then name only) and classified. Outputs:
  build/out/diff_old_rows.csv   one row per old row with match status and field differences
  build/out/diff_new_only.csv   rebuilt rows with no counterpart in the old release
  build/out/diff_summary.md     counts by error type
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OUT = ROOT / "build" / "out"


def main():
    old = pd.read_csv(REPO / "data" / "minister_panel_comprehensive.csv", dtype=str).fillna("")
    new = pd.read_csv(OUT / "minister_panel_comprehensive.csv", dtype=str).fillna("")
    nom = pd.read_csv(OUT / "nominations.csv", dtype=str).fillna("") if (OUT / "nominations.csv").exists() else pd.DataFrame()
    used = set()
    recs = []
    for i, o in old.iterrows():
        c = new[(new["name"] == o["name"]) & (new["ministry"] == o["ministry"]) & (new["admin"] == o["admin"])]
        how = "name+ministry+admin"
        if c.empty:
            c = new[(new["name"] == o["name"]) & (new["admin"] == o["admin"])]
            how = "name+admin"
        if c.empty:
            c = new[new["name"] == o["name"]]
            how = "name"
        c = c[~c["row_id"].isin(used)]
        r = {"old_line": i + 2, "name": o["name"], "ministry": o["ministry"], "admin": o["admin"],
             "old_start": o["start"], "old_end": o["end"], "old_dual": o["dual_office"],
             "old_confirmation_date": o["confirmation_date"]}
        if c.empty:
            n = nom[nom["nominee"] == o["name"]] if len(nom) else nom
            r["status"] = "not_a_minister_nominee_only" if len(n) and not (n["outcome"] == "appointed").any() else "no_counterpart"
            r["nomination_outcomes"] = ";".join(sorted(set(n["outcome"]))) if len(n) else ""
            recs.append(r)
            continue
        if len(c) > 1 and o["start"]:
            c = c.assign(_d=(pd.to_datetime(c["start"]) - pd.to_datetime(o["start"])).abs()).sort_values("_d")
        m = c.iloc[0]
        used.add(m["row_id"])
        r.update({"status": "matched", "match_on": how, "row_id": m["row_id"], "new_ministry": m["ministry"],
                  "new_start": m["start"], "new_end": m["end"], "new_dual": m["dual_office"],
                  "new_confirmation_date": m["confirmation_date"]})
        diffs = []
        if o["start"] != m["start"]:
            diffs.append("start")
        if o["end"] != m["end"]:
            diffs.append("end")
        if str(o["dual_office"]).lower() != str(m["dual_office"]).lower():
            diffs.append("dual_office")
        if o["confirmation_date"] != m["confirmation_date"]:
            diffs.append("confirmation_date")
        if o["ministry"] != m["ministry"]:
            diffs.append("ministry")
        r["diffs"] = ",".join(diffs)
        for f in ["start", "end"]:
            if o[f] and m[f]:
                r[f"{f}_days_off"] = (pd.Timestamp(m[f]) - pd.Timestamp(o[f])).days
        r["old_conf_eq_start"] = o["confirmation_date"] == o["start"] and o["start"] != ""
        recs.append(r)
    d = pd.DataFrame(recs)
    d.to_csv(OUT / "diff_old_rows.csv", index=False)
    new_only = new[~new["row_id"].isin(used)]
    new_only.to_csv(OUT / "diff_new_only.csv", index=False)
    lines = ["# Old release vs rebuilt panel", "",
             f"Old rows {len(old)}, new rows {len(new)}, old rows matched {int((d['status'] == 'matched').sum())}, new rows without an old counterpart {len(new_only)}", ""]
    lines.append(d["status"].value_counts().to_markdown())
    mt = d[d["status"] == "matched"]
    for f in ["start", "end", "dual_office", "confirmation_date", "ministry"]:
        lines.append(f"- matched rows with a different {f}: {int(mt['diffs'].fillna('').str.contains(f).sum())}")
    lines.append(f"- old confirmation_date equal to old start: {int(d['old_conf_eq_start'].fillna(False).sum())}")
    lines.append("")
    lines.append("## New rows by administration")
    lines.append(new_only.groupby("admin").size().to_markdown())
    (OUT / "diff_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
