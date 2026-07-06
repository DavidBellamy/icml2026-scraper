#!/usr/bin/env python3
"""Parse a single ICML poster HTML page into a dict."""
import re, json, html as htmllib

def _text(s):
    s = re.sub(r'<[^>]+>', '', s)          # strip tags
    s = htmllib.unescape(s)                # &bull; &amp; etc.
    s = s.replace('\\%', '%')              # latex-ish escapes seen in abstracts
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\s*\n\s*', ' ', s)
    return s.strip()

def parse_poster(h, url=None):
    out = {'url': url, 'title': None, 'authors': [],
           'abstract': None, 'location': None, 'session': None,
           'date_published': None}

    # --- JSON-LD: title, authors, dates (gold standard) ---
    m = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', h, re.S)
    if m:
        try:
            ld = json.loads(m.group(1))
            out['title'] = ld.get('name')
            auth = ld.get('author') or []
            out['authors'] = [a.get('name') for a in auth if a.get('name')]
            out['date_published'] = ld.get('datePublished')
        except json.JSONDecodeError:
            pass

    # Fallback title from <title>ICML Poster ...</title>
    if not out['title']:
        tm = re.search(r'<title>\s*ICML\s+\w+\s+(.*?)</title>', h, re.S)
        if tm:
            out['title'] = _text(tm.group(1))

    # --- Abstract ---
    am = re.search(r'<div class="abstract-text-inner">(.*?)</div>\s*(?:<div|<button|<a|<span|$)',
                   h, re.S)
    if not am:
        am = re.search(r'<div class="abstract-text-inner">(.*?)</div>', h, re.S)
    if am:
        out['abstract'] = _text(am.group(1)) or None

    # --- Meta pills: location (map marker) + session datetime (calendar) ---
    for pill in re.finditer(r'<span class="meta-pill">(.*?)</span>', h, re.S):
        block = pill.group(1)
        txt = _text(block)
        if 'fa-map-marker' in block:
            out['location'] = txt
        elif 'fa-calendar' in block or re.search(r'\b(AM|PM)\b', txt):
            if out['session'] is None:
                out['session'] = txt
    return out

if __name__ == '__main__':
    import sys
    h = open(sys.argv[1] if len(sys.argv) > 1 else '.firecrawl/raw-poster.html').read()
    print(json.dumps(parse_poster(h, 'https://icml.cc/virtual/2026/poster/66738'),
                     indent=2, ensure_ascii=False))
