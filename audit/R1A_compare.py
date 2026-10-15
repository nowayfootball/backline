import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backline import scenes
for mid, team in [(2007721, 870), (1996435, 869)]:
    mine = pd.read_pickle(f"/tmp/R1A_{mid}.pkl").set_index("eid")
    sc = scenes.scenes(mid, team)
    print(mid, "mine", len(mine), "code", len(sc))
    for s in sc:
        r = mine.loc[s["event_id"]]
        px = {p["id"]: p["x"] for p in s["players"]}
        bx = [round(px[i], 1) for i in s["back_four"]]
        fl = [(f["no"], f["name"], round(f["dx"], 2), f["det"]) for f in s["out_of_line"]]
        rr = s["receiver_at_reception"]
        dr = np.hypot(s["ball_reception"][0]-rr[0], s["ball_reception"][1]-rr[1]) if rr else None
        print(s["event_id"], s["clock"], r.time, s["back_four"] == r.back, bx == r.backx, fl, r.flag_no,
              s["line_on_camera"], round(dr, 2) if dr is not None else None, s["passer"], "->", s["receiver"])
    print("missing:", set(mine.index) - {s["event_id"] for s in sc})
