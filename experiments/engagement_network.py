"""
EXPERIMENT - "two camps" engagement network.

Nodes = the most active likers. Two users are linked when they liked the same
markers (edge weight = number of co-liked markers). Node colour = the share of a
user's likes that landed on "To be removed" markers (green = pro-infrastructure,
red = removal-leaning); node size = total likes given. If the inferred split is
real, the layout separates a large pro-infra cluster from a small removal one.
We also report greedy-modularity community structure to back that up.

Output: experiments/output/engagement_network.png
"""
import os
from collections import Counter, defaultdict
from itertools import combinations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from matplotlib import cm, colormaps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

MARKERS = os.path.join(ROOT, "output", "markers.csv")
OUT = os.path.join(HERE, "output")
TOP_N = 140          # most active likers to include
MIN_EDGE = 3         # min co-liked markers to draw an edge


def main():
    os.makedirs(OUT, exist_ok=True)
    df = pd.read_csv(MARKERS)
    df["likers"] = df["liker_ids"].fillna("").map(
        lambda s: [int(x) for x in s.split(";") if x])

    # Per-user: total likes given and likes given to removal (cat 4) markers.
    given = Counter()
    given_removal = Counter()
    for r in df.itertuples():
        for u in r.likers:
            given[u] += 1
            if r.category_id == 4:
                given_removal[u] += 1
    top_users = {u for u, _ in given.most_common(TOP_N)}

    # Co-like edges among top users only.
    edge_w = defaultdict(int)
    for r in df.itertuples():
        ls = [u for u in r.likers if u in top_users]
        for a, b in combinations(sorted(ls), 2):
            edge_w[(a, b)] += 1

    G = nx.Graph()
    for u in top_users:
        G.add_node(u)
    for (a, b), w in edge_w.items():
        if w >= MIN_EDGE:
            G.add_edge(a, b, weight=w)
    G.remove_nodes_from(list(nx.isolates(G)))

    # Community structure (quantifies the "camps").
    comms = list(nx.community.greedy_modularity_communities(G, weight="weight"))
    modularity = nx.community.modularity(G, comms, weight="weight")

    removal_frac = {u: (given_removal[u] / given[u] if given[u] else 0) for u in G.nodes}
    sizes = [40 + given[u] * 2.5 for u in G.nodes]
    cmap = colormaps["RdYlGn_r"]             # 0 -> green, 1 -> red
    node_colors = [cmap(removal_frac[u]) for u in G.nodes]

    pos = nx.spring_layout(G, weight="weight", seed=42, k=0.45, iterations=200)

    fig, ax = plt.subplots(figsize=(12, 9))
    nx.draw_networkx_edges(G, pos, alpha=0.12, width=0.6, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color=node_colors,
                           linewidths=0.4, edgecolors="white", ax=ax)
    # Label the biggest hubs.
    hubs = sorted(G.nodes, key=lambda u: given[u], reverse=True)[:10]
    labels = {u: f"usager {u}" for u in hubs}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8,
                            font_color="black", ax=ax,
                            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7))
    ax.set_title(f"Réseau de co-appréciation des {G.number_of_nodes()} usagers les plus actifs\n"
                 f"couleur = part des j'aime sur « À retirer » (vert = pro-infra, rouge = retrait) · "
                 f"{len(comms)} communautés, modularité {modularity:.2f}")
    ax.axis("off")
    sm = cm.ScalarMappable(cmap=cmap)
    sm.set_array([0, 1])
    cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("part des j'aime de l'usager sur des marqueurs de retrait")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "engagement_network.png"), dpi=130)
    plt.close(fig)

    print(f"Nodes: {G.number_of_nodes()}  Edges: {G.number_of_edges()}  "
          f"Communities: {len(comms)}  Modularity: {modularity:.2f}")
    for i, c in enumerate(sorted(comms, key=len, reverse=True)[:5]):
        avg_rem = sum(removal_frac[u] for u in c) / len(c)
        print(f"  community {i+1}: {len(c)} users, avg removal-share {avg_rem:.0%}")
    print("Wrote engagement_network.png to experiments/output/")


if __name__ == "__main__":
    main()
