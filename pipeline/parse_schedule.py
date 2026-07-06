#!/usr/bin/env python3
"""Parse a logged-in ICML workshop page's schedule into paper/talk rows."""
import re, html

def _txt(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html.unescape(s))).strip()

def parse_schedule(h):
    """Return list of rows: {title, url, authors[], abstract, time, type}."""
    rows = []
    for chunk in re.split(r'<tr class="schedule-row"', h)[1:]:
        name = re.search(r'schedule-event-name">\s*<a href="(/virtual/2026/\d+)">(.*?)</a>', chunk, re.S)
        if not name:
            continue
        auth = re.search(r'schedule-authors">(.*?)</div>', chunk, re.S)
        absm = re.search(r'schedule-abstract"[^>]*>(.*?)</div>', chunk, re.S)
        tm = re.search(r'schedule-time">(.*?)</span>', chunk, re.S)
        typ = re.search(r'schedule-event-type"[^>]*>(.*?)</a>', chunk, re.S)
        authors = [a for a in re.split(r'\s*[⋅·•]\s*', _txt(auth.group(1))) if a] if auth else []
        rows.append({
            'title': _txt(name.group(2)),
            'url': 'https://icml.cc' + name.group(1),
            'authors': authors,
            'abstract': _txt(absm.group(1)) if absm else None,
            'time': _txt(tm.group(1)) if tm else None,
            'type': _txt(typ.group(1)) if typ else None,
        })
    return rows

if __name__ == '__main__':
    import sys, json
    rows = parse_schedule(open(sys.argv[1]).read())
    papers = [r for r in rows if r['authors']]
    print(f'rows: {len(rows)} | with authors (papers): {len(papers)} | with abstract: {sum(1 for r in rows if r["abstract"])}')
    print(json.dumps(papers[:2], indent=2, ensure_ascii=False))
