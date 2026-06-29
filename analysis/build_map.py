"""
Step 3 - Interactive HTML map of all 3,333 markers.

Reads output/markers.csv and writes output/map.html:
  - one toggleable, clustered layer per category (colours match the survey)
  - a likes-weighted heat layer to surface demand / danger hotspots
  - a layer control to switch layers on/off
Popups show category, likes, author and the (accent-repaired) comment.
"""
import html
import os

import folium
import pandas as pd
from folium.plugins import HeatMap, MarkerCluster

from textrepair import repair_text

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "output")

# Category -> (label, folium marker colour). folium has no "magenta"/"yellow"
# named icon colours, so we map to its closest supported names.
CAT = {
    1: ("Apprécié", "green"),
    2: ("À améliorer", "orange"),
    3: ("Voie manquante", "purple"),
    4: ("À retirer", "red"),
}
MONTREAL = [45.55, -73.65]


def main():
    df = pd.read_csv(os.path.join(OUT, "markers.csv"))
    df["marker_text"] = df["marker_text"].fillna("")

    m = folium.Map(location=MONTREAL, zoom_start=11, tiles="cartodbpositron")

    # One clustered layer per category.
    for cid, (label, color) in CAT.items():
        sub = df[df["category_id"] == cid]
        fg = folium.FeatureGroup(name=f"{label} ({len(sub)})", show=True)
        cluster = MarkerCluster().add_to(fg)
        for r in sub.itertuples():
            text = html.escape(repair_text(r.marker_text))
            popup = folium.Popup(
                f"<b>{label}</b> &middot; {r.num_likes} j'aime<br>"
                f"<small>usager {r.user_id}</small><br>{text}",
                max_width=300,
            )
            folium.CircleMarker(
                location=[r.lat, r.lon], radius=4, color=color,
                fill=True, fill_color=color, fill_opacity=0.7,
                popup=popup,
            ).add_to(cluster)
        fg.add_to(m)

    # Likes-weighted heat layer (hotspots of community demand / concern).
    heat = df[df["num_likes"] > 0]
    HeatMap(
        heat[["lat", "lon", "num_likes"]].values.tolist(),
        radius=12, blur=18, min_opacity=0.3, name="Chaleur des j'aime",
    ).add_to(folium.FeatureGroup(name="Chaleur des j'aime", show=False).add_to(m))

    folium.LayerControl(collapsed=False).add_to(m)

    title = ("<h3 style='position:fixed;top:8px;left:60px;z-index:9999;"
             "background:white;padding:6px 10px;border-radius:6px;"
             "font-family:sans-serif'>Consultation sur le plan v&eacute;lo &mdash; "
             "3 333 marqueurs de carte</h3>")
    m.get_root().html.add_child(folium.Element(title))

    out = os.path.join(OUT, "map.html")
    m.save(out)
    print(f"Wrote interactive map -> {out}")


if __name__ == "__main__":
    main()
