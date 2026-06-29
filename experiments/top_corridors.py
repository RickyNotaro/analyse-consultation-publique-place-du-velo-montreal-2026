"""
EXPERIMENT - top corridors mentioned in comments.

Keyword-matches well-known Montreal streets/corridors in the (accent-repaired,
accent-stripped) comment text and ranks them by community attention. Keyword-
based, so it's a lower bound and a marker mentioning two streets counts for both.

Ranked by UNIQUE USERS (one person, one count): for each corridor the bar length
is the number of *distinct* people who weighed in on it -- whether by creating a
marker OR by liking one (the two are merged into a single "participation"). The
bar is split by each person's STANCE on that corridor:
  - "For (pro-infra)"  : engaged only with appreciated / improve / missing markers
  - "Mixed"            : engaged with both pro-infra AND removal markers
  - "Against (removal)": engaged only with "to be removed" markers
A person touches a category if they created OR liked a marker of it. The three
segments don't overlap, so they sum exactly to `unique_participants`. Someone who
liked five markers on the same corridor still counts once -- this de-biases the
raw `total_likes` (kept as a reference column), which over-weights very active
likers. The per-category marker mix is kept in the CSV (`cat1..4`).

Outputs:
  - experiments/output/top_corridors.png   (horizontal bars: unique people, by stance)
  - experiments/output/top_corridors.csv
"""
import csv
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis"))
from textrepair import repair_text          # noqa: E402

MARKERS = os.path.join(ROOT, "output", "markers.csv")
OUT = os.path.join(HERE, "output")
CAT_LABEL = {1: "Appreciated", 2: "Needs improvement", 3: "Missing path", 4: "To be removed"}
CAT_COLOR = {1: "#2ca02c", 2: "#e6c700", 3: "#d62fd6", 4: "#d62728"}

# canonical corridor -> alternative spellings (accent-stripped, lowercase).
CORRIDORS = {
    "Avenue du Parc": ["du parc", "avenue parc", "ave parc"],
    "Henri-Bourassa": ["henri bourassa", "henri-bourassa", "bourassa"],
    "Saint-Denis": ["saint denis", "saint-denis", "st denis", "st-denis"],
    "Sherbrooke": ["sherbrooke"],
    "Rachel": ["rachel"],
    "Saint-Urbain": ["saint urbain", "saint-urbain", "st urbain", "st-urbain"],
    "Rene-Levesque": ["rene levesque", "rene-levesque", "levesque"],
    "Christophe-Colomb": ["christophe colomb", "christophe-colomb", "colomb"],
    "Berri": ["berri"],
    "Peel": ["peel"],
    "De la Commune": ["de la commune", "la commune"],
    "Jarry": ["jarry"],
    "Saint-Laurent (boul.)": ["saint laurent", "saint-laurent", "st laurent", "st-laurent"],
    "Notre-Dame": ["notre dame", "notre-dame"],
    "Papineau": ["papineau"],
    "De Lorimier": ["lorimier"],
    "Pie-IX": ["pie ix", "pie-ix", "pie-9", "pie 9"],
    "Viau": ["viau"],
    "Lasalle": ["lasalle", "la salle"],
    "Verdun": ["verdun"],
    "De Maisonneuve": ["maisonneuve"],
    "Wellington": ["wellington"],
    "Cote-des-Neiges": ["cote des neiges", "cote-des-neiges"],
    "Cote-Sainte-Catherine": ["cote sainte catherine", "cote-sainte-catherine"],
}


def strip(s):
    import unicodedata
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s.lower()


def main():
    os.makedirs(OUT, exist_ok=True)
    df = pd.read_csv(MARKERS)
    df["norm"] = df["marker_text"].fillna("").map(lambda s: strip(repair_text(s)))
    df["likers"] = df["liker_ids"].fillna("").map(
        lambda s: [int(x) for x in str(s).split(";") if x])
    patterns = {name: re.compile("|".join(r"\b" + re.escape(a) + r"\b" for a in alts))
                for name, alts in CORRIDORS.items()}

    from collections import defaultdict

    rows = []
    for name, pat in patterns.items():
        hit = df[df["norm"].str.contains(pat)]
        if len(hit) == 0:
            continue
        by_cat = hit["category_id"].value_counts()
        # Each person -> set of categories they engaged with (created OR liked).
        user_cats = defaultdict(set)
        for m in hit.itertuples():
            user_cats[m.user_id].add(m.category_id)
            for u in m.likers:
                user_cats[u].add(m.category_id)
        for_only = mixed = against_only = 0
        for cats in user_cats.values():
            pro = bool(cats & {1, 2, 3})
            rem = 4 in cats
            if pro and rem:
                mixed += 1
            elif rem:
                against_only += 1
            else:
                for_only += 1
        rows.append({
            "corridor": name,
            "unique_participants": int(len(user_cats)),  # bar length (one per person)
            "for_users": int(for_only),            # only pro-infra markers
            "mixed_users": int(mixed),             # both pro-infra and removal
            "against_users": int(against_only),    # only removal markers
            "markers": int(len(hit)),
            "total_likes": int(hit["num_likes"].sum()),  # reference (per-like, not deduped)
            **{f"cat{c}": int(by_cat.get(c, 0)) for c in [1, 2, 3, 4]},
        })
    res = pd.DataFrame(rows).sort_values("unique_participants", ascending=False).reset_index(drop=True)
    res.to_csv(os.path.join(OUT, "top_corridors.csv"), index=False, encoding="utf-8")

    top = res.head(18).iloc[::-1]            # smallest at bottom for barh
    fig, ax = plt.subplots(figsize=(10, 8))
    segments = [("for_users", "#2ca02c", "For (pro-infra)"),
                ("mixed_users", "#e6c700", "Mixed (both)"),
                ("against_users", "#d62728", "Against (removal)")]
    left = [0] * len(top)
    for col, color, lab in segments:
        vals = top[col].values
        ax.barh(top["corridor"], vals, left=left, color=color, label=lab)
        left = [l + v for l, v in zip(left, vals)]
    for y, (_, r) in enumerate(top.iterrows()):
        ax.text(r["unique_participants"] + 2, y, f"{r['unique_participants']} people",
                va="center", fontsize=8)
    ax.set_xlabel("Unique people (one per person), split by stance — engaged via a marker or a like")
    ax.set_title("Most-mentioned corridors: unique people for vs against cycling infrastructure")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "top_corridors.png"), dpi=120)
    plt.close(fig)

    print(res.head(18).to_string(index=False))
    print("\nWrote top_corridors.{png,csv} to experiments/output/")


if __name__ == "__main__":
    main()
