"""BigKinds news metadata checks for seat changes in terms 12-14.

BigKinds (bigkinds.or.kr, Korea Press Foundation) indexes major dailies from 1990. Metadata and a
short lead are available without login. Each query's raw JSON response is saved with
src.snapshot under sources/news/t12_14/ (with .meta.json holding URL, POST body and access time),
and a readable digest of the hits is appended to sources/news/t12_14/digest.tsv.

Usage: python3 scripts/15_news_checks_12_14.py            # runs every query in QUERIES
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "tools"))
import src  # noqa: E402

OUT = ROOT / "sources" / "news" / "t12_14"

QUERIES = [
    ("seatloss_1992_03", "의원직 상실", "1992-02-27", "1992-03-12"),
    ("feb1992_leetaeseop", "이태섭", "1992-02-24", "1992-03-04"),
    ("feb1992_ohyongwoon", "오용운", "1992-02-24", "1992-03-04"),
    ("feb1992_leewonbae", "이원배", "1992-02-24", "1992-03-04"),
    ("parkjiwon_1995", "박지원 의원직", "1995-08-25", "1995-09-06"),
    ("pr_exits_1996_03a", "전국구 의원직", "1996-02-28", "1996-03-10"),
    ("pr_exits_1996_03b", "전국구 의원직", "1996-03-11", "1996-03-28"),
    ("dj_resign_1992", "김대중 의원직", "1992-12-19", "1993-01-12"),
    ("namgungjin_1993", "남궁진", "1992-12-19", "1993-01-15"),
    ("ys_resign_1992", "김영삼 의원직", "1992-10-10", "1992-10-20"),
    ("leeinje_1995", "이인제 의원직", "1995-06-01", "1995-06-12"),
    ("kwonohseok_1990", "권오석", "1990-03-18", "1990-03-31"),
    ("leesooin_1990", "이수인", "1990-11-08", "1990-11-15"),
    ("leebuyoung_1995", "이부영 의원직", "1995-11-01", "1995-11-15"),
    ("koojachoon_1996", "구자춘", "1996-02-09", "1996-02-14"),
    ("seoseokjae_1993", "서석재 의원직", "1993-01-26", "1993-02-03"),
    ("parktaejoon_1992", "박태준 의원직", "1992-12-15", "1992-12-31"),
    ("chungjuyung_1993", "정주영 의원직", "1993-02-20", "1993-03-05"),
    ("assets_resign_1993", "의원직 사퇴", "1993-03-25", "1993-04-03"),
    ("kimdongjoo_1992", "김동주", "1992-02-24", "1992-02-29"),
    ("parkjunkyu_1993", "박준규 의원직", "1993-06-25", "1993-07-03"),
    ("leewonjo_1993", "이원조 의원직", "1993-05-25", "1993-06-05"),
    ("kimyoungsoo_1993", "의원직 사퇴 전국구 승계", "1993-02-24", "1993-03-06"),
    ("chungseokmo_1995", "정석모", "1995-02-05", "1995-02-18"),
    ("nohjaebong_1995", "노재봉", "1995-02-22", "1995-03-05"),
    ("choibyungryul_1994", "최병렬 의원직", "1994-10-28", "1994-11-08"),
    ("kimjongin_1994", "김종인 의원직", "1994-09-05", "1994-09-18"),
    ("pr_exits_1995_10", "전국구 승계", "1995-10-15", "1995-11-10"),
    ("pr_exits_1996_02", "전국구 승계", "1996-02-01", "1996-02-29"),
    ("leehaechan_1995", "이해찬 의원직", "1995-06-26", "1995-07-05"),
    ("imchaejung_1992", "임채정", "1992-09-01", "1992-09-15"),
    ("leeminheon_1996", "전국구 탈당", "1996-03-22", "1996-03-30"),
    ("leeminheon_1996b", "이민헌 의원", "1995-10-15", "1996-04-15"),
    ("leeminheon_1996c", "이민헌 탈당", "1996-03-01", "1996-04-10"),
    ("leeminheon_1996d", "이민헌", "1996-03-20", "1996-03-31"),
]


def main(keys=None):
    OUT.mkdir(parents=True, exist_ok=True)
    dig = OUT / "digest.tsv"
    new = not dig.exists()
    with dig.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        if new:
            w.writerow(["label", "query", "start", "end", "fetched_at", "total", "date", "provider", "title", "lead"])
        for label, q, a, b in QUERIES:
            if keys and label not in keys:
                continue
            d = src.bigkinds_search(q, a, b, n=30)
            src.snapshot(d["resp"], OUT, f"bigkinds_{label}.json")
            for x in d["items"]:
                w.writerow([label, q, a, b, d["fetched_at"], d["total"], x["date"], x["provider"], x["title"],
                            (x["hilight"] or "").replace("\n", " ").replace("\t", " ")[:600]])
            print(label, d["total"], len(d["items"]), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
