"""Parse the Korean Wikipedia member-list pages (대한민국 제N대 국회의원 목록, N=15..22).

Output: work/wiki_list_rows.csv, one row per person row in the district and PR tables,
with the dated events of the 비고 column split into (date, text) pairs.
"""

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "wiki"
WORK = ROOT / "work"

PARTY_RE = re.compile(r"\{\{\s*정당색(?:과 연결)?\s*\|[^}]*?정당\s*=\s*([^|}]+?)\s*(?:\|[^}]*)?\}\}")
LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
SEONSU_RE = re.compile(r"^(초선|[2-9]선|재선|1[0-9]선)$")
DATE_EVENT_RE = re.compile(r"(\d{4})\.\s*(\d{1,2})?\.?\s*(\d{1,2})?\.?\s*(.+)")


def strip_markup(s):
    s = re.sub(r"\{\{\s*글 숨김[^}]*\}\}", "", s)
    s = re.sub(r"\{\{\s*글 숨김 끝\s*\}\}", "", s)
    s = LINK_RE.sub(lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r"'''?", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", s, flags=re.S)
    return s.strip()


def cell_value(raw):
    # drop leading attributes such as rowspan="2"|
    m = re.match(r'^\s*((?:rowspan|colspan|style|class)\s*=\s*"?[^"|]*"?\s*)+\|(?!\|)', raw)
    if m:
        raw = raw[m.end():]
    return raw.strip()


def parse_events(note):
    note = re.sub(r"\{\{\s*글 숨김[^}]*\}\}|\{\{\s*글 숨김 끝\s*\}\}", "", note)
    parts = re.split(r"<br\s*/?>", note, flags=re.I)
    events = []
    for p in parts:
        p = strip_markup(p)
        if not p:
            continue
        m = re.match(r"^(\d{4})\.\s*(\d{1,2})\.\s*(?:(\d{1,2})\.)?\s*(.*)$", p)
        if m:
            y, mo, d, txt = m.groups()
            date = f"{int(y):04d}-{int(mo):02d}" + (f"-{int(d):02d}" if d else "")
            events.append((date, txt.strip()))
        else:
            events.append(("", p))
    return events


def split_cells(line, marker):
    body = line[1:]
    sep = "!!" if marker == "!" else "||"
    return [c for c in body.split(sep)]


def cell_attrs(raw):
    m = re.match(r'^\s*((?:(?:rowspan|colspan|style|class|align)\s*=\s*"?[^"|]*"?\s*)+)\|(?!\|)', raw)
    if not m:
        return 1, 1, raw.strip()
    attrs = m.group(1)
    rs = re.search(r'rowspan\s*=\s*"?(\d+)', attrs)
    cs = re.search(r'colspan\s*=\s*"?(\d+)', attrs)
    return (int(rs.group(1)) if rs else 1, int(cs.group(1)) if cs else 1, raw[m.end():].strip())


def parse_page(term):
    fn = SRC / f"대한민국_제{term}대_국회의원_목록.json"
    d = json.loads(fn.read_text(encoding="utf-8"))
    w = d["parse"]["wikitext"]["*"]
    revid = d["parse"]["revid"]
    section = subsection = None
    tables = []   # list of (section, subsection, rows) ; rows = list of list of raw cells (rs, cs, text)
    cur = None
    row = None
    for ln in w.split("\n"):
        h2 = re.match(r"^==\s*([^=].*?)\s*==\s*$", ln)
        h3 = re.match(r"^===\s*(.*?)\s*===\s*$", ln)
        if h2:
            t = h2.group(1)
            section = "district" if t.startswith("지역구") else ("pr" if (t.startswith("비례대표") or t.startswith("전국구")) else None)
            continue
        if h3:
            subsection = h3.group(1)
            continue
        if section is None:
            continue
        if ln.startswith("{|"):
            cur = {"section": section, "subsection": subsection, "rows": []}
            row = None
            continue
        if cur is None:
            continue
        if ln.startswith("|}"):
            if row:
                cur["rows"].append(row)
            tables.append(cur)
            cur = None
            row = None
            continue
        if ln.startswith("|-"):
            if row:
                cur["rows"].append(row)
            row = []
            continue
        if row is None:
            continue
        if ln.startswith("!") or ln.startswith("|"):
            for c in split_cells(ln, ln[0]):
                rs, cs, txt = cell_attrs(c)
                row.append({"rs": rs, "cs": cs, "txt": txt, "hdr": ln[0] == "!"})
        elif row:
            row[-1]["txt"] += "\n" + ln
    out = []
    for tb in tables:
        ncol = 7 if tb["section"] == "district" else 6
        pending = {}  # col -> (remaining, cell)
        for r in tb["rows"]:
            # header row of the table
            if r and all(c["hdr"] for c in r) and len(r) >= 4:
                continue
            if any("공석" in c["txt"] for c in r) and len(r) <= 2:
                # vacancy line: it still consumes the district rowspan
                for col in list(pending):
                    rem, cell = pending[col]
                    pending[col] = (rem - 1, cell)
                    if rem - 1 <= 0:
                        del pending[col]
                continue
            grid = [None] * ncol
            for col, (rem, cell) in list(pending.items()):
                grid[col] = cell
            it = iter(r)
            col = 0
            for cell in r:
                while col < ncol and grid[col] is not None:
                    col += 1
                if col >= ncol:
                    break
                grid[col] = cell
                if cell["rs"] > 1:
                    pending[col] = (cell["rs"], cell)
                col += 1
            # decrement pending
            for c in list(pending):
                rem, cell = pending[c]
                if rem - 1 <= 0:
                    del pending[c]
                else:
                    pending[c] = (rem - 1, cell)
            def g(i):
                return grid[i]["txt"] if i < ncol and grid[i] is not None else ""
            dval, name_cell = g(0), g(1)
            pe, pn = g(2), g(3)
            if tb["section"] == "district":
                seonsu, note = g(5), g(6)
            else:
                seonsu, note = g(4), g(5)
            lk = LINK_RE.search(name_cell)
            pem, pnm = PARTY_RE.search(pe), PARTY_RE.search(pn)
            dlk = LINK_RE.search(dval or "")
            out.append({
                "term": term,
                "wiki_revid": revid,
                "section": tb["section"],
                "subsection": tb["subsection"],
                "district_or_rank": strip_markup(dval),
                "district_link": dlk.group(1).strip() if dlk else "",
                "rank_italic": bool(re.search(r"''\s*\d+번\s*''", dval or "")),
                "name": strip_markup(name_cell),
                "name_link": lk.group(1).strip() if lk else "",
                "party_elected_raw": pem.group(1).strip() if pem else "",
                "party_end_raw": pnm.group(1).strip() if pnm else "",
                "seonsu": strip_markup(seonsu),
                "events": json.dumps(parse_events(note) if note else [], ensure_ascii=False),
                "note_raw": strip_markup(re.sub(r"<br\s*/?>", " | ", note)),
            })
    return out


def main():
    WORK.mkdir(exist_ok=True)
    allrows = []
    for t in range(15, 23):
        rows = parse_page(t)
        allrows += rows
        df = pd.DataFrame(rows)
        print(t, len(rows), df.section.value_counts().to_dict(),
              "no-name", (df.name == "").sum(), "no-party", (df.party_elected_raw == "").sum(),
              "bad-seonsu", (~df.seonsu.str.match(r"^(초선|재선|\d*선)$")).sum())
    pd.DataFrame(allrows).to_csv(WORK / "wiki_list_rows.csv", index=False)


if __name__ == "__main__":
    main()
