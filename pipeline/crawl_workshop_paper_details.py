#!/usr/bin/env python3
"""For workshop papers lacking a PDF link, crawl their ICML detail page
(authenticated) to recover the OpenReview forum id -> forum + PDF URLs.

Usage: source .env.icml && python3 crawl_workshop_paper_details.py
"""
import os, sys, re, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

SID = os.environ.get('ICML_SESSIONID', '')
if not SID or SID.startswith('paste-'):
    sys.exit('ERROR: source .env.icml first')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

def fetch(url):
    last = None
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Cookie': f'sessionid={SID}'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # noqa: BLE001
            last = e; time.sleep(1.0 * (a + 1))
    raise last

def get_forum(url):
    try:
        h = fetch(url)
        m = re.search(r'openreview\.net/forum\?id=([A-Za-z0-9_-]+)', h)
        return m.group(1) if m else None
    except Exception:
        return None

ws = json.load(open('icml2026_workshops.json'))
targets = {p['icml_url'] for w in ws for p in w['papers'] if not p.get('pdf')}
print(f'no-PDF papers to resolve: {len(targets)}')

forum_by_url = {}
t0 = time.time()
with ThreadPoolExecutor(max_workers=16) as ex:
    futs = {ex.submit(get_forum, u): u for u in targets}
    for i, fut in enumerate(as_completed(futs), 1):
        forum_by_url[futs[fut]] = fut.result()
        if i % 300 == 0:
            print(f'  {i}/{len(targets)}  ({i/(time.time()-t0):.0f}/s)')

# Apply: set openreview_forum + pdf where a forum was found
n_found = 0
for w in ws:
    for p in w['papers']:
        if p.get('pdf'):
            continue
        fid = forum_by_url.get(p['icml_url'])
        if fid:
            p['openreview_forum'] = f'https://openreview.net/forum?id={fid}'
            p['pdf'] = f'https://openreview.net/pdf?id={fid}'
            n_found += 1

json.dump(ws, open('icml2026_workshops.json', 'w'), indent=2, ensure_ascii=False)

# rebuild consolidated workshop_papers.{json,csv} from workshops.json
import csv
consolidated = [{'workshop': w['title'], 'icml_url': w['url'],
                 'openreview_venue_id': w.get('openreview_venue_id'),
                 'num_papers': w['num_papers'], 'papers': w['papers']} for w in ws]
json.dump(consolidated, open('icml2026_workshop_papers.json', 'w'), indent=2, ensure_ascii=False)
with open('icml2026_workshop_papers.csv', 'w', newline='') as f:
    wr = csv.writer(f)
    wr.writerow(['workshop', 'paper_title', 'authors', 'type', 'time', 'icml_url',
                 'pdf', 'openreview_forum', 'abstract'])
    for rec in consolidated:
        for p in rec['papers']:
            wr.writerow([rec['workshop'], p['title'], '; '.join(p['authors']), p.get('type'),
                         p.get('time'), p['icml_url'], p.get('pdf'), p.get('openreview_forum'),
                         p.get('abstract')])

total = sum(w['num_papers'] for w in ws)
withpdf = sum(1 for w in ws for p in w['papers'] if p.get('pdf'))
noforum = len(targets) - n_found
print(f'\nresolved forum/PDF for {n_found} more papers')
print(f'workshop papers: {total} | with PDF now: {withpdf} | still none (likely invited talks): {noforum}')
