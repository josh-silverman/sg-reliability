"""Generate the three article figures from analysis/results/*.csv.

Dark theme matched to the portfolio site (zinc-950 page, teal accent).
Categorical palette validated for CVD separation and contrast on the
#09090b surface. Outputs SVG (for the article) and 2x PNG (for the
portfolio card) to figures/.

Usage: python scripts/make_figures.py
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "analysis" / "results"
FIGURES = ROOT / "figures"

SURFACE = "#09090b"      # portfolio zinc-950 page
GRID = "#26262a"
BASELINE = "#383835"
INK = "#ffffff"
SECONDARY = "#c3c2b7"
MUTED = "#898781"

CAT_LABEL = {
    "sg_ott": "Off the tee",
    "sg_app": "Approach",
    "sg_arg": "Around the green",
    "sg_putt": "Putting",
    "sg_total_calc": "Total",
}
# validated categorical palette (dark surface #09090b): worst adjacent
# CVD deltaE 29.6, all >= 3:1 contrast, lightness band OK
COLOR = {
    "sg_ott": "#0d9488",
    "sg_app": "#9085e9",
    "sg_arg": "#d95926",
    "sg_putt": "#3987e5",
    "sg_total_calc": MUTED,
}
CATS4 = ["sg_ott", "sg_app", "sg_arg", "sg_putt"]

mpl.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"],
        "text.color": SECONDARY,
        "axes.edgecolor": BASELINE,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 1,
        "axes.linewidth": 1,
        "svg.fonttype": "none",
    }
)


def style_axes(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(FIGURES / f"{name}.svg")
    fig.savefig(FIGURES / f"{name}.png", dpi=200)
    plt.close(fig)
    print(f"wrote figures/{name}.svg + .png")


def titles(fig, title, subtitle):
    fig.text(0.06, 0.955, title, fontsize=16, fontweight="semibold",
             color=INK, ha="left", va="top")
    fig.text(0.06, 0.905, subtitle, fontsize=10.5, color=MUTED,
             ha="left", va="top")


# --------------------------------------------------------------------------
# Figure 1: stabilization curves (the money chart)
# --------------------------------------------------------------------------

def fig_stabilization():
    curve = pd.read_csv(RESULTS / "reliability_curve.csv")
    stab = pd.read_csv(RESULTS / "stabilization.csv").set_index("category")
    x_max = 120
    xs = np.linspace(2, x_max, 400)

    fig, ax = plt.subplots(figsize=(10, 6.2))
    fig.subplots_adjust(left=0.06, right=0.855, top=0.80, bottom=0.10)
    style_axes(ax)

    for r_ref in (0.5, 0.7):
        ax.axhline(r_ref, color=BASELINE, lw=1, zorder=1)
        ax.text(1.5, r_ref + 0.012, f"R = {r_ref}", fontsize=9,
                color=MUTED, ha="left", zorder=1)

    for cat in CATS4:
        c = COLOR[cat]
        k = stab.loc[cat, "k_rounds_to_R50"]
        sub = curve[curve["category"] == cat].sort_values("n")
        fitted = xs / (xs + k)
        grid_max = sub["n"].max()
        ax.plot(xs[xs <= grid_max], fitted[xs <= grid_max], color=c, lw=2,
                solid_capstyle="round", zorder=3)
        ax.plot(xs[xs >= grid_max], fitted[xs >= grid_max], color=c, lw=2,
                ls=(0, (1.5, 2.5)), zorder=3)  # dotted = extrapolated
        ax.scatter(sub["n"], sub["reliability"], s=26, color=c,
                   edgecolor=SURFACE, linewidth=1.5, zorder=4)
        # R = 0.5 crossing: dot + rounds annotation
        ax.scatter([k], [0.5], s=52, color=c, edgecolor=SURFACE,
                   linewidth=2, zorder=5)
        ax.annotate(f"{k:.0f}", (k, 0.5), xytext=(0, -16),
                    textcoords="offset points", ha="center", fontsize=10.5,
                    fontweight="semibold", color=INK, zorder=5)
        # end label with line-key dot
        y_end = x_max / (x_max + k)
        ax.scatter([x_max], [y_end], s=26, color=c, edgecolor=SURFACE,
                   linewidth=1.5, zorder=4)
        ax.annotate(CAT_LABEL[cat], (x_max, y_end), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=10.5,
                    color=SECONDARY, annotation_clip=False)

    handles = [
        mpl.lines.Line2D([], [], color=COLOR[c], lw=2, marker="o",
                         markersize=5, markeredgecolor=SURFACE,
                         label=CAT_LABEL[c])
        for c in CATS4
    ]
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=10,
              handlelength=1.4, labelcolor=SECONDARY, borderaxespad=0.2)

    ax.set_xlim(0, x_max + 1)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0, 0.25, 0.5, 0.7, 1.0])
    ax.set_xticks([0, 20, 40, 60, 80, 100, 120])
    ax.set_xlabel("Rounds in the sample", fontsize=10.5)
    ax.set_ylabel("Split-half reliability R", fontsize=10.5)

    titles(
        fig,
        "Driving becomes signal in ~9 rounds. Putting takes ~48.",
        "Split-half reliability of a player's n-round strokes-gained average, "
        "PGA Tour 2017–26. Labeled: rounds to R = 0.5.\n"
        "Points: measured. Lines: fitted R(n) = n/(n+k); dotted where "
        "extrapolated beyond the measured grid.",
    )
    save(fig, "stabilization_curves")


# --------------------------------------------------------------------------
# Figure 2: year-over-year scatters (2x2 small multiples)
# --------------------------------------------------------------------------

def fig_yoy():
    import sys
    sys.path.insert(0, str(ROOT / "analysis"))
    from reliability import load_clean_rounds, season_pairs

    pairs_df = season_pairs(load_clean_rounds())
    yoy = pd.read_csv(RESULTS / "yoy.csv").set_index("category")

    fig, axes = plt.subplots(2, 2, figsize=(9, 8.6), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.09, right=0.96, top=0.82, bottom=0.09,
                        hspace=0.30, wspace=0.14)
    lim = 2.6
    for ax, cat in zip(axes.flat, CATS4):
        style_axes(ax)
        ax.plot([-lim, lim], [-lim, lim], color=BASELINE, lw=1, zorder=1)
        ax.scatter(pairs_df[f"{cat}_t"], pairs_df[f"{cat}_t1"], s=9,
                   color=COLOR[cat], alpha=0.45, linewidth=0, zorder=2)
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_xticks([-2, -1, 0, 1, 2])
        ax.set_yticks([-2, -1, 0, 1, 2])
        ax.set_title(CAT_LABEL[cat], fontsize=11.5, color=INK, pad=8,
                     loc="left")
        ax.text(0.05, 0.92, f"r = {yoy.loc[cat, 'pearson']:.2f}",
                transform=ax.transAxes, fontsize=11, color=INK,
                fontweight="semibold")
    fig.supxlabel("This season (SG per round)", fontsize=10.5, color=MUTED)
    fig.supylabel("Next season (SG per round)", fontsize=10.5, color=MUTED)

    titles(
        fig,
        "Driving skill carries over. Putting mostly doesn't.",
        "Player season averages in consecutive seasons, min. 30 tracked "
        "rounds in each (1,309 season pairs, 2017–26).\n"
        "Diagonal: perfect persistence.",
    )
    save(fig, "yoy_scatter")


# --------------------------------------------------------------------------
# Figure 3: shrinkage meter (how much of 12 rounds is signal)
# --------------------------------------------------------------------------

def rounded_right_bar(ax, width, y, height, color, alpha=1.0, radius=None):
    """Bar from x=0: square at the baseline, 4px-ish rounded data end."""
    r = min(radius if radius is not None else height * 0.22, width / 2)
    x1 = width
    k = 0.5523 * r  # circle-to-bezier constant
    verts = [
        (0, y), (x1 - r, y),
        (x1 - r + k, y), (x1, y + r - k), (x1, y + r),
        (x1, y + height - r),
        (x1, y + height - r + k), (x1 - r + k, y + height), (x1 - r, y + height),
        (0, y + height), (0, y),
    ]
    codes = [
        MplPath.MOVETO, MplPath.LINETO,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.LINETO,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.LINETO, MplPath.CLOSEPOLY,
    ]
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color,
                           alpha=alpha, linewidth=0, zorder=3))


def fig_shrinkage():
    shrink = pd.read_csv(RESULTS / "shrinkage.csv").set_index("category")
    order = ["sg_ott", "sg_app", "sg_arg", "sg_putt"]

    fig, ax = plt.subplots(figsize=(9, 4.4))
    fig.subplots_adjust(left=0.19, right=0.94, top=0.74, bottom=0.10)
    style_axes(ax)
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)

    h, gap = 0.52, 1.0
    for i, cat in enumerate(order):
        w = shrink.loc[cat, "weight_12_rounds"] * 100
        y = -i * gap
        rounded_right_bar(ax, 100, y, h, COLOR[cat], alpha=0.16)  # track
        rounded_right_bar(ax, w, y, h, COLOR[cat])
        ax.text(-2, y + h / 2, CAT_LABEL[cat], ha="right", va="center",
                fontsize=11, color=SECONDARY)
        ax.text(w + 1.6, y + h / 2, f"{w:.0f}%", ha="left", va="center",
                fontsize=11.5, fontweight="semibold", color=INK)
    ax.text(100, gap * 0.62, "100% = trust the 12 rounds fully",
            ha="right", fontsize=9, color=MUTED)

    ax.set_xlim(0, 100)
    ax.set_ylim(-3.6 * gap, 0.9)
    ax.set_yticks([])
    ax.set_xticks([])

    titles(
        fig,
        "How much of a 12-round hot streak is real",
        "Weight to give a player's last 12 rounds in each category; the "
        "rest is regression to the tour mean.\nWeight = n / (n + k), with "
        "k from the stabilization fits.",
    )
    save(fig, "shrinkage_meter")


if __name__ == "__main__":
    FIGURES.mkdir(exist_ok=True)
    fig_stabilization()
    fig_yoy()
    fig_shrinkage()
