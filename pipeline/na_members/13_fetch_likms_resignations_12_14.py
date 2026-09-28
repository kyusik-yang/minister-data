"""NA bill records of 국회의원(○○○)사직의건 for terms 12-14 from likms.assembly.go.kr.

Search: tools/src.likms_search("사직", age) for age 12, 13, 14 (no key). Only titles that contain
국회의원( are kept (committee-chair resignations are dropped). Each bill's detail page is rendered
with Playwright (src.likms_bill_detail) and saved with src.snapshot, plus the rendered text.

Outputs
  sources/na_bills/likms_12_14/<bill_id>.html (+ .meta.json)  raw detail page
  sources/na_bills/likms_12_14/<bill_id>.txt                   rendered text
  sources/na_bills/resignation_motions_12_14.csv               one row per bill
Resumable. Bills whose .txt exists are not fetched again.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "tools"))
import src  # noqa: E402

OUT = ROOT / "sources" / "na_bills" / "likms_12_14"


def parse_detail(text):
    flat = re.sub(r"[ \t]+", " ", text)
    m = re.search(r"의결일자\s*(\d{4}-\d{2}-\d{2})?\s*의결결과\s*([^\n]*)", flat)
    decided = m.group(1) if m and m.group(1) else ""
    result = (m.group(2).strip() if m else "")
    m2 = re.search(r"제안일자\s*(\d{4}-\d{2}-\d{2})", flat)
    plen = re.findall(r"(\d{4}-\d{2}-\d{2})\s+(\d{4}-\d{2}-\d{2})\s+(제\d+회[^\n]*?본회의)\s+([^\n]*)", flat)
    # remark lines printed under the plenary table, for example "* 經濟企劃院次官에 任命"
    notes = re.findall(r"^\*\s*(.+)$", text, flags=re.M)
    return {"propose_date_detail": m2.group(1) if m2 else "", "decided_date": decided, "result": result,
            "plenary": " | ".join(" ".join(x) for x in plen), "remark": " | ".join(n.strip() for n in notes)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bills = {}
    for age in (12, 13, 14):
        res = src.likms_search("사직", age)
        for r in res:
            if re.search(r"국회의원\s*\(", r["title"]):
                r["age"] = age
                bills.setdefault(r["bill_id"], r)
        print("search", age, len(res), "kept so far", len(bills), flush=True)
    rows = []
    for i, (bid, r) in enumerate(sorted(bills.items(), key=lambda kv: kv[1]["propose_date"])):
        txtf, metaf = OUT / f"{bid}.txt", OUT / f"{bid}.json"
        if txtf.exists() and metaf.exists():
            meta = json.loads(metaf.read_text(encoding="utf-8"))
            text = txtf.read_text(encoding="utf-8")
        else:
            try:
                det = src.likms_bill_detail(bid)
            except Exception as e:  # keep going, report the failure in the csv
                print("detail error", bid, e, flush=True)
                rows.append({**r, "detail_error": str(e)})
                continue
            src.snapshot(det["resp"], OUT, f"{bid}.html")
            text = det["text"]
            txtf.write_text(text, encoding="utf-8")
            meta = {"stages": det["stages"], "fetched_at": det["fetched_at"],
                    "url": r["detail_url"]}
            metaf.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        mname = re.search(r"국회의원\s*\(([^)]+)\)", r["title"])
        rows.append({**r, "member_name": mname.group(1).strip() if mname else "", **parse_detail(text),
                     "detail_fetched_at": meta["fetched_at"], "detail_error": ""})
        if i % 10 == 0:
            print("detail", i, len(bills), flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "sources" / "na_bills" / "resignation_motions_12_14.csv", index=False)
    print("TOTAL", len(df), df.result.value_counts().to_dict() if "result" in df else "", flush=True)


if __name__ == "__main__":
    main()
