"""
EXPERIMENT - participation concentration (Lorenz curves + Gini).

Shows how unequally participation is distributed across users:
  - markers created per user
  - likes given per user
  - likes received per user (on the markers they created)
A diagonal = perfect equality; the more the curve bows, the more a few users
dominate. Gini in [0,1] (0 = equal, 1 = one user does everything).

Output: experiments/output/concentration_lorenz.png
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MARKERS = os.path.join(ROOT, "output", "markers.csv")
OUT = os.path.join(HERE, "output")


def lorenz(values):
    v = np.sort(np.asarray(values, dtype=float))
    cum = np.cumsum(v)
    cum = np.insert(cum, 0, 0) / cum[-1]
    x = np.linspace(0, 1, len(cum))
    trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))
    gini = 1 - 2 * trapz(cum, x)
    return x, cum, gini


def topshare(values, frac):
    v = np.sort(np.asarray(values, dtype=float))[::-1]
    k = max(1, int(round(len(v) * frac)))
    return v[:k].sum() / v.sum() * 100


def main():
    os.makedirs(OUT, exist_ok=True)
    df = pd.read_csv(MARKERS)

    markers_per_user = df.groupby("user_id").size()
    likes_given = pd.Series(
        df["liker_ids"].dropna().str.split(";").explode().value_counts().values)
    likes_received = df.groupby("user_id")["num_likes"].sum()

    series = [
        ("Marqueurs créés / usager", markers_per_user, "#d62fd6"),
        ("J'aime donnés / usager", likes_given, "#4477aa"),
        ("J'aime reçus / usager", likes_received[likes_received > 0], "#117733"),
    ]

    fig, ax = plt.subplots(figsize=(7.5, 7))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="égalité parfaite")
    summary = []
    for name, vals, color in series:
        x, cum, gini = lorenz(vals)
        ax.plot(x, cum, color=color, lw=2.2, label=f"{name} (Gini {gini:.2f})")
        summary.append((name, len(vals), gini, topshare(vals, 0.01), topshare(vals, 0.10)))

    ax.set_xlabel("Part cumulative des usagers (du moins actif au plus actif)")
    ax.set_ylabel("Part cumulative de l'activité")
    ax.set_title("Concentration de la participation (courbes de Lorenz)")
    ax.legend(loc="upper left")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "concentration_lorenz.png"), dpi=120)
    plt.close(fig)

    print(f"{'metric':28} {'n_users':>8} {'Gini':>6} {'top1%':>8} {'top10%':>8}")
    for name, n, gini, t1, t10 in summary:
        print(f"{name:28} {n:8d} {gini:6.2f} {t1:7.1f}% {t10:7.1f}%")
    print("\nWrote concentration_lorenz.png to experiments/output/")


if __name__ == "__main__":
    main()
