"""Push the IEEE pre-1980 dataset to the Hugging Face Hub.

Requires an HF token with write access. Provide it one of two ways:
  export HF_TOKEN=hf_xxx            # then: python push_to_hf.py
  python push_to_hf.py             # falls back to interactive login()

Set REPO to your own namespace before running.
"""
import os

import pandas as pd
from datasets import Dataset
from huggingface_hub import login

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("HF_REPO", "Drbellamy/ieee-pre1980")


def main():
    token = os.environ.get("HF_TOKEN")
    login(token=token) if token else login()

    df = pd.read_parquet(os.path.join(HERE, "ieee_pre1980.parquet"))
    ds = Dataset.from_pandas(df, preserve_index=False)
    ds.push_to_hub(REPO)
    print(f"Pushed {len(df):,} rows to https://huggingface.co/datasets/{REPO}")


if __name__ == "__main__":
    main()
