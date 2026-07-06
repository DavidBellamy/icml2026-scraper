#!/usr/bin/env python3
"""Finalize event deliverables: add normalized timestamps, write detailed JSON,
a flat events CSV, and a speaker-bios CSV. Also enrich the calendar with abstracts."""
import json, csv
from add_timestamps import parse_session
from datetime import timezone

def norm_ts(rec):
    p = parse_session(rec.get('session'))
    if p:
        su, eu, sk, ek = p
        rec['start_utc'], rec['end_utc'] = su.isoformat(), eu.isoformat()
        rec['start_kst'], rec['end_kst'] = sk.isoformat(), ek.isoformat()
    else:
        rec['start_utc'] = rec['end_utc'] = rec['start_kst'] = rec['end_kst'] = None
    return rec

events = [norm_ts(r) for r in json.load(open('events.json'))]

# Detailed JSON
json.dump(events, open('icml2026_events_detailed.json', 'w'), indent=2, ensure_ascii=False)

# Flat events CSV
with open('icml2026_events.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['type', 'title', 'url', 'organizers', 'location',
                'session', 'start_kst', 'end_kst', 'num_children',
                'has_abstract', 'abstract'])
    for r in sorted(events, key=lambda x: (x.get('start_kst') or 'z', x.get('type') or '')):
        w.writerow([r.get('type'), r.get('title'), r['url'],
                    '; '.join(r.get('organizers') or []), r.get('location'),
                    r.get('session'), r.get('start_kst'), r.get('end_kst'),
                    len(r.get('children') or []),
                    bool(r.get('abstract')), r.get('abstract')])

# Speaker bios CSV
with open('icml2026_speaker_bios.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['speaker', 'event_type', 'event_title', 'url', 'bio'])
    n = 0
    for r in events:
        for b in r.get('speaker_bios') or []:
            w.writerow([b['name'], r.get('type'), r.get('title'), r['url'], b['bio']])
            n += 1

# Enrich calendar: attach event abstracts/organizers/bios to top-level events
by_url = {r['url']: r for r in events}
cal = json.load(open('icml2026_calendar_enriched.json'))
for day in cal['days']:
    for e in day['events']:
        r = by_url.get(e['url'])
        if r:
            if r.get('abstract'):
                e['abstract'] = r['abstract']
            if r.get('organizers'):
                e['organizers'] = r['organizers']
            if r.get('speaker_bios'):
                e['speaker_bios'] = r['speaker_bios']
            for k in ('start_kst', 'end_kst', 'start_utc', 'end_utc'):
                if r.get(k):
                    e[k] = r[k]
json.dump(cal, open('icml2026_calendar_enriched.json', 'w'), indent=2, ensure_ascii=False)

ok = [r for r in events if r.get('ok')]
print(f'events: {len(events)} | with abstract: {sum(1 for r in ok if r.get("abstract"))}'
      f' | with bios: {sum(1 for r in ok if r.get("speaker_bios"))}'
      f' | bios rows: {n}')
print(f'events with normalized time: {sum(1 for r in events if r["start_kst"])}')
