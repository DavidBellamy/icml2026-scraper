#!/usr/bin/env python3
"""Build the HuggingFace dataset: flat, agent-friendly configs in Parquet + CSV,
plus per-day JSON, plus a killer README. Output dir: hf_dataset/"""
import json, re, csv, os, shutil, unicodedata
from datetime import datetime
import pandas as pd

OUT = 'hf_dataset'
DATA = os.path.join(OUT, 'data')
os.makedirs(DATA, exist_ok=True)

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = s.encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s.lower())

WD = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday'}
def day_of(iso):
    if not iso:
        return None
    try:
        return WD[datetime.fromisoformat(iso).weekday()]
    except ValueError:
        return None

# ---- Load sources ----
cal = json.load(open('icml2026_calendar_enriched.json'))
posters = json.load(open('icml2026_posters.json'))
mainconf = json.load(open('icml2026_mainconf_papers.json'))
workshops = json.load(open('icml2026_workshops.json'))
events = json.load(open('icml2026_events_detailed.json'))

# poster_url -> session name/day (from calendar grouping); + oral-title set
poster_session = {}
oral_titles = set()
for day in cal['days']:
    for e in day['events']:
        is_oral = 'oral' in (e.get('title') or '').lower() or e.get('type') == 'Session' and 'Oral' in (e.get('title') or '')
        for c in e['children']:
            if c.get('url') and '/poster/' in c['url']:
                poster_session[c['url']] = {'session': e['title'], 'day': None}
            if 'time' in c and not c.get('url'):        # oral talk (no url) -> title only
                oral_titles.add(norm(c['title']))

# OpenReview main-conf index by normalized title
or_idx = {}
for p in mainconf:
    or_idx.setdefault(norm(p['title']), p)

def tier_type(orp, title):
    if norm(title) in oral_titles:
        return 'oral'
    if orp and 'spotlight' in (orp.get('venue') or '').lower():
        return 'spotlight'
    return 'poster'

# ---- Config 1: papers (the star) ----
papers = []
for p in posters:                                        # main-conference presented papers
    orp = or_idx.get(norm(p['title']))
    sess = poster_session.get(p['url'], {})
    papers.append({
        'track': 'main_conference',
        'paper_type': tier_type(orp, p['title']),
        'title': p['title'],
        'authors': p['authors'],
        'abstract': p.get('abstract'),
        'day': day_of(p.get('start_kst')),
        'date': (p.get('start_kst') or '')[:10] or None,
        'session': sess.get('session'),
        'session_start_kst': p.get('start_kst'),
        'session_end_kst': p.get('end_kst'),
        'location': p.get('location'),
        'workshop': None,
        'url': p['url'],
        'pdf': (orp.get('pdf') if orp else None),
        'openreview': (orp.get('forum') if orp else None),
    })
for w in workshops:                                      # workshop papers
    for p in w.get('papers', []):
        papers.append({
            'track': 'workshop',
            'paper_type': 'workshop',
            'title': p['title'],
            'authors': p['authors'],
            'abstract': p.get('abstract'),
            'day': day_of(w.get('start_kst')),
            'date': (w.get('start_kst') or '')[:10] or None,
            'session': w['title'],
            'session_start_kst': w.get('start_kst'),
            'session_end_kst': w.get('end_kst'),
            'location': w.get('location'),
            'workshop': w['title'],
            'url': p['icml_url'],
            'pdf': p.get('pdf'),
            'openreview': p.get('openreview_forum'),
        })

# ---- Config 2: main_conference_full (all accepted, with PDFs) ----
mc_full = [{
    'title': p['title'], 'authors': p['authors'], 'authorids': p.get('authorids') or [],
    'abstract': p.get('abstract'),
    'venue_tier': ('spotlight' if 'spotlight' in (p.get('venue') or '').lower() else 'regular'),
    'keywords': p.get('keywords') or [], 'primary_area': p.get('primary_area'),
    'pdf': p.get('pdf'), 'openreview': p.get('forum'),
} for p in mainconf]

# ---- Config 3: events (non-paper schedule items) ----
ev_rows = [{
    'day': day_of(e.get('start_kst')), 'date': (e.get('start_kst') or '')[:10] or None,
    'type': e.get('type'), 'title': e.get('title'),
    'organizers': e.get('organizers') or [], 'abstract': e.get('abstract'),
    'speaker_bios': [f"{b['name']}: {b['bio']}" for b in (e.get('speaker_bios') or [])],
    'location': e.get('location'), 'session_start_kst': e.get('start_kst'), 'url': e['url'],
} for e in events]

# ---- Config 4: workshops (metadata) ----
ws_rows = [{
    'title': w['title'], 'day': day_of(w.get('start_kst')),
    'organizers': w.get('organizers') or [], 'abstract': w.get('abstract'),
    'location': w.get('location'), 'num_papers': w.get('num_papers', 0),
    'openreview_venue': w.get('openreview_venue_id'), 'url': w['url'],
} for w in workshops]

# ---- Write parquet + csv ----
def write_config(name, rows):
    df = pd.DataFrame(rows)
    df.to_parquet(os.path.join(DATA, f'{name}.parquet'), index=False)
    # CSV: join list columns with "; "
    dfc = df.copy()
    for col in dfc.columns:
        if dfc[col].apply(lambda x: isinstance(x, list)).any():
            dfc[col] = dfc[col].apply(lambda x: '; '.join(x) if isinstance(x, list) else x)
    dfc.to_csv(os.path.join(DATA, f'{name}.csv'), index=False, quoting=csv.QUOTE_MINIMAL)
    return len(df)

counts = {
    'papers': write_config('papers', papers),
    'main_conference_full': write_config('main_conference_full', mc_full),
    'events': write_config('events', ev_rows),
    'workshops': write_config('workshops', ws_rows),
}

# ---- Copy per-day JSON ----
if os.path.exists(os.path.join(OUT, 'by_day')):
    shutil.rmtree(os.path.join(OUT, 'by_day'))
shutil.copytree('by_day', os.path.join(OUT, 'by_day'))

print('Config row counts:')
for k, v in counts.items():
    print(f'  {v:6d}  {k}')
# coverage stats
pdf = sum(1 for p in papers if p['pdf'])
print(f'\npapers with PDF/OpenReview link: {pdf}/{len(papers)}')
print(f'papers by track:', {t: sum(1 for p in papers if p["track"] == t) for t in ("main_conference", "workshop")})
print(f'paper_type:', {t: sum(1 for p in papers if p["paper_type"] == t) for t in ("oral", "spotlight", "poster", "workshop")})
