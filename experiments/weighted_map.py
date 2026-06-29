"""
EXPERIMENT - user-weighted map visualisations.

Builds experiments/output/weighted_map.html with several toggleable heat layers
so you can directly compare how hotspots change once prolific users are
de-biased (each user's markers share a total weight of 1):

  - "Density - RAW (per marker)"        : every marker counts equally (weight 1)
  - "Density - USER-WEIGHTED"           : weight = 1 / user's marker count   <- default
  - "Likes-weighted"                    : weight = number of likes
  - "User-weighted - <category>" (x4)   : per-category, de-biased demand surfaces

All heat layers share identical radius/blur so the comparison is fair. Toggle
one at a time in the layer control (top-left).
"""
import os

import folium
from folium.plugins import HeatMap

from user_weighting import load_weighted, CAT_LABEL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
MONTREAL = [45.55, -73.65]
HEAT = dict(radius=12, blur=18, min_opacity=0.25)  # shared params for fair comparison
CAT_GRAD = {
    1: {0.4: "#a8e6a3", 1: "#1a7a1a"},   # green
    2: {0.4: "#ffe680", 1: "#b39400"},   # yellow
    3: {0.4: "#f3a8f3", 1: "#a000a0"},   # magenta
    4: {0.4: "#f3a8a8", 1: "#a00000"},   # red
}


def heat_layer(df, name, weight_col, show, gradient=None):
    fg = folium.FeatureGroup(name=name, show=show)
    if weight_col is None:
        data = df[["lat", "lon"]].assign(w=1.0).values.tolist()
    else:
        sub = df[df[weight_col] > 0]
        data = sub[["lat", "lon", weight_col]].values.tolist()
    HeatMap(data, gradient=gradient, **HEAT).add_to(fg)
    return fg


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load_weighted()

    m = folium.Map(location=MONTREAL, zoom_start=11, tiles="cartodbpositron")

    heat_layer(df, "Density - USER-WEIGHTED (1 per person)", "w", show=True).add_to(m)
    heat_layer(df, "Density - RAW (per marker)", None, show=False).add_to(m)
    heat_layer(df, "Likes-weighted", "num_likes", show=False).add_to(m)
    for cid in [1, 2, 3, 4]:
        sub = df[df["category_id"] == cid]
        heat_layer(sub, f"User-weighted - {CAT_LABEL[cid]}", "w",
                   show=False, gradient=CAT_GRAD[cid]).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    note = ("<div style='position:fixed;top:8px;left:60px;z-index:9999;max-width:340px;"
            "background:white;padding:8px 12px;border-radius:6px;font-family:sans-serif;"
            "font-size:12px;box-shadow:0 1px 4px rgba(0,0,0,.3)'>"
            "<b>User-weighted heatmaps</b><br>Each user's markers share a total weight of 1, "
            "so a person who placed 100 markers no longer outweighs 100 people. "
            "Toggle <i>RAW</i> vs <i>USER-WEIGHTED</i> to see hotspots shift.</div>")
    m.get_root().html.add_child(folium.Element(note))

    out = os.path.join(OUT, "weighted_map.html")
    m.save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
