"""
EXPERIMENT - blended, single-view user-weighted maps.

Heatmaps blend additively and have no z-order, so "most weight on top" only
works with discrete marks. This builds experiments/output/blended_map.html with
two blended layers (toggle in the top-left control):

  1. "Weighted markers (heaviest on top)"  [default]
     Every marker is a circle coloured by category; radius + opacity scale with
     the user-weight (1 / that user's marker count). Markers are drawn lightest
     first so the HIGHEST-weight voices render on TOP. Because casual users
     (1 marker -> weight 1) outrank prolific ones, this visually elevates the
     broad base over the few power-users.

  2. "Dominant category grid (~300 m, user-weighted)"
     ~300 m cells coloured by the category holding the most user-weight in that
     cell; fill opacity scales with the cell's total user-weight. One glance =
     what each area feels, de-biased for prolific users.
"""
import os

import folium
import numpy as np

from user_weighting import load_weighted, CAT_LABEL, CAT_COLOR

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
MONTREAL = [45.55, -73.65]
LAT_CELL, LON_CELL = 0.0027, 0.0038        # ~300 m cells


def weighted_markers_layer(df):
    fg = folium.FeatureGroup(name="Weighted markers (heaviest on top)", show=True)
    # Lightest first -> heaviest drawn last -> heaviest on top.
    for r in df.sort_values("w").itertuples():
        folium.CircleMarker(
            location=[r.lat, r.lon],
            radius=2 + 6 * (r.w ** 0.5),
            color=CAT_COLOR[r.category_id],
            weight=0,
            fill=True,
            fill_color=CAT_COLOR[r.category_id],
            fill_opacity=0.25 + 0.55 * r.w,
            popup=folium.Popup(
                f"<b>{CAT_LABEL[r.category_id]}</b><br>"
                f"user-weight {r.w:.3f} (placed {r.user_marker_count} markers)<br>"
                f"{r.num_likes} likes", max_width=260),
        ).add_to(fg)
    return fg


def dominant_grid_layer(df):
    fg = folium.FeatureGroup(name="Dominant category grid (~300m, user-weighted)", show=False)
    df = df.copy()
    df["ilat"] = np.floor(df["lat"] / LAT_CELL).astype(int)
    df["ilon"] = np.floor(df["lon"] / LON_CELL).astype(int)
    grouped = df.groupby(["ilat", "ilon"])
    cell_weight = grouped["w"].sum()
    max_w = cell_weight.max()
    for (ilat, ilon), g in grouped:
        total = g["w"].sum()
        if total < 0.5:                    # skip near-empty cells
            continue
        dom = g.groupby("category_id")["w"].sum().idxmax()
        lat0, lon0 = ilat * LAT_CELL, ilon * LON_CELL
        folium.Rectangle(
            bounds=[[lat0, lon0], [lat0 + LAT_CELL, lon0 + LON_CELL]],
            color=CAT_COLOR[dom], weight=0,
            fill=True, fill_color=CAT_COLOR[dom],
            fill_opacity=0.2 + 0.65 * min(total / max_w, 1.0),
            popup=folium.Popup(
                f"<b>{CAT_LABEL[dom]}</b> (dominant)<br>"
                f"total user-weight {total:.2f}<br>"
                + "<br>".join(f"{CAT_LABEL[c]}: {w:.2f}"
                              for c, w in g.groupby('category_id')['w'].sum().items()),
                max_width=260),
        ).add_to(fg)
    return fg


def legend():
    items = "".join(
        f"<div><span style='display:inline-block;width:12px;height:12px;"
        f"background:{CAT_COLOR[c]};margin-right:6px;border-radius:2px'></span>"
        f"{CAT_LABEL[c]}</div>" for c in [1, 2, 3, 4])
    return ("<div style='position:fixed;bottom:18px;left:18px;z-index:9999;"
            "background:white;padding:8px 12px;border-radius:6px;font-family:sans-serif;"
            "font-size:12px;box-shadow:0 1px 4px rgba(0,0,0,.3)'>"
            "<b>Category</b>" + items +
            "<hr style='margin:6px 0'><i>Size/opacity = user-weight<br>"
            "(1 ÷ that user's marker count)</i></div>")


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load_weighted()
    m = folium.Map(location=MONTREAL, zoom_start=11, tiles="cartodbpositron")
    weighted_markers_layer(df).add_to(m)
    dominant_grid_layer(df).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(legend()))
    out = os.path.join(OUT, "blended_map.html")
    m.save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
