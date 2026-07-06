#!/usr/bin/env python3
"""Merge fetched OpenReview workshop papers into the workshop records and the
per-day build inputs. Updates icml2026_workshops.json in place."""
import json

papers_by_venue = {r['venue_id']: r['papers']
                   for r in json.load(open('icml2026_workshop_papers.json'))}

ws = json.load(open('icml2026_workshops.json'))
n_with = 0
for w in ws:
    vid = w.get('openreview_venue_id')
    papers = papers_by_venue.get(vid, []) if vid else []
    w['num_papers'] = len(papers)
    w['papers'] = papers
    if papers:
        n_with += 1
json.dump(ws, open('icml2026_workshops.json', 'w'), indent=2, ensure_ascii=False)

total = sum(w['num_papers'] for w in ws)
print(f'workshops: {len(ws)} | with papers: {n_with} | total papers merged: {total}')
