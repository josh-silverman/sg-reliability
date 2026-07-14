# Data quality summary

Source: DataGolf historical-raw-data rounds endpoint, PGA Tour 2017–2026. 134,951 player-rounds across 347 events, 1,773 distinct players.

## Rows per calendar year

|   calendar_year |   events |   player_rounds |   players |
|----------------:|---------:|----------------:|----------:|
|            2017 |       34 |           13578 |       539 |
|            2018 |       34 |           13576 |       553 |
|            2019 |       34 |           13682 |       546 |
|            2020 |       28 |           10375 |       419 |
|            2021 |       35 |           13542 |       532 |
|            2022 |       35 |           14122 |       682 |
|            2023 |       35 |           13765 |       637 |
|            2024 |       43 |           16119 |       654 |
|            2025 |       41 |           15519 |       637 |
|            2026 |       28 |           10673 |       501 |

## SG coverage

DataGolf lists 443 PGA Tour events in 2017–2026; 347 have SG categories (ShotLink or equivalent tracking) and were fetched. 96 events lack SG and are excluded — mostly opposite-field and fall events. All analysis is therefore conditional on SG-tracked events.

Missing SG values within fetched events:

| category   |   missing_rounds |   pct_missing |
|:-----------|-----------------:|--------------:|
| sg_ott     |             1744 |          1.29 |
| sg_app     |             1744 |          1.29 |
| sg_arg     |             1744 |          1.29 |
| sg_putt    |             1744 |          1.29 |

1,744 rounds (1.29%) have no SG in any category. Events where >10% of rounds lack SG entirely:

|   calendar_year | event_name             |   pct_rounds_no_sg |
|----------------:|:-----------------------|-------------------:|
|            2024 | The American Express   |               67.9 |
|            2025 | The American Express   |               57.6 |
|            2026 | The American Express   |               57.6 |
|            2024 | The RSM Classic        |               34.9 |
|            2025 | The RSM Classic        |               34.1 |
|            2025 | Farmers Insurance Open |               33.5 |
|            2024 | Farmers Insurance Open |               33.3 |
|            2026 | Farmers Insurance Open |               33.3 |

These are all multi-course events (The American Express, Farmers Insurance Open, The RSM Classic) where shot tracking covers only the host course; rounds played on satellite courses have no SG. **Decision:** keep these events and drop only the untracked rounds — SG values on the tracked course are valid.

**Flag for the analysis plan:** the Zurich Classic of New Orleans (2023, 2025, 2026 in this pull) is a two-man team event; per-player SG there is not comparable to stroke-play rounds and should likely be excluded. To be decided in `ANALYSIS_PLAN.md`.

## Duplicates

Duplicate (player, year, event, round) keys: 0 rows. None found.

## Category-sum reconciliation

| check              |   rounds_checked |   max_abs_error |   rows_over_0.05 |
|:-------------------|-----------------:|----------------:|-----------------:|
| OTT+APP+ARG vs T2G |           133207 |           1.287 |               48 |
| T2G+PUTT vs TOTAL  |           133207 |           1.971 |              284 |

The rows exceeding tolerance on T2G+PUTT vs TOTAL are concentrated in a handful of rounds (2021 Arnold Palmer R2, 2022 Genesis R1, 2023 Masters R1–R3, 2020 PLAYERS R1) where the gap is *constant across every player in the round* (std ≈ 0) — a field-baseline difference in how DataGolf computed `sg_total` for those rounds, not player-level errors. All offsets are ≤ 0.16 strokes. **Decision:** where a total is needed, compute it as the sum of the four category columns rather than using `sg_total`.

## Value ranges

| stat   |   score |   sg_ott |   sg_app |   sg_arg |   sg_putt |   sg_total |
|:-------|--------:|---------:|---------:|---------:|----------:|-----------:|
| min    |  59     |   -9.995 |  -10.213 |  -10.674 |    -8.884 |    -19.172 |
| mean   |  70.614 |   -0     |    0     |   -0.001 |     0     |      0     |
| max    |  92     |    4.113 |    6.874 |    5.92  |     7.321 |     10.994 |

All events have a completion date (none in progress).
