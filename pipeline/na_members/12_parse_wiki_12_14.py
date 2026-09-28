"""Parse the Korean Wikipedia pages for terms 12-14 with the parsers of scripts 04 and 05.

Reuses parse_page() of 04_parse_wiki_lists.py (member lists) and parse_term() of
05_parse_wiki_seatchanges.py (의석 변동 tables) without changing them, and writes separate
intermediates so that the 15-22 intermediates stay untouched:
  work/wiki_list_rows_12_14.csv
  work/wiki_seat_changes_12_14.csv
"""

import importlib.util
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
WORK = HERE.parent / "work"


def load(fn, name):
    spec = importlib.util.spec_from_file_location(name, HERE / fn)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    p04 = load("04_parse_wiki_lists.py", "p04")
    p05 = load("05_parse_wiki_seatchanges.py", "p05")
    rows, sc = [], []
    for t in (12, 13, 14):
        r = p04.parse_page(t)
        df = pd.DataFrame(r)
        print("list", t, len(r), df.section.value_counts().to_dict(),
              "no-name", (df.name == "").sum(), "no-party", (df.party_elected_raw == "").sum())
        rows += r
        s = p05.parse_term(t)
        print("seat changes", t, len(s))
        sc += s
    pd.DataFrame(rows).to_csv(WORK / "wiki_list_rows_12_14.csv", index=False)
    pd.DataFrame(sc).to_csv(WORK / "wiki_seat_changes_12_14.csv", index=False)


if __name__ == "__main__":
    main()
