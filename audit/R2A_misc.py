"""R2A: same-frame possession starts, halftime frame gaps, tracking read cost old vs new."""
import sys, time, json
import pandas as pd
sys.path.insert(0, "/home/opc/football_acup2/analysis/acup2/backline_repo")
from backline import data
df = pd.read_pickle("/tmp/r2a/scan.pkl")
for r in df[df.nxt_start_eq_end > 0].itertuples():
    ev = data.events(r.mid); pp = ev[ev.event_type == "player_possession"]
    q = pp[pp.frame_start == r.f0]
    print(r.mid, r.eid, [(e, p == r.rec) for e, p in zip(q.event_id, q.player_id)])
# halftime: frame numbering around period change, passes within 50 frames of period end
mid = 1996435
per = {}
for fr in data.tracking(mid):
    per.setdefault(fr["period"], [fr["frame"], fr["frame"]]); per[fr["period"]][1] = fr["frame"]
print("periods", per)
for mid in data.match_ids():
    ev = data.events(mid); pp = ev[(ev.event_type == "player_possession") & (ev.last_line_break == True) & (ev.end_type == "pass")]
    m = data.meta(mid)
    ends = pp.groupby("period").frame_end.max()
# timing
mid = 1886347
ev = data.events(mid); P = ev[(ev.event_type == "player_possession") & (ev.last_line_break == True) & (ev.end_type == "pass")]
for name, want in (("old", set(P.frame_end.astype(int))), ("new", {f for x in P.frame_end.astype(int) for f in range(x, x + 51)})):
    t0 = time.time(); S = {fr["frame"]: fr for fr in data.tracking(mid, want)}; print(name, len(want), len(S), round(time.time() - t0, 2), "s")
t0 = time.time(); n = sum(1 for _ in open(data.data_dir() / str(mid) / f"{mid}_tracking_extrapolated.jsonl")); print("line count only", n, round(time.time() - t0, 2))
