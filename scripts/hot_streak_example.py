"""Compute the real-world example used in the article's Practical
implications section, so every number there traces to an output.

Spieth's May-June 2019 putting stretch (the hottest 12-round putting
window in the dataset sits inside it) and Rahm's early-2022 driving
stretch, each with the shrinkage prediction and what actually happened.

Usage: python scripts/hot_streak_example.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))

from reliability import load_clean_rounds  # noqa: E402

RESULTS = ROOT / "analysis" / "results"

EXAMPLES = [
    # (label, player substring, category, streak start/end event dates)
    ("spieth_putting_2019", "Spieth", "sg_putt", "2019-05-12", "2019-06-02"),
    ("rahm_driving_2022", "Rahm", "sg_ott", "2022-02-13", "2022-03-06"),
]


def main() -> None:
    df = load_clean_rounds().sort_values(
        ["dg_id", "event_date", "round_num"]
    ).reset_index(drop=True)
    k = pd.read_csv(RESULTS / "stabilization.csv").set_index("category")[
        "k_rounds_to_R50"
    ]

    rows = []
    for label, name, cat, start, end in EXAMPLES:
        g = df[df["player_name"].str.contains(name)]
        g = g[g["dg_id"] == g["dg_id"].iloc[0]].reset_index(drop=True)
        streak = g[(g["event_date"] >= start) & (g["event_date"] <= end)]
        n = len(streak)
        streak_avg = streak[cat].mean()
        weight = n / (n + k[cat])
        prior = g.loc[: streak.index.min() - 1, cat]
        after = g.loc[streak.index.max() + 1:, cat]
        rows.append(
            {
                "example": label,
                "player": g["player_name"].iloc[0],
                "category": cat,
                "streak_rounds": n,
                "streak_avg": round(streak_avg, 3),
                "streak_total": round(streak[cat].sum(), 1),
                "events": "; ".join(streak["event_name"].unique()),
                "finishes": "; ".join(
                    streak.drop_duplicates("event_name")["fin_text"]
                ),
                "shrink_weight": round(weight, 3),
                "predicted_true_skill": round(weight * streak_avg, 2),
                "next30_avg": round(after.head(30).mean(), 2),
                "prior_career_avg": round(prior.mean(), 2),
                "prior_career_rounds": len(prior),
                "after_career_avg": round(after.mean(), 2),
                "after_career_rounds": len(after),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "hot_streak_example.csv", index=False)
    print(out.T.to_string())


if __name__ == "__main__":
    main()
