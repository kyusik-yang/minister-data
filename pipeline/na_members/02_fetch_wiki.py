"""Fetch Korean Wikipedia wikitext snapshots used to build the member table.

Saves the full API JSON (title, revid, wikitext) under sources/wiki/ and appends
an access log (UTC timestamp, title, revid, URL) to sources/wiki/access_log.tsv.

Usage:
    python3 scripts/02_fetch_wiki.py "대한민국 제15대 국회의원 목록" [more titles ...]
"""

import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import httpx

API = "https://ko.wikipedia.org/w/api.php"
UA = "kyusik-research/0.1 (kyusik.yang@nyu.edu)"
OUT = Path(__file__).resolve().parent.parent / "sources" / "wiki"


def now():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip()


def safe(title):
    return title.replace("/", "_").replace(" ", "_")


def fetch(title):
    params = {"action": "parse", "page": title, "prop": "wikitext|revid",
              "format": "json", "redirects": 1}
    r = httpx.get(API, params=params, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return r.json()


def main(titles):
    OUT.mkdir(parents=True, exist_ok=True)
    log = OUT / "access_log.tsv"
    if not log.exists():
        log.write_text("accessed_utc\trequested_title\tresolved_title\trevid\turl\tfile\n", encoding="utf-8")
    for t in titles:
        ts = now()
        d = fetch(t)
        if "parse" not in d:
            print("MISSING", t, d.get("error", {}).get("info"))
            with log.open("a", encoding="utf-8") as f:
                f.write(f"{ts}\t{t}\tMISSING\t\t\t\n")
            time.sleep(0.8)
            continue
        p = d["parse"]
        fn = OUT / f"{safe(p['title'])}.json"
        fn.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        url = "https://ko.wikipedia.org/w/index.php?title=" + urllib.parse.quote(p["title"].replace(" ", "_")) + f"&oldid={p['revid']}"
        with log.open("a", encoding="utf-8") as f:
            f.write(f"{ts}\t{t}\t{p['title']}\t{p['revid']}\t{url}\t{fn.name}\n")
        print(ts, p["title"], p["revid"], len(p["wikitext"]["*"]))
        time.sleep(0.8)


if __name__ == "__main__":
    main(sys.argv[1:])
