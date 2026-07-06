#!/usr/bin/env python3
"""Crawl ICML 2026 poster pages in parallel, parse authors + abstracts.
Resumable: skips URLs already present in the output JSONL."""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from parse_poster import parse_poster

URLS_FILE = 'poster_urls.txt'
OUT_JSONL = 'posters.jsonl'
WORKERS = 24
TIMEOUT = 30
RETRIES = 3
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 research-scrape'

def fetch(url):
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last

def worker(url):
    try:
        h = fetch(url)
        rec = parse_poster(h, url)
        rec['ok'] = bool(rec.get('title'))
        return rec
    except Exception as e:  # noqa: BLE001
        return {'url': url, 'ok': False, 'error': str(e)}

def main():
    urls = [u.strip() for u in open(URLS_FILE) if u.strip()]
    done = set()
    if os.path.exists(OUT_JSONL):
        for line in open(OUT_JSONL):
            try:
                rec = json.loads(line)
                if rec.get('ok'):
                    done.add(rec['url'])
            except json.JSONDecodeError:
                pass
    todo = [u for u in urls if u not in done]
    print(f'total={len(urls)} done={len(done)} todo={len(todo)}', flush=True)

    n_ok = n_err = 0
    t0 = time.time()
    with open(OUT_JSONL, 'a') as out, ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(worker, u): u for u in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            out.flush()
            if rec.get('ok'):
                n_ok += 1
            else:
                n_err += 1
            if i % 250 == 0 or i == len(todo):
                rate = i / (time.time() - t0)
                eta = (len(todo) - i) / rate if rate else 0
                print(f'  {i}/{len(todo)}  ok={n_ok} err={n_err}  '
                      f'{rate:.1f}/s  eta={eta:.0f}s', flush=True)
    print(f'DONE ok={n_ok} err={n_err} in {time.time()-t0:.0f}s', flush=True)

if __name__ == '__main__':
    main()
