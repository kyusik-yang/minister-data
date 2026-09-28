"""Save a raw HTML snapshot of a web page used for a manual date check.

Usage: python3 scripts/07_snapshot_url.py <label> <url> [grep-pattern]
Writes sources/news/<label>.html and appends (UTC time, label, url, file, http status) to
sources/news/access_log.tsv. With a pattern, prints matching text snippets from the page.
"""
import re
import subprocess
import sys
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parent.parent / "sources" / "news"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) kyusik-research/0.1 (kyusik.yang@nyu.edu)"


def main():
    label, url = sys.argv[1], sys.argv[2]
    pat = sys.argv[3] if len(sys.argv) > 3 else None
    OUT.mkdir(parents=True, exist_ok=True)
    ts = subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip()
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=60, follow_redirects=True)
    raw = r.content
    enc = r.encoding or "utf-8"
    m = re.search(rb'charset=["\']?([A-Za-z0-9_-]+)', raw[:3000])
    if m:
        enc = m.group(1).decode()
    try:
        txt = raw.decode(enc, errors="replace")
    except LookupError:
        txt = raw.decode("utf-8", errors="replace")
    fn = OUT / f"{label}.html"
    fn.write_bytes(raw)
    log = OUT / "access_log.tsv"
    if not log.exists():
        log.write_text("accessed_utc\tlabel\turl\tfile\thttp_status\n", encoding="utf-8")
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{label}\t{url}\t{fn.name}\t{r.status_code}\n")
    print(ts, r.status_code, len(raw), "bytes", fn.name)
    if pat:
        plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", txt, flags=re.S)
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"&nbsp;|&#160;", " ", plain)
        plain = re.sub(r"\s+", " ", plain)
        for mm in re.finditer(pat, plain):
            a, b = max(0, mm.start() - 160), min(len(plain), mm.end() + 160)
            print("...", plain[a:b], "...")


if __name__ == "__main__":
    main()
