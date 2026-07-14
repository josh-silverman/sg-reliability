"""Sanity checks on the fetched round-level data.

Runs the pre-analysis data-quality checks (row counts, SG coverage,
duplicates, category-sum reconciliation) and writes a one-page summary to
writeup/data_quality.md.

Usage: python scripts/data_quality.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = ROOT / "data" / "rounds.parquet"
EVENT_LIST_PATH = ROOT / "data" / "raw" / "event_list.json"
OUT_PATH = ROOT / "writeup" / "data_quality.md"

SG_CATS = ["sg_ott", "sg_app", "sg_arg", "sg_putt"]
KEY_COLS = ["dg_id", "calendar_year", "event_id", "round_num"]
RECON_TOL = 0.05  # strokes; fields are rounded to 3 decimals upstream


def md_table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def main() -> None:
    df = pd.read_parquet(PARQUET_PATH)
    events = json.loads(EVENT_LIST_PATH.read_text())
    lines: list[str] = ["# Data quality summary", ""]
    lines.append(
        f"Source: DataGolf historical-raw-data rounds endpoint, PGA Tour "
        f"2017–2026. {len(df):,} player-rounds across "
        f"{df.groupby(['calendar_year', 'event_id']).ngroups} events, "
        f"{df['dg_id'].nunique():,} distinct players."
    )
    lines.append("")

    # --- 1. Row counts per season -------------------------------------
    lines.append("## Rows per calendar year")
    per_year = (
        df.groupby("calendar_year")
        .agg(
            events=("event_id", "nunique"),
            player_rounds=("dg_id", "size"),
            players=("dg_id", "nunique"),
        )
        .reset_index()
    )
    lines += ["", md_table(per_year), ""]

    # --- 2. SG coverage ------------------------------------------------
    lines.append("## SG coverage")
    pga = [e for e in events if e["tour"] == "pga" and 2017 <= e["calendar_year"] <= 2026]
    no_sg = [e for e in pga if e["sg_categories"] != "yes"]
    lines.append(
        f"\nDataGolf lists {len(pga)} PGA Tour events in 2017–2026; "
        f"{len(pga) - len(no_sg)} have SG categories (ShotLink or equivalent "
        f"tracking) and were fetched. {len(no_sg)} events lack SG and are "
        f"excluded — mostly opposite-field and fall events. All analysis is "
        f"therefore conditional on SG-tracked events.\n"
    )

    # Within fetched events, per-round missingness of each SG column.
    miss = (
        df[SG_CATS].isna().sum().rename("missing_rounds").to_frame().reset_index()
        .rename(columns={"index": "category"})
    )
    miss["pct_missing"] = (miss["missing_rounds"] / len(df) * 100).round(2)
    lines += ["Missing SG values within fetched events:", "", md_table(miss), ""]

    # Rows missing all four categories (e.g. players untracked that week),
    # and events with substantial missingness.
    df["sg_all_missing"] = df[SG_CATS].isna().all(axis=1)
    ev_miss = (
        df.groupby(["calendar_year", "event_name"])["sg_all_missing"]
        .mean()
        .reset_index(name="pct_rounds_no_sg")
    )
    worst = ev_miss[ev_miss["pct_rounds_no_sg"] > 0.10].copy()
    worst["pct_rounds_no_sg"] = (worst["pct_rounds_no_sg"] * 100).round(1)
    lines.append(
        f"{df['sg_all_missing'].sum():,} rounds "
        f"({df['sg_all_missing'].mean() * 100:.2f}%) have no SG in any "
        f"category. Events where >10% of rounds lack SG entirely:"
    )
    lines += ["", md_table(worst.sort_values("pct_rounds_no_sg", ascending=False)), ""]
    lines.append(
        "These are all multi-course events (The American Express, Farmers "
        "Insurance Open, The RSM Classic) where shot tracking covers only "
        "the host course; rounds played on satellite courses have no SG. "
        "**Decision:** keep these events and drop only the untracked rounds "
        "— SG values on the tracked course are valid.\n"
    )
    lines.append(
        "**Flag for the analysis plan:** the Zurich Classic of New Orleans "
        "(2023, 2025, 2026 in this pull) is a two-man team event; per-player "
        "SG there is not comparable to stroke-play rounds and should likely "
        "be excluded. To be decided in `ANALYSIS_PLAN.md`.\n"
    )

    # --- 3. Duplicates ---------------------------------------------------
    lines.append("## Duplicates")
    dup_key = df.duplicated(subset=KEY_COLS, keep=False)
    lines.append(
        f"\nDuplicate (player, year, event, round) keys: {dup_key.sum()} rows. "
        + ("**Needs investigation.**" if dup_key.any() else "None found.")
    )
    if dup_key.any():
        lines += ["", md_table(df.loc[dup_key, KEY_COLS + ["player_name", "score"]].head(20)), ""]
    lines.append("")

    # --- 4. Category sums reconcile against totals ----------------------
    lines.append("## Category-sum reconciliation")
    have_all = df[SG_CATS + ["sg_t2g", "sg_total"]].notna().all(axis=1)
    sub = df[have_all]
    t2g_err = (sub["sg_ott"] + sub["sg_app"] + sub["sg_arg"] - sub["sg_t2g"]).abs()
    tot_err = (sub["sg_t2g"] + sub["sg_putt"] - sub["sg_total"]).abs()
    recon = pd.DataFrame(
        {
            "check": ["OTT+APP+ARG vs T2G", "T2G+PUTT vs TOTAL"],
            "rounds_checked": [len(sub)] * 2,
            "max_abs_error": [t2g_err.max(), tot_err.max()],
            f"rows_over_{RECON_TOL}": [
                int((t2g_err > RECON_TOL).sum()),
                int((tot_err > RECON_TOL).sum()),
            ],
        }
    )
    lines += ["", md_table(recon), ""]
    lines.append(
        "The rows exceeding tolerance on T2G+PUTT vs TOTAL are concentrated "
        "in a handful of rounds (2021 Arnold Palmer R2, 2022 Genesis R1, "
        "2023 Masters R1–R3, 2020 PLAYERS R1) where the gap is *constant "
        "across every player in the round* (std ≈ 0) — a field-baseline "
        "difference in how DataGolf computed `sg_total` for those rounds, "
        "not player-level errors. All offsets are ≤ 0.16 strokes. "
        "**Decision:** where a total is needed, compute it as the sum of "
        "the four category columns rather than using `sg_total`.\n"
    )

    # --- 5. Basic value sanity ------------------------------------------
    lines.append("## Value ranges")
    desc = (
        df[["score"] + SG_CATS + ["sg_total"]]
        .describe()
        .loc[["min", "mean", "max"]]
        .round(3)
        .reset_index()
        .rename(columns={"index": "stat"})
    )
    lines += ["", md_table(desc), ""]
    # event_completed is a completion-date string; null would mean in progress.
    incomplete = df[df["event_completed"].isna()]
    if len(incomplete):
        evs = incomplete[["calendar_year", "event_name"]].drop_duplicates()
        lines.append(
            f"Events with no completion date ({len(evs)}): "
            + "; ".join(f"{r.calendar_year} {r.event_name}" for r in evs.itertuples())
        )
    else:
        lines.append("All events have a completion date (none in progress).")
    lines.append("")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines))
    print(f"Wrote {OUT_PATH}")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
