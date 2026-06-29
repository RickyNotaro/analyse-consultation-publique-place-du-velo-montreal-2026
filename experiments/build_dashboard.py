"""
EXPERIMENT - clean animated dashboard (the "vocal minority" story), Tabler UI.

Builds a single HTML dashboard on the Tabler admin template (Bootstrap 5, via
CDN) with animated Chart.js charts telling one story: the overwhelming majority
of participants want MORE/better cycling infrastructure, while removal demands
come from a small, vocal handful of users and get almost no community support.

Reads output/markers.csv (+ top_creators_by_category.csv for names) and writes
experiments/output/dashboard.html. Needs internet (Tabler + Chart.js via CDN).
"""
import csv
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "output")
CATS = ["Apprécié", "À améliorer", "Voie manquante", "À retirer"]
COLORS = ["#2ca02c", "#e6c700", "#d62fd6", "#d62728"]


def compute():
    df = pd.read_csv(os.path.join(ROOT, "output", "markers.csv"))
    n = len(df)
    df["w"] = 1.0 / df.groupby("user_id")["user_id"].transform("count")

    counts = [int((df.category_id == c).sum()) for c in [1, 2, 3, 4]]
    raw_pct = [round(c / n * 100, 1) for c in counts]
    wsum = df.groupby("category_id")["w"].sum()
    wtot = wsum.sum()
    weighted_pct = [round(wsum.get(c, 0) / wtot * 100, 1) for c in [1, 2, 3, 4]]
    avg_likes = [round(df[df.category_id == c]["num_likes"].mean(), 2) for c in [1, 2, 3, 4]]

    anti = df[df.category_id == 4]
    tot_likes = int(df.num_likes.sum())
    anti_likes = int(anti.num_likes.sum())
    vc = anti.user_id.value_counts()

    # Per-person stance: Pro (only pro-infra markers), Mix (both), Wants removal (only).
    pro_cnt = df.assign(pro=df.category_id != 4).groupby("user_id")["pro"].sum()
    rem_cnt = df.assign(rem=df.category_id == 4).groupby("user_id")["rem"].sum()
    n_users = df.user_id.nunique()
    ppl_pro = int(((pro_cnt > 0) & (rem_cnt == 0)).sum())
    ppl_mix = int(((pro_cnt > 0) & (rem_cnt > 0)).sum())
    ppl_rem = int(((pro_cnt == 0) & (rem_cnt > 0)).sum())

    # Per-user marker counts (sorted desc) for the concentration slider.
    pro_counts = df[df.category_id != 4].groupby("user_id").size().sort_values(ascending=False).tolist()
    rem_counts = df[df.category_id == 4].groupby("user_id").size().sort_values(ascending=False).tolist()

    # Removal contributors with names (from the people ranking).
    cr = [r for r in csv.DictReader(
        open(os.path.join(ROOT, "output", "top_creators_by_category.csv"), encoding="utf-8"))
        if r["category"] == "To be removed"][:10]
    removal_users = [["usager " + r["user_id"], int(r["markers_created"])] for r in cr]

    return {
        "cats": CATS, "colors": COLORS,
        "counts": counts, "raw_pct": raw_pct, "weighted_pct": weighted_pct,
        "avg_likes": avg_likes,
        "total_markers": n,
        "pro_pct": round(sum(counts[:3]) / n * 100, 1),
        "anti_pct": raw_pct[3],
        "anti_weighted_pct": weighted_pct[3],
        "anti_authors": int(anti.user_id.nunique()),
        "total_authors": int(df.user_id.nunique()),
        "top1_share": round(vc.iloc[0] / len(anti) * 100, 1),
        "top3_share": round(vc.head(3).sum() / len(anti) * 100, 1),
        "likes_pro_pct": round((tot_likes - anti_likes) / tot_likes * 100, 1),
        "likes_anti_pct": round(anti_likes / tot_likes * 100, 1),
        "total_likes": tot_likes,
        "removal_users": removal_users,
        # per-person stance (counts + %)
        "ppl_pro": ppl_pro, "ppl_mix": ppl_mix, "ppl_rem": ppl_rem,
        "ppl_pro_pct": round(ppl_pro / n_users * 100, 1),
        "ppl_mix_pct": round(ppl_mix / n_users * 100, 1),
        "ppl_rem_pct": round(ppl_rem / n_users * 100, 1),
        # concentration slider
        "pro_counts": [int(x) for x in pro_counts],
        "rem_counts": [int(x) for x in rem_counts],
        "pro_authors": len(pro_counts), "rem_authors": len(rem_counts),
    }


TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Consultation sur le plan vélo - une minorité bruyante contre une majorité pro-vélo</title>
<link href="https://cdn.jsdelivr.net/npm/@tabler/core@1.0.0/dist/css/tabler.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.17.0/dist/tabler-icons.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style> .chart-wrap{position:relative} </style>
</head>
<body>
<div class="page">
  <header class="navbar navbar-expand-md d-print-none">
    <div class="container-xl">
      <a href="#" class="navbar-brand fw-bold"><i class="ti ti-bike me-2"></i>Consultation sur le plan vélo</a>
      <div class="ms-auto text-secondary small">Agglomération de Montréal &middot; question 11865</div>
    </div>
  </header>

  <div class="page-wrapper">
    <div class="page-header d-print-none">
      <div class="container-xl">
        <div class="page-pretitle">Marqueurs de carte interactifs</div>
        <h2 class="page-title">Une minorité bruyante contre une majorité pro-vélo</h2>
        <p class="text-secondary mt-2 mb-0" style="max-width:780px">
          Consultation sur le plan vélo de la région de Montréal &middot; <b id="tm"></b> marqueurs de carte.
          La plupart des participants réclament des infrastructures cyclables <b>plus nombreuses et de meilleure
          qualité</b>; les demandes de retrait proviennent d'une petite poignée de voix et n'ont récolté
          presque aucun appui.</p>
      </div>
    </div>

    <div class="page-body">
      <div class="container-xl">

        <!-- stat cards -->
        <div class="row row-deck row-cards">
          <div class="col-sm-6 col-lg-3"><div class="card card-sm"><div class="card-body">
            <div class="row align-items-center"><div class="col-auto">
              <span class="bg-green text-white avatar"><i class="ti ti-thumb-up"></i></span></div>
              <div class="col"><div class="h1 mb-0 text-green"><span id="s1">0</span>%</div>
                <div class="text-secondary">des marqueurs réclament <b>plus ou de meilleures</b> infrastructures cyclables</div>
              </div></div></div></div></div>
          <div class="col-sm-6 col-lg-3"><div class="card card-sm"><div class="card-body">
            <div class="row align-items-center"><div class="col-auto">
              <span class="bg-red text-white avatar"><i class="ti ti-thumb-down"></i></span></div>
              <div class="col"><div class="h1 mb-0 text-red"><span id="s2">0</span>%</div>
                <div class="text-secondary">veulent qu'on <b>retire</b> des infrastructures <span id="s2b"></span></div>
              </div></div></div></div></div>
          <div class="col-sm-6 col-lg-3"><div class="card card-sm"><div class="card-body">
            <div class="row align-items-center"><div class="col-auto">
              <span class="bg-orange text-white avatar"><i class="ti ti-users-group"></i></span></div>
              <div class="col"><div class="h1 mb-0 text-orange"><span id="s3">0</span>%</div>
                <div class="text-secondary">de tous les marqueurs de retrait proviennent de seulement <b>3 utilisateurs</b></div>
              </div></div></div></div></div>
          <div class="col-sm-6 col-lg-3"><div class="card card-sm"><div class="card-body">
            <div class="row align-items-center"><div class="col-auto">
              <span class="bg-green text-white avatar"><i class="ti ti-heart"></i></span></div>
              <div class="col"><div class="h1 mb-0 text-green"><span id="s4">0</span>%</div>
                <div class="text-secondary">de tous les <b>j'aime</b> de la communauté sont allés aux marqueurs pro-vélo</div>
              </div></div></div></div></div>
        </div>

        <!-- two charts -->
        <div class="row row-cards mt-1">
          <div class="col-lg-6"><div class="card">
            <div class="card-header">
              <h3 class="card-title">Qu'est-ce que les gens ont demandé?</h3>
              <div class="card-actions"><button class="btn btn-sm" id="doToggle">Afficher par personnes plutôt que par marqueurs</button></div>
            </div>
            <div class="card-body">
              <p class="text-secondary" id="doTake">Près de 9 marqueurs sur 10 appuient des infrastructures cyclables plus nombreuses ou de meilleure qualité.</p>
              <div class="chart-wrap" style="height:300px"><canvas id="doughnut"></canvas></div>
            </div></div></div>
          <div class="col-lg-6"><div class="card">
            <div class="card-header"><h3 class="card-title">La communauté appuie-t-elle les retraits?</h3></div>
            <div class="card-body">
              <p class="text-secondary">Les marqueurs de retrait reçoivent de loin le moins de j'aime &mdash; le public ne les appuie pas.</p>
              <div class="chart-wrap" style="height:300px"><canvas id="likes"></canvas></div>
            </div></div></div>
        </div>

        <!-- concentration slider -->
        <div class="row row-cards mt-1"><div class="col-12"><div class="card">
          <div class="card-header"><h3 class="card-title">À quel point chaque camp est-il concentré?</h3></div>
          <div class="card-body">
            <p class="text-secondary">Glissez le curseur : quelle part des marqueurs <span class="text-green">pro</span> contre
               <span class="text-red">retrait</span> provient des quelques utilisateurs les plus actifs?
               Le retrait est beaucoup plus concentré &mdash; une poignée de comptes en génère la majeure partie.</p>
            <input type="range" class="form-range" id="cSlide" min="1" max="60" value="3">
            <div class="h3 mt-2 mb-3">Les <span id="cN">3</span> utilisateurs les plus actifs ont placé
               <span class="text-green"><span id="cPro"></span> des marqueurs pro</span> &middot;
               <span class="text-red"><span id="cRem"></span> des marqueurs de retrait</span></div>
            <div class="chart-wrap" style="height:300px"><canvas id="conc"></canvas></div>
          </div></div></div></div>

        <!-- one person one vote -->
        <div class="row row-cards mt-1"><div class="col-12"><div class="card">
          <div class="card-header">
            <h3 class="card-title">Une personne, un vote &mdash; le retrait rétrécit</h3>
            <div class="card-actions"><button class="btn btn-sm" id="toggle">Passer à « une personne, un vote »</button></div>
          </div>
          <div class="card-body">
            <p class="text-secondary">Compter chaque marqueur également surévalue les utilisateurs prolifiques. Donnez à chaque
               <i>personne</i> un seul vote (poids = 1 / son nombre de marqueurs) et la part des retraits diminue encore.
               Vue actuelle : <span class="fw-bold text-green" id="modeLabel">Comptes bruts</span>.</p>
            <div class="chart-wrap" style="height:320px"><canvas id="bars"></canvas></div>
          </div></div></div></div>

        <!-- removers -->
        <div class="row row-cards mt-1"><div class="col-12"><div class="card">
          <div class="card-header"><h3 class="card-title">Qui demande le retrait?</h3></div>
          <div class="card-body">
            <p class="text-secondary">Les demandes de retrait sont très concentrées : un seul utilisateur en a placé la majorité,
               et les trois premiers représentent <b id="t3"></b> de tous les marqueurs de retrait.</p>
            <div class="chart-wrap" style="height:360px"><canvas id="removers"></canvas></div>
          </div></div></div></div>

      </div>
    </div>

    <footer class="footer footer-transparent d-print-none">
      <div class="container-xl text-secondary small">
        Source : question 11865 (carte interactive), <span id="tm2"></span> marqueurs, <span id="ta"></span> participants.
        Données anonymisées : les usagers sont désignés par leur identifiant numérique seulement, sans nom.
        « Une personne, un vote » pondère chaque marqueur par 1 / le nombre total de marqueurs de cet usager
        &mdash; cosmétique seulement; les comptes, j'aime et coordonnées ne sont pas affectés.
      </div>
    </footer>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/@tabler/core@1.0.0/dist/js/tabler.min.js"></script>
<script>
const DATA = __DATA__;
Chart.defaults.color = '#667382';
Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
const GRID = '#e6e7e9';

document.getElementById('tm').textContent = DATA.total_markers.toLocaleString('fr-CA');
document.getElementById('tm2').textContent = DATA.total_markers.toLocaleString('fr-CA');
document.getElementById('ta').textContent = DATA.total_authors.toLocaleString('fr-CA');
document.getElementById('t3').textContent = DATA.top3_share + ' %';
document.getElementById('s2b').innerHTML = '&mdash; seulement <b>' + DATA.anti_weighted_pct +
  ' %</b> quand chaque personne ne compte qu\'une fois';

// animated count-up for the stat cards
function countUp(id, end, dec){
  const el = document.getElementById(id); const t0 = performance.now(); const dur = 1100;
  function step(t){ let p = Math.min((t-t0)/dur,1); p = 1-Math.pow(1-p,3);
    el.textContent = (end*p).toFixed(dec); if(p<1) requestAnimationFrame(step); }
  requestAnimationFrame(step);
}
countUp('s1', DATA.pro_pct, 1); countUp('s2', DATA.anti_pct, 1);
countUp('s3', DATA.top3_share, 0); countUp('s4', DATA.likes_pro_pct, 1);

// doughnut: pro vs anti, toggleable between "by markers" and "by people"
const VIEWS = {
  markers:{labels:['Pro-infrastructure (apprécié / à améliorer / manquant)','Veulent le retrait'],
    data:[DATA.pro_pct, DATA.anti_pct], colors:['#2ca02c','#d62728'],
    take:'Près de 9 marqueurs sur 10 appuient des infrastructures cyclables plus nombreuses ou de meilleure qualité.',
    btn:'Afficher par personnes plutôt que par marqueurs'},
  people:{labels:['Pro seulement','Mixte (les deux)','Retrait seulement'],
    data:[DATA.ppl_pro_pct, DATA.ppl_mix_pct, DATA.ppl_rem_pct],
    colors:['#2ca02c','#e6c700','#d62728'],
    take:'Par personne, c\'est encore plus clair : '+DATA.ppl_pro_pct+' % sont purement pro ('+DATA.ppl_pro+
      ' personnes), seulement '+DATA.ppl_rem_pct+' % se concentrent uniquement sur le retrait ('+DATA.ppl_rem+
      '), et '+DATA.ppl_mix_pct+' % sont mixtes.',
    btn:'Afficher par marqueurs plutôt que par personnes'}
};
const doughnut = new Chart(document.getElementById('doughnut'), {
  type:'doughnut',
  data:{labels:VIEWS.markers.labels,
    datasets:[{data:VIEWS.markers.data,
      backgroundColor:VIEWS.markers.colors, borderColor:'#fff', borderWidth:3}]},
  options:{maintainAspectRatio:false, cutout:'62%', plugins:{legend:{position:'bottom'},
    tooltip:{callbacks:{label:c=>c.label+': '+c.parsed+'%'}}},
    animation:{animateRotate:true,duration:1200}}
});
let doPeople = false;
document.getElementById('doToggle').onclick = ()=>{
  doPeople = !doPeople;
  const v = doPeople ? VIEWS.people : VIEWS.markers;
  doughnut.data.labels = v.labels;
  doughnut.data.datasets[0].data = v.data;
  doughnut.data.datasets[0].backgroundColor = v.colors;
  doughnut.update();
  document.getElementById('doTake').textContent = v.take;
  document.getElementById('doToggle').textContent = v.btn;
};

// avg likes per category
new Chart(document.getElementById('likes'), {
  type:'bar',
  data:{labels:DATA.cats, datasets:[{label:'J\'aime moyens par marqueur', data:DATA.avg_likes,
    backgroundColor:DATA.colors, borderRadius:4}]},
  options:{maintainAspectRatio:false, plugins:{legend:{display:false}},
    scales:{y:{grid:{color:GRID}, title:{display:true,text:'j\'aime moy. / marqueur'}},
      x:{grid:{display:false}}}, animation:{duration:1200}}
});

// toggle bars: raw vs weighted category share
let weighted = false;
const bars = new Chart(document.getElementById('bars'), {
  type:'bar',
  data:{labels:DATA.cats, datasets:[{label:'% des marqueurs', data:DATA.raw_pct.slice(),
    backgroundColor:DATA.colors, borderRadius:4}]},
  options:{maintainAspectRatio:false, plugins:{legend:{display:false},
    tooltip:{callbacks:{label:c=>c.parsed.y+' %'}}},
    scales:{y:{grid:{color:GRID}, title:{display:true,text:'% des marqueurs'}, suggestedMax:45},
      x:{grid:{display:false}}}, animation:{duration:900}}
});
function setMode(w){
  weighted = w;
  bars.data.datasets[0].data = (w?DATA.weighted_pct:DATA.raw_pct).slice();
  bars.update();
  document.getElementById('modeLabel').textContent = w?'Une personne, un vote':'Comptes bruts';
  document.getElementById('toggle').textContent = w?'Revenir aux comptes bruts':'Passer à « une personne, un vote »';
}
document.getElementById('toggle').onclick = ()=>setMode(!weighted);
setTimeout(()=>setMode(true), 1400);   // auto-demo the shrink once on load

// concentration slider: top-N users -> cumulative % of pro / removal markers
function cumArr(counts){ const t=counts.reduce((a,b)=>a+b,0); let s=0; return counts.map(c=>{s+=c;return s/t*100;}); }
const cumPro = cumArr(DATA.pro_counts), cumRem = cumArr(DATA.rem_counts);
const MAXN = +document.getElementById('cSlide').max;
const atN = (arr,n)=>arr[Math.min(n,arr.length)-1];        // clamp; saturates at 100
const xs = Array.from({length:MAXN},(_,i)=>i+1);
const conc = new Chart(document.getElementById('conc'), {
  type:'line',
  data:{labels:xs, datasets:[
    {label:'Marqueurs pro', data:xs.map(n=>atN(cumPro,n)), borderColor:'#2ca02c',
      backgroundColor:'rgba(44,160,44,.12)', fill:true, pointRadius:0, tension:.25},
    {label:'Marqueurs de retrait', data:xs.map(n=>atN(cumRem,n)), borderColor:'#d62728',
      backgroundColor:'rgba(214,39,40,.12)', fill:true, pointRadius:0, tension:.25},
    {label:'', data:[], borderColor:'#2ca02c', backgroundColor:'#2ca02c',
      showLine:false, pointRadius:6},
    {label:'', data:[], borderColor:'#d62728', backgroundColor:'#d62728',
      showLine:false, pointRadius:6}]},
  options:{maintainAspectRatio:false, plugins:{legend:{labels:{filter:i=>i.text!==''}},
    tooltip:{callbacks:{title:c=>'Top '+c[0].label+' utilisateurs',
      label:c=>c.dataset.label+' : '+c.parsed.y.toFixed(1)+' %'}}},
    scales:{y:{min:0,max:100,grid:{color:GRID},title:{display:true,text:'% des marqueurs de ce camp'}},
      x:{grid:{display:false},title:{display:true,text:'nombre d’utilisateurs les plus actifs (top N)'}}},
    animation:{duration:1000}}
});
function setN(n){
  const p=atN(cumPro,n), r=atN(cumRem,n);
  document.getElementById('cN').textContent = n;
  document.getElementById('cPro').textContent = p.toFixed(1)+' %';
  document.getElementById('cRem').textContent = r.toFixed(1)+' %';
  const mp=new Array(MAXN).fill(null), mr=new Array(MAXN).fill(null);
  mp[n-1]=p; mr[n-1]=r;
  conc.data.datasets[2].data=mp; conc.data.datasets[3].data=mr; conc.update('none');
}
document.getElementById('cSlide').oninput = e=>setN(+e.target.value);
setN(3);

// removal contributors (one giant bar)
new Chart(document.getElementById('removers'), {
  type:'bar',
  data:{labels:DATA.removal_users.map(u=>u[0]),
    datasets:[{label:'Marqueurs de retrait placés', data:DATA.removal_users.map(u=>u[1]),
      backgroundColor:'#d62728', borderRadius:4}]},
  options:{maintainAspectRatio:false, indexAxis:'y', plugins:{legend:{display:false}},
    scales:{x:{grid:{color:GRID}, title:{display:true,text:'marqueurs de retrait placés'}},
      y:{grid:{display:false}}}, animation:{duration:1200}}
});
</script>
</body>
</html>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    data = compute()
    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    out = os.path.join(OUT, "dashboard.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {out}")
    print(f"  pro {data['pro_pct']}% / anti {data['anti_pct']}% (weighted {data['anti_weighted_pct']}%)")
    print(f"  top3 removal share {data['top3_share']}% · likes to pro-bike {data['likes_pro_pct']}%")


if __name__ == "__main__":
    main()
