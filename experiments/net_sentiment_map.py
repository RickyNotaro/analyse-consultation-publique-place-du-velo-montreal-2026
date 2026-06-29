"""
EXPERIMENT - net-sentiment choropleth (Appreciated vs To-be-removed).

Per ~300 m cell, paints a diverging scale where GREEN = appreciated and
RED = to-be-removed. Only these two valence categories drive the colour, so the
removal signal is unambiguous (needs-improvement and missing-path demand are
covered by the dominant-category grid in blended_map.py).

  score = (w_appreciated - w_removed) / (w_appreciated + w_removed)   (user-weighted)
  +1 = uniformly praised (green), -1 = uniformly wants removal (red).
Cell opacity scales with total weight (more participants -> more confident).

Note: because cells are user-weighted, a corridor a few prolific users want
removed but many others appreciate still reads green (more people, not more
markers). Toggle the per-category layers in blended_map.py for raw removal spots.

Output: experiments/output/net_sentiment_map.html
"""
import os

import folium
import numpy as np
from matplotlib import colormaps, colors

from user_weighting import load_weighted, CAT_LABEL

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
MONTREAL = [45.55, -73.65]
LAT_CELL, LON_CELL = 0.0027, 0.0038
CMAP = colormaps["RdYlGn"]                 # red(low) -> green(high)


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load_weighted()
    df["ilat"] = np.floor(df["lat"] / LAT_CELL).astype(int)
    df["ilon"] = np.floor(df["lon"] / LON_CELL).astype(int)

    m = folium.Map(location=MONTREAL, zoom_start=11, tiles="cartodbpositron")
    fg = folium.FeatureGroup(name="Appreciated (green) vs To be removed (red)", show=True)

    rows = []
    for (ilat, ilon), g in df.groupby(["ilat", "ilon"]):
        w = g.groupby("category_id")["w"].sum()
        appr = float(w.get(1, 0.0))
        removed = float(w.get(4, 0.0))
        denom = appr + removed
        if denom < 0.3:                    # not enough valence signal
            continue
        score = (appr - removed) / denom            # -1 .. +1
        rows.append((ilat, ilon, score, denom, appr, removed, float(w.get(3, 0.0))))

    if not rows:
        print("No cells passed the threshold.")
        return
    max_w = max(r[3] for r in rows)
    for ilat, ilon, score, denom, appr, removed, missing in rows:
        rgba = CMAP((score + 1) / 2)                # map -1..1 -> 0..1
        lat0, lon0 = ilat * LAT_CELL, ilon * LON_CELL
        folium.Rectangle(
            bounds=[[lat0, lon0], [lat0 + LAT_CELL, lon0 + LON_CELL]],
            color=colors.to_hex(rgba), weight=0,
            fill=True, fill_color=colors.to_hex(rgba),
            fill_opacity=0.25 + 0.6 * min(denom / max_w, 1.0),
            popup=folium.Popup(
                f"<b>score {score:+.2f}</b> "
                f"({'praised' if score >= 0 else 'wants removal'})<br>"
                f"appreciated (weight): {appr:.2f}<br>"
                f"to be removed (weight): {removed:.2f}<br>"
                f"missing-path demand: {missing:.2f}", max_width=240),
        ).add_to(fg)
    fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    legend = ("<div style='position:fixed;bottom:18px;left:18px;z-index:9999;"
              "background:white;padding:8px 12px;border-radius:6px;font-family:sans-serif;"
              "font-size:12px;box-shadow:0 1px 4px rgba(0,0,0,.3)'>"
              "<b>Appreciated vs To be removed</b><br>"
              "<span style='background:linear-gradient(90deg,#a50026,#ffffbf,#006837);"
              "display:inline-block;width:160px;height:12px'></span><br>"
              "<span style='float:left'>wants removal</span>"
              "<span style='float:right'>appreciated</span><br style='clear:both'>"
              "<i>opacity = participants; needs-improvement & missing excluded</i></div>")
    m.get_root().html.add_child(folium.Element(legend))

    out = os.path.join(OUT, "net_sentiment_map.html")
    m.save(out)
    print(f"Wrote {out}  ({len(rows)} cells)")


if __name__ == "__main__":
    main()
