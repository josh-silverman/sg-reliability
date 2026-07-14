# How Many Rounds Until Strokes-Gained Numbers Mean Something?

Reliability and stabilization analysis of strokes-gained categories (off the tee,
approach, around the green, putting) using round-level PGA Tour data from the
DataGolf API, 2017–2026.

**Status: work in progress** — this README will be replaced with findings once
the analysis is complete.

## Questions (pre-registered in `ANALYSIS_PLAN.md`)

1. Split-half reliability per SG category (Spearman-Brown corrected)
2. Stabilization curves: rounds needed for each category to reach R = 0.5 and 0.7
3. Year-over-year correlation per category
4. Practical shrinkage: how much to regress small samples to the mean, and which
   categories best predict future total SG

## Repo structure

```
├── data/            # cached API pulls — gitignored, never committed
├── scripts/         # fetch_data.py, run_analysis.py
├── analysis/        # analysis modules / notebooks
├── figures/         # generated charts (committed)
└── writeup/         # the article
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your DataGolf API key
```

Raw data is pulled from the [DataGolf API](https://datagolf.com/api-access) and
cached locally to parquet. Per DataGolf's redistribution terms, the fetch script
is committed but the data itself never is.
