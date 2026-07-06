#!/usr/bin/env python3
"""Render the Tuesday RL-infra schedule from candidates.json + classification.json."""
import json, sys

cands = json.load(open('candidates.json'))
cls = json.load(open('classification.json'))
tier = {c['title']: c for c in cls}

by_title = {c['title']: c for c in cands}


def t(v):
    v = str(v or '')
    return v[11:16] if len(v) >= 16 else 'TBD'


def slot(c):
    return f"{t(c['start'])}–{t(c['end'])}"


rows = []
for c in cands:
    k = tier.get(c['title'])
    if not k or k['tier'] == 'NOT':
        continue
    rows.append({**c, 'tier': k['tier'], 'subtype': k.get('subtype', ''), 'reason': k.get('reason', '')})

order = {'CORE': 0, 'ADJACENT': 1}
rows.sort(key=lambda r: (order[r['tier']], str(r['start'] or ''), -r['score']))

core = [r for r in rows if r['tier'] == 'CORE']
adj = [r for r in rows if r['tier'] == 'ADJACENT']

L = []
L.append("# ICML 2026 — Tuesday, July 7: Reinforcement Learning Infrastructure")
L.append("")
L.append(f"_A curated slice of the {len(by_title)}-paper candidate pool from the "
         "[Drbellamy/icml-2026](https://huggingface.co/datasets/Drbellamy/icml-2026) dataset. "
         "“RL infrastructure” is not an official ICML track — this is topic-scored and "
         f"LLM-classified. Times in KST (venue local). {len(core)} core + {len(adj)} adjacent papers._")
L.append("")


def emit(r):
    loc = r['location'] or 'TBD'
    typ = (r['paper_type'] or '').title()
    auth = ', '.join(r['authors'][:4]) + ('…' if len(r['authors']) > 4 else '')
    L.append(f"**{slot(r)} · {loc}**{'  ⭐ ' + typ if typ == 'Spotlight' else ' · ' + typ}")
    L.append(f"[{r['title']}]({r['url']})  ")
    L.append(f"<sub>{auth} — *{r['subtype']}*</sub>")
    L.append("")


L.append("## \U0001f3d7️ Core — RL systems & training/serving stack")
L.append("")
if core:
    cur = None
    for r in core:
        s = slot(r)
        if s != cur:
            cur = s
            L.append(f"### Poster block {s}")
            L.append("")
        emit(r)
else:
    L.append("_No core RL-systems papers matched._\n")

L.append("## \U0001f527 Adjacent — RL training efficiency, stability & scaling")
L.append("")
if adj:
    cur = None
    for r in adj:
        s = slot(r)
        if s != cur:
            cur = s
            L.append(f"### Poster block {s}")
            L.append("")
        emit(r)
else:
    L.append("_No adjacent papers matched._\n")

out = "\n".join(L)
open('tuesday_rl_infra_schedule.md', 'w').write(out)
print(out)
