"""R2A: ball-receiver / ball-passer distance trajectories for outlier scenes."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "<repo>")
from backline import data
df = pd.read_pickle("/tmp/r2a/scan.pkl")
sel = sys.argv[1:]
for key in sel:
    mid, eid = key.split(":"); mid = int(mid)
    r = df[(df.mid == mid) & (df.eid == eid)].iloc[0]
    ev = data.events(mid); pp = ev[ev.event_type == "player_possession"].sort_values("frame_start")
    e = ev[ev.event_id == eid].iloc[0]
    pas = e.player_id
    print(f"== {key} f0={r.f0} f1={r.f1} method={r.method} passer={pas} rec={r.rec} frame_start={e.frame_start}")
    print(pp[(pp.frame_start >= r.f0 - 2) & (pp.frame_start <= r.f0 + 60)][["event_id", "frame_start", "frame_end", "player_id", "team_id", "end_type"]].to_string())
    S = {fr["frame"]: fr for fr in data.tracking(mid, range(r.f0, r.f0 + 56))}
    out = []
    for f in range(r.f0, r.f0 + 56):
        if f not in S: out.append(f"{f-r.f0}:-"); continue
        b = S[f]["ball_data"]; q = {x["player_id"]: x for x in S[f]["player_data"]}
        if b.get("x") is None: out.append(f"{f-r.f0}:noball"); continue
        dr = np.hypot(b["x"] - q[r.rec]["x"], b["y"] - q[r.rec]["y"]) if r.rec in q else np.nan
        dp = np.hypot(b["x"] - q[pas]["x"], b["y"] - q[pas]["y"]) if pas in q else np.nan
        out.append(f"{f-r.f0}:{dr:.1f}/{dp:.1f}{'' if b.get('is_detected') else '*'}{'' if q.get(r.rec,{}).get('is_detected') else 'r'}")
    print("  ".join(out))
