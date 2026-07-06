#!/usr/bin/env python3
"""Consolidate workshop papers: ICML authenticated schedule (complete + abstracts)
as the base, enriched with OpenReview PDF links + author profile IDs by title match.
Updates icml2026_workshop_papers.{json,csv} and icml2026_workshops.json."""
import json, csv, re

def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

# ICML schedule (base) keyed by workshop url
icml = {r['url']: r for r in json.load(open('icml2026_workshop_schedules.json'))}
# OpenReview papers, indexed by normalized title for enrichment
or_by_title = {}
for rec in json.load(open('icml2026_workshop_papers.json')):
    for p in rec.get('papers', []):
        or_by_title.setdefault(norm(p['title']), p)

ws = json.load(open('icml2026_workshops.json'))
consolidated = []
n_papers = n_pdf = n_abs = 0
for w in ws:
    sched = icml.get(w['url'], {})
    papers = []
    for p in sched.get('papers', []):
        orp = or_by_title.get(norm(p['title']))
        rec = {
            'title': p['title'],
            'authors': p['authors'],
            'abstract': p.get('abstract'),
            'icml_url': p['url'],
            'type': p.get('type'),
            'time': p.get('time'),
            'pdf': orp.get('pdf') if orp else None,           # from OpenReview
            'openreview_forum': orp.get('forum') if orp else None,
            'authorids': orp.get('authorids') if orp else None,
        }
        papers.append(rec)
        n_papers += 1
        n_pdf += bool(rec['pdf'])
        n_abs += bool(rec['abstract'])
    w['num_papers'] = len(papers)
    w['papers'] = papers
    consolidated.append({'workshop': w['title'], 'icml_url': w['url'],
                         'openreview_venue_id': w.get('openreview_venue_id'),
                         'num_papers': len(papers), 'papers': papers})

json.dump(ws, open('icml2026_workshops.json', 'w'), indent=2, ensure_ascii=False)
json.dump(consolidated, open('icml2026_workshop_papers.json', 'w'), indent=2, ensure_ascii=False)
with open('icml2026_workshop_papers.csv', 'w', newline='') as f:
    wr = csv.writer(f)
    wr.writerow(['workshop', 'paper_title', 'authors', 'type', 'time',
                 'icml_url', 'pdf', 'openreview_forum', 'abstract'])
    for rec in consolidated:
        for p in rec['papers']:
            wr.writerow([rec['workshop'], p['title'], '; '.join(p['authors']),
                         p.get('type'), p.get('time'), p['icml_url'],
                         p.get('pdf'), p.get('openreview_forum'), p.get('abstract')])

wwp = sum(1 for w in ws if w['num_papers'])
print(f'workshops with papers: {wwp}/44 | total papers: {n_papers}')
print(f'  with abstract: {n_abs} | with PDF (from OpenReview match): {n_pdf}')
