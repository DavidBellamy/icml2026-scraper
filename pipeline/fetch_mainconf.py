#!/usr/bin/env python3
"""Pull ALL ICML 2026 main-conference papers from OpenReview (authenticated),
with PDF links + author profile IDs. Cross-references our calendar poster set
to flag the papers we didn't previously have.

Usage: source .env.openreview && python3 fetch_mainconf.py
"""
import os, json, csv, re
import openreview

USER, PASS = os.environ.get('OPENREVIEW_USERNAME'), os.environ.get('OPENREVIEW_PASSWORD')

def gv(note, k):
    v = note.content.get(k)
    return v.get('value') if isinstance(v, dict) else v

client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net',
                                         username=USER, password=PASS)
print('Authenticated. Pulling main-conference notes...')
notes = client.get_all_notes(content={'venueid': 'ICML.cc/2026/Conference'})
print(f'main-conference papers: {len(notes)}')

papers = []
for n in notes:
    pdf = gv(n, 'pdf')
    papers.append({
        'id': n.id,
        'forum': f'https://openreview.net/forum?id={n.forum}',
        'title': gv(n, 'title'),
        'authors': gv(n, 'authors') or [],
        'authorids': gv(n, 'authorids') or [],       # unique profile IDs (~First_Last1)
        'abstract': gv(n, 'abstract'),
        'venue': gv(n, 'venue'),                       # "ICML 2026 regular" / "spotlight"
        'pdf': (f'https://openreview.net{pdf}' if pdf else None),
        'keywords': gv(n, 'keywords') or [],
        'primary_area': gv(n, 'primary_area'),
    })

json.dump(papers, open('icml2026_mainconf_papers.json', 'w'), indent=2, ensure_ascii=False)
with open('icml2026_mainconf_papers.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['forum', 'title', 'authors', 'authorids', 'venue', 'primary_area',
                'keywords', 'pdf', 'abstract'])
    for p in papers:
        w.writerow([p['forum'], p['title'], '; '.join(p['authors']), '; '.join(p['authorids']),
                    p['venue'], p['primary_area'], '; '.join(p['keywords']), p['pdf'], p['abstract']])

# --- Cross-reference with calendar poster set ---
def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

cal_titles = {norm(p['title']) for p in json.load(open('icml2026_posters.json'))}
or_titles = {norm(p['title']) for p in papers}
extra = [p for p in papers if norm(p['title']) not in cal_titles]      # on OR, not in our posters
missing_from_or = cal_titles - or_titles                              # in our posters, not matched on OR

from collections import Counter
print(f'\nwith PDF link: {sum(1 for p in papers if p["pdf"])}/{len(papers)}')
print('by venue tier:', dict(Counter(p["venue"] for p in papers)))
print(f'\nCross-reference vs our {len(cal_titles)} calendar posters:')
print(f'  papers on OpenReview NOT in our poster set: {len(extra)}')
print(f'  our posters NOT title-matched on OpenReview: {len(missing_from_or)}')
print('  (tier of the extras):', dict(Counter(p["venue"] for p in extra)))
