"""Core analysis functions for the pre-registered SG reliability study.

Implements the four registered questions (see ANALYSIS_PLAN.md):
split-half reliability, stabilization-curve fits, year-over-year
correlation, and shrinkage/prediction. All randomness flows through a
caller-supplied numpy Generator so runs are reproducible.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = ROOT / "data" / "rounds.parquet"

SG_CATS = ["sg_ott", "sg_app", "sg_arg", "sg_putt"]
CATS = SG_CATS + ["sg_total_calc"]  # total = sum of the four categories
WINDOWS = [(2017, 2018), (2019, 2020), (2021, 2022), (2023, 2024), (2025, 2026)]
GRID = [5, 10, 15, 20, 25, 30, 40, 50, 60]
N_SPLITS = 200
N_BOOT = 1000
SEED = 42
YOY_MIN_ROUNDS = 30
TEAM_EVENTS = ["Zurich Classic of New Orleans"]


def load_clean_rounds(path: Path = PARQUET_PATH) -> pd.DataFrame:
    """Analysis set per the registered exclusions."""
    df = pd.read_parquet(path)
    df = df.dropna(subset=SG_CATS)
    df = df[~df["event_name"].isin(TEAM_EVENTS)].copy()
    df["sg_total_calc"] = df[SG_CATS].sum(axis=1)
    df["window"] = df["calendar_year"].map(
        {yr: f"{a}-{b % 100:02d}" for a, b in WINDOWS for yr in (a, b)}
    )
    return df


# --------------------------------------------------------------------------
# Q1/Q2: split-half reliability and stabilization
# --------------------------------------------------------------------------

def half_mean_pairs(
    df: pd.DataFrame,
    grid: list[int] = GRID,
    n_splits: int = N_SPLITS,
    rng: np.random.Generator | None = None,
) -> dict[int, dict]:
    """Precompute split-half means for every grid size.

    For each player-window with >= 2n rounds, draw `n_splits` random
    permutations of that player's rounds once; for each n, the two halves
    are the first n and second n rounds of each permutation (disjoint by
    construction).

    Returns {n: {"ids": list of player-window ids,
                 "x": (P, n_splits, C) first-half means,
                 "y": (P, n_splits, C) second-half means}}.
    """
    rng = rng or np.random.default_rng(SEED)
    out = {n: {"ids": [], "x": [], "y": []} for n in grid}
    min_rounds = 2 * min(grid)

    for pw_id, grp in df.groupby(["dg_id", "window"], sort=True):
        vals = grp[CATS].to_numpy()
        m = len(vals)
        if m < min_rounds:
            continue
        perms = np.argsort(rng.random((n_splits, m)), axis=1)
        cs = vals[perms].cumsum(axis=1)  # (n_splits, m, C)
        for n in grid:
            if m < 2 * n:
                continue
            first = cs[:, n - 1, :] / n
            second = (cs[:, 2 * n - 1, :] - cs[:, n - 1, :]) / n
            out[n]["ids"].append(pw_id)
            out[n]["x"].append(first)
            out[n]["y"].append(second)

    for n in grid:
        out[n]["x"] = np.array(out[n]["x"])  # (P, n_splits, C)
        out[n]["y"] = np.array(out[n]["y"])
    return out


def colwise_pearson(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pearson r along axis 0 for matching columns of x and y (P, ...)."""
    xc = x - x.mean(axis=0)
    yc = y - y.mean(axis=0)
    num = (xc * yc).sum(axis=0)
    den = np.sqrt((xc**2).sum(axis=0) * (yc**2).sum(axis=0))
    return num / den


def reliability_curve(pairs: dict[int, dict]) -> pd.DataFrame:
    """R(n) per category: mean split-half correlation over the K splits."""
    rows = []
    for n, d in pairs.items():
        r = colwise_pearson(d["x"], d["y"]).mean(axis=0)  # (C,)
        for c, cat in enumerate(CATS):
            rows.append(
                {"category": cat, "n": n, "reliability": r[c],
                 "n_players": len(d["ids"])}
            )
    return pd.DataFrame(rows)


def fixed_population_curve(pairs: dict[int, dict]) -> pd.DataFrame:
    """Sensitivity analysis (not pre-registered): R(n) holding the player
    pool fixed to those eligible at the largest grid size, so every grid
    point is estimated on the same population. Documents how much the
    primary curve reflects pool composition (range restriction) vs n.
    """
    n_max = max(pairs)
    keep = set(pairs[n_max]["ids"])
    rows = []
    for n, d in pairs.items():
        mask = np.array([pid in keep for pid in d["ids"]])
        r = colwise_pearson(d["x"][mask], d["y"][mask]).mean(axis=0)
        for c, cat in enumerate(CATS):
            rows.append(
                {"category": cat, "n": n, "reliability": r[c],
                 "n_players": int(mask.sum())}
            )
    return pd.DataFrame(rows)


def fit_k(ns: np.ndarray, rs: np.ndarray) -> float:
    """Least-squares fit of the Spearman-Brown form R(n) = n / (n + k)."""
    def sse(k):
        return ((rs - ns / (ns + k)) ** 2).sum()

    res = minimize_scalar(sse, bounds=(0.1, 10_000), method="bounded")
    return float(res.x)


def bootstrap_stabilization(
    pairs: dict[int, dict],
    n_boot: int = N_BOOT,
    rng: np.random.Generator | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bootstrap CIs for R(n) and for the fitted k, resampling player-windows.

    One joint resample of the full player-window universe per replicate,
    filtered to each grid size's eligible set, so the k fit within a
    replicate is internally consistent.

    Returns (curve_ci, k_boot) where curve_ci has per-(category, n)
    percentile CIs for R(n) and k_boot has one fitted k per (replicate,
    category).
    """
    rng = rng or np.random.default_rng(SEED)
    grid = sorted(pairs)
    all_ids = sorted({pid for n in grid for pid in pairs[n]["ids"]})
    id_index = {pid: i for i, pid in enumerate(all_ids)}
    # eligibility map per n: global id index -> row in that n's arrays, or -1
    elig = {}
    for n in grid:
        m = np.full(len(all_ids), -1, dtype=np.int64)
        for row, pid in enumerate(pairs[n]["ids"]):
            m[id_index[pid]] = row
        elig[n] = m

    r_boot = {n: np.empty((n_boot, len(CATS))) for n in grid}
    k_boot = np.empty((n_boot, len(CATS)))
    ns = np.array(grid, dtype=float)
    for b in range(n_boot):
        draw = rng.integers(0, len(all_ids), size=len(all_ids))
        for n in grid:
            rows = elig[n][draw]
            rows = rows[rows >= 0]
            r = colwise_pearson(pairs[n]["x"][rows], pairs[n]["y"][rows])
            r_boot[n][b] = r.mean(axis=0)
        for c in range(len(CATS)):
            k_boot[b, c] = fit_k(ns, np.array([r_boot[n][b, c] for n in grid]))

    curve_rows = []
    for n in grid:
        lo, hi = np.percentile(r_boot[n], [2.5, 97.5], axis=0)
        for c, cat in enumerate(CATS):
            curve_rows.append(
                {"category": cat, "n": n, "ci_lo": lo[c], "ci_hi": hi[c]}
            )
    k_df = pd.DataFrame(k_boot, columns=CATS)
    return pd.DataFrame(curve_rows), k_df


def stabilization_table(curve: pd.DataFrame, k_boot: pd.DataFrame) -> pd.DataFrame:
    """Fitted k (= rounds to R=0.5) and rounds to R=0.7 with bootstrap CIs."""
    rows = []
    for cat in CATS:
        sub = curve[curve["category"] == cat].sort_values("n")
        k_hat = fit_k(sub["n"].to_numpy(float), sub["reliability"].to_numpy())
        k_lo, k_hi = np.percentile(k_boot[cat], [2.5, 97.5])
        rows.append(
            {
                "category": cat,
                "k_rounds_to_R50": k_hat,
                "k_ci_lo": k_lo,
                "k_ci_hi": k_hi,
                "rounds_to_R70": 7 * k_hat / 3,
                "r70_ci_lo": 7 * k_lo / 3,
                "r70_ci_hi": 7 * k_hi / 3,
                "extrapolated_beyond_grid": 7 * k_hat / 3 > max(GRID),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Q3: year-over-year correlation
# --------------------------------------------------------------------------

def season_pairs(
    df: pd.DataFrame, min_rounds: int = YOY_MIN_ROUNDS
) -> pd.DataFrame:
    """Consecutive-season pairs of player means, both seasons >= min_rounds."""
    means = df.groupby(["dg_id", "calendar_year"])[CATS].mean()
    counts = df.groupby(["dg_id", "calendar_year"]).size().rename("n_rounds")
    seasons = means.join(counts).reset_index()
    seasons = seasons[seasons["n_rounds"] >= min_rounds]
    nxt = seasons.copy()
    nxt["calendar_year"] -= 1
    return seasons.merge(
        nxt, on=["dg_id", "calendar_year"], suffixes=("_t", "_t1")
    )


def yoy_correlations(pairs_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cat in CATS:
        a, b = pairs_df[f"{cat}_t"], pairs_df[f"{cat}_t1"]
        rows.append(
            {
                "category": cat,
                "pearson": a.corr(b),
                "spearman": a.corr(b, method="spearman"),
                "n_pairs": len(pairs_df),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Q4: shrinkage and prediction
# --------------------------------------------------------------------------

def shrinkage_table(stab: pd.DataFrame, example_n: int = 12) -> pd.DataFrame:
    """Regression-to-the-mean weight n/(n+k) for a worked example."""
    out = stab[["category", "k_rounds_to_R50"]].copy()
    out[f"weight_{example_n}_rounds"] = example_n / (
        example_n + out["k_rounds_to_R50"]
    )
    return out


def prediction_table(pairs_df: pd.DataFrame) -> pd.DataFrame:
    """Which season-t categories predict season-t+1 total SG.

    Univariate Pearson r per category, plus standardized coefficients from
    one multiple regression of next-season total on all four categories.
    """
    y = pairs_df["sg_total_calc_t1"].to_numpy()
    yz = (y - y.mean()) / y.std()
    X = np.column_stack([pairs_df[f"{c}_t"].to_numpy() for c in SG_CATS])
    Xz = (X - X.mean(axis=0)) / X.std(axis=0)
    betas, *_ = np.linalg.lstsq(
        np.column_stack([np.ones(len(yz)), Xz]), yz, rcond=None
    )
    rows = []
    for i, cat in enumerate(SG_CATS):
        rows.append(
            {
                "category": cat,
                "r_with_next_total": float(np.corrcoef(Xz[:, i], yz)[0, 1]),
                "beta_std": float(betas[i + 1]),
                "n_pairs": len(pairs_df),
            }
        )
    return pd.DataFrame(rows)
