#!/usr/bin/env python3
"""Authenticated OpenReview fetch of ICML 2026 workshop papers.

Usage:
    source .env.openreview && python3 fetch_openreview_authed.py

Reads OPENREVIEW_USERNAME / OPENREVIEW_PASSWORD from the environment, logs in,
validates access on the main conference venue, then pulls every workshop venue's
papers (title/authors/abstract/pdf). Writes icml2026_workshop_papers.{json,csv}.
"""
import os, sys, json, csv, time
import openreview

USER = os.environ.get('OPENREVIEW_USERNAME')
PASS = os.environ.get('OPENREVIEW_PASSWORD')

if not USER or not PASS or USER.startswith('your-email'):
    sys.exit('ERROR: set real creds first:  source .env.openreview  (edit the file)')

def gv(note, k):
    v = note.content.get(k)
    return v.get('value') if isinstance(v, dict) else v

print(f'Logging in as {USER} ...')
client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net',
                                         username=USER, password=PASS)
print('Authenticated. Token acquired.')

# --- Validation: main conference should return thousands of accepted papers ---
try:
    conf = client.get_all_notes(content={'venueid': 'ICML.cc/2026/Conference'})
    print(f'VALIDATION: main conference notes = {len(conf)} (expect thousands)')
except openreview.OpenReviewException as e:
    print(f'VALIDATION failed: {e}')
    conf = []

# --- Workshop venues from our mapping ---
ws = json.load(open('icml2026_workshops.json'))
venue_ids = sorted({w['openreview_venue_id'] for w in ws if w.get('openreview_venue_id')})
title_by_venue = {w['openreview_venue_id']: w['title'] for w in ws if w.get('openreview_venue_id')}

def fetch_venue(vid):
    """Try venueid then common submission suffixes; return list of notes."""
    for q in (vid, vid + '/Submission', vid + '/Blind_Submission'):
        try:
            notes = client.get_all_notes(content={'venueid': q})
        except openreview.OpenReviewException:
            notes = []
        if notes:
            return notes
    # fall back to submission invitation
    for inv in (vid + '/-/Submission', vid + '/-/Blind_Submission'):
        try:
            notes = client.get_all_notes(invitation=inv)
        except openreview.OpenReviewException:
            notes = []
        if notes:
            return notes
    return []

out, total = [], 0
print(f'\nFetching {len(venue_ids)} workshop venues...')
for vid in venue_ids:
    notes = fetch_venue(vid)
    papers = []
    for n in notes:
        papers.append({
            'id': n.id,
            'title': gv(n, 'title'),
            'authors': gv(n, 'authors') or [],
            'abstract': gv(n, 'abstract'),
            'venue': gv(n, 'venue'),
            'forum': f'https://openreview.net/forum?id={n.forum}',
            'pdf': (f"https://openreview.net{gv(n, 'pdf')}" if gv(n, 'pdf') else None),
        })
    total += len(papers)
    out.append({'venue_id': vid, 'workshop': title_by_venue.get(vid),
                'num_papers': len(papers), 'papers': papers})
    print(f'  {len(papers):4d}  {vid}')
    time.sleep(0.2)

json.dump(out, open('icml2026_workshop_papers.json', 'w'), indent=2, ensure_ascii=False)
with open('icml2026_workshop_papers.csv', 'w', newline='') as f:
    wr = csv.writer(f)
    wr.writerow(['workshop', 'venue_id', 'paper_title', 'authors', 'forum', 'pdf', 'abstract'])
    for rec in out:
        for p in rec['papers']:
            wr.writerow([rec['workshop'], rec['venue_id'], p['title'],
                         '; '.join(p['authors']), p['forum'], p['pdf'], p['abstract']])

print(f'\nTOTAL workshop papers fetched: {total}')
if total == 0:
    print('Still 0 -> papers are role-restricted (not just login-gated); the ICML '
          'registration route is needed instead.')
