#!/usr/bin/env python3
"""Merge crawled poster details into final JSON + CSV deliverables,
and enrich the calendar tree with authors/abstracts."""
import json, csv

posters = {}
for line in open('posters.jsonl'):
    r = json.loads(line)
    if r.get('ok'):
        posters[r['url']] = r

# 1) Standalone posters JSON (sorted by url)
poster_list = [posters[u] for u in sorted(posters)]
for r in poster_list:
    r.pop('ok', None)
json.dump(poster_list, open('icml2026_posters.json', 'w'),
          indent=2, ensure_ascii=False)

# 2) Standalone posters CSV
with open('icml2026_posters.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['url', 'title', 'authors', 'num_authors',
                'location', 'session', 'date_published', 'abstract'])
    for r in poster_list:
        w.writerow([r['url'], r['title'], '; '.join(r['authors']),
                    len(r['authors']), r.get('location'), r.get('session'),
                    r.get('date_published'), r.get('abstract')])

# 3) Enrich the calendar tree: attach authors/abstract to each poster child
cal = json.load(open('icml2026_calendar.json'))
n_enriched = 0
for day in cal['days']:
    for e in day['events']:
        for c in e['children']:
            u = c.get('url')
            if u and u in posters:
                p = posters[u]
                c['authors'] = p['authors']
                c['abstract'] = p.get('abstract')
                c['location'] = p.get('location')
                n_enriched += 1
json.dump(cal, open('icml2026_calendar_enriched.json', 'w'),
          indent=2, ensure_ascii=False)

print(f'posters: {len(poster_list)}')
print(f'calendar children enriched: {n_enriched}')

# quick author leaderboard
from collections import Counter
ac = Counter()
for r in poster_list:
    for a in r['authors']:
        ac[a] += 1
print('\nTop 10 authors by poster count:')
for a, c in ac.most_common(10):
    print(f'  {c:3d}  {a}')
