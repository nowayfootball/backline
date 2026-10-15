import json, numpy as np, pandas as pd
D="<data>/matches/1996435/1996435_"
ev=pd.read_csv(D+"dynamic_events.csv",low_memory=False)
print(ev[(ev.frame_start>4009)&(ev.frame_start<4376)][['event_id','event_type','event_subtype','frame_start','player_name','team_shortname']].head(15).to_string())
pid=int(ev[ev.event_id=='8_103'].player_targeted_id.iloc[0])
for line in open(D+"tracking_extrapolated.jsonl"):
    fr=json.loads(line)
    if fr["frame"] in (4019,4029,4040,4060,4100,4415):
        b=fr["ball_data"]; q={p["player_id"]:p for p in fr["player_data"]}[pid]
        print(fr["frame"], round(b["x"],1),round(b["y"],1), round(q["x"],1),round(q["y"],1), round(np.hypot(b["x"]-q["x"],b["y"]-q["y"]),1))
    if fr["frame"]>4415: break
