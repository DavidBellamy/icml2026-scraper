#!/usr/bin/env python3
"""Crawl all 44 workshop pages via the authenticated ICML session and extract
their schedules (papers with titles/authors/abstracts). Fills the workshops that
aren't on OpenReview and cross-checks the rest.

Usage: source .env.icml && python3 crawl_workshop_schedules.py
"""
import os, sys, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from parse_schedule import parse_schedule

SID = os.environ.get('ICML_SESSIONID', '')
if not SID or SID.startswith('paste-'):
    sys.exit('ERROR: source .env.icml (with your real sessionid) first')

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

def fetch(url):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Cookie': f'sessionid={SID}'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last

def worker(w):
    try:
        h = fetch(w['url'])
        gated = 'Log in and register to view live content' in h
        rows = parse_schedule(h)
        papers = [r for r in rows if r['authors']]        # rows with authors = papers/talks
        return {'title': w['title'], 'url': w['url'],
                'openreview_abbrev': w.get('openreview_abbrev'),
                'openreview_num_papers': w.get('num_papers', 0),
                'login_gated_still': gated,
                'schedule_rows': len(rows), 'schedule_papers': len(papers),
                'papers': papers}
    except Exception as e:  # noqa: BLE001
        return {'title': w['title'], 'url': w['url'], 'error': str(e), 'papers': []}

def main():
    ws = json.load(open('icml2026_workshops.json'))
    results = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(worker, w) for w in ws]
        for fut in as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda r: r['url'])
    json.dump(results, open('icml2026_workshop_schedules.json', 'w'), indent=2, ensure_ascii=False)

    tot_papers = sum(len(r['papers']) for r in results)
    with_abs = sum(1 for r in results for p in r['papers'] if p['abstract'])
    print(f'workshops crawled: {len(results)}')
    print(f'total schedule papers: {tot_papers} | with abstract: {with_abs}')
    print(f'\n{"ABBR":16s} {"OR_papers":>9s} {"ICML_papers":>11s}   title')
    for r in sorted(results, key=lambda x: -len(x['papers'])):
        ab = r.get('openreview_abbrev') or '-'
        print(f'{ab:16s} {r.get("openreview_num_papers",0):9d} {len(r["papers"]):11d}   {r["title"][:38]}')

if __name__ == '__main__':
    main()
