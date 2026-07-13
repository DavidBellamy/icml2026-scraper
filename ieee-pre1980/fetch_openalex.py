"""Pull IEEE (publisher lineage P4310319808) pre-1980 works metadata from OpenAlex.

Resumable: appends each page to works.jsonl and records the next cursor in
progress.json, so re-running continues where it left off. No API key required;
mailto puts us in the polite pool.
"""
import json
import os
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSONL = os.path.join(HERE, "works.jsonl")
PROGRESS = os.path.join(HERE, "progress.json")

PARAMS = {
    "filter": "primary_location.source.publisher_lineage:P4310319808,publication_year:<1980",
    # No "select": omitting it returns the full work object (every field OpenAlex
    # exposes — abstracts, authorships, citations, topics, locations, ...).
    "per-page": 200,
    "mailto": "bellamyrd@gmail.com",
}
BASE = "https://api.openalex.org/works"


def load_progress():
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            return json.load(f)
    return {"cursor": "*", "fetched": 0, "expected": None}


def save_progress(p):
    tmp = PROGRESS + ".tmp"
    with open(tmp, "w") as f:
        json.dump(p, f)
    os.replace(tmp, PROGRESS)


def main():
    p = load_progress()
    cursor = p["cursor"]
    fetched = p["fetched"]

    # Fresh start: truncate output so we don't duplicate rows.
    if cursor == "*" and os.path.exists(OUT_JSONL):
        os.remove(OUT_JSONL)

    session = requests.Session()
    out = open(OUT_JSONL, "a")
    page = 0
    while cursor:
        params = dict(PARAMS, cursor=cursor)
        for attempt in range(5):
            try:
                r = session.get(BASE, params=params, timeout=60)
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:  # noqa: BLE001
                wait = 2 ** attempt
                print(f"  retry {attempt+1} after error: {e} (sleep {wait}s)")
                time.sleep(wait)
        else:
            print("Giving up after 5 retries; progress saved for resume.")
            break

        results = data["results"]
        for w in results:
            out.write(json.dumps(w) + "\n")
        out.flush()

        fetched += len(results)
        cursor = data["meta"]["next_cursor"]
        expected = data["meta"]["count"]
        page += 1
        if page % 10 == 0 or not cursor:
            print(f"page {page}: {fetched}/{expected} records")

        save_progress({"cursor": cursor or "", "fetched": fetched, "expected": expected})

        if not results:
            break
        time.sleep(0.1)  # be polite

    out.close()
    print(f"Done. {fetched} records in {OUT_JSONL}")


if __name__ == "__main__":
    main()
