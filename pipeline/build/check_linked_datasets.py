"""Check whether linked datasets have moved past the versions recorded in data/v2/MANIFEST.json.

kna: reads the version from the kna checkout (KNA_DATA points to kna/data/processed, as for the
NA-member scripts). If it differs from the recorded version, prints the rebuild steps.
"""
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
man = json.loads((REPO / "data" / "v2" / "MANIFEST.json").read_text())
linked = man.get("linked_datasets", {})
kna_data = os.environ.get("KNA_DATA")
if not kna_data:
    sys.exit("Set KNA_DATA to the kna repository's data/processed folder.")
pyproject = Path(kna_data).parents[1] / "pyproject.toml"
current = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.M).group(1)
recorded = linked.get("kna", {}).get("version")
print(f"kna recorded {recorded}, local {current}")
if current != recorded:
    print("kna changed. Rebuild steps:")
    print("  1. python3 pipeline/na_members/00_extract_kna_resignation_motions.py")
    print("  2. python3 pipeline/na_members/06_build_table.py && python3 pipeline/na_members/14_build_table_12_22.py")
    print("  3. compare seat dates and in_kna_build with the previous table (they should rarely change)")
    print("  4. python3 pipeline/build/build_panel.py && python3 pipeline/build/finalize.py, then check dual-office columns")
    print("  5. update the kna entry of linked_datasets and write a new release")
else:
    print("kna is current.")
print("kr-hearings-data:", linked.get("kr-hearings-data", {}).get("checked", "not recorded"))
