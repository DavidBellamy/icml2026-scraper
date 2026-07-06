#!/usr/bin/env python3
"""Parse an ICML 2026 event page (session/workshop/invited-talk/tutorial/expo/etc.)
Extracts organizers, abstract/summary, speaker bios, location, time, and child links."""
import re, json, html as htmllib

def _text(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = htmllib.unescape(s)
    s = s.replace('\\%', '%')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def _names(s):
    s = _text(s)
    parts = re.split(r'\s*[⋅·•]\s*', s)
    return [p.strip() for p in parts if p.strip()]

def parse_event(h, url=None, cal_type=None):
    out = {'url': url, 'type': cal_type, 'title': None, 'organizers': [],
           'abstract': None, 'speaker_bios': [], 'location': None,
           'session': None, 'children': []}

    # --- Title ---
    m = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', h, re.S)
    ld = None
    if m:
        try:
            ld = json.loads(m.group(1))
            out['title'] = ld.get('name')
        except json.JSONDecodeError:
            pass
    if not out['title']:
        tm = re.search(r'<title>(.*?)</title>', h, re.S)
        if tm:
            t = _text(tm.group(1))
            # strip leading "ICML <Type> " boilerplate
            t = re.sub(r'^ICML\s+(?:Invited Talk|Tutorial|Expo\s+\w+(?:\s+\w+)?|Poster|Workshop|Oral|Affinity[\w\s]*|Social|Town Hall|Test Of Time)\s+', '', t)
            out['title'] = t

    # --- Organizers / speakers (event-organizers div, body occurrence) ---
    org_ends = [mm.end() for mm in re.finditer(r'event-organizers"[^>]*>', h)]
    if org_ends:
        seg = h[org_ends[-1]:]
        cut = seg.find('</div>')
        seg = seg[:cut if cut > 0 else 600]
        seg = re.split(r'<!--', seg)[0]
        out['organizers'] = _names(seg)
    if not out['organizers'] and ld:
        out['organizers'] = [a.get('name') for a in ld.get('author', []) if a.get('name')]
    # Fallback: expo-style card-subtitle byline
    if not out['organizers']:
        sm = re.search(r'card-subtitle[^>]*>(.*?)</h\d>', h, re.S)
        if sm and ('⋅' in sm.group(1) or _text(sm.group(1))):
            names = _names(sm.group(1))
            # avoid picking up generic subtitles; keep only if looks like names
            if names and len(names) <= 20:
                out['organizers'] = names

    # --- Abstract / summary ---
    am = re.search(r'<div class="abstract-text-inner">(.*?)</div>', h, re.S)
    if am:
        out['abstract'] = _text(am.group(1)) or None
    else:
        # expo-style: card-body with "Abstract:" prefix
        cm = re.search(r'card card-body">(.*?)(?:Live content is unavailable|Log in and register|</div>)', h, re.S)
        if cm:
            txt = _text(cm.group(1))
            txt = re.sub(r'^Abstract:\s*', '', txt)
            out['abstract'] = txt or None

    # --- Speaker bios (invited talks etc.) ---
    for bm in re.finditer(r'speaker-bio-name"[^>]*>(.*?)</(?:h\d|div|p)>.*?speaker-bio-text"[^>]*>(.*?)</div>', h, re.S):
        name = _text(bm.group(1))
        bio = _text(bm.group(2))
        if name and bio:
            out['speaker_bios'].append({'name': name, 'bio': bio})

    # --- Location + session datetime (meta pills) ---
    for pill in re.finditer(r'<span class="meta-pill">(.*?)</span>', h, re.S):
        block = pill.group(1)
        txt = _text(block)
        if 'fa-map-marker' in block:
            out['location'] = txt
        elif 'fa-calendar' in block or re.search(r'\b[AP]M\b', txt):
            if out['session'] is None:
                out['session'] = txt

    # --- Child links (schedule items: posters / papers / talks) ---
    seen = set()
    for cm in re.finditer(r'<a[^>]+href="([^"]*/virtual/2026/(?:poster|workshop-paper|oral|session)/\d+)"[^>]*>(.*?)</a>', h, re.S):
        cu = cm.group(1)
        if '/login' in cu or 'nextp=' in cu:
            continue
        if not cu.startswith('http'):
            cu = 'https://icml.cc' + cu
        title = _text(cm.group(2))
        key = cu.split('#')[0]
        if key not in seen and title:
            seen.add(key)
            out['children'].append({'title': title, 'url': key})
    return out

if __name__ == '__main__':
    import sys
    h = open(sys.argv[1]).read()
    print(json.dumps(parse_event(h, sys.argv[1]), indent=2, ensure_ascii=False))
