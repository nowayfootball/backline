"""R2A: scan all 20 matches x 2 teams; reception frame diagnostics."""
import json, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, "<repo>")
from backline import data, scenes

rows = []
tim = []
for mid in data.match_ids():
    m = data.meta(mid)
    ev = data.events(mid)
    pp = ev[ev.event_type == "player_possession"].sort_values("frame_start")
    # raw tracking frames for diagnostics
    for t in (m["home_team"]["id"], m["away_team"]["id"]):
        t0 = time.time(); sc = scenes.scenes(mid, t); tim.append((mid, t, time.time() - t0, len(sc)))
        if not sc: continue
        need = set()
        for s in sc:
            need |= set(range(s["frame"] - 5, s["frame"] + 60))
        S = {fr["frame"]: fr for fr in data.tracking(mid, need)}
        for s in sc:
            r = ev[ev.event_id == s["event_id"]].iloc[0]
            f0, f1 = s["frame"], s["reception_frame"]
            nxt = pp[pp.frame_start > f0].head(1)
            nxt_same = pp[pp.frame_start >= f0].head(2)
            method = "none" if f1 is None else ("next" if len(nxt) and int(nxt.frame_start.iloc[0]) == f1 and nxt.player_id.iloc[0] == s["receiver_id"] else "nearest")
            def d(f, pid):
                if f not in S: return np.nan
                b = S[f]["ball_data"]; q = {x["player_id"]: x for x in S[f]["player_data"]}
                if b.get("x") is None or pid not in q: return np.nan
                return float(np.hypot(b["x"] - q[pid]["x"], b["y"] - q[pid]["y"]))
            rows.append(dict(mid=mid, team=t, eid=s["event_id"], method=method, f0=f0, f1=f1,
                             gap=None if f1 is None else f1 - f0,
                             d_rec=d(f1, s["receiver_id"]) if f1 else np.nan,
                             d_pass_at_f1=d(f1, s["passer_id"]) if f1 else np.nan,
                             d_pass_at_f0=d(f0, s["passer_id"]),
                             per0=S[f0]["period"], per1=S[f1]["period"] if f1 in S else None,
                             nxt_pid=None if not len(nxt) else nxt.player_id.iloc[0], nxt_gap=None if not len(nxt) else int(nxt.frame_start.iloc[0]) - f0,
                             nxt_team=None if not len(nxt) else nxt.team_id.iloc[0], rec=s["receiver_id"],
                             nxt_start_eq_end=int((pp.frame_start == f0).sum()),
                             time_end=r.time_end, clock=s["clock"], period=s["period"], ev_period=r.period,
                             ok=s["line_on_camera"] and s["receiver_on_camera"], goal=s["lead_to_goal"], shot=s["lead_to_shot"],
                             order=[(x["line_on_camera"] and x["receiver_on_camera"], x["lead_to_goal"], x["lead_to_shot"], x["frame"]) for x in sc].index((s["line_on_camera"] and s["receiver_on_camera"], s["lead_to_goal"], s["lead_to_shot"], s["frame"]))))
df = pd.DataFrame(rows); df.to_pickle("/tmp/r2a/scan.pkl")
pd.DataFrame(tim, columns=["mid", "team", "sec", "n"]).to_csv("/tmp/r2a/time.csv", index=False)
print(len(df)); print(df.method.value_counts())
