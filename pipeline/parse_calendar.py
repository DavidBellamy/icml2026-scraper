#!/usr/bin/env python3
"""Parse the scraped ICML 2026 calendar markdown into structured JSON + CSV."""
import json, re, csv

d = json.load(open('.firecrawl/icml-calendar.json'))
md = d['markdown']

# Locate the schedule body: starts at first day header
DAY_RE = re.compile(r'^(SUN|MON|TUE|WED|THU|FRI|SAT) (\d+) ([A-Z]{3})$')
TIME_RE = re.compile(r'^(?:\d{1,2}(?::\d{2})?\s?(?:a\.m\.|p\.m\.)|noon|midnight)$')
LINK_RE = re.compile(r'^\[(.+?)\]\((https?://[^)]+)\)$', re.S)
ENDS_RE = re.compile(r'^\(ends (.+?)\)$')
ORAL_TIME_RE = re.compile(r'^\\\[(\d{1,2}:\d{2})\\\]$')

# Split body into paragraphs (blocks separated by blank lines)
start = md.find('SUN 5 JUL')
body = md[start:]
paras = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]

days = []
cur_day = None
cur_time = None
pending_type = None
cur_event = None      # current top-level event dict
mode = None           # None | 'oral' | 'poster'
pending_oral_time = None

def clean_session_title(t):
    # session titles arrive like "Oral 3A Diffusion Models\\\n\\\n\[10:00-11:00\]"
    t = t.replace('\\', '')            # drop markdown escape backslashes
    t = re.sub(r'\s*\n\s*', ' ', t)    # collapse newlines
    t = re.sub(r'\s+', ' ', t).strip() # collapse runs of spaces
    return t

for p in paras:
    m = DAY_RE.match(p)
    if m:
        wd, dnum, mon = m.groups()
        cur_day = {'weekday': wd, 'date': f'{dnum} {mon} 2026',
                   'day': int(dnum), 'month': mon, 'events': []}
        days.append(cur_day)
        cur_time = None; pending_type = None; cur_event = None; mode = None
        continue
    if cur_day is None:
        continue

    if TIME_RE.match(p):
        cur_time = p
        pending_type = None
        cur_event = None
        mode = None
        continue

    # Event type marker, e.g. "Poster Session:" / "Tutorial:" / "Expo Talk Panel:"
    if p.endswith(':') and '\n' not in p and not p.startswith('['):
        pending_type = p[:-1].strip()
        continue

    lm = LINK_RE.match(p)
    if lm:
        title_raw, url = lm.groups()
        # Skip non-event links (footer contact/help links that leak into the body)
        if '/virtual/2026/' not in url:
            continue
        # Is this a child poster link inside a session?
        is_poster = '/poster/' in url
        if mode == 'poster' and is_poster and cur_event is not None:
            cur_event['children'].append({'title': title_raw.strip(), 'url': url})
            continue
        # Otherwise it's a new top-level event
        title = clean_session_title(title_raw)
        is_session = '/session/' in url
        # Infer type from URL slug when no "Type:" marker preceded (e.g. Registration Desk)
        url_type = None
        um = re.search(r'/virtual/2026/([a-z-]+)/\d+', url)
        if um:
            url_type = um.group(1).replace('-', ' ').title()
        cur_event = {
            'type': pending_type or url_type or ('Session' if is_session else None),
            'title': title,
            'url': url,
            'start_time': cur_time,
            'end_time': None,
            'speakers': [],
            'children': [],
        }
        cur_day['events'].append(cur_event)
        pending_type = None
        mode = 'session' if is_session else None
        pending_oral_time = None
        continue

    em = ENDS_RE.match(p)
    if em and cur_event is not None:
        cur_event['end_time'] = em.group(1)
        continue

    # Oral sub-talk time marker like \[10:00\]
    om = ORAL_TIME_RE.match(p)
    if om and cur_event is not None:
        pending_oral_time = om.group(1)
        mode = 'oral'
        continue

    # A bare "Orals 10:00-11:00" / "Posters 10:30-12:15" descriptor
    if re.match(r'^(Orals|Posters)\s', p):
        mode = 'poster' if p.startswith('Posters') else 'oral'
        continue

    # Plain text paragraph: oral talk title, or speaker name, attached to current event
    if cur_event is not None and '\n' not in p:
        if mode == 'oral' and pending_oral_time is not None:
            cur_event['children'].append({'time': pending_oral_time, 'title': p})
            pending_oral_time = None
        else:
            # speaker / descriptor line
            cur_event['speakers'].append(p)
        continue

# ---- Write outputs ----
out = {
    'source': 'https://icml.cc/virtual/2026/calendar',
    'timezone': 'Asia/Seoul',
    'days': days,
}
json.dump(out, open('icml2026_calendar.json', 'w'), indent=2, ensure_ascii=False)

# Flat CSV of top-level events
with open('icml2026_events.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['date', 'weekday', 'start_time', 'end_time', 'type', 'title', 'url', 'num_children', 'speakers'])
    for day in days:
        for e in day['events']:
            w.writerow([day['date'], day['weekday'], e['start_time'], e['end_time'],
                        e['type'], e['title'], e['url'], len(e['children']),
                        '; '.join(e['speakers'])])

# Flat CSV of every poster/talk child
with open('icml2026_papers.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['date', 'session_type', 'session_title', 'session_url', 'child_time', 'child_title', 'child_url'])
    for day in days:
        for e in day['events']:
            for c in e['children']:
                w.writerow([day['date'], e['type'], e['title'], e['url'],
                            c.get('time', ''), c['title'], c.get('url', '')])

# ---- Summary ----
n_events = sum(len(day['events']) for day in days)
n_children = sum(len(e['children']) for day in days for e in day['events'])
from collections import Counter
types = Counter(e['type'] for day in days for e in day['events'])
print(f'Days: {len(days)}')
print(f'Top-level events: {n_events}')
print(f'Nested items (posters/orals): {n_children}')
print('\nEvents by type:')
for t, c in types.most_common():
    print(f'  {c:4d}  {t}')
print('\nPer day:')
for day in days:
    ch = sum(len(e["events"]) for e in [day])
    kids = sum(len(e['children']) for e in day['events'])
    print(f'  {day["weekday"]} {day["date"]}: {len(day["events"])} events, {kids} nested items')
