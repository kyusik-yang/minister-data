"""Harvest every cabinet-level appointment notice in the Official Gazette (관보), 2001-01..2026-09.

Uses tools/src.py (gazette_cabinet_notices: category 19 인사 items per month, item PDFs parsed with
poppler). One JSON file per month under gazette_months/ so the run can resume. Combined output:
gazette_cabinet_notices_2001_2026.csv. The gazette has no downloadable files before 2001-01.
"""
import json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import src

OUT = Path(__file__).resolve().parent / "gazette_months"
TXT = Path(__file__).resolve().parent / "gazette_text"


def save_texts(date_from, date_to):
    """Save the full text of every 인사 item in the window (the parser misses some notices,
    so builders also grep these texts). File name: <regdate>_<ebook_no>_<toc_seq>.txt"""
    res = src.gazette_search(date_from=date_from, date_to=date_to, category=19, size=500)
    n = 0
    for it in res["items"]:
        f = TXT / f"{it['regdate']}_{it['ebook_no']}_{it['toc_seq']}.txt"
        if f.exists():
            continue
        try:
            pdf = src.gazette_item_pdf(it["toc_seq"])
            f.write_text(f"# 관보 제{it['ebook_no']}호 published {it['regdate']} subject {it['subject']} "
                         f"toc_seq {it['toc_seq']} viewer {it['viewer_url']} fetched {pdf.fetched_at}\n"
                         + src.pdf_text(pdf.content), encoding="utf-8")
            n += 1
        except Exception as e:
            print("text error", it["toc_seq"], e, flush=True)
    return n, len(res["items"])

def months(a=(2001, 1), b=(2026, 9)):
    y, m = a
    while (y, m) <= b:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)

def main():
    for y, m in months():
        f = OUT / f"{y}-{m:02d}.json"
        if f.exists():
            continue
        last = (pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
        try:
            n_txt = save_texts(f"{y}-{m:02d}-01", last)
            recs = src.gazette_cabinet_notices(f"{y}-{m:02d}-01", last)
        except Exception as e:
            print(y, m, "ERROR", e, flush=True)
            continue
        f.write_text(json.dumps({"month": f"{y}-{m:02d}", "harvested_at": src.now(), "records": recs},
                                ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(y, m, len(recs), "texts", n_txt, flush=True)
    rows = []
    for f in sorted(OUT.glob("*.json")):
        for r in json.loads(f.read_text())["records"]:
            r = dict(r)
            r["actions"] = " || ".join(r.get("actions") or [])
            r["pre"] = " || ".join(r.get("pre") or [])
            rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(Path(__file__).resolve().parent / "gazette_cabinet_notices_2001_2026.csv", index=False)
    print("TOTAL", df.shape, flush=True)
    (Path(__file__).resolve().parent / "GAZETTE_DONE").write_text(src.now())

if __name__ == "__main__":
    main()
