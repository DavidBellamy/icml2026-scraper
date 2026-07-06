# icml2026-scraper

Scrape an entire ML conference into a clean, agent-queryable dataset — then explore it from your phone with one line.

This is the exact pipeline behind the **[drbellamy/icml-2026](https://huggingface.co/datasets/drbellamy/icml-2026)** HuggingFace dataset: **10,815 papers** (5,872 main-conference + 4,943 workshop) with titles, abstracts, authors, **session times, rooms, and PDF links**, plus every tutorial, invited talk, and workshop.

> **The pattern:** *any conference's virtual site + OpenReview + an agent = a queryable conference in your pocket.* This repo is the ICML 2026 instance; the approach generalizes to any Whova/OpenReview-style conference.

## What it does

| Stage | Source | Output |
|---|---|---|
| Calendar | `icml.cc/virtual/2026` (public) | full 7-day schedule, 180 events |
| Poster abstracts | ICML poster pages (public, server-rendered) | 5,872 papers w/ authors + abstracts |
| Main-conference PDFs | OpenReview API (authenticated) | 6,341 accepted papers + PDFs + author IDs |
| Workshop papers | ICML attendee schedule (authenticated) | 4,943 papers w/ abstracts + PDFs |
| Packaging | — | per-day JSON + HuggingFace Parquet/CSV |

## Key ideas worth stealing

- **Server-rendered pages need no browser.** ICML poster pages are SSR, so plain `urllib` gets titles/authors/abstracts — no headless Chrome, no API credits. Parse from JSON-LD, not visible HTML.
- **Two logins unlock two tiers.** OpenReview (token) gets the archival papers with PDFs; the ICML attendee cookie (`sessionid`) gets the *superset* including non-archival workshop papers. Neither is scrapable anonymously — both are challenge/login gated.
- **Flat, one-row-per-paper schema** is what makes an agent effective. Nested JSON is for humans; Parquet tables are for agents.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env && $EDITOR .env   # add your OpenReview + ICML + HF credentials
```

Credentials (all optional depending on which stages you run):
- `OPENREVIEW_USERNAME` / `OPENREVIEW_PASSWORD` — for main-conference PDFs + workshop papers on OpenReview
- `ICML_SESSIONID` — your logged-in `sessionid` cookie from icml.cc (unlocks workshop schedules)
- `HF_TOKEN` — a write token, to push the dataset

## Run the pipeline

Scripts are numbered by dependency order in [`pipeline/`](./pipeline). Roughly:

```bash
source .env
python pipeline/parse_calendar.py                 # 1. schedule + event/paper lists
python pipeline/crawl_posters.py                  # 2. poster abstracts (public, ~6 min)
python pipeline/add_timestamps.py                 # 3. normalize times -> UTC/KST
python pipeline/crawl_events.py                   # 4. tutorials/invited talks/expo abstracts + bios
python pipeline/map_workshops.py                  # 5. workshop -> OpenReview venue mapping
python pipeline/fetch_mainconf.py                 # 6. all main-conf papers + PDFs (OpenReview auth)
python pipeline/crawl_workshop_schedules.py       # 7. workshop papers (ICML attendee login)
python pipeline/crawl_workshop_paper_details.py   # 8. workshop paper PDF/forum links
python pipeline/build_by_day.py                   # 9. split everything per conference day
python pipeline/build_hf_dataset.py               # 10. build Parquet/CSV + dataset card
```

Each crawler is **resumable** (skips already-fetched items) and rate-limit-friendly.

## Adapting to another conference

Most of the work is in the URL patterns and the OpenReview venue id (`ICML.cc/2026/...`). Swap those and the year, and the same shape works for other virtual-conference sites. PRs generalizing this welcome.

## License

MIT (code). The *data* it produces belongs to the respective authors and the conference — see the dataset card for terms.

*Built with Claude Code.*
