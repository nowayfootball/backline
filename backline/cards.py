"""One page of scene cards per team and match: where the last line was broken."""
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .report import SURFACE, INK, INK2, PITCH, LINE, _font
from .usual import COARSE

DEF, ATT = "#2a78d6", "#eb6834"
TXT = {
    "en": dict(title="{team} defending: {n} opponent {passes} completed in behind the last line  ·  vs {opp}",
               sub=("Completed passes SkillCorner tags as breaking the last line, between its players (through) or outside its widest player (around); positions at the moment of the pass.\n"
                    "Tracked positions only, no verdict on who was at fault. Replaying offside calls puts most targeted receivers onside (median +4 m):\n"
                    "position, event timing or receiver identity may be off, so read positions as the rough shape, not metre-level gaps.\n"
                    "Dashed arrow = ball · dotted = receiver's run · faded = off camera (estimated) · line = deepest four outfield players (part of the line in a back five).\n"
                    "Players more than {xmax:.0f} m into the opponents' half are not drawn.  "
                    "Order: back four and receiver on camera first, then goal → shot → match time."),
               half={1: "1st half", 2: "2nd half"}, shot="shot", goal="GOAL", through="through the line", around="around the line",
               blocks={"low_block": "low block", "medium_block": "mid block", "high_block": "high block",
                       "defending_direct": "vs direct play", "defending_transition": "in transition", "chaotic": "broken play",
                       "defending_set_play": "set play", "defending_quick_break": "vs quick break"},
               legend_def="{team} (defending)", legend_att="{opp}", passer="passer", receiver="receiver", est=" (off camera)",
               none="No completed pass got in behind the last line ({k} attempted). Dribbles and runs are not counted.",
               own_goal="own goal ←", frame="tracking frame {f}", key="Blue = {team} (defending)  ·  orange = {opp} (attacking)", shown="  (first {k} shown)", u_high="line higher than usual (3 m+)",
               u_deep="line deeper than usual (3 m+)", u_same="line about usual", offcam="reference only (key players off camera)"),
    "ko": dict(title="{team} 수비: 상대가 최후방 라인 뒤로 성공시킨 패스 {n}개{passes}  ·  상대 {opp}",
               sub=("SkillCorner가 최후방 라인 돌파로 표시한 성공 패스 — 라인 선수 사이(사이로) 또는 가장 바깥 선수 바깥(바깥으로). 위치는 패스 순간.\n"
                    "트래킹 위치만 표시하고 누구 잘못인지 판정하지 않음. 오프사이드 판정을 재현해 보면 패스 대상 선수가 대부분 온사이드로 계산됨(중앙값 +4m):\n"
                    "위치·이벤트 시각·받는 선수 식별 중 어디서든 어긋날 수 있으니, 위치는 대략적인 배치로 보고 m 단위 차이는 읽지 말 것.\n"
                    "파선 화살표 = 공 · 점선 = 받는 선수 이동 · 흐린 점 = 화면 밖(추정) · 연결선 = 가장 깊은 필드 선수 4명(5백이면 라인 일부).\n"
                    "상대 진영 {xmax:.0f}m보다 깊은 선수는 생략.  "
                    "순서: 최후방 4명·받는 선수가 화면에 잡힌 장면 먼저, 그 안에서 골 → 슈팅 → 경기 시간."),
               half={1: "전반", 2: "후반"}, shot="슈팅", goal="골", through="라인 사이로", around="라인 바깥으로",
               blocks={"low_block": "로우 블록", "medium_block": "미드 블록", "high_block": "하이 블록",
                       "defending_direct": "직접 플레이 대응", "defending_transition": "전환 수비", "chaotic": "혼전",
                       "defending_set_play": "세트피스", "defending_quick_break": "역습 대응"},
               legend_def="{team} (수비)", legend_att="{opp}", passer="패서", receiver="받는 선수", est="(화면 밖)",
               none="최후방 라인 뒤로 들어간 성공 패스 없음(시도 {k}개는 모두 실패). 드리블·침투는 세지 않음.",
               own_goal="← 자기 골대", frame="트래킹 프레임 {f}", key="파랑 = {team}(수비)  ·  주황 = {opp}(공격)", shown="  (앞 {k}개만 표시)", u_high="평소보다 라인 높음(3m+)",
               u_deep="평소보다 라인 깊음(3m+)", u_same="평소와 비슷한 라인", offcam="참고용(핵심 선수 화면 밖)"),
}


XMAX = 32.0


def _half_pitch(ax, xmax):
    ax.set_facecolor(PITCH)
    ax.plot([-52.5, -52.5], [-34, 34], color=LINE, lw=1.2)
    for y in (-34, 34):
        ax.plot([-52.5, xmax], [y, y], color=LINE, lw=1.2)
    if xmax >= 0:
        ax.plot([0, 0], [-34, 34], color=LINE, lw=1.2)
    ax.plot([-52.5, -36, -36, -52.5], [-20.16, -20.16, 20.16, 20.16], color=LINE, lw=1.2)
    ax.plot([-52.5, -54.5, -54.5, -52.5], [-3.66, -3.66, 3.66, 3.66], color=INK2, lw=2)
    ax.set_xlim(-56, xmax)
    ax.set_ylim(-36, 36)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def render(sc: list[dict], team_name: str, opp_name: str, out: Path, lang="en", font=None, attempts: int = 0,
           total: int | None = None):
    from matplotlib.lines import Line2D
    _font(lang, font)
    T = TXT[lang]
    n = len(sc)
    cols = 2
    rows = max(1, math.ceil(n / cols))
    H = 4.3 + 6.2 * rows
    fig = plt.figure(figsize=(16, H), facecolor=SURFACE)
    nn = total if total is not None else n
    title = T["title"].format(team=team_name, n=nn, opp=opp_name, passes=("pass" if nn == 1 else "passes") if lang == "en" else "")
    if total is not None and total > n:
        title += T["shown"].format(k=n)
    if len(title) > 70:                                   # wide fonts: break before the opponent
        title = title.replace("  ·  ", "\n", 1)
    fig.text(0.03, 1 - 0.4 / H, title, fontsize=21, linespacing=1.3, fontweight="bold", color=INK, va="top")
    fig.text(0.03, 1 - 1.45 / H, T["sub"].format(xmax=XMAX), fontsize=11.5, color=INK2, va="top", linespacing=1.55)
    h = [Line2D([], [], marker="o", ls="", ms=11, color=DEF, label=T["legend_def"].format(team=team_name)),
         Line2D([], [], marker="o", ls="", ms=11, color=ATT, label=T["legend_att"].format(opp=opp_name))]
    fig.text(0.03, 1 - 2.8 / H, T["key"].format(team=team_name, opp=opp_name), fontsize=12, color=INK, va="top")
    if n % 2 == 1:
        lax = fig.add_subplot(fig.add_gridspec(rows, 2, left=0.03, right=0.985, top=1 - 3.75 / H, bottom=0.015,
                                               wspace=0.06, hspace=0.24)[rows - 1, 1])
        lax.axis("off")
        lax.legend(handles=h, loc="center", frameon=False, fontsize=15)

    if n == 0:
        fig.text(0.03, 0.4, T["none"].format(k=attempts), fontsize=14, color=INK)
    gs = fig.add_gridspec(rows, cols, left=0.03, right=0.985, top=1 - 3.75 / H, bottom=0.015, wspace=0.06, hspace=0.24)
    for i, s in enumerate(sc):
        ax = fig.add_subplot(gs[i // cols, i % cols])
        _half_pitch(ax, XMAX)
        ok = s["line_on_camera"] and s["receiver_on_camera"] and s["receiver_on_camera_at_reception"]
        u = s.get("usual")
        if u is not None:
            ax.plot(u["x"], u["y"], color=DEF, lw=2.2, ls=(0, (4, 3)), alpha=.55, zorder=2)
            ax.scatter(u["x"], u["y"], s=120, facecolor="none", edgecolor=DEF, lw=1.6, alpha=.7, zorder=2)
        b4 = sorted([p for p in s["players"] if p["id"] in s["back_four"]], key=lambda p: p["y"])
        ax.plot([p["x"] for p in b4], [p["y"] for p in b4], color=DEF, lw=1.5, alpha=.6, zorder=2)
        bp, br = s["ball_pass"], s["ball_reception"]
        if not np.isnan(bp[0]) and bp[0] <= XMAX:
            ax.scatter(*bp, s=30, color=INK, zorder=3)
        if not np.isnan(bp[0]) and not np.isnan(br[0]):
            ax.annotate("", xy=(min(br[0], XMAX), br[1]), xytext=(min(bp[0], XMAX), bp[1]),
                        arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6, ls="--"), zorder=3)
        rp = next((p for p in s["players"] if p["id"] == s["receiver_id"]), None)
        if rp is not None and s["receiver_at_reception"] is not None:
            rx1, ry1 = s["receiver_at_reception"]
            ax.plot([rp["x"], min(rx1, XMAX)], [rp["y"], ry1], color=ATT, lw=2, ls=":", zorder=3)
        for p in s["players"]:
            if p["x"] > XMAX:
                continue
            c = DEF if p["defending"] else ATT
            a = 1.0 if p["det"] else 0.4
            key = p["id"] in (s["receiver_id"], s["passer_id"])
            ax.scatter(p["x"], p["y"], s=300 if key else 180, color=c, alpha=a, edgecolor=INK if key else SURFACE,
                       lw=2.2 if key else 1.5, zorder=4.6 if key else 4)
            if p["no"] is not None:
                ax.text(p["x"], p["y"], str(p["no"]), fontsize=9.5, color="white" if p["det"] else INK, ha="center",
                        va="center", zorder=5.6 if key else 5, fontweight="bold")
            if key:
                lab = T["receiver"] if p["id"] == s["receiver_id"] else T["passer"]
                if not p["det"]:
                    lab += T["est"]
                ax.annotate(lab, (p["x"], p["y"]), xytext=(0, 15 if p["id"] == s["receiver_id"] else -19), textcoords="offset points", ha="center", fontsize=10.5,
                            color=INK, fontweight="bold", zorder=7, bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=.85))
        res = T["goal"] if s["lead_to_goal"] else (T["shot"] if s["lead_to_shot"] else "")
        g = s.get("usual_gap")
        utxt = "" if g is None else (T["u_high"] if g >= COARSE else T["u_deep"] if g <= -COARSE else T["u_same"])
        tag = "  ·  ".join(x for x in (T.get(s.get("break_type") or "", ""), T["blocks"].get(s["block"], s["block"]), utxt,
                                        T["frame"].format(f=s["frame"]), res,
                                        "" if ok else T["offcam"]) if x)
        col = INK if ok else INK2
        ax.set_title(f'{T["half"].get(s["period"], s["period"])} {s["clock"]}  ·  {s["passer"]} → {s["receiver"]}\n{tag}',
                     fontsize=12.5, color=col, loc="left", pad=6, linespacing=1.4)
        ax.text(-55, 33.5, T["own_goal"], fontsize=10.5, color=INK2, va="top")
    fig.savefig(out, dpi=100, facecolor=SURFACE)
    plt.close(fig)
    return out
