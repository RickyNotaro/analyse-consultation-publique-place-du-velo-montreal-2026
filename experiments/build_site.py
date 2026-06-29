"""
Build the full French project website -> index.html (repo root).

A single-page Tabler dashboard (sidebar nav) in Canadian French that gathers ALL
the project findings: executive summary, category breakdown, engagement, the
"vocal minority vs pro-bike majority" story, geographic hotspots (interactive map
embedded), corridors for/against, concentration, engagement network, text themes,
people rankings (anonymized -> user_id only), and methodology.

Interactive charts are rendered in French with Chart.js; the genuinely image-only
views (Lorenz curves, co-like network) are embedded as French-regenerated PNGs;
the main interactive map is embedded via <iframe>, heavier maps are linked.

Reuses compute() from build_dashboard.py (single source of truth for the core
numbers) and reads output/findings.json + the anonymized CSVs. Writes index.html
at the repo root so it is directly publishable (e.g. GitHub Pages).
"""
import csv
import html
import json
import os

from build_dashboard import compute  # single source of truth for core numbers

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTPUT = os.path.join(ROOT, "output")
EXP_OUT = os.path.join(HERE, "output")

CAT_FR = {"Appreciated": "Apprécié", "Needs improvement": "À améliorer",
          "Missing path": "Voie manquante", "To be removed": "À retirer"}
CAT_BADGE = {"Appreciated": "green", "Needs improvement": "yellow",
             "Missing path": "purple", "To be removed": "red"}


def badge(en):
    return f'<span class="badge bg-{CAT_BADGE[en]}-lt">{CAT_FR[en]}</span>'


def esc(s):
    return html.escape(str(s))


def load_findings():
    with open(os.path.join(OUTPUT, "findings.json"), encoding="utf-8") as f:
        return json.load(f)


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- table builders
def tbl_top_markers(fnd):
    rows = ""
    for m in fnd["top_markers"][:12]:
        rows += (f"<tr><td class='text-center'><span class='badge bg-azure-lt'>{m['likes']}</span></td>"
                 f"<td>{badge(m['category'])}</td><td>{esc(m['text'])}</td></tr>")
    return rows


def tbl_hotspots(fnd):
    rows = ""
    for h in fnd["hotspots"][:12]:
        rows += (f"<tr><td class='text-center'>{h['markers']}</td>"
                 f"<td class='text-center'><span class='badge bg-azure-lt'>{h['total_likes']}</span></td>"
                 f"<td>{badge(h['dominant_category'])}</td>"
                 f"<td class='text-secondary'>{h['lat']:.4f}, {h['lon']:.4f}</td>"
                 f"<td>{esc(h['rep_text'])}</td></tr>")
    return rows


def tbl_themes(fnd):
    rows = ""
    for t in fnd["themes"]:
        terms = ", ".join(t["top_terms"][:6])
        rows += (f"<tr><td class='text-center'><b>{t['size']}</b></td>"
                 f"<td class='text-secondary'>{esc(terms)}</td>"
                 f"<td>« {esc(t['samples'][0])} »</td></tr>")
    return rows


def tbl_distinct(fnd):
    rows = ""
    for en, terms in fnd["top_terms_by_category"].items():
        rows += (f"<tr><td>{badge(en)}</td>"
                 f"<td class='text-secondary'>{esc(', '.join(terms[:8]))}</td></tr>")
    return rows


def _rank_table(rows, valcol):
    by_cat = {c: [] for c in CAT_FR}
    for r in rows:
        by_cat[r["category"]].append(r)
    body = ""
    for i in range(10):
        cells = ""
        for en in CAT_FR:
            lst = by_cat[en]
            if i < len(lst):
                r = lst[i]
                cells += f"<td>usager {r['user_id']} <span class='text-secondary'>— {r[valcol]}</span></td>"
            else:
                cells += "<td></td>"
        body += f"<tr><td class='text-secondary'>{i + 1}</td>{cells}</tr>"
    return body


def tbl_creators():
    return _rank_table(read_csv(os.path.join(OUTPUT, "top_creators_by_category.csv")), "markers_created")


def tbl_likers():
    return _rank_table(read_csv(os.path.join(OUTPUT, "top_likers_by_category.csv")), "likes_given")


def corridors_data():
    rows = read_csv(os.path.join(EXP_OUT, "top_corridors.csv"))
    table = ""
    for r in rows:
        table += (f"<tr><td>{esc(r['corridor'])}</td>"
                  f"<td class='text-center'><b>{r['unique_participants']}</b></td>"
                  f"<td class='text-center text-green'>{r['for_users']}</td>"
                  f"<td class='text-center'>{r['mixed_users']}</td>"
                  f"<td class='text-center text-red'>{r['against_users']}</td>"
                  f"<td class='text-center text-secondary'>{r['markers']}</td>"
                  f"<td class='text-center text-secondary'>{r['total_likes']}</td></tr>")
    chart = [{"name": r["corridor"], "f": int(r["for_users"]), "m": int(r["mixed_users"]),
              "a": int(r["against_users"])} for r in rows[:12]]
    return table, chart


def build_data():
    d = compute()
    fnd = load_findings()
    d["total_likes_by_cat"] = [c["total_likes"] for c in
                               sorted(fnd["likes_by_category"], key=lambda x: x["id"])]
    d["top_terms"] = fnd["top_terms_overall"][:16]
    d["top_contributors"] = [{"id": c["user_id"], "markers": c["markers"],
                              "likes": c["likes_earned"]} for c in fnd["top_contributors"][:12]]
    _, chart = corridors_data()
    d["corridors"] = chart
    return d, fnd


# ----------------------------------------------------------------------- template
TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Consultation sur le plan vélo — Analyse des marqueurs de carte</title>
<link href="https://cdn.jsdelivr.net/npm/@tabler/core@1.0.0/dist/css/tabler.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.17.0/dist/tabler-icons.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  html{scroll-behavior:smooth}
  section{scroll-margin-top:1rem}
  .chart-wrap{position:relative}
  .navbar-vertical .nav-link{padding-top:.35rem;padding-bottom:.35rem}
  .lead-quote{border-left:4px solid var(--tblr-green);padding-left:1rem}
</style>
</head>
<body>
<div class="page">
  <aside class="navbar navbar-vertical navbar-expand-lg" data-bs-theme="dark">
    <div class="container-fluid">
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#sidebar-menu">
        <span class="navbar-toggler-icon"></span></button>
      <h1 class="navbar-brand fs-3 mb-0"><i class="ti ti-bike me-2"></i>Plan vélo</h1>
      <div class="collapse navbar-collapse" id="sidebar-menu">
        <ul class="navbar-nav pt-lg-2">
          <li class="nav-item"><a class="nav-link" href="#resume"><i class="ti ti-home me-2"></i>Résumé</a></li>
          <li class="nav-item"><a class="nav-link" href="#categories"><i class="ti ti-chart-donut me-2"></i>Catégories</a></li>
          <li class="nav-item"><a class="nav-link" href="#engagement"><i class="ti ti-heart me-2"></i>Engagement</a></li>
          <li class="nav-item"><a class="nav-link" href="#positions"><i class="ti ti-scale me-2"></i>Pour vs contre</a></li>
          <li class="nav-item"><a class="nav-link" href="#carte"><i class="ti ti-map-2 me-2"></i>Carte & points chauds</a></li>
          <li class="nav-item"><a class="nav-link" href="#corridors"><i class="ti ti-road me-2"></i>Corridors</a></li>
          <li class="nav-item"><a class="nav-link" href="#concentration"><i class="ti ti-chart-line me-2"></i>Concentration</a></li>
          <li class="nav-item"><a class="nav-link" href="#reseau"><i class="ti ti-affiliate me-2"></i>Réseau</a></li>
          <li class="nav-item"><a class="nav-link" href="#themes"><i class="ti ti-message me-2"></i>Thèmes</a></li>
          <li class="nav-item"><a class="nav-link" href="#personnes"><i class="ti ti-users me-2"></i>Personnes</a></li>
          <li class="nav-item"><a class="nav-link" href="#methodo"><i class="ti ti-info-circle me-2"></i>Méthodologie</a></li>
        </ul>
      </div>
    </div>
  </aside>

  <div class="page-wrapper">
    <div class="page-body">
      <div class="container-xl">

      <!-- ============ RÉSUMÉ ============ -->
      <section id="resume">
        <div class="page-header"><div>
          <div class="page-pretitle">Consultation publique · agglomération de Montréal · question 11865</div>
          <h2 class="page-title fs-1">Une minorité bruyante contre une majorité pro-vélo</h2>
          <p class="text-secondary mt-2" style="max-width:820px">Analyse des <b id="tm"></b> marqueurs de
            carte déposés par <b id="ta"></b> participants. La plupart réclament des infrastructures
            cyclables <b>plus nombreuses et de meilleure qualité</b>; les demandes de retrait proviennent
            d'une poignée d'usagers très actifs et n'ont récolté presque aucun appui.</p>
        </div></div>

        <div class="row row-deck row-cards">
          <div class="col-sm-6 col-lg-3"><div class="card card-sm"><div class="card-body"><div class="row align-items-center">
            <div class="col-auto"><span class="bg-green text-white avatar"><i class="ti ti-thumb-up"></i></span></div>
            <div class="col"><div class="h1 mb-0 text-green"><span id="s1">0</span>%</div>
              <div class="text-secondary">des marqueurs veulent <b>plus / mieux</b></div></div></div></div></div></div>
          <div class="col-sm-6 col-lg-3"><div class="card card-sm"><div class="card-body"><div class="row align-items-center">
            <div class="col-auto"><span class="bg-red text-white avatar"><i class="ti ti-thumb-down"></i></span></div>
            <div class="col"><div class="h1 mb-0 text-red"><span id="s2">0</span>%</div>
              <div class="text-secondary">veulent un <b>retrait</b> <span id="s2b"></span></div></div></div></div></div></div>
          <div class="col-sm-6 col-lg-3"><div class="card card-sm"><div class="card-body"><div class="row align-items-center">
            <div class="col-auto"><span class="bg-orange text-white avatar"><i class="ti ti-users-group"></i></span></div>
            <div class="col"><div class="h1 mb-0 text-orange"><span id="s3">0</span>%</div>
              <div class="text-secondary">des marqueurs de retrait viennent de <b>3 usagers</b></div></div></div></div></div></div>
          <div class="col-sm-6 col-lg-3"><div class="card card-sm"><div class="card-body"><div class="row align-items-center">
            <div class="col-auto"><span class="bg-green text-white avatar"><i class="ti ti-heart"></i></span></div>
            <div class="col"><div class="h1 mb-0 text-green"><span id="s4">0</span>%</div>
              <div class="text-secondary">des <b>j'aime</b> vont aux marqueurs pro-vélo</div></div></div></div></div></div>
        </div>

        <div class="card mt-1"><div class="card-body">
          <p class="lead-quote mb-0">En comptant <b>une personne, un vote</b>, la part des demandes de
          retrait tombe de <b>11,8 % à 7,6 %</b>. Même sur Henri-Bourassa — le corridor le plus visé par
          le retrait (108 marqueurs « À retirer ») — seulement <b>19 personnes sont contre</b> contre
          <b>100 pour</b>. L'opposition est réelle mais étroite et concentrée.</p>
        </div></div>
      </section>

      <!-- ============ CATÉGORIES ============ -->
      <section id="categories" class="mt-4">
        <h2 class="mb-3"><i class="ti ti-chart-donut me-2 text-purple"></i>Répartition par catégorie</h2>
        <div class="row row-cards">
          <div class="col-lg-5"><div class="card"><div class="card-body">
            <div class="chart-wrap" style="height:320px"><canvas id="catDoughnut"></canvas></div></div></div></div>
          <div class="col-lg-7"><div class="card"><div class="card-body">
            <p class="text-secondary">Près de <b>7 marqueurs sur 10 (68,6 %)</b> signalent une lacune ou un
            problème (voie manquante + à améliorer). À peine ~1 sur 5 célèbre l'existant, et les demandes
            de retrait forment le plus petit groupe.</p>
            <div class="chart-wrap" style="height:230px"><canvas id="catBar"></canvas></div></div></div></div>
        </div>
      </section>

      <!-- ============ ENGAGEMENT ============ -->
      <section id="engagement" class="mt-4">
        <h2 class="mb-3"><i class="ti ti-heart me-2 text-red"></i>Engagement & priorités de la communauté</h2>
        <div class="row row-cards">
          <div class="col-lg-6"><div class="card"><div class="card-header"><h3 class="card-title">J'aime moyens par catégorie</h3></div>
            <div class="card-body"><p class="text-secondary">Les marqueurs « À retirer » reçoivent de loin le
              moins de j'aime — le public ne se rallie pas derrière eux.</p>
              <div class="chart-wrap" style="height:280px"><canvas id="avgLikes"></canvas></div></div></div></div>
          <div class="col-lg-6"><div class="card"><div class="card-header"><h3 class="card-title">Total de j'aime par catégorie</h3></div>
            <div class="card-body"><p class="text-secondary"><b id="tl"></b> j'aime au total · moyenne 3,84 ·
              78 % des marqueurs ont au moins un j'aime. La « voie manquante » récolte le plus de j'aime.</p>
              <div class="chart-wrap" style="height:280px"><canvas id="totLikes"></canvas></div></div></div></div>
        </div>
        <div class="card mt-1"><div class="card-header"><h3 class="card-title">Marqueurs les plus aimés (priorités citoyennes)</h3></div>
          <div class="table-responsive"><table class="table table-vcenter card-table">
            <thead><tr><th class="text-center">J'aime</th><th>Catégorie</th><th>Commentaire</th></tr></thead>
            <tbody>__TBL_TOPMARKERS__</tbody></table></div></div>
      </section>

      <!-- ============ POUR VS CONTRE ============ -->
      <section id="positions" class="mt-4">
        <h2 class="mb-3"><i class="ti ti-scale me-2 text-azure"></i>Pour ou contre l'infrastructure cyclable ?</h2>
        <div class="row row-cards">
          <div class="col-lg-6"><div class="card"><div class="card-header"><h3 class="card-title">Qu'est-ce que les gens ont demandé ?</h3>
            <div class="card-actions"><button class="btn btn-sm" id="doToggle">Par personnes</button></div></div>
            <div class="card-body"><p class="text-secondary" id="doTake"></p>
              <div class="chart-wrap" style="height:280px"><canvas id="doughnut"></canvas></div></div></div></div>
          <div class="col-lg-6"><div class="card"><div class="card-header"><h3 class="card-title">Une personne, un vote — le retrait rétrécit</h3>
            <div class="card-actions"><button class="btn btn-sm" id="toggle">Une personne, un vote</button></div></div>
            <div class="card-body"><p class="text-secondary">Compter chaque marqueur également surévalue les
              usagers prolifiques. Vue : <b class="text-green" id="modeLabel">Comptes bruts</b>.</p>
              <div class="chart-wrap" style="height:280px"><canvas id="bars"></canvas></div></div></div></div>
        </div>
        <div class="card mt-1"><div class="card-header"><h3 class="card-title">À quel point chaque camp est-il concentré ?</h3></div>
          <div class="card-body">
            <p class="text-secondary">Glissez le curseur : part des marqueurs <span class="text-green">pro</span> vs
              <span class="text-red">retrait</span> provenant des usagers les plus actifs. Le retrait est bien plus concentré.</p>
            <input type="range" class="form-range" id="cSlide" min="1" max="60" value="3">
            <div class="h3 mt-2 mb-3">Les <span id="cN">3</span> usagers les plus actifs ont placé
              <span class="text-green"><span id="cPro"></span> des marqueurs pro</span> ·
              <span class="text-red"><span id="cRem"></span> des marqueurs de retrait</span></div>
            <div class="chart-wrap" style="height:280px"><canvas id="conc"></canvas></div></div></div>
        <div class="card mt-1"><div class="card-header"><h3 class="card-title">Qui demande le retrait ? (anonymisé)</h3></div>
          <div class="card-body"><p class="text-secondary">Les demandes de retrait sont très concentrées : un
            seul usager en a placé 116 (29,6 % de la catégorie), et le top 3 représente <b id="t3"></b>.</p>
            <div class="chart-wrap" style="height:340px"><canvas id="removers"></canvas></div></div></div>
      </section>

      <!-- ============ CARTE ============ -->
      <section id="carte" class="mt-4">
        <h2 class="mb-3"><i class="ti ti-map-2 me-2 text-purple"></i>Carte interactive & points chauds</h2>
        <div class="card"><div class="card-header"><h3 class="card-title">Carte des 3 333 marqueurs</h3></div>
          <div class="card-body text-center">
            <p class="text-secondary">Aperçu géographique par catégorie. La <b>carte interactive</b> complète
              (groupes de marqueurs, infobulles, couches activables, chaleur des j'aime) s'ouvre dans un
              nouvel onglet — elle est volontairement séparée car elle charge 3 333 marqueurs.</p>
            <img src="output/charts/spatial_scatter.png" class="img-fluid rounded border mb-3"
              style="max-width:580px" alt="Emplacement des marqueurs par catégorie">
            <div><a class="btn btn-primary" href="output/map.html" target="_blank"><i class="ti ti-map-2 me-1"></i>Ouvrir la carte interactive</a></div>
          </div></div>
        <div class="card mt-1"><div class="card-header"><h3 class="card-title">Principaux points chauds (cellules de ~300 m)</h3></div>
          <div class="card-body"><p class="text-secondary mb-0">176 cellules contiennent ≥5 marqueurs
            (1 580 marqueurs). Deux pôles dominent : le <b>Vieux-Port / centre-ville est</b> et
            <b>l'avenue du Parc</b>, tous deux signalés <i>manquants</i> et <i>dangereux</i>. Dans les 7
            cellules à dominante de retrait, les marqueurs « Apprécié » récoltent <b>395 j'aime</b> contre
            <b>183</b> pour le retrait (2,2×).</p></div>
          <div class="table-responsive"><table class="table table-vcenter card-table">
            <thead><tr><th class="text-center">Marq.</th><th class="text-center">J'aime</th><th>Catégorie dominante</th>
              <th>Localisation</th><th>Commentaire représentatif</th></tr></thead>
            <tbody>__TBL_HOTSPOTS__</tbody></table></div></div>
        <div class="card mt-1"><div class="card-body">
          <div class="text-secondary mb-2">Cartes complémentaires (vues techniques) :</div>
          <div class="btn-list">
            <a class="btn btn-outline-primary" href="experiments/output/net_sentiment_map.html" target="_blank"><i class="ti ti-map me-1"></i>Sentiment net (apprécié vs retrait)</a>
            <a class="btn btn-outline-primary" href="experiments/output/blended_map.html" target="_blank"><i class="ti ti-map me-1"></i>Marqueurs pondérés / grille dominante</a>
            <a class="btn btn-outline-primary" href="experiments/output/weighted_map.html" target="_blank"><i class="ti ti-map me-1"></i>Densité brute vs pondérée</a>
          </div></div></div>
      </section>

      <!-- ============ CORRIDORS ============ -->
      <section id="corridors" class="mt-4">
        <h2 class="mb-3"><i class="ti ti-road me-2 text-green"></i>Corridors : personnes uniques, pour vs contre</h2>
        <div class="row row-cards">
          <div class="col-lg-7"><div class="card"><div class="card-body">
            <p class="text-secondary">Chaque barre = personnes distinctes ayant participé (créé <b>ou</b> aimé
              un marqueur), scindées par position. <b>Chaque corridor est massivement pour.</b></p>
            <div class="chart-wrap" style="height:420px"><canvas id="corridorsChart"></canvas></div></div></div></div>
          <div class="col-lg-5"><div class="card"><div class="card-header"><h3 class="card-title">Détail par corridor</h3></div>
            <div class="table-responsive" style="max-height:440px;overflow:auto"><table class="table table-sm table-vcenter card-table">
              <thead><tr><th>Corridor</th><th class="text-center">Pers.</th><th class="text-center">Pour</th>
                <th class="text-center">Mixte</th><th class="text-center">Contre</th>
                <th class="text-center">Marq.</th><th class="text-center">J'aime</th></tr></thead>
              <tbody>__TBL_CORRIDORS__</tbody></table></div></div></div>
        </div>
      </section>

      <!-- ============ CONCENTRATION ============ -->
      <section id="concentration" class="mt-4">
        <h2 class="mb-3"><i class="ti ti-chart-line me-2 text-pink"></i>Concentration de la participation</h2>
        <div class="card"><div class="card-body">
          <p class="text-secondary">La participation est très inégale : Gini de <b>0,62</b> (marqueurs créés),
            <b>0,67</b> (j'aime donnés) et <b>0,71</b> (j'aime reçus). Le 10 % d'usagers les plus actifs
            représente ~51–60 % de toute l'activité — ce qui motive la pondération « une personne, un vote ».</p>
          <img src="experiments/output/concentration_lorenz.png" class="img-fluid rounded border" style="max-width:680px"
            alt="Courbes de Lorenz de la concentration de la participation">
        </div></div>
      </section>

      <!-- ============ RÉSEAU ============ -->
      <section id="reseau" class="mt-4">
        <h2 class="mb-3"><i class="ti ti-affiliate me-2 text-azure"></i>Réseau d'engagement (deux camps)</h2>
        <div class="card"><div class="card-body">
          <p class="text-secondary">Réseau de co-appréciation des 140 usagers les plus actifs (deux usagers
            sont reliés s'ils ont aimé les mêmes marqueurs). On distingue une grande masse pro-infrastructure
            (3 communautés, 0 % de j'aime de retrait) et <b>un petit groupe détaché de 8 usagers à 95 % de
            j'aime de retrait</b> — confirmation visuelle d'une opposition concentrée et distincte.</p>
          <img src="experiments/output/engagement_network.png" class="img-fluid rounded border"
            alt="Réseau de co-appréciation, deux camps">
        </div></div>
      </section>

      <!-- ============ THÈMES ============ -->
      <section id="themes" class="mt-4">
        <h2 class="mb-3"><i class="ti ti-message me-2 text-orange"></i>Thèmes textuels</h2>
        <div class="row row-cards">
          <div class="col-lg-6"><div class="card"><div class="card-header"><h3 class="card-title">Termes les plus fréquents</h3></div>
            <div class="card-body"><div class="chart-wrap" style="height:420px"><canvas id="terms"></canvas></div></div></div></div>
          <div class="col-lg-6">
            <div class="card"><div class="card-header"><h3 class="card-title">Termes distinctifs par catégorie</h3></div>
              <div class="table-responsive"><table class="table table-vcenter card-table">
                <tbody>__TBL_DISTINCT__</tbody></table></div></div>
            <div class="card mt-1"><div class="card-header"><h3 class="card-title">Regroupements thématiques (KMeans)</h3></div>
              <div class="table-responsive"><table class="table table-sm table-vcenter card-table">
                <thead><tr><th class="text-center">Taille</th><th>Termes</th><th>Exemple</th></tr></thead>
                <tbody>__TBL_THEMES__</tbody></table></div></div>
          </div>
        </div>
      </section>

      <!-- ============ PERSONNES ============ -->
      <section id="personnes" class="mt-4">
        <h2 class="mb-3"><i class="ti ti-users me-2 text-blue"></i>Classements de personnes (anonymisé)</h2>
        <p class="text-secondary">Les usagers sont désignés par leur identifiant numérique seulement. Top 10
          par catégorie; listes complètes (top 20 créateurs, top 50 donneurs) dans les CSV du dépôt.</p>
        <div class="card"><div class="card-header"><h3 class="card-title">Principaux créateurs (marqueurs placés)</h3></div>
          <div class="table-responsive"><table class="table table-sm table-vcenter card-table">
            <thead><tr><th>#</th><th>🟢 Apprécié</th><th>🟡 À améliorer</th><th>🟣 Voie manquante</th><th>🔴 À retirer</th></tr></thead>
            <tbody>__TBL_CREATORS__</tbody></table></div></div>
        <div class="card mt-1"><div class="card-header"><h3 class="card-title">Principaux donneurs de j'aime</h3></div>
          <div class="table-responsive"><table class="table table-sm table-vcenter card-table">
            <thead><tr><th>#</th><th>🟢 Apprécié</th><th>🟡 À améliorer</th><th>🟣 Voie manquante</th><th>🔴 À retirer</th></tr></thead>
            <tbody>__TBL_LIKERS__</tbody></table></div></div>
        <div class="card mt-1"><div class="card-header"><h3 class="card-title">Contributeurs les plus prolifiques</h3></div>
          <div class="card-body"><div class="chart-wrap" style="height:360px"><canvas id="contributors"></canvas></div></div></div>
      </section>

      <!-- ============ MÉTHODOLOGIE ============ -->
      <section id="methodo" class="mt-4">
        <h2 class="mb-3"><i class="ti ti-info-circle me-2 text-secondary"></i>Méthodologie & anonymisation</h2>
        <div class="card"><div class="card-body">
          <ul class="text-secondary">
            <li><b>Source :</b> question 11865 (carte interactive) d'une consultation publique sur le plan
              vélo de la région de Montréal — <b id="tm3"></b> marqueurs, <b id="ta3"></b> participants.</li>
            <li><b>Anonymisation :</b> aucun nom n'est diffusé; les usagers sont désignés par leur
              <code>user_id</code> (un pseudonyme). Le fichier source brut (noms, courriels, réponses
              complètes) n'est pas versionné.</li>
            <li><b>Réserve résiduelle :</b> le texte libre des commentaires, les coordonnées exactes et la
              carte interactive (qui affiche chaque commentaire) sont inclus tels quels et pourraient, à la
              marge, permettre une réidentification.</li>
            <li><b>Accents :</b> les données source ont une corruption d'accents irréversible (78 % des
              marqueurs); une réparation cosmétique au mieux est appliquée, sans effet sur les comptes.</li>
            <li><b>Pondération :</b> « une personne, un vote » = chaque marqueur pondéré par 1 / le nombre
              total de marqueurs de l'usager. Thèmes : TF-IDF + KMeans. Points chauds : quadrillage de ~300 m.</li>
          </ul>
        </div></div>
      </section>

      <footer class="footer footer-transparent mt-4"><div class="text-secondary small">
        Analyse des marqueurs de carte — question 11865. Données anonymisées (identifiants seulement).
      </div></footer>

      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/@tabler/core@1.0.0/dist/js/tabler.min.js"></script>
<script>
const DATA = __DATA__;
Chart.defaults.color = '#667382';
Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
const GRID = '#e6e7e9';
const $ = id => document.getElementById(id);

const fmt = n => n.toLocaleString('fr-CA');
$('tm').textContent = fmt(DATA.total_markers); $('tm3').textContent = fmt(DATA.total_markers);
$('ta').textContent = fmt(DATA.total_authors); $('ta3').textContent = fmt(DATA.total_authors);
$('tl').textContent = fmt(DATA.total_likes);
$('t3').textContent = DATA.top3_share + ' %';
$('s2b').innerHTML = '&mdash; <b>' + DATA.anti_weighted_pct + ' %</b> à une personne, un vote';

function countUp(id, end, dec){const el=$(id),t0=performance.now(),dur=1100;
  (function step(t){let p=Math.min((t-t0)/dur,1);p=1-Math.pow(1-p,3);
    el.textContent=(end*p).toFixed(dec);if(p<1)requestAnimationFrame(step);})(performance.now());}
countUp('s1',DATA.pro_pct,1);countUp('s2',DATA.anti_pct,1);countUp('s3',DATA.top3_share,0);countUp('s4',DATA.likes_pro_pct,1);

// category doughnut + bar
new Chart($('catDoughnut'),{type:'doughnut',
  data:{labels:DATA.cats,datasets:[{data:DATA.counts,backgroundColor:DATA.colors,borderColor:'#fff',borderWidth:3}]},
  options:{maintainAspectRatio:false,cutout:'58%',plugins:{legend:{position:'bottom'},
    tooltip:{callbacks:{label:c=>c.label+': '+fmt(c.parsed)+' ('+DATA.raw_pct[c.dataIndex]+' %)'}}},animation:{animateRotate:true,duration:1100}}});
new Chart($('catBar'),{type:'bar',
  data:{labels:DATA.cats,datasets:[{data:DATA.counts,backgroundColor:DATA.colors,borderRadius:4}]},
  options:{maintainAspectRatio:false,indexAxis:'y',plugins:{legend:{display:false}},
    scales:{x:{grid:{color:GRID},title:{display:true,text:'nombre de marqueurs'}},y:{grid:{display:false}}},animation:{duration:900}}});

// avg + total likes
new Chart($('avgLikes'),{type:'bar',
  data:{labels:DATA.cats,datasets:[{data:DATA.avg_likes,backgroundColor:DATA.colors,borderRadius:4}]},
  options:{maintainAspectRatio:false,plugins:{legend:{display:false}},
    scales:{y:{grid:{color:GRID},title:{display:true,text:"j'aime moy. / marqueur"}},x:{grid:{display:false}}},animation:{duration:1000}}});
new Chart($('totLikes'),{type:'bar',
  data:{labels:DATA.cats,datasets:[{data:DATA.total_likes_by_cat,backgroundColor:DATA.colors,borderRadius:4}]},
  options:{maintainAspectRatio:false,plugins:{legend:{display:false}},
    scales:{y:{grid:{color:GRID},title:{display:true,text:"total de j'aime"}},x:{grid:{display:false}}},animation:{duration:1000}}});

// positions doughnut markers/people
const VIEWS={markers:{labels:['Pro-infrastructure','Veulent le retrait'],data:[DATA.pro_pct,DATA.anti_pct],
    colors:['#2ca02c','#d62728'],take:'Près de 9 marqueurs sur 10 appuient plus ou de meilleures infrastructures cyclables.',btn:'Par personnes'},
  people:{labels:['Pro seulement','Mixte','Retrait seulement'],data:[DATA.ppl_pro_pct,DATA.ppl_mix_pct,DATA.ppl_rem_pct],
    colors:['#2ca02c','#e6c700','#d62728'],
    take:'Par personne, c\'est encore plus net : '+DATA.ppl_pro_pct+' % purement pro, seulement '+DATA.ppl_rem_pct+' % uniquement retrait, '+DATA.ppl_mix_pct+' % mixtes.',btn:'Par marqueurs'}};
const doughnut=new Chart($('doughnut'),{type:'doughnut',
  data:{labels:VIEWS.markers.labels,datasets:[{data:VIEWS.markers.data,backgroundColor:VIEWS.markers.colors,borderColor:'#fff',borderWidth:3}]},
  options:{maintainAspectRatio:false,cutout:'60%',plugins:{legend:{position:'bottom'},
    tooltip:{callbacks:{label:c=>c.label+': '+c.parsed+' %'}}},animation:{animateRotate:true,duration:1100}}});
$('doTake').textContent=VIEWS.markers.take;
let doPeople=false;
$('doToggle').onclick=()=>{doPeople=!doPeople;const v=doPeople?VIEWS.people:VIEWS.markers;
  doughnut.data.labels=v.labels;doughnut.data.datasets[0].data=v.data;doughnut.data.datasets[0].backgroundColor=v.colors;doughnut.update();
  $('doTake').textContent=v.take;$('doToggle').textContent=v.btn;};

// one person one vote bars
let weighted=false;
const bars=new Chart($('bars'),{type:'bar',
  data:{labels:DATA.cats,datasets:[{data:DATA.raw_pct.slice(),backgroundColor:DATA.colors,borderRadius:4}]},
  options:{maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.parsed.y+' %'}}},
    scales:{y:{grid:{color:GRID},title:{display:true,text:'% des marqueurs'},suggestedMax:45},x:{grid:{display:false}}},animation:{duration:900}}});
function setMode(w){weighted=w;bars.data.datasets[0].data=(w?DATA.weighted_pct:DATA.raw_pct).slice();bars.update();
  $('modeLabel').textContent=w?'Une personne, un vote':'Comptes bruts';
  $('toggle').textContent=w?'Comptes bruts':'Une personne, un vote';}
$('toggle').onclick=()=>setMode(!weighted);
setTimeout(()=>setMode(true),1400);

// concentration slider
function cumArr(c){const t=c.reduce((a,b)=>a+b,0);let s=0;return c.map(x=>{s+=x;return s/t*100;});}
const cumPro=cumArr(DATA.pro_counts),cumRem=cumArr(DATA.rem_counts);
const MAXN=+$('cSlide').max,atN=(a,n)=>a[Math.min(n,a.length)-1],xs=Array.from({length:MAXN},(_,i)=>i+1);
const conc=new Chart($('conc'),{type:'line',
  data:{labels:xs,datasets:[
    {label:'Marqueurs pro',data:xs.map(n=>atN(cumPro,n)),borderColor:'#2ca02c',backgroundColor:'rgba(44,160,44,.12)',fill:true,pointRadius:0,tension:.25},
    {label:'Marqueurs de retrait',data:xs.map(n=>atN(cumRem,n)),borderColor:'#d62728',backgroundColor:'rgba(214,39,40,.12)',fill:true,pointRadius:0,tension:.25},
    {label:'',data:[],borderColor:'#2ca02c',backgroundColor:'#2ca02c',showLine:false,pointRadius:6},
    {label:'',data:[],borderColor:'#d62728',backgroundColor:'#d62728',showLine:false,pointRadius:6}]},
  options:{maintainAspectRatio:false,plugins:{legend:{labels:{filter:i=>i.text!==''}},
    tooltip:{callbacks:{title:c=>'Top '+c[0].label+' usagers',label:c=>c.dataset.label+' : '+c.parsed.y.toFixed(1)+' %'}}},
    scales:{y:{min:0,max:100,grid:{color:GRID},title:{display:true,text:'% des marqueurs du camp'}},
      x:{grid:{display:false},title:{display:true,text:'usagers les plus actifs (top N)'}}},animation:{duration:900}}});
function setN(n){const p=atN(cumPro,n),r=atN(cumRem,n);$('cN').textContent=n;
  $('cPro').textContent=p.toFixed(1)+' %';$('cRem').textContent=r.toFixed(1)+' %';
  const mp=new Array(MAXN).fill(null),mr=new Array(MAXN).fill(null);mp[n-1]=p;mr[n-1]=r;
  conc.data.datasets[2].data=mp;conc.data.datasets[3].data=mr;conc.update('none');}
$('cSlide').oninput=e=>setN(+e.target.value);setN(3);

// removal contributors
new Chart($('removers'),{type:'bar',
  data:{labels:DATA.removal_users.map(u=>u[0]),datasets:[{data:DATA.removal_users.map(u=>u[1]),backgroundColor:'#d62728',borderRadius:4}]},
  options:{maintainAspectRatio:false,indexAxis:'y',plugins:{legend:{display:false}},
    scales:{x:{grid:{color:GRID},title:{display:true,text:'marqueurs de retrait placés'}},y:{grid:{display:false}}},animation:{duration:1100}}});

// corridors for/mixed/against (stacked horizontal)
const cd=DATA.corridors.slice().reverse();
new Chart($('corridorsChart'),{type:'bar',
  data:{labels:cd.map(c=>c.name),datasets:[
    {label:'Pour',data:cd.map(c=>c.f),backgroundColor:'#2ca02c'},
    {label:'Mixte',data:cd.map(c=>c.m),backgroundColor:'#e6c700'},
    {label:'Contre',data:cd.map(c=>c.a),backgroundColor:'#d62728'}]},
  options:{maintainAspectRatio:false,indexAxis:'y',plugins:{legend:{position:'bottom'}},
    scales:{x:{stacked:true,grid:{color:GRID},title:{display:true,text:'personnes uniques'}},y:{stacked:true,grid:{display:false}}},animation:{duration:1000}}});

// top terms
new Chart($('terms'),{type:'bar',
  data:{labels:DATA.top_terms.slice().reverse(),datasets:[{data:DATA.top_terms.map((_,i)=>DATA.top_terms.length-i).reverse(),
    backgroundColor:'#206bc4',borderRadius:3}]},
  options:{maintainAspectRatio:false,indexAxis:'y',plugins:{legend:{display:false},
    tooltip:{callbacks:{label:c=>'rang '+(DATA.top_terms.length-c.parsed.x+1)}}},
    scales:{x:{display:false},y:{grid:{display:false}}},animation:{duration:900}}});

// top contributors
const tc=DATA.top_contributors.slice().reverse();
new Chart($('contributors'),{type:'bar',
  data:{labels:tc.map(c=>'usager '+c.id),datasets:[{data:tc.map(c=>c.markers),backgroundColor:'#4263eb',borderRadius:4}]},
  options:{maintainAspectRatio:false,indexAxis:'y',plugins:{legend:{display:false},
    tooltip:{callbacks:{afterLabel:c=>tc[c.dataIndex].likes+" j'aime obtenus"}}},
    scales:{x:{grid:{color:GRID},title:{display:true,text:'marqueurs placés'}},y:{grid:{display:false}}},animation:{duration:1000}}});
</script>
</body>
</html>
"""


def main():
    data, fnd = build_data()
    corridor_table, _ = corridors_data()
    html_out = (TEMPLATE
                .replace("__DATA__", json.dumps(data))
                .replace("__TBL_TOPMARKERS__", tbl_top_markers(fnd))
                .replace("__TBL_HOTSPOTS__", tbl_hotspots(fnd))
                .replace("__TBL_THEMES__", tbl_themes(fnd))
                .replace("__TBL_DISTINCT__", tbl_distinct(fnd))
                .replace("__TBL_CREATORS__", tbl_creators())
                .replace("__TBL_LIKERS__", tbl_likers())
                .replace("__TBL_CORRIDORS__", corridor_table))
    out = os.path.join(ROOT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"Wrote {out}  ({len(html_out) // 1024} KB)")


if __name__ == "__main__":
    main()
