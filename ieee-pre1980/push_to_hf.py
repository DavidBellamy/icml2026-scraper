"""Push the IEEE pre-1980 dataset to the Hugging Face Hub.

Requires an HF token with write access. Provide it one of two ways:
  export HF_TOKEN=hf_xxx            # then: python push_to_hf.py
  python push_to_hf.py             # falls back to interactive login()

Set REPO to your own namespace before running.
"""
import os

from datasets import Dataset
from huggingface_hub import login

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("HF_REPO", "Drbellamy/ieee-pre1980")


def main():
    token = os.environ.get("HF_TOKEN")
    login(token=token) if token else login()

    # Memory-map the parquet from disk (Arrow) rather than loading through
    # pandas — the abstract/JSON-string rows are too heavy for a full in-RAM
    # copy. Small shards keep the upload's memory footprint bounded.
    ds = Dataset.from_parquet(os.path.join(HERE, "ieee_pre1980.parquet"))
    ds.push_to_hub(REPO, private=True, max_shard_size="200MB")
    print(f"Pushed {ds.num_rows:,} rows (private) to https://huggingface.co/datasets/{REPO}")


if __name__ == "__main__":
    main()
