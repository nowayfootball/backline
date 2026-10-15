"""Scenes where a team's last line was broken: one card per completed pass that broke the last defensive line.

Cards show facts only - where everyone was when the pass was played, the ball's path, the receiver's run.
They make NO judgement about who was at fault:
- replaying offside calls fails (only 6 of 62 come out offside at the pass frame, audit/offside_diag.py): positions,
  event timing or receiver identity can be off by metres, so metre-level gaps are not trustworthy;
- a "player left behind the line" flag was tested and dropped: most flags used off-camera estimates, half vanished
  when the pass moment moved by 0.5 s, and marking / covering / mistake cannot be told apart (audit/R1B_robust.py).
Coordinates: defending team attacks +x (own goal on the left at x = -52.5).
"""
import numpy as np

from . import data

MAX_RECEPTION_GAP = 50     # frames (5 s); reception must follow the pass directly


def attempts(mid: int, team_id: int) -> int:
    """Number of (completed or not) passes against this team flagged as breaking the last line."""
    ev = data.events(mid)
    return int(((ev.event_type == "player_possession") & (ev.last_line_break == True) & (ev.team_id != team_id)
                & (ev.end_type == "pass")).sum())


def scenes(mid: int, team_id: int, include_failed: bool = False) -> list[dict]:
    m = data.meta(mid)
    team, gk, home, side = data.roster(m)
    num = {p["id"]: p.get("number") for p in m["players"]}
    nm = {p["id"]: p.get("short_name") or p["last_name"] for p in m["players"]}
    ev = data.events(mid)
    pp = ev[ev.event_type == "player_possession"].sort_values("frame_start")
    btype = ev[ev.event_type == "passing_option"].set_index("event_id").last_line_break_type.to_dict()
    P = pp[(pp.last_line_break == True) & (pp.team_id != team_id) & (pp.end_type == "pass")]
    if not include_failed:
        P = P[P.pass_outcome == "successful"]
    # reception = the very next possession, if it is the targeted receiver and starts soon after the pass;
    # otherwise the frame where the ball is closest to the receiver within MAX_RECEPTION_GAP
    nxt_of, limit = {}, {}
    for r in P.itertuples():
        nxt = pp[pp.frame_start > r.frame_end].head(1)
        ok = len(nxt) and nxt.player_id.iloc[0] == r.player_targeted_id and nxt.frame_start.iloc[0] - r.frame_end <= MAX_RECEPTION_GAP
        nxt_of[r.event_id] = int(nxt.frame_start.iloc[0]) if ok else None
        # never look past the start of the next possession (someone else may have the ball by then)
        limit[r.event_id] = min(int(r.frame_end) + MAX_RECEPTION_GAP, int(nxt.frame_start.iloc[0]) if len(nxt) else 10**9)
    want = set()
    for r in P.itertuples():
        want |= set(range(int(r.frame_end), int(r.frame_end) + MAX_RECEPTION_GAP + 1))
    S = {}
    for fr in data.tracking(mid, want):
        b = fr.get("ball_data") or {}
        S[fr["frame"]] = (fr["period"], b.get("x"), b.get("y"),
                          {q["player_id"]: (q["x"], q["y"], q["is_detected"]) for q in fr["player_data"]})

    def sign(f):                                   # per frame: periods switch sides
        return 1.0 if ((side[S[f][0]] == "left_to_right") == (team_id == home)) else -1.0

    def players(f):
        if f not in S:
            return []
        sg = sign(f)
        return [dict(id=pid, x=sg * x, y=sg * y, det=d, defending=team.get(pid) == team_id, gk=pid in gk,
                     no=num.get(pid), name=nm.get(pid)) for pid, (x, y, d) in S[f][3].items()]

    def ball(f):
        if f not in S or S[f][1] is None:
            return (np.nan, np.nan)
        return (sign(f) * S[f][1], sign(f) * S[f][2])

    out = []
    for r in P.itertuples():
        f0 = int(r.frame_end)
        if f0 not in S:
            continue
        rec = r.player_targeted_id
        f1 = nxt_of[r.event_id]
        if f1 is None:                             # ball nearest to the receiver within the window, same period only
            cand = [(np.hypot(S[f][1] - S[f][3][rec][0], S[f][2] - S[f][3][rec][1]), f)
                    for f in range(f0 + 3, limit[r.event_id] + 1)
                    if f in S and S[f][0] == S[f0][0] and S[f][1] is not None and rec in S[f][3]]
            f1 = min(cand)[1] if cand else None
        at_pass = players(f0)
        defs = sorted([p for p in at_pass if p["defending"] and not p["gk"]], key=lambda p: p["x"])
        b4 = defs[:4]
        clock = str(r.time_end).split(".")[0]
        out.append(dict(match_id=mid, event_id=r.event_id, period=S[f0][0], clock=clock, frame=f0, reception_frame=f1,
                        passer_id=r.player_id, passer=r.player_name, receiver_id=rec,
                        receiver=r.player_targeted_name, outcome=r.pass_outcome,
                        break_type=btype.get(r.targeted_passing_option_event_id),   # 'through' the line or 'around' it
                        block=r.team_out_of_possession_phase_type,
                        lead_to_shot=bool(r.lead_to_shot), lead_to_goal=bool(r.lead_to_goal),
                        players=at_pass, back_four=[p["id"] for p in b4],
                        line_on_camera=all(p["det"] for p in b4), receiver_on_camera=any(p["id"] == rec and p["det"] for p in at_pass),
                        receiver_on_camera_at_reception=bool(f1 and rec in S.get(f1, (0, 0, 0, {}))[3] and S[f1][3][rec][2]),
                        ball_pass=ball(f0), ball_reception=ball(f1) if f1 else (np.nan, np.nan),
                        receiver_at_reception=next(((p["x"], p["y"]) for p in players(f1) if p["id"] == rec), None) if f1 else None))
    # most useful first: fully on camera, then those leading to a goal/shot, then match time
    out.sort(key=lambda s: (not (s["line_on_camera"] and s["receiver_on_camera"]), not s["lead_to_goal"],
                            not s["lead_to_shot"], s["frame"]))
    return out
