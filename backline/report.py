"""One-page match report for one team's back line (PNG). English and Korean."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

from .metrics import METRICS, _add_frame_cols

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#a3a29c", "#e4e3dd"
PITCH, LINE = "#f3f2ee", "#cfcdc4"
BLOCK_COLOR = {"low_block": "#1baf7a", "medium_block": "#e87ba4", "all": "#52514e"}   # blue/orange are reserved for teams (scene cards)

TXT = {
    "en": dict(
        title="{team} back line (deepest four outfield players)  ·  vs {opp}",
        sub="Organised defence only. Measured only when all four are on camera (off-camera positions are estimates, not used)\n— so mid-block values describe moments when the ball is near the line.",
        names={"height": "Line height (m from own goal)", "line_ball": "Ball in front of line (m)", "flatness": "Line spread front-to-back (m; a deliberate cover drop also counts)",
               "width": "Line width (m)", "shift": "Ball-side shift (line moves N m when ball moves 10 m sideways)", "lockstep": "Moving together (speed spread while the line moves, m/s; lower = more in step)"},
        blocks={"low_block": "low block", "medium_block": "mid block", "all": "low + mid block"},
        meas="seen {s}s of {t}s", nm="not measurable: {s}s on camera",
        rel="metric reliability (league): 1st vs 2nd half r={r:.2f}, other matches r={rc:.2f} (n={n})", league="grey dots = other A-League 24/25 team-matches where this could be measured (dot size = seconds measured)\ncoloured bar = sampling error of THIS match's measured moments (90%, resampling defensive phases)\nreliability: if 'other matches r' is near 0, read the number as this match only, not as the team's habit",
        shape="Typical back-line shape (median, measured frames)", attack="own goal ←", hb="High block: all four on camera for only {s}s of {t}s (league median {med}s) — not calculated.",
        lower_is="lower = flatter", lowv="lower = more in step",
        lb_mid="mid block: not shown — on-camera moments there are biased\ntowards the ball being near the line (measured vs estimated differ by up to ~9 m)"),
    "ko": dict(
        title="{team} 최후방 라인 (가장 깊은 필드 선수 4명)  ·  상대 {opp}",
        sub="조직 수비 국면만. 4명이 모두 화면에 잡힌 순간만 계산(화면 밖은 추정값이라 안 씀) — 그래서 미드 블록 값은 '공이 라인 가까이 있을 때'의 값.",
        names={"height": "라인 높이 (자기 골라인에서 m)", "line_ball": "라인 앞 공까지 거리 (m)", "flatness": "라인 앞뒤 흩어짐 (m, 일부러 처진 커버도 포함)",
               "width": "라인 폭 (m)", "shift": "볼 쪽 이동 (공이 옆으로 10m 갈 때 라인 이동 m)", "lockstep": "함께 움직임 (라인 이동 중 속도 흩어짐 m/s, 낮을수록 같이)"},
        blocks={"low_block": "로우 블록", "medium_block": "미드 블록", "all": "로우+미드"},
        meas="{t}초 중 {s}초 화면", nm="측정 불가: 화면 {s}초",
        rel="지표 신뢰도(리그): 전·후반 r={r:.2f}, 다른 경기 간 r={rc:.2f} (n={n})", league="회색 점 = 측정 가능했던 A리그 24/25 다른 팀-경기 (점 크기 = 측정 시간)\n색 막대 = 이 경기 측정 장면의 표본 오차 (90%, 수비 국면 재표집)\n지표 신뢰도: '다른 경기 간 r'이 0에 가까우면 이 경기만의 값이지 팀 성향이 아님",
        shape="평소 백포 모양 (중앙값, 측정된 순간)", attack="← 자기 골대", hb="하이 블록: {t}초 중 4명이 모두 화면에 잡힌 시간 {s}초(리그 중앙값 {med}초) — 계산하지 않음.",
        lower_is="낮을수록 일직선", lowv="낮을수록 같이 움직임",
        lb_mid="미드 블록: 표시 안 함 — 화면에 잡힌 순간이 '공이 라인 가까울 때'로\n쏠려 있어 추정값 포함 값과 최대 약 9m 차이"),
}


def _font(lang, font):
    fam = "DejaVu Sans"
    if font:                                       # any language: use the given font file (e.g. Pretendard covers Latin too)
        font_manager.fontManager.addfont(str(font))
        fam = font_manager.FontProperties(fname=str(font)).get_name()
    elif lang == "ko":
        fam = "Noto Sans CJK KR"
    plt.rcParams.update({"font.family": fam, "font.size": 13, "text.color": INK,
                         "axes.edgecolor": GRID, "xtick.color": INK2, "ytick.color": INK2})


def _shape(frames, team_id, block):
    f = frames[(frames.team_id == team_id) & (frames.block == block) & frames.measured]
    if len(f) < 600:
        return None
    X = f[[f"x{i}" for i in range(4)]].values
    Y = f[[f"y{i}" for i in range(4)]].values
    o = np.argsort(Y, axis=1)                                   # left-to-right order of the four
    return np.median(np.take_along_axis(X, o, 1), 0), np.median(np.take_along_axis(Y, o, 1), 0)


def render(frames, met, team_id, team_name, opp_name, league: pd.DataFrame, out: Path, lang="en", font=None, match_id=None):
    _font(lang, font)
    T = TXT[lang]
    fig = plt.figure(figsize=(17, 13.5), facecolor=SURFACE)
    names = list(METRICS)
    gs = fig.add_gridspec(len(names), 3, width_ratios=[1, 1, 1.25], left=0.03, right=0.985, top=0.765, bottom=0.06,
                          wspace=0.12, hspace=1.75)
    fig.text(0.03, 0.958, T["title"].format(team=team_name, opp=opp_name), fontsize=23, fontweight="bold", color=INK)
    fig.text(0.03, 0.935, T["sub"], fontsize=12.5, color=INK2, va="top", linespacing=1.4)
    fig.text(0.03, 0.897, T["league"], fontsize=11.5, color=INK2, va="top", linespacing=1.4)
    for j, blk in enumerate(("low_block", "medium_block")):
        fig.text(0.03 + j * 0.305, 0.835, T["blocks"][blk], fontsize=16, fontweight="bold", color=BLOCK_COLOR[blk])
    for i, name in enumerate(names):
        cells = met[met.metric == name]
        if name == "line_ball":
            nax = fig.add_subplot(gs[i, 1]); nax.axis("off")
            nax.text(0, 0.5, T["lb_mid"], fontsize=11.5, color=INK2, va="center", linespacing=1.4)
        for _, r in cells.iterrows():
            ax = fig.add_subplot(gs[i, :2] if r.block == "all" else gs[i, 0 if r.block == "low_block" else 1])
            ax.set_facecolor(SURFACE)
            L = league[(league.metric == r.metric) & (league.block == r.block) & league.measurable & league.value.notna()]
            if "match_id" in L and match_id is not None:
                L = L[~((L.match_id == match_id) & (L.team_id == team_id))]
            lg, lsec = L.value, L.seconds_measured
            kk = 10 if r.metric == "shift" else 1
            lo_x, hi_x = (lg.min() * kk, lg.max() * kk) if len(lg) else (0, 1)
            if r.measurable and pd.notna(r.lo):
                lo_x, hi_x = min(lo_x, r.lo * kk), max(hi_x, r.hi * kk)
            pad = (hi_x - lo_x) * 0.06 + 1e-6
            ax.set_xlim(lo_x - pad, hi_x + pad)
            ax.set_ylim(-1, 1)
            k = 10 if r.metric == "shift" else 1
            lg = lg * k
            ax.scatter(lg, np.zeros(len(lg)), s=8 + 60 * (lsec / 600).clip(0, 1), color=MUTED, alpha=.5, lw=0, zorder=1)
            c = BLOCK_COLOR[r.block]
            if r.measurable:
                ax.plot([r.lo * k, r.hi * k], [0, 0], color=c, lw=3, solid_capstyle="round", zorder=2)
                ax.scatter([r.value * k], [0], s=150, color=c, edgecolor=SURFACE, lw=2, zorder=3)
                val = r.value * 10 if r.metric == "shift" else r.value
                txt = f"{val:.{2 if r.metric == 'lockstep' else 1}f}{(' ' + r.unit) if r.unit else (' m' if r.metric == 'shift' else '')}  ·  {T['meas'].format(s=r.seconds_measured, t=r.seconds_in_block)}"
                ax.text(1.0, 1.25, txt, transform=ax.transAxes, ha="right", va="bottom", fontsize=12, color=INK2)
                if pd.notna(r.reliability):
                    ax.text(1.0, 0.98, T['rel'].format(r=r.reliability, rc=r.reliability_cross, n=int(r.reliability_n)), transform=ax.transAxes,
                            ha="right", va="bottom", fontsize=10.5, color=INK2)
            else:
                ax.text(0.5, 0, T["nm"].format(s=r.seconds_measured), transform=ax.transAxes, ha="center", va="center", fontsize=12, color=INK2)
            if r.block in ("low_block", "all"):
                ax.text(0, 1.75, T["names"][name], transform=ax.transAxes, fontsize=13.5, color=INK, fontweight="bold", va="bottom")
            ax.set_yticks([])
            ax.tick_params(axis="x", labelsize=11, length=0, pad=2)
            for sp in ("left", "right", "top"):
                ax.spines[sp].set_visible(False)
            ax.spines["bottom"].set_color(GRID)
    # pitch: typical shapes
    ax = fig.add_subplot(gs[:, 2])
    ax.set_facecolor(PITCH)
    for x in (-52.5, 0):
        ax.plot([x, x], [-34, 34], color=LINE, lw=1.2)
    for y in (-34, 34):
        ax.plot([-52.5, 0], [y, y], color=LINE, lw=1.2)
    ax.plot([-52.5, -36, -36, -52.5], [-20.16, -20.16, 20.16, 20.16], color=LINE, lw=1.2)
    ax.plot([-52.5, -54.5, -54.5, -52.5], [-3.66, -3.66, 3.66, 3.66], color=INK2, lw=2)
    for blk in ("low_block", "medium_block"):
        sh = _shape(frames, team_id, blk)
        if sh is None:
            continue
        xs, ys = sh
        ax.plot(xs, ys, color=BLOCK_COLOR[blk], lw=2, zorder=2)
        ax.scatter(xs, ys, s=140, color=BLOCK_COLOR[blk], edgecolor=SURFACE, lw=2, zorder=3)
        ax.annotate(T["blocks"][blk], (xs.mean(), ys.max()), xytext=(0, 14), textcoords="offset points",
                    ha="center", fontsize=13, color=INK, fontweight="bold")
    ax.text(-51.5, 31.5, T["attack"], fontsize=12, color=INK2, va="top")
    ax.set_xlim(-56, 2)
    ax.set_ylim(-36, 36)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(T["shape"], fontsize=14, color=INK, loc="left")
    hb = met[met.metric == "high_block"].iloc[0]
    med = int(round(league[league.metric == "high_block"].seconds_measured.median()))
    fig.text(0.03, 0.025, T["hb"].format(s=hb.seconds_measured, t=hb.seconds_in_block, med=med), fontsize=12.5, color=INK2)
    fig.savefig(out, dpi=110, facecolor=SURFACE)
    plt.close(fig)
    return out
