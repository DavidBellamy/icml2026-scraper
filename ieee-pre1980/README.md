# IEEE pre-1980: analog vs digital

When did "digital" overtake "analog" in IEEE paper titles? This pulls every
IEEE work published before 1980 from [OpenAlex](https://openalex.org) (no API
key needed), then plots the yearly counts of titles containing each word and
marks the crossover year.

IEEE is OpenAlex publisher lineage `P4310319808`; the pre-1980 filter yields
**~175K records**.

## Run

```bash
pip install -r requirements.txt

python fetch_openalex.py     # pull metadata -> works.jsonl (resumable)
python analyze.py            # -> ieee_pre1980.parquet/.csv, analog_vs_digital.png, summary.md
python push_to_hf.py         # optional: upload to the HF Hub (needs HF_TOKEN)
```

`fetch_openalex.py` is resumable: it records the API cursor in `progress.json`
and appends pages to `works.jsonl`, so an interrupted pull continues where it
left off.

## Outputs

| File | What |
|---|---|
| `works.jsonl` | raw OpenAlex records (title, year, concepts) |
| `ieee_pre1980.parquet` / `.csv` | flat one-row-per-paper table + `analog`/`digital` flags |
| `analog_vs_digital.png` | yearly counts with the crossover year marked |
| `summary.md` | crossover year + headline numbers |
