"""
Step 2 - Analyze the map markers.

Reads output/markers.csv and produces:
  - output/charts/*.png         (category, likes, contributors, spatial, terms)
  - output/top_markers.csv      (25 most-liked markers)
  - output/findings.json        (all computed tables, consumed by the report)
Console prints sanity-check totals.

Covers: category breakdown, engagement/priorities, most-active user per
category, geographic hotspots (DBSCAN), and text themes (TF-IDF + KMeans).
"""
import json
import os
import re
import unicodedata

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from textrepair import repair_text

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")
CHARTS = os.path.join(OUT, "charts")
os.makedirs(CHARTS, exist_ok=True)

CAT_ORDER = [1, 2, 3, 4]
CAT_LABEL = {
    1: "Appreciated",
    2: "Needs improvement",
    3: "Missing path",
    4: "To be removed",
}
# Approximate the consultation colours with matplotlib-friendly hexes.
CAT_COLOR = {1: "#2ca02c", 2: "#e6c700", 3: "#d62fd6", 4: "#d62728"}

# Combined French + English stop words (consultation text is bilingual).
STOPWORDS = set("""
a au aux avec ce ces dans de des du elle en et eux il je la le les leur lui
ma mais me meme mes moi mon ne nos notre nous on ou par pas pour qu que qui sa
se ses son sur ta te tes toi ton tu un une vos votre vous c d j l m n s t y ete
etre avoir fait faire plus tres bien peu trop deja encore aussi car donc alors
ici la-bas cela cette cet ceux celui quoi dont sans sous entre vers chez selon
est sont etait soit ont ai as avait avais serai pourrait devrait faut y'a ya
the a an and or but of to in on for with at by from is are was were be been
this that these those it its as not no there here have has had do does did
will would should can could may might must i you he she we they them their our
your my me us if then than so very more most some any all out up down about
into over again just only also too can't dont don it's there's
rue avenue boulevard chemin pont piste cyclable voie route axe coin
""".split())

def strip_accents(s):
    # "sécuritaire" -> "securitaire", "vélos" -> "velos"; keeps tokens intact.
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


STOPWORDS = {strip_accents(w) for w in STOPWORDS}
TOKEN_RE = re.compile(r"[a-z']{3,}")


def tokenize(text):
    # repair corrupted accents, then strip accents so variants group together.
    return TOKEN_RE.findall(strip_accents(repair_text(text)).lower())


def save(fig, name):
    path = os.path.join(CHARTS, name)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return os.path.relpath(path, OUT)


def main():
    df = pd.read_csv(os.path.join(OUT, "markers.csv"))
    df["marker_text"] = df["marker_text"].fillna("")
    findings = {}

    # ---- 1. Category breakdown -------------------------------------------
    counts = df["category_id"].value_counts().reindex(CAT_ORDER).fillna(0).astype(int)
    pct = (counts / counts.sum() * 100).round(1)
    findings["category_breakdown"] = [
        {"id": c, "label": CAT_LABEL[c], "count": int(counts[c]), "pct": float(pct[c])}
        for c in CAT_ORDER
    ]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar([CAT_LABEL[c] for c in CAT_ORDER], [counts[c] for c in CAT_ORDER],
                  color=[CAT_COLOR[c] for c in CAT_ORDER])
    ax.bar_label(bars, labels=[f"{counts[c]}\n({pct[c]}%)" for c in CAT_ORDER])
    ax.set_ylim(0, counts.max() * 1.18)
    ax.set_title("Markers by category (n=3,333)")
    ax.set_ylabel("Markers")
    save(fig, "category_counts.png")

    # ---- 2. Engagement / priorities --------------------------------------
    findings["likes"] = {
        "total": int(df["num_likes"].sum()),
        "mean": round(float(df["num_likes"].mean()), 2),
        "max": int(df["num_likes"].max()),
        "with_likes": int((df["num_likes"] > 0).sum()),
        "zero_likes": int((df["num_likes"] == 0).sum()),
    }
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(df["num_likes"], bins=range(0, df["num_likes"].max() + 2), color="#4477aa")
    ax.set_yscale("log")
    ax.set_title("Distribution of likes per marker (log scale)")
    ax.set_xlabel("Likes on a marker")
    ax.set_ylabel("Number of markers (log)")
    save(fig, "likes_histogram.png")

    likes_by_cat = df.groupby("category_id")["num_likes"].agg(["sum", "mean"]).reindex(CAT_ORDER)
    findings["likes_by_category"] = [
        {"id": c, "label": CAT_LABEL[c],
         "total_likes": int(likes_by_cat.loc[c, "sum"]),
         "avg_likes": round(float(likes_by_cat.loc[c, "mean"]), 2)}
        for c in CAT_ORDER
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].bar([CAT_LABEL[c] for c in CAT_ORDER], [likes_by_cat.loc[c, "sum"] for c in CAT_ORDER],
                color=[CAT_COLOR[c] for c in CAT_ORDER])
    axes[0].set_title("Total likes by category")
    axes[1].bar([CAT_LABEL[c] for c in CAT_ORDER], [likes_by_cat.loc[c, "mean"] for c in CAT_ORDER],
                color=[CAT_COLOR[c] for c in CAT_ORDER])
    axes[1].set_title("Average likes per marker by category")
    for ax in axes:
        ax.tick_params(axis="x", labelrotation=20)
    save(fig, "likes_by_category.png")

    top = df.sort_values("num_likes", ascending=False).head(25).copy()
    top["marker_text"] = top["marker_text"].map(repair_text)
    top_cols = ["num_likes", "category_en", "lon", "lat", "user_id", "marker_text"]
    top[top_cols].to_csv(os.path.join(OUT, "top_markers.csv"), index=False, encoding="utf-8")
    findings["top_markers"] = [
        {"likes": int(r.num_likes), "category": CAT_LABEL[r.category_id],
         "text": r.marker_text[:160]}
        for r in top.itertuples()
    ]

    # ---- 3. Most active user per category + overall ----------------------
    per_cat = []
    for c in CAT_ORDER:
        sub = df[df["category_id"] == c]
        vc = sub["user_id"].value_counts()
        uid = int(vc.index[0])
        per_cat.append({
            "category": CAT_LABEL[c],
            "user_id": uid,
            "markers": int(vc.iloc[0]),
            "likes_earned": int(sub[sub["user_id"] == uid]["num_likes"].sum()),
        })
    findings["most_active_per_category"] = per_cat

    overall = df["user_id"].value_counts().head(15)
    likes_per_user = df.groupby("user_id")["num_likes"].sum()
    findings["top_contributors"] = [
        {"user_id": int(uid), "markers": int(n), "likes_earned": int(likes_per_user[uid])}
        for uid, n in overall.items()
    ]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh([str(u) for u in overall.index][::-1], list(overall.values)[::-1], color="#4477aa")
    ax.set_title("Top 15 contributors by number of markers")
    ax.set_xlabel("Markers placed")
    ax.set_ylabel("user_id")
    save(fig, "top_contributors.png")
    findings["contributor_stats"] = {
        "unique_authors": int(df["user_id"].nunique()),
        "median_markers_per_author": float(df["user_id"].value_counts().median()),
        "top1_share_pct": round(float(overall.iloc[0] / len(df) * 100), 1),
    }

    # Is "To be removed" sentiment broad, or driven by a few prolific opponents?
    cat4 = df[df["category_id"] == 4]
    top_opp_id = int(cat4["user_id"].value_counts().index[0])
    top_opp_n = int(cat4["user_id"].value_counts().iloc[0])
    findings["removal_concentration"] = {
        "category_total": int(len(cat4)),
        "top_opponent_id": top_opp_id,
        "top_opponent_markers": top_opp_n,
        "top_opponent_share_pct": round(top_opp_n / len(cat4) * 100, 1),
        "top_opponent_all_removal": bool((df[df["user_id"] == top_opp_id]["category_id"] == 4).all()),
    }

    # ---- 4. Geographic hotspots (~300 m grid bins) -----------------------
    # Grid binning avoids DBSCAN's density-chaining, which otherwise merges all
    # of dense downtown into one blob. Cells are ~300 m square at this latitude.
    LAT_CELL = 0.0027                       # ~300 m N-S
    LON_CELL = 0.0038                       # ~300 m E-W at 45.5 deg N
    df["cell"] = (np.floor(df["lat"] / LAT_CELL).astype(int).astype(str) + "_" +
                  np.floor(df["lon"] / LON_CELL).astype(int).astype(str))
    hotspots = []
    for _, grp in df.groupby("cell"):
        if len(grp) < 5:                    # ignore sparse cells
            continue
        rep = grp.sort_values("num_likes", ascending=False).iloc[0]
        dom = grp["category_id"].value_counts().idxmax()
        hotspots.append({
            "markers": int(len(grp)),
            "total_likes": int(grp["num_likes"].sum()),
            "lat": round(float(grp["lat"].mean()), 5),
            "lon": round(float(grp["lon"].mean()), 5),
            "dominant_category": CAT_LABEL[dom],
            "rep_text": repair_text(rep["marker_text"])[:160],
            "rep_likes": int(rep["num_likes"]),
        })
    hotspots.sort(key=lambda h: (-h["total_likes"], -h["markers"]))
    findings["hotspots"] = hotspots[:15]

    # In cells where removal markers are the plurality, how do removal likes
    # compare to appreciation likes? (Tests "concentrated opposition vs broad
    # appreciation" instead of genuine contestation.)
    rem_likes = app_likes = 0
    rem_dom_cells = 0
    for _, grp in df.groupby("cell"):
        if len(grp) >= 10 and grp["category_id"].value_counts().idxmax() == 4:
            rem_dom_cells += 1
            rem_likes += int(grp[grp["category_id"] == 4]["num_likes"].sum())
            app_likes += int(grp[grp["category_id"] == 1]["num_likes"].sum())
    findings["removal_concentration"]["removal_dominant_cells"] = rem_dom_cells
    findings["removal_concentration"]["likes_on_removal_in_those_cells"] = rem_likes
    findings["removal_concentration"]["likes_on_appreciated_in_those_cells"] = app_likes
    dense_cells = [h for h in hotspots]
    findings["cluster_stats"] = {
        "n_hotspot_cells": len(dense_cells),
        "markers_in_hotspots": int(sum(h["markers"] for h in dense_cells)),
        "cell_size_meters": 300, "min_markers_per_cell": 5,
    }

    cat_fr = {1: "Apprécié", 2: "À améliorer", 3: "Voie manquante", 4: "À retirer"}
    fig, ax = plt.subplots(figsize=(8, 7))
    for c in CAT_ORDER:
        sub = df[df["category_id"] == c]
        ax.scatter(sub["lon"], sub["lat"], s=6, alpha=0.4, color=CAT_COLOR[c], label=cat_fr[c])
    ax.set_title("Emplacement des marqueurs par catégorie")
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.legend(markerscale=2, fontsize=8)
    ax.set_aspect(1.4)
    save(fig, "spatial_scatter.png")

    # ---- 5. Text themes (TF-IDF + KMeans) --------------------------------
    texts = df["marker_text"].tolist()
    vec = TfidfVectorizer(tokenizer=tokenize, stop_words=list(STOPWORDS),
                          ngram_range=(1, 2), min_df=5, max_df=0.5, token_pattern=None)
    X = vec.fit_transform(texts)
    terms = np.array(vec.get_feature_names_out())

    def top_terms_for(mask, n=15):
        m = X[mask.to_numpy()] if hasattr(mask, "to_numpy") else X[mask]
        scores = np.asarray(m.mean(axis=0)).ravel()
        idx = scores.argsort()[::-1][:n]
        return [(terms[i], round(float(scores[i]), 4)) for i in idx]

    findings["top_terms_overall"] = [t for t, _ in top_terms_for(df.index == df.index, 20)]
    findings["top_terms_by_category"] = {
        CAT_LABEL[c]: [t for t, _ in top_terms_for(df["category_id"] == c, 12)]
        for c in CAT_ORDER
    }
    fig, ax = plt.subplots(figsize=(9, 6))
    overall_terms = top_terms_for(df.index == df.index, 20)
    names = [t for t, _ in overall_terms][::-1]
    vals = [s for _, s in overall_terms][::-1]
    ax.barh(names, vals, color="#117733")
    ax.set_title("Top 20 terms across all marker comments (mean TF-IDF)")
    save(fig, "top_terms.png")

    K = 6
    km = KMeans(n_clusters=K, random_state=42, n_init=10).fit(X)
    df["theme"] = km.labels_
    order_centroids = km.cluster_centers_.argsort()[:, ::-1]
    themes = []
    for k in range(K):
        kterms = [terms[i] for i in order_centroids[k, :8]]
        members = df[df["theme"] == k]
        samples = members.sort_values("num_likes", ascending=False)["marker_text"].head(3).tolist()
        themes.append({
            "size": int(len(members)),
            "top_terms": kterms,
            "samples": [repair_text(s)[:140] for s in samples],
        })
    themes.sort(key=lambda t: -t["size"])
    findings["themes"] = themes

    with open(os.path.join(OUT, "findings.json"), "w", encoding="utf-8") as f:
        json.dump(findings, f, ensure_ascii=False, indent=2)

    print("Analysis complete.")
    print(f"  Total likes: {findings['likes']['total']} | authors: {findings['contributor_stats']['unique_authors']}")
    print(f"  Hotspot cells (>=5 markers): {findings['cluster_stats']['n_hotspot_cells']} "
          f"holding {findings['cluster_stats']['markers_in_hotspots']} markers")
    print("  Charts + findings.json + top_markers.csv written to output/")


if __name__ == "__main__":
    main()
