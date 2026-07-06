#!/usr/bin/env python3
"""Probe whether the ICML sessionid cookie unlocks login-gated workshop schedules.

Usage: source .env.icml && python3 probe_icml_auth.py
Fetches a few of the 12 missing workshops' pages authenticated and reports whether
the schedule (paper links) now renders vs. still showing the login wall.
"""
import os, re, sys, urllib.request, html

SID = os.environ.get('ICML_SESSIONID', '')
if not SID or SID.startswith('paste-'):
    sys.exit('ERROR: set your sessionid first:  edit .env.icml then  source .env.icml')

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Cookie': f'sessionid={SID}'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')

# whoami check + a few of the 12 login-gated workshops
TESTS = {
    'F2S (control: papers on own site)': 'https://icml.cc/virtual/2026/workshop/54058',
    'GFM': 'https://icml.cc/virtual/2026/workshop/54057',
    'AI4Law': 'https://icml.cc/virtual/2026/workshop/54065',
    'Game Theory in Nature': 'https://icml.cc/virtual/2026/workshop/54070',
}

# Are we logged in? Look for a username / logout link vs a Login link.
home = fetch('https://icml.cc/virtual/2026/calendar')
logged_in = ('logout' in home.lower() or 'my stuff' in home.lower()) and 'accounts/login' not in \
            (re.search(r'href="([^"]*accounts/login[^"]*)"', home).group(0) if 'accounts/login' in home else 'x')
print('LOGIN STATUS:', 'appears LOGGED IN' if 'logout' in home.lower() else 'NOT logged in (still see Login) — cookie may be stale')
print()

for name, url in TESTS.items():
    h = fetch(url)
    gated = 'Log in and register to view live content' in h
    # count links to papers/talks in the schedule area
    paper_links = len(re.findall(r'/virtual/2026/(?:poster|workshop-paper|oral|paper)/\d+', h))
    # any visible paper titles in a schedule list?
    sched = 'schedule' in h.lower()
    print(f'{name}')
    print(f'   login-wall present: {gated} | schedule paper-links found: {paper_links}')
