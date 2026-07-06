#!/usr/bin/env python3
"""Split all conference data into per-day directories (by_day/<weekday>/).
Source of truth = enriched calendar's day grouping (Seoul-time conference day)."""
import json, csv, os, glob
import tiktoken

_enc = tiktoken.get_encoding('o200k_base')  # proxy tokenizer; ~±10-15% vs Claude's
def count_tokens(s):
    return len(_enc.encode(s))

WEEKDAY = {'SUN': 'sunday', 'MON': 'monday', 'TUE': 'tuesday', 'WED': 'wednesday',
           'THU': 'thursday', 'FRI': 'friday', 'SAT': 'saturday'}
ROOT = 'by_day'

def daydir(day):
    # e.g. "monday-july6" from weekday MON + date "6 JUL 2026"
    dnum = day['date'].split()[0]
    return f"{WEEKDAY[day['weekday']]}-july{dnum}"

cal = json.load(open('icml2026_calendar_enriched.json'))
posters = {p['url']: p for p in json.load(open('icml2026_posters.json'))}
events = {e['url']: e for e in json.load(open('icml2026_events_detailed.json'))}
workshops = {w['url']: w for w in json.load(open('icml2026_workshops.json'))}

POSTER_COLS = ['url', 'title', 'authors', 'num_authors', 'location', 'session',
               'start_kst', 'end_kst', 'start_utc', 'end_utc', 'date_published', 'abstract']
EVENT_COLS = ['type', 'title', 'url', 'organizers', 'location', 'session',
              'start_kst', 'end_kst', 'num_children', 'has_abstract', 'abstract']
WS_COLS = ['title', 'icml_url', 'organizers', 'location', 'start_kst', 'end_kst',
           'openreview_venue_id', 'openreview_abbrev', 'num_papers',
           'openreview_forum', 'abstract']

def w_json(path, obj):
    json.dump(obj, open(path, 'w'), indent=2, ensure_ascii=False)

def poster_row(p):
    return [p['url'], p['title'], '; '.join(p['authors']), len(p['authors']),
            p.get('location'), p.get('session'), p.get('start_kst'), p.get('end_kst'),
            p.get('start_utc'), p.get('end_utc'), p.get('date_published'), p.get('abstract')]

def event_row(e):
    return [e.get('type'), e.get('title'), e['url'], '; '.join(e.get('organizers') or []),
            e.get('location'), e.get('session'), e.get('start_kst'), e.get('end_kst'),
            len(e.get('children') or []), bool(e.get('abstract')), e.get('abstract')]

def ws_row(w):
    return [w['title'], w['url'], '; '.join(w.get('organizers') or []), w.get('location'),
            w.get('start_kst'), w.get('end_kst'), w.get('openreview_venue_id'),
            w.get('openreview_abbrev'), w.get('num_papers', 0),
            w.get('openreview_forum'), w.get('abstract')]

def write_csv(path, cols, rows):
    with open(path, 'w', newline='') as f:
        wr = csv.writer(f); wr.writerow(cols); wr.writerows(rows)

summary = []
for day in cal['days']:
    wd = daydir(day)
    d = os.path.join(ROOT, wd)
    os.makedirs(d, exist_ok=True)

    # Events that day (full detailed records)
    day_events = [events[e['url']] for e in day['events'] if e['url'] in events]
    # Posters that day (full records, from poster child links)
    purls = [c['url'] for e in day['events'] for c in e['children']
             if c.get('url') and '/poster/' in c['url']]
    purls = list(dict.fromkeys(purls))               # dedup, preserve order
    day_posters = [posters[u] for u in purls if u in posters]
    # Workshops that day
    day_ws = [workshops[e['url']] for e in day['events']
              if e.get('type') == 'Workshop' and e['url'] in workshops]

    # Per-day nested schedule (human-readable slice of the calendar)
    w_json(os.path.join(d, 'schedule.json'),
           {'weekday': day['weekday'], 'date': day['date'],
            'timezone': cal['timezone'], 'events': day['events']})

    # Events
    w_json(os.path.join(d, 'events.json'), day_events)
    write_csv(os.path.join(d, 'events.csv'), EVENT_COLS, [event_row(e) for e in day_events])

    # Posters (only on days that have them)
    if day_posters:
        w_json(os.path.join(d, 'posters.json'), day_posters)
        write_csv(os.path.join(d, 'posters.csv'), POSTER_COLS, [poster_row(p) for p in day_posters])
    # Workshops (only on days that have them)
    if day_ws:
        w_json(os.path.join(d, 'workshops.json'), day_ws)
        write_csv(os.path.join(d, 'workshops.csv'), WS_COLS, [ws_row(w) for w in day_ws])

    # Token counts for this day: pure content (text fields) + raw JSON files
    def poster_text(p):
        return ' '.join(filter(None, [p['title'], ' '.join(p['authors']), p.get('abstract') or '']))
    def event_text(e):
        parts = [e.get('title') or '', ' '.join(e.get('organizers') or []), e.get('abstract') or '']
        for b in e.get('speaker_bios') or []:
            parts += [b['name'], b['bio']]
        return ' '.join(parts)
    def ws_paper_text(w):
        return ' '.join(count_src for p in (w.get('papers') or [])
                        for count_src in [p.get('title') or '',
                                          ' '.join(p.get('authors') or []),
                                          p.get('abstract') or ''])
    content_tok = (sum(count_tokens(poster_text(p)) for p in day_posters)
                   + sum(count_tokens(event_text(e)) for e in day_events)
                   + sum(count_tokens(ws_paper_text(w)) for w in day_ws))
    json_tok = sum(count_tokens(open(f).read())
                   for f in glob.glob(os.path.join(d, '*.json')))

    ws_papers = sum(w.get('num_papers', 0) for w in day_ws)
    ws_pdfs = sum(1 for w in day_ws for p in (w.get('papers') or []) if p.get('pdf'))
    summary.append((wd, day['date'], len(day_events), len(day_posters), len(day_ws),
                    content_tok, json_tok, ws_papers, ws_pdfs))

# Top-level index
idx = {'source': cal['source'], 'timezone': cal['timezone'],
       'token_note': 'Approx tokens via tiktoken o200k_base (~±10-15% vs Claude). '
                     'content_tokens = text fields only; json_tokens = raw .json files in the dir.',
       'totals': {'events': sum(s[2] for s in summary),
                  'posters': sum(s[3] for s in summary),
                  'workshops': sum(s[4] for s in summary),
                  'workshop_papers': sum(s[7] for s in summary),
                  'workshop_paper_pdfs': sum(s[8] for s in summary),
                  'content_tokens': sum(s[5] for s in summary),
                  'json_tokens': sum(s[6] for s in summary)},
       'days': [{'dir': f'by_day/{wd}', 'date': dt,
                 'events': ne, 'posters': npz, 'workshops': nw, 'workshop_papers': wp,
                 'content_tokens': ct, 'json_tokens': jt}
                for wd, dt, ne, npz, nw, ct, jt, wp, _ in summary]}
w_json(os.path.join(ROOT, 'index.json'), idx)

print(f'{"DAY":16s} {"EVENTS":>7s} {"POSTERS":>8s} {"WS":>4s} {"WS_PAPERS":>9s} {"CONTENT_TOK":>12s} {"JSON_TOK":>10s}')
for wd, dt, ne, npz, nw, ct, jt, wp, _ in summary:
    print(f'{wd:16s} {ne:7d} {npz:8d} {nw:4d} {wp:9d} {ct:12,d} {jt:10,d}')
print(f'\nTotals: posters={sum(s[3] for s in summary)}  workshops={sum(s[4] for s in summary)}  '
      f'workshop_papers={sum(s[7] for s in summary)}  events={sum(s[2] for s in summary)}  '
      f'content_tok={sum(s[5] for s in summary):,}')
