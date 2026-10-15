"""R1A independent reimplementation of scene cards (from spec only)."""
import json, sys
import numpy as np, pandas as pd
D = "<data>/matches"

def run(mid, team):
    m = json.load(open(f"{D}/{mid}/{mid}_match.json"))
    home = m["home_team"]["id"]; side = m["home_team_side"]
    pl = {p["id"]: p for p in m["players"]}
    gk = {p["id"] for p in m["players"] if p["player_role"]["acronym"] == "GK"}
    ev = pd.read_csv(f"{D}/{mid}/{mid}_dynamic_events.csv", low_memory=False)
    pp = ev[ev.event_type == "player_possession"].sort_values("frame_start")
    P = pp[(pp.end_type == "pass") & (pp.last_line_break == True) & (pp.pass_outcome == "successful") & (pp.team_id != team)]
    rec = {}
    for r in P.itertuples():
        n = pp[(pp.frame_start > r.frame_end) & (pp.player_id == r.player_targeted_id)]
        rec[r.event_id] = int(n.frame_start.iloc[0]) if len(n) else int(r.frame_end) + 10
    want = set(P.frame_end.astype(int)) | set(rec.values())
    T = {}
    with open(f"{D}/{mid}/{mid}_tracking_extrapolated.jsonl") as f:
        for line in f:
            fr = json.loads(line)
            if fr["frame"] in want: T[fr["frame"]] = fr
    rows = []
    for r in P.itertuples():
        f0, f1 = int(r.frame_end), rec[r.event_id]
        fr = T[f0]; per = fr["period"]
        hs = side[per - 1]
        # sign so that defending team attacks +x
        team_ltr = (hs == "left_to_right") if team == home else (hs != "left_to_right")
        s = 1 if team_ltr else -1
        pos = {q["player_id"]: (s*q["x"], s*q["y"]) for q in fr["player_data"]}
        defs = sorted([(pos[i][0], i) for i in pos if pl.get(i, {}).get("team_id") == team and i not in gk])
        back = defs[:4]
        flag = None
        if len(back) >= 2 and back[1][0] - back[0][0] >= 2.0: flag = back[0][1]
        b = fr["ball_data"]; bx = s*b["x"] if b["x"] is not None else np.nan; by = s*b["y"] if b["y"] is not None else np.nan
        pas = pos.get(r.player_id, (np.nan, np.nan))
        fr1 = T[f1]; s1 = s if fr1["period"] == per else -s
        p1 = {q["player_id"]: (s1*q["x"], s1*q["y"]) for q in fr1["player_data"]}
        b1 = fr1["ball_data"]; rc = p1.get(r.player_targeted_id, (np.nan, np.nan))
        bx1 = s1*b1["x"] if b1["x"] is not None else np.nan; by1 = s1*b1["y"] if b1["y"] is not None else np.nan
        rows.append(dict(eid=r.event_id, f0=f0, f1=f1, per=per, time=r.time_end, passer=r.player_id, ptm=pl[r.player_id]["team_id"],
                         recv=r.player_targeted_id, rtm=pl.get(r.player_targeted_id, {}).get("team_id"),
                         back=[i for _, i in back], backx=[round(x, 1) for x, _ in back], flag=flag,
                         flag_no=pl[flag]["number"] if flag else None, flag_nm=pl[flag]["short_name"] if flag else None,
                         d_ball_passer=float(np.hypot(bx-pas[0], by-pas[1])), d_ball_recv=float(np.hypot(bx1-rc[0], by1-rc[1])),
                         ball_x=bx, recv_x1=rc[0], ndef=len(defs)))
    return pd.DataFrame(rows)

if __name__ == "__main__":
    for mid, team in [(2007721, 870), (1996435, 869)]:
        df = run(mid, team); df.to_pickle(f"/tmp/R1A_{mid}.pkl")
        pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
        print(mid, team, len(df)); print(df[["eid","f0","f1","per","time","ptm","rtm","backx","flag_no","flag_nm","d_ball_passer","d_ball_recv","ndef"]])
