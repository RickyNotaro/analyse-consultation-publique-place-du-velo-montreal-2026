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
     ~300 m cells coloured by the category holding the most engaged weight in
     that cell (marker-placer weight + de-spammed liker weight, see
     user_weighting.load_weighted); fill opacity scales with the cell's total
     engaged weight. One glance = what each area feels, de-biased for both
     prolific posters and like-spam accounts. A slider (bottom-right) hides
     cells whose total engaged weight is below a chosen threshold.
"""
import html
import os

import folium
from folium.plugins import MarkerCluster
import numpy as np
import pandas as pd

from user_weighting import load_weighted, CAT_LABEL, CAT_COLOR

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "output")
# The dominant-category grid is a favourite view: publish it as its own top-level
# page at the repo root (a sibling of index.html) so it has a clean, shareable URL.
GRID_PAGE = os.path.join(ROOT, "carte-dominante.html")
MONTREAL = [45.55, -73.65]
LAT_CELL, LON_CELL = 0.0027, 0.0038        # ~300 m cells
MIN_CELL_WEIGHT = 0.5                       # default slider threshold
GRID_SATURATION_WEIGHT = 5.0                # cell reaches full colour at this total user-weight (slider default)
CLUSTER_POPUP_CAP = 25                      # max comments shown in a cluster popup
GRID_COMMENT_CAP = 40                       # max comments stored/shown per grid cell

# French (fr-CA) category labels for the clustered layers / popups.
CAT_LABEL_FR = {1: "Apprécié", 2: "À améliorer", 3: "Piste manquante", 4: "À retirer"}


def weighted_markers_layer(df):
    fg = folium.FeatureGroup(name="Weighted markers (heaviest on top)", show=False)
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


def _cluster_icon_fn(color):
    """JS iconCreateFunction: a category-coloured disc whose size grows with the
    number of merged markers, with the count drawn inside."""
    return (
        "function(cluster){"
        "var n=cluster.getChildCount();"
        "var s=Math.round(30+Math.min(n,200)/200*26);"  # 30..56 px
        "return L.divIcon({className:'',iconSize:[s,s],"
        "html:'<div style=\"width:'+s+'px;height:'+s+'px;line-height:'+s+'px;'"
        "+'border-radius:50%;text-align:center;color:#fff;'"
        "+'font:bold 12px sans-serif;opacity:.88;"
        f"background:{color};box-shadow:0 0 0 4px {color}55\">'+n+'</div>'}});"
        "}"
    )


def _marker_icon(w, color):
    """A DivIcon disc matching the weighted-markers look (size + opacity = weight).

    DivIcon markers (not CircleMarkers) are used so they cluster reliably with
    Leaflet.markercluster's spiderfy/animation code paths.
    """
    r = 2 + 6 * (w ** 0.5)
    d = int(round(2 * r))
    a = int(round(r))
    op = round(0.25 + 0.55 * w, 3)
    return folium.DivIcon(
        icon_size=(d, d), icon_anchor=(a, a), class_name="",
        html=f'<div style="width:{d}px;height:{d}px;border-radius:50%;'
             f'background:{color};opacity:{op}"></div>')


def clustered_category_layers(df):
    """One MarkerCluster per category, so only SAME-typed markers merge.

    Each marker carries its comment / weight / likes as Leaflet options; the
    cluster-click handler (see cluster_comment_js) reads them to build a single
    popup listing every merged comment. Returns [(cluster, category_id), ...].
    """
    layers = []
    for cat in [1, 2, 3, 4]:
        color = CAT_COLOR[cat]
        mc = MarkerCluster(
            name=f"{CAT_LABEL_FR[cat]} (regroupés)", show=True,
            icon_create_function=_cluster_icon_fn(color),
            options={
                "zoomToBoundsOnClick": False,   # click shows the combined popup
                "spiderfyOnMaxZoom": False,     # ... rather than fanning out
                "showCoverageOnHover": False,
                "maxClusterRadius": 60,
            },
        )
        for r in df[df.category_id == cat].itertuples():
            txt = "" if pd.isna(r.marker_text) else str(r.marker_text)
            esc = html.escape(txt)
            likes = int(r.num_likes)
            folium.Marker(
                location=[r.lat, r.lon],
                icon=_marker_icon(r.w, color),
                popup=folium.Popup(
                    f"<b>{CAT_LABEL_FR[cat]}</b><br>{esc or '<i>(sans texte)</i>'}<br>"
                    f"<span style='color:#888'>poids {r.w:.3f} · "
                    f"{likes} j’aime</span>", max_width=280),
                comment=esc, w=round(float(r.w), 4), likes=likes,
            ).add_to(mc)
        layers.append((mc, cat))
    return layers


def cluster_comment_js(map_name, layers):
    """clusterclick -> one scrollable popup listing every merged comment.

    `layers` is the list returned by clustered_category_layers. Comments are
    sorted heaviest-weight first and capped at CLUSTER_POPUP_CAP.
    """
    attaches = "\n".join(
        f"  attach({mc.get_name()}, '{CAT_COLOR[cat]}', "
        f"{_js_str(CAT_LABEL_FR[cat])});"
        for mc, cat in layers)
    return folium.Element(f"""
<script>
window.addEventListener('load', function () {{
  var MAP = {map_name};
  var CAP = {CLUSTER_POPUP_CAP};
  function attach(group, color, label) {{
    group.on('clusterclick', function (e) {{
      var kids = e.layer.getAllChildMarkers();
      kids.sort(function (a, b) {{ return (b.options.w || 0) - (a.options.w || 0); }});
      var head = '<div style="font:bold 13px sans-serif;color:' + color +
                 ';margin-bottom:6px">' + label + ' — ' + kids.length +
                 ' commentaires</div>';
      var body = '';
      kids.slice(0, CAP).forEach(function (m) {{
        var o = m.options;
        var c = (o.comment && o.comment.length) ? o.comment : '<i>(sans texte)</i>';
        var jaime = (o.likes === 1) ? '1 j’aime' : (o.likes || 0) + ' j’aime';
        body += '<div style="border-top:1px solid #eee;padding:5px 0;font:12px sans-serif">' +
                c + '<div style="color:#888;font-size:11px;margin-top:2px">poids ' +
                (o.w || 0).toFixed(3) + ' · ' + jaime + '</div></div>';
      }});
      if (kids.length > CAP) {{
        body += '<div style="color:#888;font:italic 11px sans-serif;padding-top:6px">… et ' +
                (kids.length - CAP) + ' de plus (zoomez pour les voir)</div>';
      }}
      L.popup({{maxWidth: 320}}).setLatLng(e.layer.getLatLng())
        .setContent('<div style="max-height:300px;overflow:auto">' + head + body + '</div>')
        .openOn(MAP);
    }});
  }}
{attaches}
}});
</script>
""")


def _js_str(s):
    """A safely JS-quoted string literal (handles quotes/specials)."""
    import json
    return json.dumps(s)


def dominant_grid_geojson(df):
    """Build a GeoJSON FeatureCollection of dominant-category cells.

    A cell's weight blends two one-person-one-vote pools: `w` (from placing a
    marker) and `liked_w` (from liking one), so a category's dominance in a
    cell reflects both people who spoke up and people who endorsed a comment,
    without a marker-spam or like-spam account distorting either pool.

    Each feature carries its total engaged weight (`weight`) so the slider can
    show/hide it client-side. Returns (geojson, max_weight).
    """
    df = df.copy()
    df["ilat"] = np.floor(df["lat"] / LAT_CELL).astype(int)
    df["ilon"] = np.floor(df["lon"] / LON_CELL).astype(int)
    df["engaged"] = df["w"] + df["liked_w"]
    grouped = df.groupby(["ilat", "ilon"])
    max_w = float(grouped["engaged"].sum().max())
    features = []
    for (ilat, ilon), g in grouped:
        total = float(g["engaged"].sum())
        cat_w = g.groupby("category_id")["engaged"].sum()
        dom = int(cat_w.idxmax())
        lat0, lon0 = ilat * LAT_CELL, ilon * LON_CELL
        lat1, lon1 = lat0 + LAT_CELL, lon0 + LON_CELL
        breakdown = "<br>".join(f"{CAT_LABEL_FR[c]} : {w:.2f}" for c, w in cat_w.items())
        # Comments in this cell, ranked by (de-spammed) liked-weight first, then
        # by user-weight as a tiebreak. Capped for size/readability.
        g_sorted = g.sort_values(["liked_w", "w"], ascending=[False, False])
        comments = [
            [html.escape("" if pd.isna(r.marker_text) else str(r.marker_text)),
             round(float(r.w), 4), int(r.num_likes), int(r.category_id),
             round(float(r.liked_w), 4)]
            for r in g_sorted.head(GRID_COMMENT_CAP).itertuples()
        ]
        features.append({
            "type": "Feature",
            "properties": {
                "weight": round(total, 4),
                "color": CAT_COLOR[dom],
                # Colour saturates at GRID_SATURATION_WEIGHT total engaged weight per cell.
                "fillOpacity": round(0.2 + 0.65 * min(total / GRID_SATURATION_WEIGHT, 1.0), 3),
                "popup": (f"<b>{CAT_LABEL_FR[dom]}</b> (dominante)<br>"
                          f"poids total (usagers + j'aime) {total:.2f}<br>{breakdown}"),
                "comments": comments,
                "n_total": int(len(g_sorted)),
                "dom_color": CAT_COLOR[dom],
                "dom_label": CAT_LABEL_FR[dom],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[lon0, lat0], [lon1, lat0],
                                 [lon1, lat1], [lon0, lat1], [lon0, lat0]]],
            },
        })
    return {"type": "FeatureCollection", "features": features}, max_w


def dominant_grid_layer(geojson, show=False, name="Dominant category grid (~300m, user-weighted)", popup=True):
    return folium.GeoJson(
        data=geojson,
        name=name,
        show=show,
        style_function=lambda f: {
            "color": f["properties"]["color"],
            "weight": 0,
            "fillColor": f["properties"]["color"],
            "fillOpacity": f["properties"]["fillOpacity"],
        },
        # popup=False: the caller binds its own click handler (see grid_comments_js).
        popup=folium.GeoJsonPopup(fields=["popup"], labels=False) if popup else None,
    )


def grid_slider(map_name, grid_name, max_w):
    """A range slider (bottom-right) that hides grid cells below the threshold."""
    slider_max = max(1.0, round(max_w, 2))
    html = f"""
<div id="gridFilter" style="position:fixed;bottom:18px;right:18px;z-index:9999;
     background:white;padding:10px 14px;border-radius:6px;font-family:sans-serif;
     font-size:12px;box-shadow:0 1px 4px rgba(0,0,0,.3);width:220px">
  <b>Grid: min cell weight</b><br>
  <input id="gridThr" type="range" min="0" max="{slider_max}" step="0.5"
         value="{MIN_CELL_WEIGHT}" style="width:100%">
  <div>hide cells &lt; <span id="gridThrVal">{MIN_CELL_WEIGHT}</span>
       <span style="color:#888">(max {slider_max:g})</span></div>
</div>
<script>
window.addEventListener('load', function () {{
  var grid = {grid_name};
  var cells = [];
  grid.eachLayer(function (l) {{ cells.push(l); }});
  var slider = document.getElementById('gridThr');
  var label  = document.getElementById('gridThrVal');
  function applyGridFilter() {{
    var thr = parseFloat(slider.value);
    label.textContent = thr;
    cells.forEach(function (l) {{
      var w = l.feature.properties.weight;
      if (w < thr) {{ if (grid.hasLayer(l)) grid.removeLayer(l); }}
      else        {{ if (!grid.hasLayer(l)) grid.addLayer(l); }}
    }});
  }}
  slider.addEventListener('input', applyGridFilter);
  applyGridFilter();
}});
</script>
"""
    return folium.Element(html)


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


def legend_fr():
    items = "".join(
        f"<div><span style='display:inline-block;width:12px;height:12px;"
        f"background:{CAT_COLOR[c]};margin-right:6px;border-radius:2px'></span>"
        f"{CAT_LABEL_FR[c]}</div>" for c in [1, 2, 3, 4])
    return ("<div style='position:fixed;bottom:18px;left:18px;z-index:9999;"
            "background:white;padding:8px 12px;border-radius:6px;font-family:sans-serif;"
            "font-size:12px;box-shadow:0 1px 4px rgba(0,0,0,.3)'>"
            "<b>Catégorie dominante</b>" + items +
            "<hr style='margin:6px 0'><i>Opacité = poids total du secteur "
            "(marqueurs + j'aime)<br>(chaque personne pèse 1, réparti sur ses "
            "marqueurs et sur ses j'aime)</i></div>")


def grid_controls_fr(grid_name, max_w):
    """French control panel (bottom-right): colour-saturation + min-weight sliders.

    Saturation sets the total engaged weight (markers + likes) at which a cell
    reaches full colour (higher = more nuance / more basemap context visible);
    the min-weight slider hides sparse cells. Both recompute cell styling
    client-side, so all cells are captured once at load to keep the two
    sliders consistent.
    """
    min_max = max(1.0, round(max_w, 2))
    sat_max = max(10.0, round(max_w))
    html = f"""
<div id="gridCtl" style="position:fixed;bottom:18px;right:18px;z-index:9999;
     background:white;padding:10px 14px;border-radius:6px;font-family:sans-serif;
     font-size:12px;box-shadow:0 1px 4px rgba(0,0,0,.3);width:250px">
  <b>Grille (~300&nbsp;m)</b>
  <div style="margin-top:6px">Saturation des couleurs à
    <span id="gridSatVal">{GRID_SATURATION_WEIGHT:g}</span></div>
  <input id="gridSat" type="range" min="0.5" max="{sat_max:g}" step="0.5"
         value="{GRID_SATURATION_WEIGHT}" style="width:100%">
  <div style="color:#888;font-size:11px">plus haut = plus de nuances, plus de contexte</div>
  <div style="margin-top:8px">Masquer les secteurs &lt;
    <span id="gridMinVal">{MIN_CELL_WEIGHT:g}</span></div>
  <input id="gridMin" type="range" min="0" max="{min_max}" step="0.5"
         value="{MIN_CELL_WEIGHT}" style="width:100%">
  <div style="color:#888;font-size:11px">poids total, usagers + j'aime (max {min_max:g})</div>
</div>
<script>
window.addEventListener('load', function () {{
  var grid = {grid_name};
  var cells = [];
  grid.eachLayer(function (l) {{ cells.push(l); }});
  var sat = document.getElementById('gridSat'), satVal = document.getElementById('gridSatVal');
  var mn  = document.getElementById('gridMin'), mnVal  = document.getElementById('gridMinVal');
  function apply() {{
    var s = parseFloat(sat.value), m = parseFloat(mn.value);
    satVal.textContent = s; mnVal.textContent = m;
    cells.forEach(function (l) {{
      var w = l.feature.properties.weight;
      if (w < m) {{ if (grid.hasLayer(l)) grid.removeLayer(l); return; }}
      if (!grid.hasLayer(l)) grid.addLayer(l);
      l.setStyle({{ fillOpacity: 0.2 + 0.65 * Math.min(w / s, 1.0) }});
    }});
  }}
  sat.addEventListener('input', apply);
  mn.addEventListener('input', apply);
  apply();
}});
</script>
"""
    return folium.Element(html)


def grid_title_fr():
    return ("<h3 style='position:fixed;top:8px;left:60px;z-index:9999;"
            "background:white;padding:6px 10px;border-radius:6px;"
            "font-family:sans-serif;font-size:14px;margin:0'>Cat&eacute;gorie dominante "
            "par secteur (~300&nbsp;m, pond&eacute;r&eacute; par usager et j'aime)</h3>")


def grid_comments_js(map_name, grid_name):
    """Click a grid cell -> one scrollable popup listing its comments, ranked by
    (de-spammed) liked-weight first, then user-weight. Each feature carries its
    (capped) comments in properties."""
    colors = ",".join(f"{c}:'{CAT_COLOR[c]}'" for c in [1, 2, 3, 4])
    return folium.Element(f"""
<script>
window.addEventListener('load', function () {{
  var MAP = {map_name};
  var grid = {grid_name};
  var CATCOLOR = {{{colors}}};
  grid.on('click', function (e) {{
    var p = (e.layer && e.layer.feature) ? e.layer.feature.properties : null;
    if (!p) return;
    var cs = p.comments || [];
    var head = '<div style="font:bold 13px sans-serif;color:' + p.dom_color +
               ';margin-bottom:6px">' + p.dom_label + ' (dominante) — ' + p.n_total +
               ' commentaire' + (p.n_total > 1 ? 's' : '') + ' · poids ' +
               p.weight.toFixed(2) + '</div>';
    var body = '';
    cs.forEach(function (a) {{
      var txt = (a[0] && a[0].length) ? a[0] : '<i>(sans texte)</i>';
      var jaime = (a[2] === 1) ? '1 j’aime' : (a[2] || 0) + ' j’aime';
      var col = CATCOLOR[a[3]] || '#888';
      body += '<div style="border-top:1px solid #eee;padding:5px 0;font:12px sans-serif">' +
              '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;' +
              'background:' + col + ';margin-right:5px;vertical-align:middle"></span>' + txt +
              '<div style="color:#888;font-size:11px;margin-top:2px">poids ' +
              a[1].toFixed(3) + ' · ' + jaime + ' (poids j’aime ' + a[4].toFixed(3) +
              ')</div></div>';
    }});
    if (p.n_total > cs.length) {{
      body += '<div style="color:#888;font:italic 11px sans-serif;padding-top:6px">… et ' +
              (p.n_total - cs.length) + ' de plus (zoomez pour un secteur plus fin)</div>';
    }}
    L.popup({{maxWidth: 340}}).setLatLng(e.latlng)
      .setContent('<div style="max-height:300px;overflow:auto">' + head + body + '</div>')
      .openOn(MAP);
  }});
}});
</script>
""")


def dashboard_backlink():
    """A "back to dashboard" link, auto-hidden when the map is shown in an iframe."""
    return folium.Element(
        '<a id="backLink" href="index.html" style="position:fixed;top:8px;right:12px;'
        'z-index:9999;background:white;padding:6px 12px;border-radius:6px;'
        'font-family:sans-serif;font-size:13px;text-decoration:none;color:#206bc4;'
        'box-shadow:0 1px 4px rgba(0,0,0,.3)">&larr; Tableau de bord</a>'
        '<script>if(window.self!==window.top){var b=document.getElementById("backLink");'
        'if(b)b.style.display="none";}</script>')


def build_grid_only_map(df):
    """The dominant-category grid as its own standalone French page (carte-dominante.html).

    Only the grid (no per-marker layer), so it stays light enough to also embed in
    index.html. Click a cell to list its comments (ranked by liked-weight, then
    user-weight); a back-link to the dashboard appears only when the page is
    opened on its own.
    """
    geojson, max_w = dominant_grid_geojson(df)
    m = folium.Map(location=MONTREAL, zoom_start=11, tiles="cartodbpositron")
    grid = dominant_grid_layer(geojson, show=True, popup=False,
                               name="Catégorie dominante par secteur")
    grid.add_to(m)
    m.get_root().html.add_child(folium.Element(grid_title_fr()))
    m.get_root().html.add_child(folium.Element(legend_fr()))
    m.get_root().html.add_child(grid_controls_fr(grid.get_name(), max_w))
    m.get_root().html.add_child(grid_comments_js(m.get_name(), grid.get_name()))
    m.get_root().html.add_child(dashboard_backlink())
    m.save(GRID_PAGE)
    print(f"Wrote {GRID_PAGE}")
    return GRID_PAGE


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load_weighted()
    build_grid_only_map(df)
    geojson, max_w = dominant_grid_geojson(df)
    m = folium.Map(location=MONTREAL, zoom_start=11, tiles="cartodbpositron")
    cluster_layers = clustered_category_layers(df)
    for mc, _ in cluster_layers:
        mc.add_to(m)
    weighted_markers_layer(df).add_to(m)
    grid = dominant_grid_layer(geojson)
    grid.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(legend()))
    m.get_root().html.add_child(grid_slider(m.get_name(), grid.get_name(), max_w))
    m.get_root().html.add_child(cluster_comment_js(m.get_name(), cluster_layers))
    out = os.path.join(OUT, "blended_map.html")
    m.save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
