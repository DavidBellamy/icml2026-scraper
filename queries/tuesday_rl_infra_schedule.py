#!/usr/bin/env python3
"""Build the candidate pool for a Tuesday 'RL infrastructure' reading track from
the Drbellamy/icml-2026 HF dataset (papers config).

Two-stage pipeline:
  1. THIS script scores every Tuesday paper for RL-infrastructure relevance over
     title+abstract using hard systems/infra signals (distributed/async RL,
     rollout & inference engines, training-inference consistency, throughput,
     parallelism, ...) and writes candidates.json (~55 papers).
  2. An LLM judge then reads the full abstracts and classifies each candidate as
     CORE (RL systems/infra), ADJACENT (RL training efficiency/stability/scaling),
     or NOT. render_schedule.py turns CORE+ADJACENT into the final schedule.

Regex alone can't cleanly separate "infra for RL" from "RL applied to a task"
(the word "framework" appears in nearly every abstract), so stage 2 is the judge.
The committed queries/tuesday_rl_infra_schedule.md is that curated output.

Run (needs huggingface.co allowlisted, or pass a local parquet):
    python queries/tuesday_rl_infra_schedule.py [papers.parquet]
"""
import sys, os, re, json, subprocess

URL = "https://huggingface.co/datasets/Drbellamy/icml-2026/resolve/main/data/papers.parquet"
LOCAL = "papers.parquet"

RL = [r'reinforcement learning', r'\brl\b', r'\brlhf\b', r'\brlvr\b', r'\bppo\b', r'\bgrpo\b',
      r'policy optimization', r'policy gradient', r'actor[- ]critic', r'reward model', r'\brollout',
      r'post[- ]?training', r'off[- ]policy', r'on[- ]policy', r'experience replay']
# HARD systems/infra signals only (deliberately excludes generic "framework/system/scaling").
INFRA = [r'distributed', r'asynchron', r'\basync', r'throughput', r'\bgpu', r'\bcluster', r'parallelism',
         r'tensor parallel', r'data parallel', r'pipeline parallel', r'\bfsdp\b', r'megatron', r'\bvllm\b', r'\bsglang\b',
         r'rollout (engine|generation|worker|system|schedul)', r'inference (engine|server|system)', r'serving',
         r'weight (sync|synchroniz|reshard|transfer|update)', r'training[- ]inference', r'inference[- ]training',
         r'replay buffer', r'actor[- ]learner', r'load balanc', r'\bscheduler\b', r'scheduling',
         r'memory[- ]efficient', r'kv[- ]?cache', r'checkpoint', r'elastic', r'fault[- ]toleran', r'colocat',
         r'disaggregat', r'wall[- ]clock', r'utiliz', r'latency', r'\bhardware', r'\bsystem-level', r'compute[- ]efficien']
STRONG = [r'rl (framework|system|library|infrastructure|platform|engine|stack)',
          r'reinforcement learning (system|framework|library|infrastructure|platform|engine|pipeline|stack)',
          r'(distributed|scalable|asynchronous|async) (reinforcement learning|rl)\b',
          r'rlhf (system|framework|infrastructure|pipeline|engine)',
          r'\bverl\b|openrlhf|\btrlx\b|nemo[- ]?aligner|\bareal\b|\bslime\b|\brllib\b',
          r'rollout (engine|generation)', r'training[- ]inference (mismatch|gap|consisten)']
RLr = [re.compile(x, re.I) for x in RL]
INr = [re.compile(x, re.I) for x in INFRA]
STr = [re.compile(x, re.I) for x in STRONG]


def score(title, abstract):
    txt = f"{title or ''}  {abstract or ''}"
    strong = sum(1 for r in STr if r.search(txt))
    rl = sum(1 for r in RLr if r.search(txt))
    infra = sum(1 for r in INr if r.search(txt))
    rl_t = any(r.search(title or '') for r in RLr)
    infra_t = any(r.search(title or '') for r in INr)
    rel = strong > 0 or (rl > 0 and infra >= 2) or (rl_t and infra_t)
    s = strong * 8 + (3 if (rl_t and infra_t) else 0) + rl + infra
    return rel, s


def load_df():
    import pandas as pd
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src and os.path.exists(src):
        return pd.read_parquet(src)
    if not os.path.exists(LOCAL):
        r = subprocess.run(["curl", "-sS", "-L", "-o", LOCAL, URL], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(LOCAL) or os.path.getsize(LOCAL) < 1000:
            sys.exit(f"Download failed (huggingface.co likely not allowlisted): {r.stderr[:400]}")
    return pd.read_parquet(LOCAL)


def main():
    df = load_df()
    tue = df[df["day"].astype(str).str.lower() == "tuesday"].copy()
    cands = []
    for _, p in tue.iterrows():
        rel, s = score(p.get("title"), p.get("abstract"))
        if rel:
            cands.append({
                "score": int(s), "title": p["title"], "abstract": (p.get("abstract") or "")[:1200],
                "authors": list(p["authors"])[:6] if p.get("authors") is not None else [],
                "start": str(p.get("session_start_kst")), "end": str(p.get("session_end_kst")),
                "location": p.get("location"), "paper_type": p.get("paper_type"), "url": p.get("url"),
            })
    cands.sort(key=lambda x: -x["score"])
    json.dump(cands, open("candidates.json", "w"), indent=1, default=str)
    print(f"tuesday papers={len(tue)}  candidates={len(cands)} -> candidates.json", file=sys.stderr)
    print("next: LLM-classify candidates.json (CORE/ADJACENT/NOT) -> classification.json, "
          "then: python queries/render_schedule.py", file=sys.stderr)


if __name__ == "__main__":
    main()
