"""Per-frame back-four positions during organised defence.

Coordinates are flipped so the DEFENDING team attacks +x (own goal at x = -52.5).
The back four is the four deepest outfield players at each frame. A frame is "measured"
only when all four are detected by the camera; off-screen positions are estimates and
are never used for metrics (see README, "Why coverage matters").
"""
import numpy as np
import pandas as pd

from . import data

BLOCKS = ("low_block", "medium_block", "high_block")


def back_four(mid: int) -> pd.DataFrame:
    m = data.meta(mid)
    team, gk, home, side = data.roster(m)
    away = m["away_team"]["id"]
    ph = data.phases(mid)
    ph = ph[ph.team_out_of_possession_phase_type.isin(BLOCKS)].sort_values("frame_start")
    fs, fe = ph.frame_start.values, ph.frame_end.values
    tin, blk, pidx = ph.team_in_possession_id.values, ph.team_out_of_possession_phase_type.values, ph.index.values
    rows, pos = [], {}
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
        pl = [(s * p["x"], s * p["y"], p["is_detected"], p["player_id"]) for p in fr["player_data"]
              if team.get(p["player_id"]) == dteam and p["player_id"] not in gk]
        if len(pl) < 8:
            continue
        pl.sort()
        b4 = pl[:4]
        pos[(dteam, f)] = (int(pidx[k]), {p[3]: (p[0], p[2]) for p in pl})
        b = fr.get("ball_data") or {}
        rows.append((mid, f, per, int(pidx[k]), blk[k], dteam,
                     all(p[2] for p in b4), *[p[0] for p in b4], *[p[1] for p in b4], *[p[3] for p in b4],
                     np.nan if b.get("x") is None else s * b["x"], np.nan if b.get("y") is None else s * b["y"]))
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
