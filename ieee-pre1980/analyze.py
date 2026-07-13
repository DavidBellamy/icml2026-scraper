"""Analyze analog vs digital in IEEE pre-1980 titles and find the crossover year.

Reads works.jsonl (produced by fetch_openalex.py), writes:
  - ieee_pre1980.parquet / .csv  (flat one-row-per-paper dataset for upload)
  - analog_vs_digital.png        (yearly counts with the crossover marked)
  - summary.md                   (crossover year + headline numbers)
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
JSONL = os.path.join(HERE, "works.jsonl")


def load():
    rows = []
    with open(JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    # Flatten concepts to a compact string so the table stays agent-friendly.
    if "concepts" in df.columns:
        df["concepts"] = df["concepts"].apply(
            lambda cs: "; ".join(c["display_name"] for c in cs) if isinstance(cs, list) else ""
        )
    return df


def main():
    df = load()
    print(f"Loaded {len(df)} records")

    title = df["title"].fillna("")
    df["analog"] = title.str.contains(r"analog", case=False, na=False)
    df["digital"] = title.str.contains(r"digital", case=False, na=False)

    df.to_parquet(os.path.join(HERE, "ieee_pre1980.parquet"), index=False)
    df.to_csv(os.path.join(HERE, "ieee_pre1980.csv"), index=False)

    by_year = (
        df[df["publication_year"].notna()]
        .groupby("publication_year")[["analog", "digital"]]
        .sum()
        .sort_index()
    )

    # Crossover: first year where digital overtakes analog and stays ahead next year too.
    crossover = None
    years = by_year.index.tolist()
    for i, y in enumerate(years):
        if by_year.loc[y, "digital"] > by_year.loc[y, "analog"]:
            crossover = int(y)
            break

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(by_year.index, by_year["analog"], label="analog", color="#c1440e", lw=2, marker="o", ms=3)
    ax.plot(by_year.index, by_year["digital"], label="digital", color="#1b6ca8", lw=2, marker="o", ms=3)
    if crossover is not None:
        ax.axvline(crossover, color="#555", ls="--", lw=1)
        ax.annotate(
            f"crossover: {crossover}",
            xy=(crossover, ax.get_ylim()[1] * 0.9),
            xytext=(6, 0), textcoords="offset points", fontsize=11, color="#555",
        )
    ax.set_xlabel("publication year")
    ax.set_ylabel("# IEEE papers with word in title")
    ax.set_title("'analog' vs 'digital' in IEEE paper titles (pre-1980)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "analog_vs_digital.png"), dpi=130)

    total_analog = int(df["analog"].sum())
    total_digital = int(df["digital"].sum())
    summary = f"""# IEEE pre-1980: analog vs digital

- Records analyzed: **{len(df):,}** (OpenAlex, IEEE publisher lineage P4310319808, year < 1980)
- Titles containing "analog": **{total_analog:,}**
- Titles containing "digital": **{total_digital:,}**
- **Crossover year (digital first exceeds analog): {crossover}**

Chart: `analog_vs_digital.png` · Dataset: `ieee_pre1980.parquet` / `.csv`
"""
    with open(os.path.join(HERE, "summary.md"), "w") as f:
        f.write(summary)
    print(summary)


if __name__ == "__main__":
    main()
