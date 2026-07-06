#!/usr/bin/env python3
"""Build a Tuesday 'RL infrastructure' schedule from the Drbellamy/icml-2026 HF dataset.

Reads the `papers` config (papers.parquet). Filters to Tuesday, scores each paper
for reinforcement-learning-infrastructure relevance over title+abstract, and emits
a time-ordered markdown schedule.

Run once huggingface.co is allowlisted:
    python build_tue_rl_infra.py
Or against a local file:
    python build_tue_rl_infra.py /path/to/papers.parquet
"""
import sys, os, re, subprocess

URL = "https://huggingface.co/datasets/Drbellamy/icml-2026/resolve/main/data/papers.parquet"
LOCAL = "papers.parquet"


def load_df():
    import pandas as pd
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src and os.path.exists(src):
        return pd.read_parquet(src)
    if not os.path.exists(LOCAL):
        # curl is proxy-aware in this environment; urllib is not.
        r = subprocess.run(["curl", "-sS", "-L", "-o", LOCAL, URL], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(LOCAL) or os.path.getsize(LOCAL) < 1000:
            sys.exit(f"Download failed (host likely still blocked): {r.stderr[:400]}")
    return pd.read_parquet(LOCAL)


# --- RL-infrastructure relevance ---------------------------------------------
RL_TERMS = [
    r"reinforcement learning", r"\brl\b", r"\brlhf\b", r"\brlvr\b", r"\bppo\b",
    r"policy optimization", r"policy gradient", r"actor[- ]critic", r"q[- ]learning",
    r"markov decision", r"\bmdp\b", r"bandit", r"agentic", r"\bagent\b",
    r"reward model", r"self[- ]play", r"grpo", r"dpo\b",
]
INFRA_TERMS = [
    r"infrastructure", r"framework", r"library", r"toolkit", r"platform", r"system",
    r"distributed", r"scalab", r"scaling", r"parallel", r"throughput", r"pipeline",
    r"rollout", r"sampler", r"simulat", r"environment suite", r"benchmark suite",
    r"engine", r"serving", r"inference", r"training system", r"gpu", r"cluster",
    r"asynchronous", r"actor[- ]learner", r"replay buffer", r"vectorized",
    r"orchestrat", r"deployment", r"efficient training", r"open[- ]source",
]
# Strong standalone signals — count as a hit on their own.
STRONG = [
    r"rl infrastructure", r"rl framework", r"rl system", r"rl library",
    r"reinforcement learning (system|framework|library|infrastructure|platform)",
    r"distributed (reinforcement learning|rl)", r"scalable (reinforcement learning|rl)",
    r"(training|inference) (system|framework|infrastructure) for (rl|reinforcement)",
    r"rlhf (system|framework|infrastructure|pipeline)", r"veRL|verl|openrlhf|trl\b|trlx",
    r"rollout (engine|system|generation)", r"async(hronous)? rl",
]
RL_RE = [re.compile(t, re.I) for t in RL_TERMS]
INFRA_RE = [re.compile(t, re.I) for t in INFRA_TERMS]
STRONG_RE = [re.compile(t, re.I) for t in STRONG]


def score(title, abstract):
    text = f"{title or ''}  {abstract or ''}"
    strong = sum(1 for r in STRONG_RE if r.search(text))
    rl = sum(1 for r in RL_RE if r.search(text))
    infra = sum(1 for r in INFRA_RE if r.search(text))
    rl_in_title = any(r.search(title or "") for r in RL_RE)
    # relevant if: any strong signal, OR (has RL term AND infra term)
    relevant = strong > 0 or (rl > 0 and infra > 0)
    s = strong * 5 + (rl and infra) * 2 + rl + infra + (2 if rl_in_title else 0)
    return relevant, s


def main():
    import pandas as pd
    df = load_df()
    tue = df[df["day"].astype(str).str.lower() == "tuesday"].copy()
    print(f"[info] total papers={len(df)}  tuesday={len(tue)}", file=sys.stderr)

    rows = []
    for _, p in tue.iterrows():
        rel, s = score(p.get("title"), p.get("abstract"))
        if rel:
            rows.append((s, p))
    rows.sort(key=lambda x: (str(x[1].get("session_start_kst") or ""), -x[0]))
    print(f"[info] rl-infra matches on tuesday={len(rows)}", file=sys.stderr)

    def fmt_time(v):
        v = str(v or "")
        return v[11:16] if len(v) >= 16 else "TBD"

    lines = ["# ICML 2026 — Tuesday: RL Infrastructure track (unofficial)", ""]
    lines.append(f"_{len(rows)} papers matched on Tuesday. Times in KST (conference local)._\n")
    for s, p in rows:
        t0 = fmt_time(p.get("session_start_kst"))
        t1 = fmt_time(p.get("session_end_kst"))
        loc = p.get("location") or "TBD"
        typ = p.get("paper_type") or ""
        auth = p.get("authors")
        if hasattr(auth, "__len__") and not isinstance(auth, str):
            auth = ", ".join(list(auth)[:4]) + ("…" if len(auth) > 4 else "")
        lines.append(f"### {t0}–{t1} · {loc} · {typ}")
        lines.append(f"**{p.get('title')}**  ")
        lines.append(f"{auth}  ")
        sess = p.get("session") or p.get("workshop")
        if sess:
            lines.append(f"_{sess}_  ")
        url = p.get("url")
        if url:
            lines.append(f"[details]({url})")
        lines.append("")
    out = "\n".join(lines)
    with open("tuesday_rl_infra_schedule.md", "w") as f:
        f.write(out)
    print(out)


if __name__ == "__main__":
    main()
