"""Per-frame back-four positions during organised defence.

Coordinates are flipped so the DEFENDING team attacks +x (own goal at x = -52.5).
The back four is the four deepest outfield players at each frame. A frame is "measured"
only when all four are detected by the camera; off-screen positions are estimates and
are never used for metrics (see README, "Only what the camera saw").
"""
import numpy as np
import pandas as pd

from . import data

BLOCKS = ("low_block", "medium_block", "high_block")


def _defending(mid: int):
    """Yield (frame, period, phase_id, block, defending team, outfield players sorted by depth, ball x, ball y)
    for every organised-defence frame with at least 8 defending outfield players. Players are
    (x, y, on_camera, player_id) with coordinates flipped so the defending team attacks +x."""
    m = data.meta(mid)
    team, gk, home, side = data.roster(m)
    away = m["away_team"]["id"]
    ph = data.phases(mid)
    ph = ph[ph.team_out_of_possession_phase_type.isin(BLOCKS)].sort_values("frame_start")
    fs, fe = ph.frame_start.values, ph.frame_end.values
    tin, blk, pidx = ph.team_in_possession_id.values, ph.team_out_of_possession_phase_type.values, ph.index.values
    for fr in data.tracking(mid):
        f, per = fr["frame"], fr.get("period")
        if per is None:
            continue
        k = np.searchsorted(fs, f, side="right") - 1
        if k < 0 or f > fe[k]:
            continue
        dteam = away if tin[k] == home else home
        home_ltr = side[per] == "left_to_right"
        s = 1.0 if (home_ltr if dteam == home else not home_ltr) else -1.0
        pl = sorted((s * p["x"], s * p["y"], bool(p["is_detected"]), p["player_id"]) for p in fr["player_data"]
                    if team.get(p["player_id"]) == dteam and p["player_id"] not in gk)
        if len(pl) < 8:
            continue
        b = fr.get("ball_data") or {}
        yield (f, per, int(pidx[k]), blk[k], dteam, pl,
               np.nan if b.get("x") is None else s * b["x"], np.nan if b.get("y") is None else s * b["y"])


def back_four(mid: int) -> pd.DataFrame:
    rows, pos = [], {}
    for f, per, phase, block, dteam, pl, bx, by in _defending(mid):
        b4 = pl[:4]
        pos[(dteam, f)] = (phase, {p[3]: (p[0], p[2]) for p in pl})
        rows.append((mid, f, per, phase, block, dteam,
                     all(p[2] for p in b4), *[p[0] for p in b4], *[p[1] for p in b4], *[p[3] for p in b4], bx, by))
    cols = (["match_id", "frame", "period", "phase_id", "block", "team_id", "measured"]
            + [f"x{i}" for i in range(4)] + [f"y{i}" for i in range(4)] + [f"id{i}" for i in range(4)] + ["ball_x", "ball_y"])
    df = pd.DataFrame(rows, columns=cols)
    # 0.5 s ahead x of the SAME four players: same defensive phase, and the player still on camera
    def ahead(t, f, ph, p):
        nxt = pos.get((t, f + 5))
        if nxt is None or nxt[0] != ph or p not in nxt[1] or not nxt[1][p][1]:
            return np.nan
        return nxt[1][p][0]
    for i in range(4):
        df[f"x{i}_p5"] = [ahead(t, f, ph, p) for t, f, ph, p in zip(df.team_id, df.frame, df.phase_id, df[f"id{i}"])]
    return df


def team_frames(mid: int) -> pd.DataFrame:
    """Organised-defence frames with ALL defending outfield players, ordered by depth (x0 = deepest).

    Columns x0..x9, y0..y9 (metres, defending team attacks +x) and d0..d9 (on camera?). Missing slots
    (fewer than 10 outfield players, e.g. after a red card) are NaN / False. Used by backline.trust.
    """
    rows = []
    for f, per, phase, block, dteam, pl, bx, by in _defending(mid):
        pl = [p[:3] for p in pl[:10]] + [(np.nan, np.nan, False)] * (10 - len(pl[:10]))
        rows.append((mid, f, per, phase, block, dteam, bx, by,
                     *[p[0] for p in pl], *[p[1] for p in pl], *[p[2] for p in pl]))
    cols = (["match_id", "frame", "period", "phase_id", "block", "team_id", "ball_x", "ball_y"]
            + [f"x{i}" for i in range(10)] + [f"y{i}" for i in range(10)] + [f"d{i}" for i in range(10)])
    return pd.DataFrame(rows, columns=cols)
