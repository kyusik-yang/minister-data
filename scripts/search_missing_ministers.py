"""
Targeted minister name search for missing minister-year pairs.
For each missing pair, scan a wide MNTS_ID range to find sessions
where the minister's name appears AND the session has 국정감사 in the title.
"""
import json, re, sys, time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

AUDIT_JSON = Path('data/raw/minister_audit_meetings.json')
VIEWER_URL = 'https://record.assembly.go.kr/assembly/viewer/minutes/xml.do'

SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; research)'})

# Wide ranges to scan for each year
SEARCH_RANGES = {
    2004: (27000, 28200),
    2005: (28200, 29300),
    2006: (29300, 30700),
    2007: (30700, 32000),
    2016: (40550, 40830),
    2017: (40600, 41100),
    2018: (40990, 41300),
    2019: (41200, 41500),
    2020: (44450, 44750),
    2021: (44550, 45100),
    2022: (44700, 45100),
    2023: (44850, 45400),
    2024: (52000, 52600),
    2025: (55200, 55800),
}

def check_minister_in_session(mnts_id, minister_name, year):
    """Check if minister appears in session AND session is 국감. Returns (title, valid) or None."""
    try:
        resp = SESSION.get(
            VIEWER_URL,
            params={'id': mnts_id, 'type': 'view'},
            timeout=15,
            stream=True,
        )
        if resp.status_code != 200:
            resp.close()
            return None
        chunk = resp.raw.read(30720)  # 30KB to catch title
        resp.close()
        if not chunk:
            return None
        html = chunk.decode('utf-8', errors='replace')

        if '회의록 정보를 찾을 수 없습니다' in html:
            return None
        if minister_name not in html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        h2 = soup.find('h2')
        if not h2:
            return None
        title = h2.get_text(strip=True)

        # Check if session is actually 국감
        if '국정감사' not in title:
            return None

        # Check year from title
        year_match = re.search(r'(\d{4})년도', title)
        if year_match:
            session_year = int(year_match.group(1))
            if session_year != year:
                return None  # Different year

        return (mnts_id, title)
    except Exception:
        return None


def search_for_minister(name, ministry, year, lo, hi):
    """Search MNTS_ID range for a specific minister in a specific year's 국감."""
    results = []
    ids = list(range(lo, hi + 1))

    def check_one(mid):
        return check_minister_in_session(mid, name, year)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(check_one, mid): mid for mid in ids}
        for future in as_completed(futures):
            result = future.result()
            if result:
                mnts_id, title = result
                results.append({'mnts_id': mnts_id, 'title': title})

    results.sort(key=lambda x: x['mnts_id'])
    return results


def main():
    import pandas as pd

    PANEL_FILE = Path('data/minister_panel_comprehensive.csv')
    MINISTRY_COMMITTEE = {
        '기획재정부': '기획재정위원회', '교육부': '교육위원회',
        '과학기술정보통신부': '과학기술정보방송통신위원회',
        '외교부': '외교통일위원회', '통일부': '외교통일위원회',
        '법무부': '법제사법위원회', '국방부': '국방위원회',
        '행정안전부': '행정안전위원회', '문화체육관광부': '문화체육관광위원회',
        '농림축산식품부': '농림축산식품해양수산위원회', '해양수산부': '농림축산식품해양수산위원회',
        '산업통상자원부': '산업통상자원중소벤처기업위원회',
        '중소벤처기업부': '산업통상자원중소벤처기업위원회',
        '보건복지부': '보건복지위원회', '환경부': '환경노동위원회',
        '고용노동부': '환경노동위원회', '여성가족부': '여성가족위원회',
        '성평등가족부': '여성가족위원회', '국토교통부': '국토교통위원회',
        '국가보훈부': '정무위원회', '국가보훈처': '정무위원회',
        '기후에너지환경부': '환경노동위원회',
        '미래창조과학부': '미래창조과학방송통신위원회', '안전행정부': '안전행정위원회',
        '지식경제부': '지식경제위원회', '국토해양부': '국토해양위원회',
        '행정자치부': '행정안전위원회',
        '재정경제부': '재정경제위원회', '기획예산처': '재정경제위원회',
        '교육인적자원부': '교육위원회', '과학기술부': '과학기술정보통신위원회',
        '정보통신부': '과학기술정보통신위원회', '외교통상부': '통일외교통상위원회',
        '농림부': '농림해양수산위원회', '산업자원부': '산업자원위원회',
        '노동부': '환경노동위원회', '건설교통부': '건설교통위원회',
        '문화관광부': '문화관광위원회',
    }
    PDF_ONLY_YEARS = set(range(2008, 2016))
    AUDIT_WINDOWS = {
        2004: (27430, 27700), 2005: (28300, 28900),
        2006: (29400, 30671), 2007: (31100, 31200),
        2016: (40600, 40700), 2017: (40800, 41050),
        2018: (41050, 41250), 2019: (41200, 41500),
        2020: (44480, 44600), 2021: (44550, 44780),
        2022: (44750, 44900), 2023: (44900, 45400),
        2024: (52000, 55480), 2025: (55480, 55700),
    }

    panel = pd.read_csv(PANEL_FILE)
    panel['start'] = pd.to_datetime(panel['start'], errors='coerce')
    panel['end'] = pd.to_datetime(panel['end'], errors='coerce')
    panel['confirmation_date'] = pd.to_datetime(panel['confirmation_date'], errors='coerce')

    with open(AUDIT_JSON) as f:
        meetings = json.load(f)

    found_pairs = {(m['minister'], m['year']) for m in meetings}
    existing_keys = {(m['minister'], str(m['mnts_id'])) for m in meetings}

    # Filter by command line: --year YYYY or --minister NAME
    year_filter = None
    minister_filter = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == '--year' and i + 1 < len(sys.argv) - 1:
            year_filter = int(sys.argv[i + 2])
        if arg == '--minister' and i + 1 < len(sys.argv) - 1:
            minister_filter = sys.argv[i + 2]

    # Build missing pairs
    missing = []
    for _, row in panel.iterrows():
        name = row['name']
        ministry = row['ministry']
        start = row['start']
        conf = row['confirmation_date']
        end = row['end']
        admin = row['admin']
        dual = str(row['dual_office'])

        if pd.isna(start):
            if pd.isna(conf): continue
            start = conf
        elif not pd.isna(conf):
            start = min(start, conf)
        if pd.isna(end):
            end = pd.Timestamp('2026-12-31')

        committee = MINISTRY_COMMITTEE.get(ministry)
        if not committee: continue

        for y in range(start.year, end.year + 1):
            if y not in AUDIT_WINDOWS: continue
            if y in PDF_ONLY_YEARS: continue
            if year_filter and y != year_filter: continue
            if minister_filter and name != minister_filter: continue
            oct_start = pd.Timestamp(f'{y}-10-01')
            oct_end = pd.Timestamp(f'{y}-10-31')
            if oct_start <= end and oct_end >= start:
                if (name, y) not in found_pairs:
                    missing.append({
                        'name': name, 'ministry': ministry,
                        'admin': admin, 'dual_office': dual,
                        'year': y, 'committee': committee,
                    })

    if not missing:
        print('No missing minister-year pairs found.')
        return

    print(f'Missing pairs to search: {len(missing)}')

    new_results = list(meetings)
    added = 0

    for rec in missing:
        name = rec['name']
        ministry = rec['ministry']
        year = rec['year']
        lo, hi = SEARCH_RANGES.get(year, AUDIT_WINDOWS[year])

        print(f'  Searching {name} ({ministry}) {year}국감 in range {lo}-{hi}...')
        results = search_for_minister(name, ministry, year, lo, hi)

        if results:
            for r in results:
                key = (name, str(r['mnts_id']))
                if key in existing_keys:
                    print(f'    SKIP {r["mnts_id"]}: already found')
                    continue
                entry = {
                    'mnts_id': str(r['mnts_id']),
                    'cmit_nm': r['title'],
                    'year': year,
                    'minister': name,
                    'ministry': ministry,
                    'admin': rec['admin'],
                    'dual_office': rec['dual_office'],
                    'hearing_type': 'AUDIT',
                }
                new_results.append(entry)
                existing_keys.add(key)
                found_pairs.add((name, year))
                print(f'    FOUND {name} @ {r["mnts_id"]}: {r["title"][:55]}')
                added += 1
        else:
            print(f'    NOT FOUND in range')

    new_results.sort(key=lambda x: (x['year'], int(x['mnts_id'])))

    with open(AUDIT_JSON, 'w', encoding='utf-8') as f:
        json.dump(new_results, f, ensure_ascii=False, indent=2)

    print(f'\nAdded: {added} new entries')
    print(f'Total: {len(new_results)} entries')

    from collections import Counter
    print('Year dist:', dict(sorted(Counter(m['year'] for m in new_results).items())))


if __name__ == '__main__':
    main()
