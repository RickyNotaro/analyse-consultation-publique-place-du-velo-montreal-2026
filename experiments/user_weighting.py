"""
EXPERIMENT - per-user weighting.

Idea: prolific users distort both the map and the category totals (e.g. one
account placed 116 of 392 "To be removed" markers). To give every participant
an equal voice ("one person, one vote"), weight each marker by 1 / (number of
markers that user placed). Each user's weights then sum to 1.

This module:
  - exposes load_weighted() -> DataFrame with a `w` column (used by weighted_map.py)
  - when run directly, compares raw vs user-weighted category breakdown
    (chart + CSV + console).

Outputs (in experiments/output/):
  - category_breakdown_weighted.png
  - category_breakdown_weighted.csv
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MARKERS = os.path.join(ROOT, "output", "markers.csv")
OUT = os.path.join(HERE, "output")

CAT_ORDER = [1, 2, 3, 4]
CAT_LABEL = {1: "Appreciated", 2: "Needs improvement", 3: "Missing path", 4: "To be removed"}
CAT_COLOR = {1: "#2ca02c", 2: "#e6c700", 3: "#d62fd6", 4: "#d62728"}


def _liker_list(s):
    """`liker_ids` is a ';'-separated string of user ids (or NaN if unliked)."""
    if pd.isna(s) or not str(s).strip():
        return []
    return [int(x) for x in str(s).split(";") if x.strip()]


def load_weighted():
    """markers.csv + two one-person-one-vote weight columns:

      - `w`        = 1 / user's marker count (de-biases prolific posters)
      - `liked_w`  = sum over this marker's likers of 1 / (that liker's total
                     likes given), so a like-spam account (someone who likes
                     hundreds of markers) can't out-endorse a casual liker any
                     more than a marker-spam account can out-vote a casual
                     poster. Each liker's weight sums to 1 across everything
                     they liked, same as `w` does across a user's markers.
    """
    df = pd.read_csv(MARKERS)
    df["user_marker_count"] = df.groupby("user_id")["user_id"].transform("count")
    df["w"] = 1.0 / df["user_marker_count"]

    likers = df["liker_ids"].apply(_liker_list)
    liker_total_likes = pd.Series([u for lst in likers for u in lst]).value_counts()
    df["liked_w"] = likers.apply(
        lambda lst: sum(1.0 / liker_total_likes[u] for u in lst) if lst else 0.0
    )
    return df


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load_weighted()

    raw = df["category_id"].value_counts().reindex(CAT_ORDER).fillna(0)
    raw_pct = (raw / raw.sum() * 100)
    wt = df.groupby("category_id")["w"].sum().reindex(CAT_ORDER).fillna(0)
    wt_pct = (wt / wt.sum() * 100)

    table = pd.DataFrame({
        "category": [CAT_LABEL[c] for c in CAT_ORDER],
        "raw_count": [int(raw[c]) for c in CAT_ORDER],
        "raw_pct": [round(float(raw_pct[c]), 1) for c in CAT_ORDER],
        "user_weighted": [round(float(wt[c]), 1) for c in CAT_ORDER],
        "user_weighted_pct": [round(float(wt_pct[c]), 1) for c in CAT_ORDER],
        "shift_pp": [round(float(wt_pct[c] - raw_pct[c]), 1) for c in CAT_ORDER],
    })
    table.to_csv(os.path.join(OUT, "category_breakdown_weighted.csv"), index=False, encoding="utf-8")

    # Grouped bar chart: raw % vs user-weighted %.
    x = np.arange(len(CAT_ORDER))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - 0.2, raw_pct.values, 0.4, label="Raw (per marker)", color="#999999")
    ax.bar(x + 0.2, wt_pct.values, 0.4, label="User-weighted (1 per person)",
           color=[CAT_COLOR[c] for c in CAT_ORDER])
    for xi, c in zip(x, CAT_ORDER):
        ax.text(xi - 0.2, raw_pct[c] + 0.4, f"{raw_pct[c]:.1f}", ha="center", fontsize=8)
        ax.text(xi + 0.2, wt_pct[c] + 0.4, f"{wt_pct[c]:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([CAT_LABEL[c] for c in CAT_ORDER])
    ax.set_ylabel("Share of markers (%)")
    ax.set_title("Category share: raw vs per-user-weighted")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "category_breakdown_weighted.png"), dpi=120)
    plt.close(fig)

    print(table.to_string(index=False))
    print(f"\nUnique users (= total weight): {df['w'].sum():.0f}")
    print(f"Most prolific user placed {int(df['user_marker_count'].max())} markers "
          f"(raw weight {int(df['user_marker_count'].max())}x -> 1.0 when user-weighted).")
    print("Wrote category_breakdown_weighted.{png,csv} to experiments/output/")


if __name__ == "__main__":
    main()
