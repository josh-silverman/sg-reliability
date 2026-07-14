# Pre-registered analysis plan

Written and committed **before** any reliability number was computed. The data
pull and quality checks (commit `444e71f`) are the only analysis run so far;
the sample-size counts below were checked only to set feasible thresholds.
Any deviation from this plan will be documented in a "Deviations" section of
the write-up rather than silently changed.

## Question

How many rounds does it take for each strokes-gained category — off the tee
(OTT), approach (APP), around the green (ARG), putting (PUTT) — to become a
reliable measure of a PGA Tour player's skill, and what does that imply for
how much to trust small samples?

## Data (locked)

- `data/rounds.parquet`: 134,951 player-rounds, 347 SG-tracked PGA Tour
  events, 2017–2026 (see `writeup/data_quality.md`).
- Exclusions, applied everywhere: rounds missing any of the four SG
  categories (1.29%, mostly untracked satellite courses at multi-course
  events); all Zurich Classic of New Orleans rounds (two-man team event).
  Analysis set: **131,847 rounds**.
- Total SG is always computed as the sum of the four categories, not the
  `sg_total` column (baseline quirks documented in the data-quality summary).

## Methods

**Q1 — Split-half reliability per category.** Unit: player-window, using
five non-overlapping two-calendar-year windows (2017–18, 2019–20, 2021–22,
2023–24, 2025–26). For sample size *n*, take every player-window with ≥ 2*n*
rounds, randomly split that player's rounds into two disjoint halves of *n*,
and average SG per half. R(*n*) = Pearson correlation between half-means
across player-windows, averaged over **K = 200** random splits. Because both
halves have size *n*, this estimates the reliability of an *n*-round average
directly.

**Q2 — Stabilization curves.** Compute R(*n*) on the grid
n ∈ {5, 10, 15, 20, 25, 30, 40, 50, 60} (n = 60 still has 386
player-windows). Fit the Spearman-Brown form **R(n) = n / (n + k)** per
category (least squares on the grid). Report, per category: the fitted *k*
(the round count where R = 0.5) and the R = 0.7 crossing (= 7k/3 under the
fitted form), each with a **bootstrap CI (B = 1000, resampling
player-windows, percentile method, seed = 42)**. Crossings beyond n = 60 are
model-based extrapolations and will be labeled as such.

**Q3 — Year-over-year correlation.** All consecutive-season pairs
(2017→18 … 2025→26) where the player has ≥ 30 clean rounds in both seasons
(1,309 pairs). Pearson r per category between season means, pooled across
pairs; Spearman rank correlation reported alongside as a robustness check.

**Q4 — Shrinkage and prediction.** (a) Shrinkage: with *k* from Q2, the
regression-to-the-mean weight for an *n*-round sample is n / (n + k); report
k per category plus a worked example (a 12-round hot streak in each
category). (b) Prediction: for the Q3 pairs, correlate each season-*t*
category mean with season-*t+1* **total** SG (univariate r), and report
standardized coefficients from one multiple regression of next-season total
on all four current-season categories.

## Reporting commitments

- All four questions get reported with CIs **regardless of outcome** —
  including results that contradict the expected ordering (APP stabilizes
  fastest, PUTT slowest).
- Fixed seed (42) and pinned environment; every figure and number in the
  write-up must be reproducible from `scripts/` + the cached data.
- Anything beyond these four questions goes to a "future work" note, not
  into this analysis.
