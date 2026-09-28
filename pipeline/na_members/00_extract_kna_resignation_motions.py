"""Copy the 국회의원 사직의 건 motions (NA bill records) out of the kna release (read only).

Source files: kna/data/processed/master_bills_{17..22}.parquet (kna release, set KNA_DATA to its data/processed folder)
(built by kna from the NA bill information service; coverage ends with the kna build, March 2026).
Output: sources/na_bills/resignation_motions_17_22.csv
"""
import re
from pathlib import Path
import os
import pandas as pd

KNA = Path(os.environ.get("KNA_DATA", str(Path(__file__).resolve().parents[4] / "kna" / "data" / "processed")))  # kna repo checked out next to minister-data, or set KNA_DATA
import re as _re
KNA_VERSION = _re.search(r'^version\s*=\s*"([^"]+)"', (KNA.parents[1] / "pyproject.toml").read_text(), _re.M).group(1)
OUT = Path(__file__).resolve().parent.parent / "sources" / "na_bills"
OUT.mkdir(parents=True, exist_ok=True)
rows = []
for t in range(17, 23):
    f = KNA / f"master_bills_{t}.parquet"
    df = pd.read_parquet(f)
    m = df[df.bill_nm.astype(str).str.contains(r"국회의원\s*\(.+?\)\s*사직")].copy()
    m["member_name"] = m.bill_nm.str.extract(r"국회의원\s*\((.+?)\)")[0].str.strip()
    m["kna_file"] = f.name
    m["kna_file_mtime"] = pd.Timestamp(f.stat().st_mtime, unit="s").strftime("%Y-%m-%dT%H:%M:%SZ")
    m["kna_version"] = KNA_VERSION
    rows.append(m[["age", "member_name", "bill_id", "bill_no", "bill_nm", "ppsl_dt", "proc_rslt",
                   "rgs_rsln_dt", "rgs_conf_nm", "link_url", "kna_file", "kna_file_mtime", "kna_version"]])
out = pd.concat(rows)
out.to_csv(OUT / "resignation_motions_17_22.csv", index=False)
print(len(out), out.proc_rslt.value_counts().to_dict())
