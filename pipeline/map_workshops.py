#!/usr/bin/env python3
"""Map each ICML 2026 workshop to its OpenReview venue ID (by title similarity),
extract each workshop's OpenReview forum link, and write a workshops deliverable."""
import json, re, csv, urllib.request, time
from difflib import SequenceMatcher

UA = 'Mozilla/5.0 research-scrape'

def gv(c, k):
    v = c.get(k)
    return v.get('value') if isinstance(v, dict) else v

def norm(s):
    s = (s or '').lower()
    s = re.sub(r"icml['’]?\s*'?\s*20?26|@|workshop|the\b|\bon\b|\bfor\b|:|,|-", ' ', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')

# 1) OpenReview workshop venues (id, abbrev, title)
u = 'https://api2.openreview.net/groups?parent=ICML.cc/2026/Workshop'
groups = json.load(urllib.request.urlopen(u, timeout=30)).get('groups', [])
venues = []
for g in groups:
    c = g.get('content', {})
    venues.append({'venue_id': g['id'], 'abbrev': g['id'].split('/')[-1],
                   'or_title': gv(c, 'title') or '',
                   'public_submissions': gv(c, 'public_submissions')})

# 2) ICML workshop events (from crawled details)
events = json.load(open('icml2026_events_detailed.json'))
workshops = [e for e in events if e.get('type') == 'Workshop']

# 3) Score every (workshop, venue) pair. Abbreviation appearing as a token in the
#    ICML title is a strong signal (e.g. "(LM4Plan)", "SCALE:"); else title similarity.
def title_tokens(t):
    return set(re.findall(r'[a-z0-9]+', t.lower()))

def pair_score(wtitle, v):
    sim = SequenceMatcher(None, norm(wtitle), norm(v['or_title'])).ratio()
    ab = v['abbrev'].lower()
    if len(ab) >= 3 and ab in title_tokens(wtitle):     # abbrev present as a word
        sim = max(sim, 0.95)
    return sim

# 4) Extract OpenReview forum link from each workshop page (raw HTML)
for w in workshops:
    try:
        h = fetch(w['url'])
        m = re.search(r'openreview\.net/forum\?id=([A-Za-z0-9_-]+)', h)
        w['openreview_forum'] = ('https://openreview.net/forum?id=' + m.group(1)) if m else None
    except Exception as e:  # noqa: BLE001
        w['openreview_forum'] = None
        w['_fetch_err'] = str(e)
    time.sleep(0.05)

# 5) Greedy UNIQUE assignment: sort all pairs by score desc, assign 1:1.
pairs = []
for wi, w in enumerate(workshops):
    for v in venues:
        pairs.append((pair_score(w['title'], v), wi, v))
pairs.sort(key=lambda x: -x[0])
used_w, used_v = set(), set()
assign = {}
for score, wi, v in pairs:
    if wi in used_w or v['venue_id'] in used_v or score < 0.5:
        continue
    used_w.add(wi); used_v.add(v['venue_id']); assign[wi] = (v, score)
# Verified overrides for workshops whose ICML title shares no tokens with the
# OpenReview venue title but was confirmed by hand against the venue title.
# Applied only if the target venue is still unclaimed (keeps assignment 1:1).
VERIFIED = {
    'failure modes in agentic ai': 'FAGEN',        # "Failure Modes of Agentic AI"
    'ai for science: ai scientists': 'AI4Science',  # "AI for Science Workshop"
}
vbab = {v['abbrev']: v for v in venues}
for wi, w in enumerate(workshops):
    if wi in assign:
        continue
    for key, abbrev in VERIFIED.items():
        v = vbab.get(abbrev)
        if key in w['title'].lower() and v and v['venue_id'] not in used_v:
            assign[wi] = (v, 1.0); used_v.add(v['venue_id'])

for wi, w in enumerate(workshops):
    v, score = assign.get(wi, (None, 0.0))
    w['openreview_venue_id'] = v['venue_id'] if v else None
    w['openreview_abbrev'] = v['abbrev'] if v else None
    w['openreview_public_submissions'] = v['public_submissions'] if v else None
    w['_match_score'] = round(score, 2)

# 5) Write deliverables
json.dump(workshops, open('icml2026_workshops.json', 'w'), indent=2, ensure_ascii=False)
with open('icml2026_workshops.csv', 'w', newline='') as f:
    wr = csv.writer(f)
    wr.writerow(['title', 'icml_url', 'organizers', 'location', 'start_kst', 'end_kst',
                 'openreview_venue_id', 'openreview_abbrev', 'public_submissions',
                 'openreview_forum', 'match_score', 'abstract'])
    for w in sorted(workshops, key=lambda x: x.get('start_kst') or 'z'):
        wr.writerow([w['title'], w['url'], '; '.join(w.get('organizers') or []),
                     w.get('location'), w.get('start_kst'), w.get('end_kst'),
                     w.get('openreview_venue_id'), w.get('openreview_abbrev'),
                     w.get('openreview_public_submissions'),
                     w.get('openreview_forum'), w.get('_match_score'), w.get('abstract')])

matched = sum(1 for w in workshops if w.get('openreview_venue_id'))
withforum = sum(1 for w in workshops if w.get('openreview_forum'))
pub = sum(1 for w in workshops if w.get('openreview_public_submissions') is True)
print(f'workshops: {len(workshops)}')
print(f'matched to OpenReview venue: {matched} | with forum link: {withforum} | public submissions: {pub}')
low = [w for w in workshops if w.get('_match_score', 0) < 0.5]
print(f'unmatched (score<0.5): {len(low)}')
for w in low:
    print('   ?', w['title'][:60])
