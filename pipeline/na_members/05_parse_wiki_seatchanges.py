"""Parse the 의석 변동 tables of the Korean Wikipedia pages 대한민국 제N대 국회 (N=15..22).

Each table row is (날짜, 이름, 소속정당, 선거구, 사유, 증감, 의석수) with rowspans. Output:
work/wiki_seat_changes.csv with one row per (date, name) event and the reason text, kept only
when the reason concerns a seat (resignation, death, loss of seat, succession, by-election).
"""

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "wiki"
WORK = ROOT / "work"
LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
SEAT_RE = re.compile(r"의원직|사망|별세|서거|승계|당선|무효|사퇴|사직|퇴직|상실|궐원|취임|선출")


def strip_markup(s):
    s = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", s, flags=re.S)
    s = LINK_RE.sub(lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r"<br\s*/?>", " / ", s, flags=re.I)
    s = re.sub(r"'''?|\{\{[^}]*\}\}", "", s)
    return re.sub(r"\s+", " ", s).strip()


def cell_attrs(raw):
    m = re.match(r'^\s*((?:(?:rowspan|colspan|style|class|align)\s*=\s*"?[^"|]*"?\s*)+)\|(?!\|)', raw)
    if not m:
        return 1, raw.strip()
    rs = re.search(r'rowspan\s*=\s*"?(\d+)', m.group(1))
    return (int(rs.group(1)) if rs else 1), raw[m.end():].strip()


def parse_date(s):
    s = strip_markup(s)
    m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return s


def parse_term(term):
    d = json.loads((SRC / f"대한민국_제{term}대_국회.json").read_text(encoding="utf-8"))
    w = d["parse"]["wikitext"]["*"]
    i = w.find("== 의석 변동")
    j = w.find("\n== ", i + 5)
    block = w[i:j if j > 0 else None]
    rows, row = [], None
    for ln in block.split("\n"):
        if ln.startswith("{|"):
            row = None
            continue
        if ln.startswith("|}"):
            if row:
                rows.append(row)
            row = None
            continue
        if ln.startswith("|-"):
            if row:
                rows.append(row)
            row = []
            continue
        if row is None:
            continue
        if ln.startswith("!"):
            row = None  # header row
            continue
        if ln.startswith("|"):
            body = ln[1:]
            # handle an empty leading cell written as '| |'
            for c in body.split("||"):
                row.append(cell_attrs(c))
        elif row:
            rs, txt = row[-1]
            row[-1] = (rs, txt + "\n" + ln)
    out = []
    ncol = 7
    pending = {}
    for r in rows:
        grid = [None] * ncol
        for col, (rem, txt) in pending.items():
            grid[col] = txt
        col = 0
        for rs, txt in r:
            while col < ncol and grid[col] is not None:
                col += 1
            if col >= ncol:
                break
            grid[col] = txt
            if rs > 1:
                pending[col] = (rs, txt)
            col += 1
        for c in list(pending):
            rem, txt = pending[c]
            if rem - 1 <= 0:
                del pending[c]
            else:
                pending[c] = (rem - 1, txt)
        g = [x if x is not None else "" for x in grid]
        reason = strip_markup(g[4])
        name = strip_markup(g[1])
        if not name or not SEAT_RE.search(reason):
            continue
        out.append({"term": term, "wiki_revid": d["parse"]["revid"], "date": parse_date(g[0]),
                    "name": name, "party": strip_markup(g[2]), "district": strip_markup(g[3]),
                    "reason": reason})
    return out


def main():
    allr = []
    for t in range(15, 23):
        r = parse_term(t)
        print(t, len(r))
        allr += r
    pd.DataFrame(allr).to_csv(WORK / "wiki_seat_changes.csv", index=False)


if __name__ == "__main__":
    main()
