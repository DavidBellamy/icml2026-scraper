#!/usr/bin/env python3
"""Normalize poster session times (shown in PDT) into UTC and Asia/Seoul (KST).
Adds start_utc/end_utc/start_kst/end_kst ISO-8601 columns."""
import json, csv, re
from datetime import datetime, timedelta, timezone

# US timezone abbreviations -> UTC offset (hours). ICML July => daylight time.
TZ_OFFSETS = {'PDT': -7, 'PST': -8, 'EDT': -4, 'EST': -5,
              'CDT': -5, 'CST': -6, 'MDT': -6, 'MST': -7, 'UTC': 0, 'GMT': 0}
KST = timezone(timedelta(hours=9))

MONTHS = {m: i for i, m in enumerate(
    ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)}

# e.g. "Wed, Jul 8, 2026 • 1:00 AM – 2:45 AM PDT"
SESS_RE = re.compile(
    r'\w+,\s*(\w+)\s+(\d+),\s*(\d{4})\s*[•·]\s*'
    r'(\d{1,2}):(\d{2})\s*([AP]M)\s*[–\-—]\s*'
    r'(\d{1,2}):(\d{2})\s*([AP]M)\s*([A-Z]{2,4})')

def _to_24(h, m, ampm):
    h = int(h) % 12
    if ampm == 'PM':
        h += 12
    return h, int(m)

def parse_session(s):
    """Return (start_utc, end_utc, start_kst, end_kst) as tz-aware datetimes, or None."""
    if not s:
        return None
    m = SESS_RE.search(s)
    if not m:
        return None
    mon, day, year, sh, sm, sap, eh, em, eap, tz = m.groups()
    off = TZ_OFFSETS.get(tz)
    if off is None or mon not in MONTHS:
        return None
    tzinfo = timezone(timedelta(hours=off))
    sh24, sm2 = _to_24(sh, sm, sap)
    eh24, em2 = _to_24(eh, em, eap)
    start = datetime(int(year), MONTHS[mon], int(day), sh24, sm2, tzinfo=tzinfo)
    end = datetime(int(year), MONTHS[mon], int(day), eh24, em2, tzinfo=tzinfo)
    if end <= start:                 # crosses midnight
        end += timedelta(days=1)
    su, eu = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    return su, eu, su.astimezone(KST), eu.astimezone(KST)

def enrich(rec):
    p = parse_session(rec.get('session'))
    if p:
        su, eu, sk, ek = p
        rec['start_utc'] = su.isoformat()
        rec['end_utc'] = eu.isoformat()
        rec['start_kst'] = sk.isoformat()
        rec['end_kst'] = ek.isoformat()
    else:
        rec['start_utc'] = rec['end_utc'] = rec['start_kst'] = rec['end_kst'] = None
    return rec

def main():
    posters = [enrich(p) for p in json.load(open('icml2026_posters.json'))]
    json.dump(posters, open('icml2026_posters.json', 'w'), indent=2, ensure_ascii=False)

    parsed = sum(1 for p in posters if p['start_utc'])
    print(f'posters: {len(posters)} | timestamps parsed: {parsed} | failed: {len(posters)-parsed}')

    with open('icml2026_posters.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['url', 'title', 'authors', 'num_authors', 'location', 'session',
                    'start_utc', 'end_utc', 'start_kst', 'end_kst',
                    'date_published', 'abstract'])
        for r in posters:
            w.writerow([r['url'], r['title'], '; '.join(r['authors']), len(r['authors']),
                        r.get('location'), r.get('session'),
                        r.get('start_utc'), r.get('end_utc'), r.get('start_kst'), r.get('end_kst'),
                        r.get('date_published'), r.get('abstract')])

    # sample
    for r in posters[:2]:
        print(f"  {r['session']}\n    -> KST {r['start_kst']}  |  UTC {r['start_utc']}")

if __name__ == '__main__':
    main()
