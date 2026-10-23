"""Offside replay used by audit/offside_diag.py (the "would have been offside" card feature it was built for was dropped).

Passes that break the last defensive line: who played the receiver onside, and what if they had held the line?

For each SkillCorner `player_possession` that ends in a pass flagged `last_line_break`, at the pass frame:
- offside line = second-deepest defending player (goalkeeper included), capped by the ball and the halfway line;
- onside margin = how far the receiver was behind that line (m, positive = onside);
- the "line holder" = the defender who set the offside line; if he had stood level with the next defender,
  would the receiver have been offside, and by how much?
Coordinates: defending team attacks +x (own goal at x = -52.5), so "deeper" = smaller x.
"""
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data

SHIFTS = (-2, -1, 0, 1, 2)          # frames around the pass moment, to show timing sensitivity
TOO_CLOSE = 0.5                     # m; tracking error makes margins below this a coin flip


def _passes(mid, which="breaks"):
    ev = data.events(mid)
    pp = ev[(ev.event_type == "player_possession") & (ev.end_type == "pass")]
    if which == "breaks":
        p = pp[pp.last_line_break == True]
    else:   # validation: every pass called offside + completed passes to a receiver near/behind the last line
        near = pp.delta_to_last_defensive_line_end.abs() <= 6
        p = pp[(pp.pass_outcome == "offside") | ((pp.pass_outcome == "successful") & near)]
    return p[["event_id", "frame_end", "period", "time_end", "team_id", "player_id", "player_name",
              "player_targeted_id", "player_targeted_name", "pass_outcome", "team_out_of_possession_phase_type"]]


def _one(mid, which="breaks"):
    m = data.meta(mid)
    team, gk, home, side = data.roster(m)
    names = {p["id"]: f'{p.get("short_name") or p["last_name"]}' for p in m["players"]}
    nums = {p["id"]: p.get("number") for p in m["players"]}
    P = _passes(mid, which)
    want = {int(f) + s for f in P.frame_end for s in SHIFTS}
    snaps = {}
    for fr in data.tracking(mid, want):
        b = fr.get("ball_data") or {}
        snaps[fr["frame"]] = (fr["period"], (b.get("x"), b.get("y")),
                              {q["player_id"]: (q["x"], q["y"], q["is_detected"]) for q in fr["player_data"]})
    rows = []
    for r in P.itertuples():
        att = r.team_id
        dteam = [t for t in set(team.values()) if t != att][0]
        rec = r.player_targeted_id
        out = dict(match_id=mid, event_id=r.event_id, frame=int(r.frame_end), period=r.period, time=r.time_end,
                   attacking_team=att, defending_team=dteam, passer=r.player_name, receiver_id=rec,
                   receiver=r.player_targeted_name, outcome=r.pass_outcome, block=r.team_out_of_possession_phase_type)
        for s in SHIFTS:
            snap = snaps.get(int(r.frame_end) + s)
            if snap is None or pd.isna(rec) or int(rec) not in snap[2]:
                continue
            per, ball, pl = snap
            sg = 1.0 if ((side[per] == "left_to_right") == (dteam == home)) else -1.0
            D = sorted((sg * x, pid, det, sg * y) for pid, (x, y, det) in pl.items() if team.get(pid) == dteam)
            if len(D) < 3:
                continue
            rx, ry, rdet = sg * pl[int(rec)][0], sg * pl[int(rec)][1], pl[int(rec)][2]
            bx = sg * ball[0] if ball[0] is not None else np.nan
            cap = min(np.nanmin([bx, 99]), 0.0)                        # cannot be offside behind the ball or in own half
            line = min(D[1][0], cap) if not np.isnan(bx) else min(D[1][0], 0.0)
            # holder = deepest outfield defender (normally the one who sets the line); counterfactual:
            # he stands level with the next outfield defender, then the line is recomputed the same way
            outfield = [d for d in D if d[1] not in gk]
            holder, nxt = outfield[0], outfield[1]
            xs = sorted(nxt[0] if d[1] == holder[1] else d[0] for d in D)
            cf_line = min(xs[1], cap)
            row = dict(onside_margin=rx - line, cf_margin=rx - cf_line, holder_gap=nxt[0] - holder[0],
                       receiver_det=rdet, holder_det=holder[2], next_det=nxt[2])
            if s == 0:
                out.update(row, holder_id=holder[1], holder=names.get(holder[1]), holder_no=nums.get(holder[1]),
                           next_id=nxt[1], rx=rx, ry=ry, bx=bx, line_x=line)
            out[f"onside_margin_{s:+d}"] = row["onside_margin"]
        rows.append(out)
    return pd.DataFrame(rows)


def classify(df: pd.DataFrame) -> pd.DataFrame:
    """Add a `verdict` column (no_data / estimated / too_close / looks_offside / holder_kept_onside / clean_break)."""
    def verdict(r):
        if pd.isna(r.get("onside_margin")):
            return "no_data"
        if not (r.receiver_det and r.holder_det):
            return "estimated"                      # a key player was off camera: position is an estimate
        if abs(r.onside_margin) < TOO_CLOSE:
            return "too_close"
        if r.onside_margin < 0:
            return "looks_offside"
        if r.cf_margin <= -TOO_CLOSE:
            return "holder_kept_onside"             # holding the line would have made it offside
        if r.cf_margin < TOO_CLOSE:
            return "holder_kept_onside_marginal"
        return "clean_break"                        # receiver was beyond the whole line: no single culprit
    return df.assign(verdict=df.apply(verdict, axis=1))


def all_breaks(mids=None, procs=3, which="breaks") -> pd.DataFrame:
    """Offside-replay rows for every line-breaking pass in `mids` (default: all matches), in `procs` processes."""
    mids = mids or data.match_ids()
    with Pool(procs) as p:
        return classify(pd.concat(p.starmap(_one, [(m, which) for m in mids]), ignore_index=True))
