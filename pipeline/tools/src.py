"""Source toolkit for the minister-data rebuild.

Polite, cached helpers for the sources that were tested on 2026-09-24
(see ../SOURCES_TOOLKIT.md for what works and what does not).

Usage from any agent script:

    import sys; sys.path.insert(0, "<path to this tools folder>")
    import src
    hits = src.gazette_search(date_from="2022-05-10", date_to="2022-05-31", category=19)
    recs = src.gazette_cabinet_notices("2022-05-10", "2022-05-31")
    r = src.wiki_wikitext("대한민국 법무부 장관")
    src.snapshot(r, "/path/to/my/sources", "wiki_moj.json")

Design notes
- Every network call goes through fetch() (or playwright_get()). Responses are
  cached on disk under tools/cache/<host>/<sha1>.bin with a .json sidecar that
  records the URL, request body, HTTP status and the ORIGINAL access time.
  A cache hit therefore still reports when the page was really fetched.
- A cross-process throttle (fcntl lock per host) keeps all parallel agents
  together below a per-host request rate.
- snapshot() copies a cached response plus its metadata into an agent's own
  sources folder, which is what the source rules require.
"""
from __future__ import annotations

import csv
import fcntl
import hashlib
import html as _html
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode, urlparse

import requests

TOOLS_DIR = Path(__file__).resolve().parent
REBUILD_DIR = TOOLS_DIR.parent
CACHE_DIR = TOOLS_DIR / "cache"
LOCK_DIR = CACHE_DIR / "_locks"
INPUTS_DIR = REBUILD_DIR / "inputs"

BOT_UA = "kyusik-research/0.1 (kyusik.yang@nyu.edu)"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124 Safari/537.36"
)

# Minimum seconds between two requests to the same host, across all processes.
HOST_INTERVAL = {
    "ko.wikipedia.org": 0.5,
    "en.wikipedia.org": 0.5,
    "www.wikidata.org": 0.5,
    "query.wikidata.org": 1.0,
    "gwanbo.go.kr": 1.0,
    "likms.assembly.go.kr": 1.0,
    "www.korea.kr": 1.0,
    "search.naver.com": 2.0,
    "n.news.naver.com": 1.0,
    "www.bigkinds.or.kr": 2.0,
    "ars.yna.co.kr": 1.0,
    "namu.wiki": 3.0,
}
DEFAULT_INTERVAL = 0.8

# Hosts that need a browser-like User-Agent (Wikimedia wants the bot UA).
_BOT_UA_HOSTS = {"ko.wikipedia.org", "en.wikipedia.org", "www.wikidata.org", "query.wikidata.org"}

_sessions: dict[str, requests.Session] = {}


# ---------------------------------------------------------------------------
# basics: timestamps, throttle, cache, fetch, snapshot
# ---------------------------------------------------------------------------

def now() -> str:
    """Local access timestamp from the shell `date` command (ISO 8601 with offset)."""
    try:
        return subprocess.run(["date", "+%Y-%m-%dT%H:%M:%S%z"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _throttle(host: str) -> None:
    interval = HOST_INTERVAL.get(host, DEFAULT_INTERVAL)
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK_DIR / f"{host}.lock", "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            fh.seek(0)
            raw = fh.read().strip()
            last = float(raw) if raw else 0.0
            wait = last + interval - time.time()
            if wait > 0:
                time.sleep(wait)
            fh.seek(0)
            fh.truncate()
            fh.write(repr(time.time()))
            fh.flush()
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


class _LegacySSLAdapter(requests.adapters.HTTPAdapter):
    """Allows servers that need legacy TLS renegotiation (ars.yna.co.kr fails
    with UNSAFE_LEGACY_RENEGOTIATION_DISABLED under OpenSSL 3). curl works."""

    def init_poolmanager(self, *a, **kw):
        import ssl
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
        kw["ssl_context"] = ctx
        return super().init_poolmanager(*a, **kw)


_LEGACY_SSL_HOSTS = {"ars.yna.co.kr", "www.yna.co.kr"}


def _session(host: str) -> requests.Session:
    s = _sessions.get(host)
    if s is None:
        s = requests.Session()
        if host in _LEGACY_SSL_HOSTS:
            s.mount("https://", _LegacySSLAdapter())
        s.headers["User-Agent"] = BOT_UA if host in _BOT_UA_HOSTS else BROWSER_UA
        s.headers["Accept-Language"] = "ko-KR,ko;q=0.9,en;q=0.8"
        _sessions[host] = s
    return s


def _cache_key(method: str, url: str, params: Any, data: Any, json_body: Any) -> str:
    blob = json.dumps([method.upper(), url, params, data, json_body], ensure_ascii=False,
                      sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp_")
    with os.fdopen(fd, "wb") as fh:
        fh.write(payload)
    os.replace(tmp, path)


@dataclass
class Resp:
    url: str                 # requested URL (with query string)
    final_url: str
    status: int
    content: bytes
    content_type: str
    fetched_at: str          # original access time (local, from `date`)
    method: str = "GET"
    request_data: Any = None
    cache_path: str = ""
    from_cache: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        enc = "utf-8"
        m = re.search(r"charset=([\w-]+)", self.content_type or "", re.I)
        if m:
            enc = m.group(1)
        try:
            return self.content.decode(enc)
        except (LookupError, UnicodeDecodeError):
            return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text.strip())

    def meta(self) -> dict:
        return {
            "url": self.url, "final_url": self.final_url, "method": self.method,
            "request_data": self.request_data, "status": self.status,
            "content_type": self.content_type, "fetched_at": self.fetched_at,
            "sha256": hashlib.sha256(self.content).hexdigest(), "bytes": len(self.content),
            **({"extra": self.extra} if self.extra else {}),
        }


def fetch(url: str, *, method: str = "GET", params: dict | None = None, data: Any = None,
          json_body: Any = None, headers: dict | None = None, use_cache: bool = True,
          refresh: bool = False, timeout: int = 40, warmup: str | None = None,
          ok_statuses: Iterable[int] = (200,)) -> Resp:
    """HTTP request with per-host throttle and on-disk cache.

    Only responses whose status is in ok_statuses are cached. `warmup` is an URL
    fetched once per process on the same session (to obtain cookies) before the
    first real request to that host.
    """
    full_url = url + (("&" if "?" in url else "?") + urlencode(params) if params else "")
    host = urlparse(full_url).netloc
    key = _cache_key(method, full_url, None, data, json_body)
    bin_path = CACHE_DIR / host / f"{key}.bin"
    meta_path = CACHE_DIR / host / f"{key}.json"
    if use_cache and not refresh and bin_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return Resp(url=full_url, final_url=meta.get("final_url", full_url), status=meta["status"],
                    content=bin_path.read_bytes(), content_type=meta.get("content_type", ""),
                    fetched_at=meta["fetched_at"], method=method.upper(), request_data=data or json_body,
                    cache_path=str(bin_path), from_cache=True)
    s = _session(host)
    if warmup and not getattr(s, "_warmed", False):
        _throttle(host)
        try:
            s.get(warmup, timeout=timeout)
        except requests.RequestException:
            pass
        s._warmed = True  # type: ignore[attr-defined]
    _throttle(host)
    stamp = now()
    r = s.request(method.upper(), full_url, data=data, json=json_body, headers=headers or {},
                  timeout=timeout, allow_redirects=True)
    resp = Resp(url=full_url, final_url=r.url, status=r.status_code, content=r.content,
                content_type=r.headers.get("Content-Type", ""), fetched_at=stamp,
                method=method.upper(), request_data=data or json_body, cache_path=str(bin_path))
    if use_cache and r.status_code in tuple(ok_statuses):
        _atomic_write(bin_path, r.content)
        _atomic_write(meta_path, json.dumps(resp.meta(), ensure_ascii=False, indent=1).encode())
    return resp


def snapshot(resp: Resp, dest_dir: str | Path, name: str | None = None) -> Path:
    """Copy a response body into dest_dir/name and write name.meta.json beside it."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    if not name:
        name = hashlib.sha1(resp.url.encode()).hexdigest()[:12] + ".bin"
    out = dest / name
    out.write_bytes(resp.content)
    (dest / (name + ".meta.json")).write_text(json.dumps(resp.meta(), ensure_ascii=False, indent=1))
    return out


def html_to_text(s: str) -> str:
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</tr>|</li>|</h\d>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


# ---------------------------------------------------------------------------
# Playwright (JS pages, Namu Wiki, likms bill detail)
# ---------------------------------------------------------------------------

def playwright_get(url: str, *, wait_ms: int = 4000, wait_until: str = "domcontentloaded",
                   use_cache: bool = True, refresh: bool = False, timeout_ms: int = 60000) -> Resp:
    """Render a page in headless Chromium. Returns a Resp whose content is the
    rendered HTML; resp.extra['text'] holds document.body.innerText."""
    host = urlparse(url).netloc
    key = _cache_key("PW", url, None, None, None)
    bin_path = CACHE_DIR / "playwright" / host / f"{key}.html"
    meta_path = CACHE_DIR / "playwright" / host / f"{key}.json"
    if use_cache and not refresh and bin_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return Resp(url=url, final_url=meta["final_url"], status=meta["status"], content=bin_path.read_bytes(),
                    content_type="text/html; charset=utf-8", fetched_at=meta["fetched_at"], method="PW",
                    cache_path=str(bin_path), from_cache=True, extra={"text": meta.get("extra", {}).get("text", "")})
    from playwright.sync_api import sync_playwright
    _throttle(host)
    stamp = now()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(user_agent=BROWSER_UA, locale="ko-KR")
        pg = ctx.new_page()
        r = pg.goto(url, wait_until=wait_until, timeout=timeout_ms)
        pg.wait_for_timeout(wait_ms)
        content = pg.content().encode("utf-8")
        text = pg.inner_text("body")
        status = r.status if r else 0
        final = pg.url
        b.close()
    resp = Resp(url=url, final_url=final, status=status, content=content,
                content_type="text/html; charset=utf-8", fetched_at=stamp, method="PW",
                cache_path=str(bin_path), extra={"text": text})
    if use_cache and status == 200:
        _atomic_write(bin_path, content)
        _atomic_write(meta_path, json.dumps(resp.meta(), ensure_ascii=False, indent=1).encode())
    return resp


# ---------------------------------------------------------------------------
# Wikipedia / Wikidata (secondary sources)
# ---------------------------------------------------------------------------

WIKI_API = "https://{lang}.wikipedia.org/w/api.php"


def wiki_wikitext(title: str, lang: str = "ko", **kw) -> Resp:
    """Wikitext of a page (redirects followed). resp.extra has title, revid,
    permalink and wikitext. Cite the permalink (oldid), not the live title."""
    r = fetch(WIKI_API.format(lang=lang), params={"action": "parse", "page": title,
              "prop": "wikitext|revid", "redirects": 1, "format": "json", "formatversion": 2}, **kw)
    d = r.json()
    if "error" in d:
        raise KeyError(f"wiki page not found: {title}: {d['error'].get('info')}")
    p = d["parse"]
    r.extra = {"title": p["title"], "revid": p.get("revid"), "wikitext": p["wikitext"],
               "permalink": f"https://{lang}.wikipedia.org/w/index.php?oldid={p.get('revid')}"}
    return r


def wiki_search(q: str, lang: str = "ko", limit: int = 10, **kw) -> list[dict]:
    r = fetch(WIKI_API.format(lang=lang), params={"action": "query", "list": "search", "srsearch": q,
              "srlimit": limit, "format": "json", "formatversion": 2}, **kw)
    return [{"title": x["title"], "pageid": x["pageid"], "snippet": html_to_text(x.get("snippet", ""))}
            for x in r.json()["query"]["search"]]


def wiki_tables(wikitext: str) -> list[list[list[str]]]:
    """Very small wikitable parser: returns tables as lists of rows of cell strings
    (links reduced to their label, refs removed). Good enough for 역대 장관 tables;
    always eyeball rowspan cells."""
    tables = []
    for tb in re.findall(r"\{\|.*?\n\|\}", wikitext, flags=re.S):
        rows = []
        for chunk in re.split(r"\n\|-[^\n]*", tb):
            cells = []
            for line in chunk.split("\n"):
                line = line.strip()
                if not line or line.startswith("{|") or line.startswith("|}") or line.startswith("|+"):
                    continue
                if line[0] in "|!":
                    for c in re.split(r"\|\||!!", line[1:]):
                        if "|" in c and not re.search(r"\[\[[^\]]*\|", c.split("|")[0] + "|"):
                            head, _, rest = c.partition("|")
                            if "=" in head and "[[" not in head:
                                c = rest
                        cells.append(_wiki_clean(c))
            if cells:
                rows.append(cells)
        tables.append(rows)
    return tables


def _wiki_clean(s: str) -> str:
    s = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("'''", "").replace("''", "").strip()


WDQS = "https://query.wikidata.org/sparql"


def wikidata_sparql(query: str, **kw) -> list[dict]:
    r = fetch(WDQS, params={"query": query, "format": "json"},
              headers={"Accept": "application/sparql-results+json"}, **kw)
    out = []
    for b in r.json()["results"]["bindings"]:
        out.append({k: v["value"] for k, v in b.items()})
    return out


def wikidata_korean_positions(min_holders: int = 1) -> list[dict]:
    """Position items with applies-to-jurisdiction (P1001) = South Korea (Q884)
    that have at least one P39 holder. Use it to find ministry position QIDs."""
    q = """SELECT ?pos ?posLabel (COUNT(DISTINCT ?p) AS ?n) WHERE {
      ?pos wdt:P1001 wd:Q884 . ?p p:P39/ps:P39 ?pos .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "ko,en". }
    } GROUP BY ?pos ?posLabel ORDER BY DESC(?n)"""
    rows = wikidata_sparql(q)
    return [{"qid": r["pos"].rsplit("/", 1)[-1], "label": r.get("posLabel"), "n": int(r["n"])}
            for r in rows if int(r["n"]) >= min_holders]


def wikidata_position_holders(position_qid: str) -> list[dict]:
    """All P39 statements for a position with start/end qualifiers and reference URLs."""
    q = f"""SELECT ?p ?pLabel ?start ?end ?ref ?replaces ?replacedBy WHERE {{
      ?p p:P39 ?st . ?st ps:P39 wd:{position_qid} .
      OPTIONAL {{ ?st pq:P580 ?start }} OPTIONAL {{ ?st pq:P582 ?end }}
      OPTIONAL {{ ?st pq:P1365 ?replaces }} OPTIONAL {{ ?st pq:P1366 ?replacedBy }}
      OPTIONAL {{ ?st prov:wasDerivedFrom/pr:P854 ?ref }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ko,en". }}
    }} ORDER BY ?start"""
    out = []
    for r in wikidata_sparql(q):
        out.append({"qid": r["p"].rsplit("/", 1)[-1], "name": r.get("pLabel"),
                    "start": r.get("start", "")[:10], "end": r.get("end", "")[:10], "ref": r.get("ref", ""),
                    "replaces": r.get("replaces", "").rsplit("/", 1)[-1],
                    "replaced_by": r.get("replacedBy", "").rsplit("/", 1)[-1]})
    return out


# ---------------------------------------------------------------------------
# 관보 Official Gazette (gwanbo.go.kr) - tier 1, digital from 2001-01
# ---------------------------------------------------------------------------

GZ = "https://gwanbo.go.kr"
GZ_WARMUP = GZ + "/main.do"
GZ_CATEGORIES = {1: "헌법", 2: "법률", 3: "조약", 4: "대통령령", 5: "총리령", 6: "부령", 7: "훈령",
                 10: "고시", 11: "공고", 12: "국회", 13: "법원", 14: "헌법재판소", 15: "선거관리위원회",
                 16: "감사원", 17: "국가인권위원회", 18: "지방자치단체", 19: "인사", 20: "상훈", 21: "기타",
                 22: "대통령지시사항", 23: "조달관보"}


def _ymd(d: str) -> str:
    return re.sub(r"\D", "", d)[:8]


def gazette_search(keyword: str | None = None, date_from: str | None = None, date_to: str | None = None,
                   category: int | str | None = 19, subject_only: bool = False, page: int = 1,
                   size: int = 100, **kw) -> dict:
    """Search the gazette table-of-contents index (covers 2001-01 onward).

    keyword: space-separated terms (ANDed), matched against item subject and the
    indexed item text (desc). The desc match is fuzzy (tokenised), so person-name
    searches return many false hits. The reliable pattern is a DATE RANGE plus
    category=19 (인사), then read each item's PDF.
    Returns {"total": int, "by_category": {...}, "items": [...]}.
    """
    parts = []
    if keyword:
        k = " AND ".join(keyword.split())
        parts.append(f"(unstored_field_subject:({k}))" if subject_only else
                     f"(unstored_field_subject:({k}) OR unstored_field_desc:({k}))")
    if date_from or date_to:
        a = _ymd(date_from or "19480101")
        b = _ymd(date_to or "29991231")
        parts.append(f"keyword_field_regdate:[{a} TO {b}]")
    parts.append(f"keyword_category_order:({category if category else '@@ORDER_NUM'})")
    query = " AND ".join(parts)
    body = {"mode": "keyword" if keyword else "daily", "index": "gwanbo", "query": query,
            "pQuery_tmp": keyword or "", "pageNo": str(page), "listSize": str(size), "sort": ""}
    r = fetch(GZ + "/SearchRestApi.jsp", method="POST", data=body, warmup=GZ_WARMUP,
              headers={"Referer": GZ + "/user/search/searchKeyword.do"}, **kw)
    d = r.json()
    items, by_cat, total = [], {}, 0
    for c in d.get("data") or []:
        if not c.get("count"):
            continue
        by_cat[c["category_name"]] = c["count"]
        total += c["count"]
        for x in c.get("list") or []:
            items.append({
                "regdate": x.get("keyword_field_regdate"), "ebook_no": x.get("stored_ebook_no"),
                "category": x.get("stored_category_name"), "subject": x.get("stored_field_subject"),
                "organ": x.get("stored_organ_nm"), "toc_seq": x.get("stored_toc_seq"),
                "viewer_url": GZ + (x.get("stored_field_url") or ""), "file_size": x.get("stored_file_size"),
                "page": x.get("stored_page"),
            })
    return {"total": total, "by_category": by_cat, "items": items, "query": query,
            "fetched_at": r.fetched_at, "resp": r}


def gazette_issues_on(date: str, **kw) -> list[dict]:
    """Gazette issues (호) published on a date. Works for all years, but issues
    before 2001 have file_size 0 and cannot be downloaded from gwanbo.go.kr."""
    r = fetch(GZ + "/user/search/getDailyBaseInfo.do", method="POST",
              data={"searchDate": _ymd(date), "ofcttGubun": "GZT001"}, warmup=GZ_WARMUP, **kw)
    return [{"ebook_no": i["ebook_no"], "ebook_seq": i["ebook_seq"], "date": i["ebook_date"],
             "title": i["title"], "file_size": i["file_size"]} for i in (r.json().get("ofcttInfo") or [])]


def gazette_item_pdf(toc_seq: str, **kw) -> Resp:
    """PDF of one table-of-contents item (e.g. a day's 인사발령)."""
    r = fetch(GZ + "/user/common/ofcttCntntDownload.do", method="POST", data={"cntnt_seq_no": toc_seq},
              warmup=GZ_WARMUP, **kw)
    if not r.content.startswith(b"%PDF"):
        raise ValueError(f"gazette item {toc_seq}: not a PDF (status {r.status}, {len(r.content)} bytes)")
    return r


def gazette_issue_pdf(ebook_seq: str, **kw) -> Resp:
    """Whole issue PDF by ebook_seq (from gazette_issues_on). 2001-01 onward only."""
    r = fetch(GZ + "/user/common/ofcttDownload.do", method="POST",
              data={"downType": "1", "ofctt_seq_no": ebook_seq}, warmup=GZ_WARMUP, timeout=120, **kw)
    if not r.content.startswith(b"%PDF"):
        raise ValueError(f"gazette issue {ebook_seq}: not a PDF (status {r.status})")
    return r


_BB_PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
_BB_LINE = re.compile(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', re.S)
_BB_WORD = re.compile(r"<word[^>]*>(.*?)</word>", re.S)


def pdf_text(pdf: str | Path | bytes, columns: bool = True) -> str:
    """Text of a PDF via poppler (pdftotext -bbox-layout), in reading order.

    columns=True detects, page by page, whether the page is set in two columns
    (older gazette pages are, most post-2015 인사 pages are not) and then reads
    the left column top to bottom before the right one. Plain pdftotext
    interleaves the two columns. PyMuPDF fails on older gazette PDFs (missing
    KSCpc-EUC CMap), so poppler is used."""
    tmp = None
    if isinstance(pdf, (bytes, bytearray)):
        fd, tmp = tempfile.mkstemp(suffix=".pdf")
        with os.fdopen(fd, "wb") as fh:
            fh.write(pdf)
        path = tmp
    else:
        path = str(pdf)
    try:
        if not columns:
            return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
        xml = subprocess.run(["pdftotext", "-bbox-layout", path, "-"], capture_output=True, text=True).stdout
        pages_out = []
        for pw, _ph, body in _BB_PAGE.findall(xml):
            W = float(pw)
            mid = W / 2
            lines = []
            for x0, y0, x1, y1, inner in _BB_LINE.findall(body):
                words = [_html.unescape(w) for w in _BB_WORD.findall(inner)]
                lines.append((float(x0), float(y0), float(x1), float(y1), " ".join(words)))
            if not lines:
                continue
            narrow = [l for l in lines if (l[2] - l[0]) < 0.8 * W]
            crossing = [l for l in narrow if l[0] < mid - 6 and l[2] > mid + 6]
            two_col = len(narrow) >= 10 and len(crossing) / len(narrow) < 0.08

            def emit(ls):
                ls = sorted(ls, key=lambda l: (l[1], l[0]))
                rows, cur, cur_y = [], [], None
                for l in ls:
                    if cur_y is not None and abs(l[1] - cur_y) <= 2.5:
                        cur.append(l)
                    else:
                        if cur:
                            rows.append("   ".join(x[4] for x in sorted(cur, key=lambda x: x[0])))
                        cur, cur_y = [l], l[1]
                if cur:
                    rows.append("   ".join(x[4] for x in sorted(cur, key=lambda x: x[0])))
                return "\n".join(rows)

            if two_col:
                left = [l for l in lines if (l[0] + l[2]) / 2 < mid]
                right = [l for l in lines if (l[0] + l[2]) / 2 >= mid]
                pages_out.append(emit(left) + "\n" + emit(right))
            else:
                pages_out.append(emit(lines))
        return "\n\f\n".join(pages_out)
    finally:
        if tmp:
            os.unlink(tmp)


_NAME_LINE = re.compile(r"^\s*([가-힣](?:\s*[가-힣]){1,4})\s*\(\s*([一-鿿豈-﫿\s]+)\s*\)\s*$")
_DATE_LINE = re.compile(r"^\s*((?:19|20)\d{2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?\s*$")
_EFFECTIVE = re.compile(r"◉\s*((?:19|20)\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*자")
_TERM_LINE = re.compile(r"^\s*\(\s*((?:19|20)\d{2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?\s*~")
_ACTION = re.compile(r"(임함|보함|면함|위촉함|해촉함|명함|해임함|파면함)\s*$")


def parse_gazette_personnel(text: str) -> list[dict]:
    """Heuristic parser for 인사 notices. Returns blocks
    {name, hanja, actions:[...], date, date_source, raw}. Two formats exist:
    2001-2010s: '◉2001년 3 월26일자' header then name blocks; later years: name,
    action lines, then a 'YYYY. M. D.' line per person. ALWAYS eyeball the raw
    snippet before using a record. Rank/position lines that precede a name
    (e.g. the person's previous post) are kept in 'pre'."""
    lines = [l.rstrip() for l in text.splitlines()]
    recs, cur, eff, pre = [], None, None, []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        m = _EFFECTIVE.search(s)
        if m:
            eff = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            cur = None
            continue
        m = _NAME_LINE.match(s)
        if m:
            cur = {"name": re.sub(r"\s+", "", m.group(1)), "hanja": re.sub(r"\s+", "", m.group(2)),
                   "actions": [], "pre": pre[-2:], "date": eff, "date_source": "section_header" if eff else None,
                   "raw": [s]}
            recs.append(cur)
            pre = []
            continue
        m = _DATE_LINE.match(s)
        if m and cur is not None:
            cur["date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            cur["date_source"] = "per_person_line"
            cur["raw"].append(s)
            cur = None
            continue
        m = _TERM_LINE.match(s)
        if m and cur is not None:
            cur["date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            cur["date_source"] = "term_line"
            cur["raw"].append(s)
            cur = None
            continue
        if cur is not None and _ACTION.search(s):
            cur["actions"].append(s)
            cur["raw"].append(s)
            continue
        cur = None if (cur is not None and cur["actions"]) else cur
        pre.append(s)
    for r in recs:
        r["raw"] = " | ".join(r["raw"])
    return recs


# Matches action lines of cabinet-level notices, e.g. '국무위원에 임함', '법무부장관에 보함',
# '국무총리에 임함', '(장관급)에 임함', '...장관 직을 면함'. Deliberately broad (includes 장관급
# heads that are not 국무위원); the roster agent decides what is in scope.
CABINET_PAT = re.compile(r"국무위원|국무총리(?:서리)?\s*(?:에|직|을|를)|부총리|장관\s*(?:에|직|을|\(|급)|특임|정무장관")


def gazette_cabinet_notices(date_from: str, date_to: str, pattern: re.Pattern = CABINET_PAT,
                            **kw) -> list[dict]:
    """All 인사 items published in [date_from, date_to] whose parsed blocks mention a
    cabinet post. Each record carries the gazette provenance (issue number,
    publication date, toc_seq, viewer URL, access time). Note that the gazette
    publication date is usually 1-10 days after the appointment date; the
    appointment date is record['date']."""
    res = gazette_search(date_from=date_from, date_to=date_to, category=19, size=500, **kw)
    out = []
    for it in res["items"]:
        try:
            pdf = gazette_item_pdf(it["toc_seq"], **kw)
        except ValueError as e:
            out.append({"error": str(e), **it})
            continue
        for rec in parse_gazette_personnel(pdf_text(pdf.content)):
            if any(pattern.search(a) for a in rec["actions"]):
                out.append({**rec, "gazette_pubdate": it["regdate"], "gazette_no": it["ebook_no"],
                            "gazette_subject": it["subject"], "toc_seq": it["toc_seq"],
                            "viewer_url": it["viewer_url"], "pdf_cache": pdf.cache_path,
                            "fetched_at": pdf.fetched_at})
    return out


# ---------------------------------------------------------------------------
# 대한민국 정책브리핑 korea.kr (tier 2)
# ---------------------------------------------------------------------------

KOREA = "https://www.korea.kr"


def korea_search(q: str, **kw) -> list[dict]:
    """Integrated search on korea.kr (first result page per section). Returns
    unique articles {news_id, url, title, snippet}. Dates are on the article page."""
    r = fetch(KOREA + "/totalSearch.do", params={"topSearchKeyword": q}, **kw)
    seen, out = {}, []
    for href, nid, inner in re.findall(r'href="([^"]*newsId=(\d+)[^"]*)"[^>]*>(.*?)</a>', r.text, flags=re.S):
        txt = html_to_text(inner)
        if "noticeView" in href:
            continue
        d = seen.get(nid)
        if d is None:
            d = {"news_id": nid, "url": KOREA + href if href.startswith("/") else href, "title": "", "snippet": ""}
            seen[nid] = d
            out.append(d)
        if txt:
            if not d["title"]:
                d["title"] = txt
            elif not d["snippet"]:
                d["snippet"] = txt
    return out


def korea_article(url: str, **kw) -> dict:
    r = fetch(url, **kw)
    t = r.text
    title = re.search(r'<meta property="og:title" content="([^"]*)"', t)
    pub = re.search(r'<meta property="article:published_time" content="([^"]*)"', t)
    body = re.search(r'<div class="article_body"[^>]*>(.*?)<div class="article_footer"', t, flags=re.S)
    return {"url": url, "title": _html.unescape(title.group(1)) if title else "",
            "published": pub.group(1) if pub else "",
            "text": html_to_text(body.group(1)) if body else html_to_text(t)[:6000],
            "fetched_at": r.fetched_at, "resp": r}


# ---------------------------------------------------------------------------
# News (tier 3): Naver News search, Naver article pages, BigKinds, Yonhap
# ---------------------------------------------------------------------------

def naver_news_search(q: str, ds: str, de: str, start: int = 1, **kw) -> list[str]:
    """Naver News search restricted to a date window (ds/de as YYYY-MM-DD).
    Returns unique n.news.naver.com article URLs ('mnews/article/<oid>/<aid>').
    oid identifies the outlet (read the outlet name from naver_article)."""
    a, b = _ymd(ds), _ymd(de)
    params = {"where": "news", "query": q, "sm": "tab_opt", "sort": "0", "pd": "3",
              "ds": f"{a[:4]}.{a[4:6]}.{a[6:]}", "de": f"{b[:4]}.{b[4:6]}.{b[6:]}",
              "nso": f"so:r,p:from{a}to{b}", "start": str(start)}
    r = fetch("https://search.naver.com/search.naver", params=params, **kw)
    urls = re.findall(r"https://n\.news\.naver\.com/mnews/article/\d{3}/\d{10}", r.text)
    return list(dict.fromkeys(urls))


def naver_article(url: str, **kw) -> dict:
    r = fetch(url.split("?")[0], **kw)
    t = r.text
    g = lambda pat: (re.search(pat, t, flags=re.S).group(1) if re.search(pat, t, flags=re.S) else "")
    body = g(r'id="dic_area"[^>]*>(.*?)</article>')
    orig = re.findall(r'<a[^>]*href="([^"]+)"[^>]*class="[^"]*media_end_head_origin_link', t)
    return {"url": r.url, "title": _html.unescape(g(r'<meta property="og:title" content="([^"]*)"')),
            "press": g(r'<meta name="twitter:creator" content="([^"]*)"'),
            "published": g(r'_ARTICLE_DATE_TIME" data-date-time="([^"]*)"'),
            "modified": g(r'data-modify-date-time="([^"]*)"'),
            "original_url": orig[0] if orig else "", "text": html_to_text(body),
            "fetched_at": r.fetched_at, "resp": r}


def bigkinds_search(q: str, start: str, end: str, n: int = 20, start_no: int = 1, **kw) -> dict:
    """BigKinds (Korea Press Foundation) news metadata search, no login needed.
    Returns {"total", "items":[{date, provider, title, news_id, byline, hilight}]}.
    Full text requires a login. Coverage starts in 1990 for major dailies."""
    body = {"indexName": "news", "searchKey": q, "searchKeys": [{}], "byLine": "", "searchFilterType": "1",
            "searchScopeType": "1", "searchSortType": "date", "sortMethod": "date", "mainTodayPersonYn": "",
            "startDate": start, "endDate": end, "newsIds": [], "categoryCodes": [], "providerCodes": [],
            "incidentCodes": [], "networkNodeType": "", "topicOrigin": "", "dateCodes": [],
            "editorialIs": False, "startNo": start_no, "resultNumber": n, "isTmUsable": False,
            "isNotTmUsable": False}
    r = fetch("https://www.bigkinds.or.kr/api/news/search.do", method="POST", json_body=body,
              warmup="https://www.bigkinds.or.kr/v2/news/index.do",
              headers={"X-Requested-With": "XMLHttpRequest", "Referer": "https://www.bigkinds.or.kr/v2/news/index.do"},
              **kw)
    d = r.json()
    items = [{"date": x.get("DATE"), "provider": x.get("PROVIDER"), "title": x.get("TITLE"),
              "news_id": x.get("NEWS_ID"), "byline": x.get("BYLINE"), "hilight": html_to_text(x.get("CONTENT", "") or "")}
             for x in d.get("resultList", [])]
    return {"total": d.get("totalCount"), "items": items, "fetched_at": r.fetched_at, "resp": r}


def yna_search(q: str, page_size: int = 20, **kw) -> list[dict]:
    """Yonhap search API. LIMITED TO THE LAST 12 MONTHS (site policy); older
    Yonhap articles must be found via Naver/BigKinds/web search and then
    fetched directly at https://www.yna.co.kr/view/<CID>."""
    r = fetch("https://ars.yna.co.kr/api/v2/search.basic", params={
        "query": q, "page_no": 1, "page_size": page_size, "scope": "all", "sort": "date",
        "channel": "basic_kr", "div_code": "all"}, headers={"Referer": "https://www.yna.co.kr/"}, **kw)
    return [{"cid": x.get("CID"), "datetime": x.get("DATETIME"), "title": _html.unescape(x.get("TITLE") or ""),
             "url": f"https://www.yna.co.kr/view/{x.get('CID')}"} for x in r.json()["YIB_KR_A"]["result"]]


def namu_text(title: str, **kw) -> Resp:
    """Namu Wiki page via Playwright (curl gets 403). resp.extra['text'] is the
    rendered text. Secondary source only."""
    from urllib.parse import quote
    return playwright_get("https://namu.wiki/w/" + quote(title), wait_ms=5000, **kw)


# ---------------------------------------------------------------------------
# National Assembly: 의안정보시스템 likms (인사청문요청안, 임명동의안)
# ---------------------------------------------------------------------------

LIKMS = "https://likms.assembly.go.kr/bill"


def likms_search(bill_name: str, age_from: int, age_to: int | None = None, rows: int = 100,
                 max_pages: int = 20, **kw) -> list[dict]:
    """Bill search on likms (no key). Use bill_name='국무위원후보자' for 인사청문요청안
    and '국무총리' (then filter '임명동의') for PM consent motions. age = 국회 대수
    (15 = 1996-2000, 16 = 2000-2004, ... 22 = 2024-). Pages through all results
    (form fields 'page' and 'rows'). Returns rows {bill_no, bill_id, title,
    proposer_kind, propose_date, detail_url}."""
    out, seen = [], set()
    for page in range(1, max_pages + 1):
        data = {"reqPageId": "billSrch", "detailedTab": "billDtl", "billNm": bill_name,
                "representKindCd": "REPR", "isPopSelect": "N", "ageFrom": str(age_from),
                "ageTo": str(age_to or age_from), "page": str(page), "rows": str(rows),
                "schSorting": "score", "ordCd": "DESC"}
        r = fetch(LIKMS + "/bi/bill/sch/findSchPaging.do", method="POST", data=data,
                  warmup=LIKMS + "/bi/bill/sch/detailedSchPage.do?detailedTab=billDtl",
                  headers={"X-Requested-With": "XMLHttpRequest",
                           "Referer": LIKMS + "/bi/bill/sch/detailedSchPage.do?detailedTab=billDtl"}, **kw)
        n_new = 0
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, flags=re.S):
            m = re.search(r'data-bill_no="([^"]+)"\s+data-bill-id="([^"]+)"', row)
            if not m or m.group(2) in seen:
                continue
            seen.add(m.group(2))
            n_new += 1
            tds = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
            title = re.search(r'title="([^"]+?)\s*\(새창 열림\)"', row)
            out.append({"bill_no": m.group(1), "bill_id": m.group(2),
                        "title": _html.unescape(title.group(1)) if title else html_to_text(tds[1] if len(tds) > 1 else ""),
                        "proposer_kind": html_to_text(tds[2]) if len(tds) > 2 else "",
                        "propose_date": html_to_text(tds[3]) if len(tds) > 3 else "",
                        "detail_url": f"{LIKMS}/bi/billDetailPage.do?billId={m.group(2)}"})
        if n_new < rows:
            break
    return out


def likms_bill_detail(bill_id: str, **kw) -> dict:
    """Rendered bill detail page (Playwright; the review panel is loaded by an
    XHR that rejects plain requests). Returns text plus the stage dates found
    in the '심사진행단계' strip (접수 / 위원회 심사 / 본회의 심의)."""
    r = playwright_get(f"{LIKMS}/bi/billDetailPage.do?billId={bill_id}", wait_ms=4000,
                       wait_until="networkidle", **kw)
    text = r.extra.get("text", "")
    flat = re.sub(r"\s+", " ", text)
    stages = {}
    m = re.search(r"심사진행단계.*?접수\s*(\d{4}-\d{2}-\d{2})?\s*위원회 심사\s*(\d{4}-\d{2}-\d{2})?\s*본회의 심의\s*(\d{4}-\d{2}-\d{2})?", flat)
    if m:
        stages = {"접수": m.group(1), "위원회심사": m.group(2), "본회의": m.group(3)}
    return {"bill_id": bill_id, "stages": stages, "text": text, "fetched_at": r.fetched_at, "resp": r}


# ---------------------------------------------------------------------------
# Ministry 역대 장관 pages (tier 2). Verified URLs only.
# ---------------------------------------------------------------------------

MINISTRY_PAGES = {
    # key: (url, note)
    "mofa": ("https://www.mofa.go.kr/minister/wpge/m_20036/contents.do",
             "외교부 역대 장관, one page, start-end dates. First hit returns 307 to set a cookie; fetch() follows it."),
    "unikorea": ("https://unikorea.go.kr/web/minister/contents/introduce_pastminister/",
                 "통일부 역대 장관 with 대수 and start-end dates, also lists 장관직무대행 periods."),
    "moj": ("https://www.moj.go.kr/minister/2090/subview.do",
            "법무부 역대 장관, 8 per page, 9 pages (newest first); 재임기간 per person. Use ministry_page('moj', page=N)."),
}


def ministry_page(key: str, page: int | None = None, **kw) -> dict:
    url, note = MINISTRY_PAGES[key]
    if page:
        url = f"{url}{'&' if '?' in url else '?'}page={page}"
    r = fetch(url, **kw)
    return {"key": key, "url": url, "note": note, "text": html_to_text(r.text), "fetched_at": r.fetched_at, "resp": r}


# ---------------------------------------------------------------------------
# Local transcript inputs (kr-hearings-data v9) - tenure bounds, not a source of dates
# ---------------------------------------------------------------------------

def transcript_rows(name: str | None = None, affiliation_contains: str | None = None,
                    roles: Iterable[str] = ("minister", "minister_acting", "prime_minister", "minister_nominee")) -> list[dict]:
    """Rows of inputs/minister_role_meetings.csv for a person (matches person_name,
    or speaker when person_name is empty) and/or an affiliation substring."""
    roles = set(roles)
    out = []
    with open(INPUTS_DIR / "minister_role_meetings.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["role"] not in roles:
                continue
            who = row["person_name"] or row["speaker"]
            if name and name not in who:
                continue
            if affiliation_contains and affiliation_contains not in (row["affiliation_raw"] + row["speaker"]):
                continue
            out.append(row)
    return out


def transcript_bounds(name: str, affiliation_contains: str | None = None) -> dict:
    """First/last transcript date per (role, affiliation) for a person."""
    agg: dict[tuple, dict] = {}
    for r in transcript_rows(name, affiliation_contains):
        k = (r["role"], r["affiliation_raw"])
        a = agg.setdefault(k, {"role": r["role"], "affiliation": r["affiliation_raw"], "first": r["date"],
                               "last": r["date"], "n_meetings": 0})
        a["first"], a["last"] = min(a["first"], r["date"]), max(a["last"], r["date"])
        a["n_meetings"] += 1
    return {"name": name, "spells": sorted(agg.values(), key=lambda x: x["first"])}


__all__ = [n for n in dir() if not n.startswith("_")]


# ===========================================================================
# Pre-2001 sources (1988-2000). Appended 2026-09-26. Everything above this
# line is unchanged. See SOURCES_TOOLKIT.md, section "Pre-2001 sources
# (1988-2000)", for tests, example calls and caveats.
#
#   newslib_*            Naver News Library (newslibrary.naver.com), scanned
#                        동아/경향/매경/한겨레/조선 1920-1999, OCR text, no login
#   bigkinds_article     BigKinds full text by NEWS_ID (no login), and
#   bigkinds_facets      per-year / per-outlet hit counts
#   history_chronology_* 국사편찬위원회 대한민국사연표 (db.history.go.kr), dated daily events
#   pa_schedule_year     대통령기록관 연도별 대통령 일정 (1948-), from 대통령비서실 일정일지
#   ministry_history     ministry 역대 장관 pages that reach the 1988-1993 predecessors
#   tenure_rows          generic "start ~ end" extractor for those pages
# ===========================================================================

HOST_INTERVAL.setdefault("newslibrary.naver.com", 1.5)
HOST_INTERVAL.setdefault("db.history.go.kr", 1.0)
HOST_INTERVAL.setdefault("www.pa.go.kr", 1.5)

# ---------------------------------------------------------------------------
# Naver News Library (newslibrary.naver.com)
# ---------------------------------------------------------------------------

NEWSLIB = "https://newslibrary.naver.com"
NEWSLIB_OFFICES = {"00020": "동아일보", "00032": "경향신문", "00009": "매일경제", "00028": "한겨레", "00023": "조선일보"}
NEWSLIB_OFFICE_IDS = {v: k for k, v in NEWSLIB_OFFICES.items()}
NEWSLIB_ORDER = {"relevance": "00010", "oldest": "00020", "newest": "00030"}
# Field bitmasks copied from the site's own JS (keyword.nl.min.js, nl.timemachine.min.js).
_NL_SEARCH_DETAIL = "11111000010000011100011011000100111100100101"
_NL_LIST_DETAIL = "1001100001000000110111100000001010000000001"
_NL_ARTICLE_DETAIL = "1001000001000000000001101100000000000000000"


def _nl_headers(referer_path: str = "/search/searchByKeyword.naver") -> dict:
    # The charset matters. Without it the server decodes the UTF-8 form body as
    # Latin-1 and silently returns zero hits.
    return {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest", "Referer": NEWSLIB + referer_path}


def _nl_clean(s: str | None) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return _html.unescape(s).strip()


def _nl_office_id(office: str | None) -> str:
    if not office:
        return ""
    return office if office in NEWSLIB_OFFICES else NEWSLIB_OFFICE_IDS[office]


def newslib_viewer_url(a: dict) -> str:
    """Human-readable viewer link (page image) for an article record from the API."""
    return (f"{NEWSLIB}/viewer/index.naver?articleId={a.get('articleId', '')}&editNo={a.get('editNo', '')}"
            f"&printCount=1&publishDate={a.get('publishDate', '')}&officeId={a.get('officeId', '')}"
            f"&pageNo={a.get('pageNo', '')}&printNo={a.get('printNo', '')}&publishType={a.get('publishType', '')}")


def _nl_item(a: dict, **extra) -> dict:
    oid = a.get("officeId", "")
    return {"article_id": a.get("articleId"), "date": a.get("publishDate"), "office_id": oid,
            "office": NEWSLIB_OFFICES.get(oid, a.get("officeName", "")), "page_no": a.get("pageNo"),
            "title": _nl_clean(a.get("title")), "title_ko": _nl_clean(a.get("translatedTitle")),
            "snippet": _nl_clean(a.get("translatedContentSummary") or a.get("contentSummary")),
            "genre": a.get("articleGenre"), "viewer_url": newslib_viewer_url(a), **extra}


def newslib_search(keyword: str, start: str, end: str, office: str | None = None, order: str = "oldest",
                   page: int = 1, size: int = 100, **kw) -> dict:
    """Keyword search of the Naver News Library (1920-1999; 동아일보, 경향신문,
    매일경제, 한겨레 from 1988-05-15, 조선일보). No login needed.

    keyword: space-separated terms are ANDed; wrap in double quotes for a phrase.
    A hangul term also matches its hanja spelling (오자복 finds 吳滋福).
    start/end: 'YYYY-MM-DD'. office: name ('동아일보') or id ('00020').
    order: 'oldest' (default), 'newest' or 'relevance'. size: up to 200 tested.
    Returns {"n": hits in the window, "items": [...], "page", "size", "fetched_at", "resp"}.
    Each item has article_id, date, office, page_no, title (as printed, hanja
    kept), title_ko (hanja followed by hangul reading), snippet and viewer_url.
    """
    data = {"keyword": keyword, "page": str(page), "startDate": start, "endDate": end,
            "order": NEWSLIB_ORDER.get(order, order), "detailCode": _NL_SEARCH_DETAIL,
            "pageSize": str(size), "officeId": _nl_office_id(office), "includeSectionId": ""}
    r = fetch(NEWSLIB + "/api/search/article/json", method="POST", data=data, headers=_nl_headers(), **kw)
    res = r.json().get("result") or {}
    arts = (res.get("articles") or {}).get("article") or []
    if isinstance(arts, dict):
        arts = [arts]
    return {"n": int(res.get("articleCount") or 0), "page": page, "size": size,
            "items": [_nl_item(a) for a in arts], "fetched_at": r.fetched_at, "resp": r}


def newslib_search_all(keyword: str, start: str, end: str, office: str | None = None, order: str = "oldest",
                       size: int = 100, max_pages: int = 10, **kw) -> dict:
    """All pages of newslib_search (up to max_pages). Returns {"n", "items", "resps"}."""
    items, resps, n = [], [], 0
    for page in range(1, max_pages + 1):
        res = newslib_search(keyword, start, end, office=office, order=order, page=page, size=size, **kw)
        n = res["n"]
        resps.append(res["resp"])
        items.extend(res["items"])
        if not res["items"] or len(items) >= n:
            break
    return {"n": n, "items": items, "resps": resps}


def newslib_article(article_id: str, **kw) -> dict:
    """OCR text of one News Library article (no login needed).
    text keeps the printed hanja; text_ko adds hangul readings in parentheses.
    OCR errors occur, so check names and dates against the page image
    (viewer_url from the search or day listing) before relying on them."""
    r = fetch(NEWSLIB + "/api/article/detail/json", method="POST",
              data={"articleId": article_id, "detailCode": _NL_ARTICLE_DETAIL},
              headers=_nl_headers("/viewer/index.naver"), **kw)
    a = (r.json().get("result") or {}).get("article") or {}
    if not a:
        raise ValueError(f"newslib article {article_id}: empty response (status {r.status})")
    return {"article_id": article_id, "date": a.get("publishDate"), "page_no": a.get("pageNo"),
            "title": _nl_clean(a.get("title")), "title_ko": _nl_clean(a.get("translatedTitle")),
            "text": _nl_clean(a.get("content")), "text_ko": _nl_clean(a.get("translatedContent")),
            "fetched_at": r.fetched_at, "resp": r}


def newslib_day_articles(date: str, office: str, max_page: int | None = None, **kw) -> dict:
    """Every article headline in one paper on one day, page by page (the
    viewer's own index). max_page=1 gives the front page only. Use it to scan
    the day after an appointment when a keyword search misses the story.
    Returns {"date", "office", "prints", "items", "resps"}; items carry
    article_id, page_no, title, title_ko and viewer_url."""
    oid = _nl_office_id(office)
    r = fetch(NEWSLIB + "/api/page/list/json", method="POST",
              data={"startDate": date, "officeId": oid, "listLevel": "2"},
              headers=_nl_headers("/viewer/index.naver"), **kw)
    resps = [r]
    dps = ((r.json().get("result") or {}).get("datePages") or {}).get("datePage") or []
    prints = []
    for dp in dps:
        ops = (dp.get("officePages") or {}).get("officePage") or []
        for op in ops if isinstance(ops, list) else [ops]:
            for kind in ("regularPrint", "extraPrint"):
                blk = op.get(kind) or {}
                pl = (blk.get("prints") or {}).get("print") or []
                for p in pl if isinstance(pl, list) else [pl]:
                    prints.append({**p, "kind": kind})
    items = []
    for p in prints:
        n = int(p.get("pageCount") or 0)
        if max_page:
            n = min(n, max_page)
        if n <= 0:
            continue
        ra = fetch(NEWSLIB + "/api/article/list/json", method="POST",
                   data={"date": date, "publishType": p.get("publishType", ""), "officeId": oid,
                         "printNo": p.get("printNo", ""), "detailYn": "false", "detailCode": _NL_LIST_DETAIL,
                         "startPageNo": "1", "pageCount": str(n), "includeBlind": "true", "includeEtcEntity": "true"},
                   headers=_nl_headers("/viewer/index.naver"), **kw)
        resps.append(ra)
        arts = ((ra.json().get("result") or {}).get("articles") or {}).get("article") or []
        for a in arts if isinstance(arts, list) else [arts]:
            a = {**a, "officeId": oid, "editNo": p.get("editNo", ""), "printNo": p.get("printNo", ""),
                 "publishType": p.get("publishType", "")}
            items.append(_nl_item(a, print_no=p.get("printNo"), edition=p["kind"]))
    return {"date": date, "office_id": oid, "office": NEWSLIB_OFFICES.get(oid, ""), "prints": prints,
            "items": items, "fetched_at": r.fetched_at, "resps": resps}


# ---------------------------------------------------------------------------
# BigKinds: full text by NEWS_ID and hit counts per year and outlet
# ---------------------------------------------------------------------------

_BK_INDEX = "https://www.bigkinds.or.kr/v2/news/index.do"


def bigkinds_article(news_id: str, **kw) -> dict:
    """Full article text from BigKinds by NEWS_ID (from bigkinds_search items),
    no login needed. Returns date, provider, title, subtitle, text, persons."""
    r = fetch("https://www.bigkinds.or.kr/news/detailView.do",
              params={"docId": news_id, "returnCnt": 1, "sectionDiv": 1000}, warmup=_BK_INDEX,
              headers={"X-Requested-With": "XMLHttpRequest", "Referer": _BK_INDEX}, **kw)
    d = r.json().get("detail") or {}
    if not d:
        raise ValueError(f"bigkinds {news_id}: no detail (status {r.status})")
    return {"news_id": news_id, "date": d.get("DATE"), "provider": d.get("PROVIDER"), "byline": d.get("BYLINE"),
            "title": d.get("TITLE"), "subtitle": d.get("SUB_TITLE"), "text": _nl_clean(d.get("CONTENT")),
            "persons": d.get("TMS_NE_PERSON"), "category": d.get("CATEGORY_MAIN"),
            "fetched_at": r.fetched_at, "resp": r}


def bigkinds_facets(q: str, start: str, end: str, **kw) -> dict:
    """Hit counts by year and by outlet for a query and window (from the
    aggregates BigKinds returns with every search). Use it to see which
    outlets exist for a period before searching."""
    res = bigkinds_search(q, start, end, n=1, **kw)
    d = res["resp"].json()
    return {"total": d.get("totalCount"),
            "years": {x["date"]: int(x["dateCount"]) for x in d.get("getDateCodeList") or []},
            "providers": {x["ProviderName"]: int(x["ProviderCount"]) for x in d.get("getProviderCodeList") or []},
            "fetched_at": res["fetched_at"], "resp": res["resp"]}


# ---------------------------------------------------------------------------
# 국사편찬위원회 대한민국사연표 (db.history.go.kr), dated daily events 1945-
# ---------------------------------------------------------------------------

DBHIST = "https://db.history.go.kr"


def history_chronology_day(date: str, **kw) -> dict:
    """Entries of the 대한민국사연표 for one day. Returns {"date", "entries":
    [{id, title, url}], "fetched_at", "resp"}. Reshuffles appear as entries such
    as '노태우 대통령, 총리에 강영훈 민주정의당 의원을 임명하는 등 개각'."""
    d = _ymd(date)
    pid = f"tcct_{d[:4]}_{d[4:6]}_{d[6:8]}"
    r = fetch(DBHIST + "/diachronic/getChildItemLevelListAjax.do",
              params={"parentId": pid, "level": 4, "types": "o", "contentsYn": "Y"},
              headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{DBHIST}/id/{pid}_0010"}, **kw)
    entries = []
    for eid, title in re.findall(r'<li id="(tcct_\d{4}_\d{2}_\d{2}_\d{4})"[^>]*>.*?title="([^"]*)"', r.text, flags=re.S):
        entries.append({"id": eid, "title": _html.unescape(title).strip(), "url": f"{DBHIST}/id/{eid}"})
    return {"date": f"{d[:4]}-{d[4:6]}-{d[6:8]}", "entries": entries, "fetched_at": r.fetched_at, "resp": r}


def history_chronology_range(date_from: str, date_to: str, pattern: str | re.Pattern | None = None, **kw) -> list[dict]:
    """history_chronology_day for every day in [date_from, date_to], keeping
    entries whose title matches pattern (regex). One request per day, so a
    year takes about six minutes on a cold cache."""
    import datetime as _dt
    a = _dt.date.fromisoformat(f"{_ymd(date_from)[:4]}-{_ymd(date_from)[4:6]}-{_ymd(date_from)[6:8]}")
    b = _dt.date.fromisoformat(f"{_ymd(date_to)[:4]}-{_ymd(date_to)[4:6]}-{_ymd(date_to)[6:8]}")
    pat = re.compile(pattern) if isinstance(pattern, str) else pattern
    out = []
    while a <= b:
        day = history_chronology_day(a.isoformat(), **kw)
        for e in day["entries"]:
            if pat is None or pat.search(e["title"]):
                out.append({**e, "date": day["date"], "fetched_at": day["fetched_at"]})
        a += _dt.timedelta(days=1)
    return out


def history_chronology_entry(entry_id: str, **kw) -> dict:
    """One 대한민국사연표 entry page. Returns {id, date, title, body, url}.
    Most entries are a dated one-line title; some carry a body with a cited
    source (for example a speech text with '[출전] ...')."""
    r = fetch(f"{DBHIST}/id/{entry_id}", **kw)
    h = r.text
    i = h.find('<div class="nd-content">')
    seg = h[i:] if i >= 0 else h
    m = re.search(r'<div class="title">(.*?)</div>', seg, flags=re.S)
    title = html_to_text(m.group(1)) if m else ""
    c = seg.find('<div class="cont">')
    e = seg.find('<div class="info">', c) if c >= 0 else -1
    body = html_to_text(seg[c:e if e > c else c + 50000]) if c >= 0 else ""
    d = re.search(r"tcct_(\d{4})_(\d{2})_(\d{2})_", entry_id)
    return {"id": entry_id, "date": f"{d.group(1)}-{d.group(2)}-{d.group(3)}" if d else "", "title": title,
            "body": body, "url": f"{DBHIST}/id/{entry_id}", "fetched_at": r.fetched_at, "resp": r}


# ---------------------------------------------------------------------------
# 대통령기록관 연도별 대통령 일정 (www.pa.go.kr), all presidents from 1948
# ---------------------------------------------------------------------------

PA_SCHEDULE = "https://www.pa.go.kr/portal/contents/stroll/schedule/scheduleYearList.do"


def pa_schedule_year(president: str, year: int, pattern: str | re.Pattern | None = None, rows: int = 100,
                     **kw) -> dict:
    """The 대통령기록관 yearly schedule for one president and year (built from
    the 대통령비서실 일정일지 and 국정백서, per the page). president is the
    hangul name ('노태우', '김영삼', '전두환'). pattern (regex) filters on title
    plus description. Returns {"rows": [{date, title, desc, image, extra}],
    "resps"}. Raises ValueError when the site does not serve that year for
    that president."""
    pat = re.compile(pattern) if isinstance(pattern, str) else pattern
    out, resps, page, total_pages = [], [], 1, 1
    while page <= total_pages:
        data = {"selPresident": president, "skinYearList": "", "method": "getYearList", "pageNo": str(page),
                "SCHEDULE_NAME": "", "year": str(year), "yearSelect": "", "monthSelect": "", "month": "1",
                "pageRowCnt": str(rows)}
        r = fetch(PA_SCHEDULE, method="POST", data=data, headers={"Referer": PA_SCHEDULE}, **kw)
        resps.append(r)
        cy = re.search(r"var curYear = '(\d+)'", r.text)
        if not cy or cy.group(1) != str(year):
            raise ValueError(f"pa schedule {president} {year}: site served year {cy.group(1) if cy else None}")
        tp = re.search(r"var totalPageCount = '(\d+)'", r.text)
        total_pages = int(tp.group(1)) if tp else 1
        body = r.text[r.text.find('<tbody id="_tbody">'):]
        body = body[:body.find("</tbody>")]
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, flags=re.S):
            md = re.search(r'<td class="date">\s*(\d{1,2})월\s*(\d{1,2})일', tr)
            if not md:
                continue
            dt = re.search(r"<dt>(.*?)</dt>", tr, flags=re.S)
            dds = [html_to_text(x) for x in re.findall(r"<dd>(.*?)</dd>", tr, flags=re.S)]
            img = re.search(r'<img src="([^"]+)"', tr)
            ctx = re.search(r'<div class="context">(.*?)</div>\s*</div>', tr, flags=re.S)
            rec = {"date": f"{year}-{int(md.group(1)):02d}-{int(md.group(2)):02d}",
                   "title": html_to_text(dt.group(1)) if dt else "", "desc": dds[0] if dds else "",
                   "extra": " | ".join(x for x in dds[1:] if x), "image": img.group(1) if img else "",
                   "context_text": html_to_text(ctx.group(1)) if ctx else "", "page": page}
            if pat is None or pat.search(rec["title"] + " " + rec["desc"]):
                out.append(rec)
        page += 1
    return {"president": president, "year": year, "rows": out, "fetched_at": resps[0].fetched_at, "resps": resps}


# ---------------------------------------------------------------------------
# Ministry 역대 장관 pages that reach the 1988-1993 predecessor ministries
# (checked 2026-09-26). The three pages in MINISTRY_PAGES above (mofa,
# unikorea, moj page=5) also reach 1988. Pages differ in how they print the
# end date, see 'end'. Always read the raw text around a row.
# ---------------------------------------------------------------------------

PRE2001_MINISTRY_PAGES = {
    "moef_his": {"url": "https://www.moef.go.kr/mi/mh/his.do?menuNo=9020800", "method": "GET",
                 "offices": "재무부, 경제기획원 (and 재정경제원, 재정경제부 and later)", "precision": "month",
                 "end": "month of successor start", "note": "YYYY.M. only, no day"},
    "msit": {"url": "https://www.msit.go.kr/contents/cont.do?sCode=user&mId=137&mPid=132", "method": "GET",
             "offices": "과학기술처 (1967-), 체신부 (1948-1994), 정보통신부", "precision": "day",
             "end": "day before successor start"},
    "moe": {"url": "https://www.moe.go.kr/mnstrHistory.do", "method": "GET",
            "offices": "문교부, 교육부", "precision": "day", "end": "day before successor start"},
    "mois_home": {"url": "https://www.mois.go.kr/mns/sub/a02/MinistryofHomeAffairs/screen.do", "method": "GET",
                  "offices": "내무부", "precision": "day", "end": "day before successor start"},
    "mois_govadmin": {"url": "https://www.mois.go.kr/mns/sub/a02/MinistryofGovernmentAdmin/screen.do", "method": "GET",
                      "offices": "총무처", "precision": "day", "end": "last day, gaps occur between holders"},
    "mohw": {"url": "https://www.mohw.go.kr/pastProfile.es?mid=a10605060000&menuType=2&searchType=&keyword=&pageNum={page}",
             "method": "GET", "default_page": 4, "offices": "보건사회부 (page 4 = 1975-1991), 보건복지부",
             "precision": "day", "end": "day before successor start"},
    "motir": {"url": "https://www.motir.go.kr/kor/21/history?pageIndex={page}", "method": "GET", "default_page": 4,
              "offices": "상공부, 동력자원부 (page 4 = 1983-1993), 상공자원부, 통상산업부",
              "precision": "day", "end": "same day as successor start"},
    "mcst_munhwagongbo": {"url": "https://www.mcst.go.kr/usr/minister/intro/minHistory.jsp?pOrgNm=05", "method": "GET",
                          "offices": "문화공보부 (1968-07-24 to 1989-12-29)", "precision": "day",
                          "end": "day before successor start"},
    "mcst_munhwa": {"url": "https://www.mcst.go.kr/usr/minister/intro/minHistory.jsp?pOrgNm=04", "method": "GET",
                    "offices": "문화부 (1990-01-30 to 1993-03-05)", "precision": "day", "end": "day before successor start"},
    "mcee": {"url": "https://mcee.go.kr/minister/web/index.do?menuId=366", "method": "GET",
             "offices": "환경청 (1980-1989, an agency), 환경처 (from 1990-01), 환경부", "precision": "day",
             "end": "same day as successor start"},
    "mafra": {"url": "https://www.mafra.go.kr/profl/home/10/artclList.do", "method": "POST",
              "data": {"layout": "fFFjpDoeis/NjzY+RnJZ3/labU8u4tWWDbOYcFOF2Xw=", "page": "{page}",
                       "srchColumn": "", "srchWrd": ""}, "default_page": 3,
              "offices": "농림수산부 (page 3 = 1985-1995) and successors", "precision": "day",
              "end": "day before successor start, typos seen (45대 row reads 1993.12.22 ~ 1993.12.21)"},
}


def ministry_history(key: str, page: int | None = None, **kw) -> dict:
    """Fetch one of PRE2001_MINISTRY_PAGES. Returns {key, url, text, rows
    (tenure_rows of the text), meta, fetched_at, resp}."""
    meta = PRE2001_MINISTRY_PAGES[key]
    pg = page or meta.get("default_page") or 1
    url = meta["url"].replace("{page}", str(pg))
    if meta.get("method") == "POST":
        data = {k: (v.replace("{page}", str(pg)) if isinstance(v, str) else v) for k, v in meta["data"].items()}
        r = fetch(url, method="POST", data=data, **kw)
    else:
        r = fetch(url, **kw)
    text = html_to_text(r.text)
    return {"key": key, "url": url, "page": pg, "meta": meta, "text": text, "rows": tenure_rows(text),
            "fetched_at": r.fetched_at, "resp": r}


_TR_DATE = r"((?:19|20)\d{2})\s*(?:[./-]|년)\s*(\d{1,2})\s*(?:[./-]|월)?\s*(?:(\d{1,2})\s*(?:일|\.)?)?"
_TENURE = re.compile(_TR_DATE + r"\s*[~∼～–\-]\s*(?:" + _TR_DATE + r")?")


def tenure_rows(text: str, context: int = 60) -> list[dict]:
    """Every 'start ~ end' date range in a page text, with the preceding text
    (where the name usually is) as context. Dates are 'YYYY-MM-DD', or
    'YYYY-MM' when the page gives no day. Heuristic: read 'context' and the
    page before using a row."""
    flat = re.sub(r"\s+", " ", text)
    out = []
    for m in _TENURE.finditer(flat):
        y1, m1, d1, y2, m2, d2 = m.groups()
        if not (1 <= int(m1) <= 12) or (m2 and not 1 <= int(m2) <= 12):
            continue
        fmt = lambda y, mo, d: (f"{y}-{int(mo):02d}-{int(d):02d}" if d else f"{y}-{int(mo):02d}") if y else ""
        out.append({"start": fmt(y1, m1, d1), "end": fmt(y2, m2, d2),
                    "context": flat[max(0, m.start() - context):m.start()].strip(), "raw": m.group(0).strip()})
    return out


__all__ = [n for n in dir() if not n.startswith("_")]
