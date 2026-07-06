#!/usr/bin/env python3
"""Crawl all top-level event pages (sessions, workshops, invited talks, tutorials,
expo, socials, etc.) and parse organizers/abstracts/bios."""
import json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from parse_event import parse_event

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 research-scrape'

def fetch(url):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last

def worker(ev):
    try:
        h = fetch(ev['url'])
        rec = parse_event(h, ev['url'], ev['type'])
        rec['calendar'] = {k: ev[k] for k in ('date', 'weekday', 'start_time', 'end_time', 'calendar_title')}
        rec['ok'] = bool(rec.get('title'))
        return rec
    except Exception as e:  # noqa: BLE001
        return {'url': ev['url'], 'type': ev['type'], 'ok': False, 'error': str(e)}

def main():
    cal = json.load(open('icml2026_calendar.json'))
    events = []
    for day in cal['days']:
        for e in day['events']:
            events.append({'url': e['url'], 'type': e['type'], 'date': day['date'],
                           'weekday': day['weekday'], 'start_time': e['start_time'],
                           'end_time': e['end_time'], 'calendar_title': e['title']})
    print(f'events to crawl: {len(events)}')
    recs = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = [ex.submit(worker, ev) for ev in events]
        for i, fut in enumerate(as_completed(futs), 1):
            recs.append(fut.result())
    recs.sort(key=lambda r: r['url'])
    json.dump(recs, open('events.json', 'w'), indent=2, ensure_ascii=False)
    ok = [r for r in recs if r.get('ok')]
    print(f'done: {len(ok)}/{len(recs)} ok in {time.time()-t0:.0f}s')
    from collections import Counter
    print('with abstract:', sum(1 for r in ok if r.get('abstract')))
    print('with bios:', sum(1 for r in ok if r.get('speaker_bios')))
    print('by type:', dict(Counter(r.get('type') for r in ok)))

if __name__ == '__main__':
    main()
