"""Harvest 국무위원/국무총리 hearing requests (인사청문요청안) and PM consent motions (임명동의안)
from the National Assembly bill system likms.assembly.go.kr, terms 15-22, with detail pages.

Search via tools/src.likms_search (no key), detail pages via Playwright (likms_bill_detail).
Outputs likms_cabinet_bills.csv (one row per bill) and likms/<bill_id>.txt (rendered detail text).
"""
import json, re, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import src

HERE = Path(__file__).resolve().parent
DET = HERE / "likms"
KEEP = re.compile(r"국무위원|국무총리")

def main():
    ages = [int(a) for a in sys.argv[1:]] or list(range(15, 23))
    out_csv = HERE / ("likms_cabinet_bills.csv" if not sys.argv[1:] else f"likms_cabinet_bills_{min(ages)}_{max(ages)}.csv")
    bills = {}
    for age in ages:
        for q in ["국무위원후보자", "국무위원", "국무총리", "인사청문요청안", "임명동의"]:
            try:
                res = src.likms_search(q, age)
            except Exception as e:
                print("search error", age, q, e, flush=True)
                continue
            for r in res:
                if KEEP.search(r["title"]) and ("청문" in r["title"] or "임명동의" in r["title"] or "후보자" in r["title"]):
                    r["age"] = age
                    bills.setdefault(r["bill_id"], r)
            print(age, q, len(res), "kept so far", len(bills), flush=True)
    rows = []
    for i, (bid, r) in enumerate(sorted(bills.items(), key=lambda kv: kv[1]["propose_date"])):
        txtf = DET / f"{bid}.txt"
        if txtf.exists():
            d = json.loads((DET / f"{bid}.json").read_text())
        else:
            try:
                det = src.likms_bill_detail(bid)
            except Exception as e:
                print("detail error", bid, e, flush=True)
                rows.append({**r, "detail_error": str(e)})
                continue
            d = {"stages": det["stages"], "fetched_at": det["fetched_at"]}
            txtf.write_text(det["text"], encoding="utf-8")
            (DET / f"{bid}.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        rows.append({**r, "stage_received": d["stages"].get("접수"), "stage_committee": d["stages"].get("위원회심사"),
                     "stage_plenary": d["stages"].get("본회의"), "detail_fetched_at": d["fetched_at"]})
        if i % 25 == 0:
            print("detail", i, len(bills), flush=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print("TOTAL", len(rows), flush=True)
    if not sys.argv[1:]:
        (HERE / "LIKMS_DONE").write_text(src.now())

if __name__ == "__main__":
    main()
