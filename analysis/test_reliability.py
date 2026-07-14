"""Tests for the reliability machinery against known ground truth.

Synthetic model: player true skill ~ N(0, s^2), each round = skill +
N(0, sigma^2). The reliability of an n-round mean is then exactly
R(n) = n / (n + k) with k = sigma^2 / s^2, which pins down every stage of
the pipeline.
"""

import numpy as np
import pandas as pd
import pytest

from reliability import (
    CATS,
    SG_CATS,
    bootstrap_stabilization,
    colwise_pearson,
    fit_k,
    half_mean_pairs,
    prediction_table,
    reliability_curve,
    season_pairs,
    stabilization_table,
)

K_TRUE = 20.0  # sigma^2 / s^2
GRID = [5, 10, 20, 40]


def synthetic_df(n_players=400, n_rounds=100, k_true=K_TRUE, seed=7):
    rng = np.random.default_rng(seed)
    s2 = 0.04
    sigma = np.sqrt(k_true * s2)
    skills = rng.normal(0, np.sqrt(s2), size=(n_players, len(SG_CATS)))
    rows = []
    for p in range(n_players):
        vals = skills[p] + rng.normal(0, sigma, size=(n_rounds, len(SG_CATS)))
        for i in range(n_rounds):
            row = {"dg_id": p, "window": "w1", "calendar_year": 2020 + i % 2}
            row.update(dict(zip(SG_CATS, vals[i])))
            row["sg_total_calc"] = vals[i].sum()
            rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def pairs():
    df = synthetic_df()
    return half_mean_pairs(df, grid=GRID, n_splits=100,
                           rng=np.random.default_rng(0))


def test_colwise_pearson_matches_corrcoef():
    rng = np.random.default_rng(1)
    x, y = rng.random((50, 3)), rng.random((50, 3))
    got = colwise_pearson(x, y)
    for j in range(3):
        assert got[j] == pytest.approx(np.corrcoef(x[:, j], y[:, j])[0, 1])


def test_halves_are_disjoint_and_sized():
    df = synthetic_df(n_players=5, n_rounds=30)
    out = half_mean_pairs(df, grid=[10], n_splits=8,
                          rng=np.random.default_rng(0))
    assert out[10]["x"].shape == (5, 8, len(CATS))
    # a player with 30 rounds is eligible for n=10 (needs 20) but the two
    # halves must come from disjoint rounds: their means almost surely differ
    assert not np.allclose(out[10]["x"], out[10]["y"])


def test_eligibility_threshold():
    df = synthetic_df(n_players=3, n_rounds=19)  # < 2*10 rounds
    out = half_mean_pairs(df, grid=[10], n_splits=4,
                          rng=np.random.default_rng(0))
    assert out[10]["x"].shape[0] == 0


def test_reliability_matches_theory(pairs):
    curve = reliability_curve(pairs)
    for _, row in curve.iterrows():
        expected = row["n"] / (row["n"] + K_TRUE)
        assert row["reliability"] == pytest.approx(expected, abs=0.06), (
            f"{row['category']} n={row['n']}"
        )


def test_fitted_k_recovers_truth(pairs):
    curve = reliability_curve(pairs)
    for cat in CATS:
        sub = curve[curve["category"] == cat]
        k = fit_k(sub["n"].to_numpy(float), sub["reliability"].to_numpy())
        assert k == pytest.approx(K_TRUE, rel=0.20), cat


def test_bootstrap_ci_covers_truth(pairs):
    _, k_boot = bootstrap_stabilization(pairs, n_boot=100,
                                        rng=np.random.default_rng(0))
    stab = stabilization_table(reliability_curve(pairs), k_boot)
    for _, row in stab.iterrows():
        assert row["k_ci_lo"] < K_TRUE < row["k_ci_hi"], row["category"]
        assert row["k_ci_lo"] < row["k_rounds_to_R50"] < row["k_ci_hi"]


def test_season_pairs_threshold_and_alignment():
    df = synthetic_df(n_players=10, n_rounds=100)  # 50 rounds per season
    pairs_df = season_pairs(df, min_rounds=30)
    assert len(pairs_df) == 10  # one 2020->2021 pair per player
    assert (pairs_df["n_rounds_t"] >= 30).all()
    df_thin = synthetic_df(n_players=10, n_rounds=40)  # 20 per season
    assert len(season_pairs(df_thin, min_rounds=30)) == 0


def test_prediction_table_sane():
    df = synthetic_df(n_players=300, n_rounds=100)
    tab = prediction_table(season_pairs(df, min_rounds=30))
    assert set(tab["category"]) == set(SG_CATS)
    # every category contributes equally to total by construction
    assert (tab["r_with_next_total"] > 0.2).all()
    assert (tab["beta_std"] > 0.1).all()
