"""Run the four pre-registered analyses and write results tables.

Outputs to analysis/results/: reliability_curve.csv, stabilization.csv,
yoy.csv, shrinkage.csv, prediction.csv. Every number in the write-up
traces back to these files.

Usage: python scripts/run_analysis.py
"""

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))

from reliability import (  # noqa: E402
    N_BOOT,
    N_SPLITS,
    SEED,
    bootstrap_stabilization,
    fixed_population_curve,
    half_mean_pairs,
    load_clean_rounds,
    prediction_table,
    reliability_curve,
    season_pairs,
    shrinkage_table,
    stabilization_table,
    yoy_correlations,
)

RESULTS = ROOT / "analysis" / "results"


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    t0 = time.time()
    df = load_clean_rounds()
    print(f"analysis set: {len(df):,} rounds, "
          f"{df['dg_id'].nunique():,} players")

    # Q1: split-half reliability
    rng = np.random.default_rng(SEED)
    pairs = half_mean_pairs(df, n_splits=N_SPLITS, rng=rng)
    curve = reliability_curve(pairs)
    # sensitivity (documented, not pre-registered): fixed player pool
    fixed = fixed_population_curve(pairs)
    fixed.to_csv(RESULTS / "sensitivity_fixed_pop.csv", index=False)
    print(f"[{time.time()-t0:.0f}s] split-half curve done")

    # Q2: bootstrap + stabilization fits
    curve_ci, k_boot = bootstrap_stabilization(pairs, n_boot=N_BOOT, rng=rng)
    curve = curve.merge(curve_ci, on=["category", "n"])
    stab = stabilization_table(curve, k_boot)
    curve.to_csv(RESULTS / "reliability_curve.csv", index=False)
    stab.to_csv(RESULTS / "stabilization.csv", index=False)
    print(f"[{time.time()-t0:.0f}s] bootstrap ({N_BOOT} reps) done")

    # Q3: year-over-year
    pairs_df = season_pairs(df)
    yoy = yoy_correlations(pairs_df)
    yoy.to_csv(RESULTS / "yoy.csv", index=False)

    # Q4: shrinkage + prediction
    shrink = shrinkage_table(stab)
    pred = prediction_table(pairs_df)
    shrink.to_csv(RESULTS / "shrinkage.csv", index=False)
    pred.to_csv(RESULTS / "prediction.csv", index=False)

    print(f"[{time.time()-t0:.0f}s] all results written to {RESULTS}\n")
    print("=== stabilization (rounds to R=0.5 / R=0.7) ===")
    print(stab.round(1).to_string(index=False))
    print("\n=== reliability curve (point estimates) ===")
    print(
        curve.pivot(index="n", columns="category", values="reliability")
        .round(3).to_string()
    )
    print("\n=== year-over-year correlation ===")
    print(yoy.round(3).to_string(index=False))
    print("\n=== shrinkage (weight on a 12-round sample) ===")
    print(shrink.round(3).to_string(index=False))
    print("\n=== predicting next-season total SG ===")
    print(pred.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
