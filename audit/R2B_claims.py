"""R2B audit: is 'broke the last line' visible in tracking? receiver vs defenders at pass & reception; SkillCorner through/around."""
import numpy as np, pandas as pd
from multiprocessing import Pool
from backline import data, scenes


def one(mid):
    m = data.meta(mid); team, gk, home, side = data.roster(m)
    ev = data.events(mid)
    po = ev[ev.event_type == "passing_option"].set_index("event_id")
    pp = ev[ev.event_type == "player_possession"].set_index("event_id")
    out = []
    for t in (m["home_team"]["id"], m["away_team"]["id"]):
        sc = scenes.scenes(mid, t)
        want = {s["reception_frame"] for s in sc if s["reception_frame"]}
        S = {fr["frame"]: fr for fr in data.tracking(mid, want)}
        for i, s in enumerate(sc):
            rec = s["receiver_id"]
            d = [p for p in s["players"] if p["defending"] and not p["gk"]]
            dx = sorted(p["x"] for p in d)
            r0 = next((p for p in s["players"] if p["id"] == rec), None)
            row = dict(match=mid, team=t, rank=i, frame=s["frame"], line_cam=s["line_on_camera"], rec_cam=s["receiver_on_camera"],
                       block=s["block"], rec_x_pass=r0["x"] if r0 else np.nan, deep1_pass=dx[0] if dx else np.nan,
                       deep2_pass=dx[1] if len(dx) > 1 else np.nan, ball_rec_x=s["ball_reception"][0])
            f1 = s["reception_frame"]
            if f1 in S:
                fr = S[f1]; per = fr["period"]
                sg = 1.0 if ((side[per] == "left_to_right") == (t == home)) else -1.0
                D = sorted(sg * q["x"] for q in fr["player_data"] if team.get(q["player_id"]) == t and q["player_id"] not in gk)
                R = [q for q in fr["player_data"] if q["player_id"] == rec]
                row.update(deep1_rec=D[0], deep2_rec=D[1], rec_x_rec=sg * R[0]["x"] if R else np.nan,
                           rec_det_rec=R[0]["is_detected"] if R else None)
            # SkillCorner type of the targeted option
            tid = pp.loc[s["event_id"], "targeted_passing_option_event_id"] if s["event_id"] in pp.index else np.nan
            row["sc_type"] = po.loc[tid, "last_line_break_type"] if pd.notna(tid) and tid in po.index else None
            out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__":
    with Pool(3) as p:
        o = pd.concat(p.map(one, data.match_ids()))
    o.to_csv("/tmp/R2B_claims.csv", index=False)
    print("scenes", len(o), "per team-match:", o.groupby(["match", "team"]).size().describe().round(1).to_dict())
    print("SkillCorner type:", o.sc_type.value_counts(dropna=False).to_dict())
    on = o.line_cam & o.rec_cam
    print("on camera (line+receiver):", on.sum())
    o["behind_rec"] = o.rec_x_rec < o.deep1_rec          # receiver deeper than every outfield defender at reception
    o["behind2_rec"] = o.rec_x_rec < o.deep2_rec
    o["front_pass"] = o.rec_x_pass > o.deep1_pass         # receiver in front of deepest defender when pass played
    for nm, g in (("all", o), ("on-camera", o[on])):
        g = g.dropna(subset=["rec_x_rec"])
        print(nm, len(g), "recv behind deepest outfield @reception %.2f, behind 2nd-deepest %.2f, ball recv x < deepest@pass %.2f, receiver in front of deepest @pass %.2f"
              % (g.behind_rec.mean(), g.behind2_rec.mean(), (g.ball_rec_x < g.deep1_pass).mean(), g.front_pass.mean()))
        print("  by type:", g.groupby("sc_type").behind_rec.agg(["mean", "size"]).round(2).to_dict())
        print("  margin rec - deepest @reception (m) q:", (g.rec_x_rec - g.deep1_rec).quantile([.1, .25, .5, .75, .9]).round(1).to_dict())
    # ordering check: within each card page, on-camera first?
    bad = o.groupby(["match", "team"]).apply(lambda g: ((g.line_cam & g.rec_cam).astype(int).diff() > 0).any()).sum()
    print("pages where an on-camera scene follows an off-camera one:", bad)
    z = o.groupby(["match", "team"]).size()
    print("team-matches with 0 scenes need separate check; teams with scenes:", len(z))
