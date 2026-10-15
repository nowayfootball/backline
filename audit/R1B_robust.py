"""R1B: robustness audit of the scene-card 'out of line' ring (scenes.py OUT_OF_LINE = 2 m).
Per scene: flag at pass frame +-1/2/5, detection state, threshold margin, back-line composition (event positions),
marking-vs-cover geometry. Plus tracking jitter around scenes (second differences, re-detection jumps).
Output: /tmp/R1B_scenes.parquet, /tmp/R1B_jitter.parquet
"""
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

from backline import data, scenes as S_

DEFPOS = {"LB", "RB", "LCB", "RCB", "CB", "LWB", "RWB"}
OFFS = [-5, -2, -1, 1, 2, 5]


def gap_at(pl, team, gk, tid, sg):
    d = sorted([(sg * x, pid, dt) for pid, (x, y, dt) in pl.items() if team.get(pid) == tid and pid not in gk])
    if len(d) < 2:
        return None
    return d[1][0] - d[0][0], d[0][1], [p for _, p, _ in d[:4]]


def one(mid):
    m = data.meta(mid)
    team, gk, home, side = data.roster(m)
    role = {p["id"]: p["player_role"]["acronym"] for p in m["players"]}
    ev = data.events(mid)
    evp = ev[ev.player_id.notna() & ev.player_position.notna()][["player_id", "frame_start", "player_position"]]
    evp = evp.assign(player_id=evp.player_id.astype(int)).sort_values("frame_start")

    def pos_at(pid, f):
        e = evp[evp.player_id == pid]
        if not len(e):
            return role.get(pid)
        i = (e.frame_start - f).abs().idxmin()
        return e.loc[i, "player_position"]

    tids = sorted({p["team_id"] for p in m["players"]})
    # team formation tag: does the team ever use CB (single) or wing-backs -> back 3/5
    team_back3 = {}
    for t in tids:
        ps = set(ev[(ev.team_id == t)].player_position.dropna())
        team_back3[t] = bool(ps & {"CB", "LWB", "RWB"})
    sc = []
    for t in tids:
        for s in S_.scenes(mid, t):
            s["team"] = t
            sc.append(s)
    want = set()
    for s in sc:
        want |= {s["frame"] + k for k in range(-30, 11)}
    T = {}
    for fr in data.tracking(mid, want):
        T[fr["frame"]] = (fr["period"], {q["player_id"]: (q["x"], q["y"], q["is_detected"]) for q in fr["player_data"]})
    rows = []
    for s in sc:
        f0, t = s["frame"], s["team"]
        per = s["period"]
        sg = 1.0 if ((side[per] == "left_to_right") == (t == home)) else -1.0
        g0 = gap_at(T[f0][1], team, gk, t, sg)
        gap0, deep0, b4 = g0
        r = dict(match_id=mid, team=t, event_id=s["event_id"], frame=f0, gap0=gap0, flag0=gap0 >= S_.OUT_OF_LINE,
                 deep_id=deep0, back3=team_back3[t], goal=s["lead_to_goal"], shot=s["lead_to_shot"],
                 line_on_camera=s["line_on_camera"])
        for k in OFFS:
            g = gap_at(T[f0 + k][1], team, gk, t, sg) if f0 + k in T else None
            r[f"gap{k:+d}"] = g[0] if g else np.nan
            r[f"same_deep{k:+d}"] = (g[1] == deep0) if g else np.nan
        pl = {p["id"]: p for p in s["players"]}
        d = pl[deep0]
        r["deep_det"] = d["det"]
        r["second_det"] = pl[b4[1]]["det"]
        r["pair_det"] = d["det"] and pl[b4[1]]["det"]
        r["deep_pos"] = pos_at(deep0, f0)
        r["b4_pos"] = ",".join(str(pos_at(p, f0)) for p in b4)
        r["n_nondef_b4"] = sum(pos_at(p, f0) not in DEFPOS for p in b4)
        # geometry: receiver, nearest attacker, ball
        att = [p for p in s["players"] if not p["defending"] and team.get(p["id"]) is not None]
        rc = pl.get(s["receiver_id"])
        if rc is not None:
            r["recv_dist"] = float(np.hypot(rc["x"] - d["x"], rc["y"] - d["y"]))
            r["recv_dx_vs_deep"] = rc["x"] - d["x"]                   # <0: receiver deeper than flagged
            r["recv_dx_vs_second"] = rc["x"] - pl[b4[1]]["x"]         # <0: receiver behind the rest of the line
            r["recv_dy"] = abs(rc["y"] - d["y"])
        na = min(att, key=lambda p: np.hypot(p["x"] - d["x"], p["y"] - d["y"]))
        r["near_att_dist"] = float(np.hypot(na["x"] - d["x"], na["y"] - d["y"]))
        r["near_att_is_recv"] = na["id"] == s["receiver_id"]
        bx, by = s["ball_pass"]
        r["ball_dy"] = abs(by - d["y"]) if not np.isnan(by) else np.nan
        # ball-side vs far-side: flagged player's y on the opposite half of ball (lateral cover)
        r["deep_y"] = d["y"]
        r["ball_y"] = by
        # lateral rank of deep player among back four
        ys = sorted(pl[p]["y"] for p in b4)
        r["deep_lat_rank"] = ys.index(d["y"])
        rows.append(r)
    # jitter: consecutive detected frames, second differences
    jit = []
    fs = sorted(T)
    for f in fs:
        if f - 1 in T and f + 1 in T and T[f - 1][0] == T[f][0] == T[f + 1][0]:
            a, b, c = T[f - 1][1], T[f][1], T[f + 1][1]
            for pid, (x, y, dt) in b.items():
                if pid in a and pid in c:
                    xa, ya, da = a[pid]; xc, yc, dc = c[pid]
                    jit.append((mid, f, pid, dt and da and dc, (not da) and dt, xa - 2 * x + xc, ya - 2 * y + yc,
                                x - xa, y - ya))
    J = pd.DataFrame(jit, columns=["match_id", "frame", "pid", "all_det", "redetect", "d2x", "d2y", "vx", "vy"])
    return pd.DataFrame(rows), J


if __name__ == "__main__":
    mids = data.match_ids()
    with Pool(3) as p:
        res = p.map(one, mids)
    R = pd.concat([r[0] for r in res], ignore_index=True)
    J = pd.concat([r[1] for r in res], ignore_index=True)
    R.to_parquet("/tmp/R1B_scenes.parquet")
    J.to_parquet("/tmp/R1B_jitter.parquet")
    print(len(R), "scenes;", int(R.flag0.sum()), "flagged;", len(J), "jitter rows")
