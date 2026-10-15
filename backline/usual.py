"""'Usual line': where this team's back four normally stood in THIS match when the ball was in a similar place.

NOT USED IN THE CARDS. Check written before running it (docs/usual_line_test.md, audit/verify_usual.py) failed: in ordinary moments the
line is already >= 3 m away from this 'usual' line 46% of the time (median 2.7 m), and scenes where the line was
beaten were not further from it (2.9 m vs 3.5 m, p = .12). Kept for transparency and reuse.

Same match only - across matches the line metrics barely repeat (reliability.json, r_cross), so another match's
shape is not a fair reference. Only measured frames (all four on camera), same defensive block, ball within RADIUS m,
and never within EXCLUDE frames of the moment being compared (so a scene is not compared with itself).
"""
import numpy as np
import pandas as pd

RADIUS, RADIUS_WIDE = 6.0, 10.0
EXCLUDE = 200          # frames (20 s)
MIN_FRAMES = 50        # 5 s of play


def prepare(frames: pd.DataFrame, team_id: int) -> pd.DataFrame:
    """Measured frames of one team with the back four ordered left-to-right (by y)."""
    f = frames[(frames.team_id == team_id) & frames.measured].dropna(subset=["ball_x", "ball_y"]).copy()
    X = f[[f"x{i}" for i in range(4)]].values
    Y = f[[f"y{i}" for i in range(4)]].values
    o = np.argsort(Y, axis=1)
    X, Y = np.take_along_axis(X, o, 1), np.take_along_axis(Y, o, 1)
    for i in range(4):
        f[f"sx{i}"], f[f"sy{i}"] = X[:, i], Y[:, i]
    return f


def usual_line(prep: pd.DataFrame, block: str, ball_xy, frame: int):
    """Median left-to-right back-four positions, or None if fewer than MIN_FRAMES comparable frames."""
    g = prep[(prep.block == block) & ((prep.frame - frame).abs() > EXCLUDE)]
    if g.empty or np.isnan(ball_xy[0]):
        return None
    d = np.hypot(g.ball_x - ball_xy[0], g.ball_y - ball_xy[1])
    for r in (RADIUS, RADIUS_WIDE):
        h = g[d <= r]
        if len(h) >= MIN_FRAMES:
            xs = np.array([h[f"sx{i}"].median() for i in range(4)])
            ys = np.array([h[f"sy{i}"].median() for i in range(4)])
            return dict(x=xs, y=ys, n_frames=len(h), radius=r)
    return None


def height_gap(actual_xs, usual) -> float:
    """Mean x of the actual back four minus the usual line (positive = higher than usual, negative = deeper)."""
    return float(np.mean(actual_xs) - np.mean(usual["x"]))


COARSE = 3.0           # m; only call a line "higher/deeper than usual" when the gap is at least this big


def attach(sc: list[dict], frames: pd.DataFrame, team_id: int) -> list[dict]:
    """Add s['usual'] (positions, n_frames) and s['usual_gap'] to each organised-defence scene with the line on camera."""
    prep = prepare(frames, team_id)
    idx = prep.set_index("frame")
    for s in sc:
        s["usual"], s["usual_gap"] = None, None
        f0 = s["frame"]
        if f0 not in idx.index or idx.loc[f0].block not in ("low_block", "medium_block", "high_block"):
            continue
        r0 = idx.loc[f0]
        u = usual_line(prep, r0.block, (r0.ball_x, r0.ball_y), f0)
        if u is not None:
            s["usual"] = u
            s["usual_gap"] = height_gap([r0[f"sx{i}"] for i in range(4)], u)
    return sc
