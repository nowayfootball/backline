"""Figure 1 of the README from trust_table.csv: what the camera sees, and how different the unseen moments are.

python -m backline.trust_figure [trust_table.csv] [out.png]
"""
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COL = {"low_block": "#2a78d6", "medium_block": "#eb6834", "high_block": "#7a5fb5"}
NAME = {"low_block": "low block", "medium_block": "mid block", "high_block": "high block"}
INK, MUTED, GRID = "#1f2328", "#5b636e", "#e3e5e8"
SHORT = {"back-line height (m from goal)": "Back-line height", "back-line width (m)": "Back-line width",
         "back-line spread (m)": "Back-line spread", "ball in front of back line (m)": "Ball in front of line",
         "defence-midfield gap (m)": "Defence–midfield gap", "team length (m)": "Team length",
         "team width (m)": "Team width"}


def draw(t: pd.DataFrame, out: str):
    plt.rcParams.update({"font.size": 13, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": INK, "text.color": INK})
    fig, (a, b) = plt.subplots(1, 2, figsize=(15, 6.6), gridspec_kw=dict(width_ratios=[1, 1.9], wspace=0.42))

    # A: coverage by players needed and block
    cov = t.groupby(["players_needed", "block"]).coverage.first().unstack()
    needs = sorted(cov.index)
    w = 0.26
    for j, blk in enumerate(COL):
        xs = np.arange(len(needs)) + (j - 1) * (w + 0.02)
        a.bar(xs, cov.loc[needs, blk] * 100, w, color=COL[blk], label=NAME[blk])
        for x, v in zip(xs, cov.loc[needs, blk] * 100):
            a.text(x, v + 1.5, f"{v:.0f}", ha="center", va="bottom", fontsize=12, color=INK)
    a.set_xticks(np.arange(len(needs)), [f"{n} deepest" if n < 10 else "all 10" for n in needs])
    a.set_xlabel("outfield players the metric needs")
    a.set_ylim(0, 85); a.set_ylabel("% of time all needed players on camera")
    a.spines[["top", "right"]].set_visible(False); a.yaxis.grid(True, color=GRID); a.set_axisbelow(True)
    a.legend(frameon=False, loc="upper right", fontsize=12)
    a.set_title("A  High block: rarely on camera", loc="left", fontweight="bold", pad=34)

    # B: on-camera minus off-camera, raw (hollow) and same ball position (filled), 95% team-bootstrap intervals
    m = t[t.block.isin(["low_block", "medium_block"])]
    metrics = list(SHORT)
    for i, name in enumerate(metrics):
        for k, blk in enumerate(["low_block", "medium_block"]):
            r = m[(m.metric == name) & (m.block == blk)].iloc[0]
            y = i + (k - 0.5) * 0.36
            c = COL[blk]
            b.plot([r.gap_ci_lo, r.gap_ci_hi], [y, y], color=c, lw=1.5, alpha=0.45)
            b.plot([r.matched_gap_ci_lo, r.matched_gap_ci_hi], [y, y], color=c, lw=3)
            b.annotate("", xy=(r.matched_gap_median, y), xytext=(r.gap_median, y),
                       arrowprops=dict(arrowstyle="-|>", color=c, lw=1.2, alpha=0.7, shrinkA=6, shrinkB=6))
            b.plot(r.gap_median, y, "o", ms=9, mfc="white", mec=c, mew=2)
            b.plot(r.matched_gap_median, y, "o", ms=9, color=c, mec="white", mew=1.5)
    b.axvline(0, color=MUTED, lw=1)
    b.set_yticks(range(len(metrics)), [SHORT[x] for x in metrics]); b.invert_yaxis()
    b.set_xlabel("on-camera minus off-camera value (m), median over team-matches\n"
                 "\u2190 smaller on camera          larger on camera \u2192")
    b.spines[["top", "right", "left"]].set_visible(False); b.tick_params(axis="y", length=0)
    b.xaxis.grid(True, color=GRID); b.set_axisbelow(True)
    b.set_title("B  Off-camera moments differ", loc="left", fontweight="bold", pad=34)
    h = [plt.Line2D([], [], marker="o", ls="", ms=9, mfc="white", mec=MUTED, mew=2, label="all moments"),
         plt.Line2D([], [], marker="o", ls="", ms=9, color=MUTED, label="same ball position"),
         plt.Line2D([], [], color=COL["low_block"], lw=3, label="low block"),
         plt.Line2D([], [], color=COL["medium_block"], lw=3, label="mid block")]
    b.legend(handles=h, frameon=False, loc="lower center", bbox_to_anchor=(0.45, 0.995), fontsize=12, ncol=4,
             handletextpad=0.4, columnspacing=1.2)
    fig.text(0.01, -0.07, "20 A-League 24/25 matches, organised defence. B: lines are 95% intervals from resampling teams "
             "(thin: all moments, thick: same ball position).\nHigh block: never 60 s with all needed players on camera, so not compared.",
             fontsize=11, color=MUTED)
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    return out


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "trust_table.csv"
    dst = sys.argv[2] if len(sys.argv) > 2 else "figures/fig1_trust.png"
    print("wrote", draw(pd.read_csv(src), dst))
