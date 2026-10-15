"""docs/usual_line_test.md: do line-break scenes deviate more from the usual line than comparable moments? (rules written before running)"""
from multiprocessing import Pool

import numpy as np
import pandas as pd

from backline import data, frames, scenes, usual

BLOCKS = ("low_block", "medium_block", "high_block")
rng_seed = 7


def one(mid):
    f = frames.back_four(mid)
    ev = data.events(mid)
    lb = ev[(ev.event_type == "player_possession") & (ev.last_line_break == True) & (ev.end_type == "pass")]
    rows = []
    rng = np.random.default_rng(rng_seed + mid % 1000)
    for team in f.team_id.unique():
        prep = usual.prepare(f, team)
        idx = prep.set_index("frame")
        breaks_against = lb[lb.team_id != team].frame_end.values
        for s in scenes.scenes(mid, team):
            f0 = s["frame"]
            if f0 not in idx.index:
                continue                                   # not organised defence, or back four not all on camera
            r0 = idx.loc[f0]
            if r0.block not in BLOCKS:
                continue
            u = usual.usual_line(prep, r0.block, (r0.ball_x, r0.ball_y), f0)
            if u is None:
                continue
            d_scene = usual.height_gap([r0[f"sx{i}"] for i in range(4)], u)
            g = prep[(prep.block == r0.block) & ((prep.frame - f0).abs() > usual.EXCLUDE)]
            g = g[np.hypot(g.ball_x - r0.ball_x, g.ball_y - r0.ball_y) <= usual.RADIUS]
            # no line-breaking pass by the opponent within the next 3 s
            ok = ~np.array([((breaks_against >= fr) & (breaks_against <= fr + 30)).any() for fr in g.frame])
            g = g[ok]
            ctrl = []
            for _, c in g.iloc[rng.permutation(len(g))].iterrows():
                uc = usual.usual_line(prep, c.block, (c.ball_x, c.ball_y), int(c.frame))
                if uc is not None:
                    ctrl.append(usual.height_gap([c[f"sx{i}"] for i in range(4)], uc))
                if len(ctrl) == 20:
                    break
            rows.append(dict(match_id=mid, team_id=team, event_id=s["event_id"], block=r0.block, d_scene=d_scene,
                             n_usual=u["n_frames"], ctrl=ctrl))
    print("done", mid, len(rows), flush=True)
    return rows


def perm_test(df, stat, B=5000, seed=7):
    rng = np.random.default_rng(seed)
    def compute(vals_list, pick):
        return np.mean([stat(v[p]) - np.mean([stat(x) for j, x in enumerate(v) if j != p]) for v, p in zip(vals_list, pick)])
    vals = [np.array([r.d_scene] + list(r.ctrl)) for r in df.itertuples()]
    obs = compute(vals, [0] * len(vals))
    null = np.array([compute(vals, [rng.integers(len(v)) for v in vals]) for _ in range(B)])
    return obs, float((np.abs(null) >= abs(obs)).mean())


if __name__ == "__main__":
    with Pool(3) as p:
        rows = [r for rr in p.map(one, data.match_ids()) for r in rr]
    df = pd.DataFrame(rows)
    df = df[df.ctrl.apply(len) >= 5]
    df.to_pickle("data/verify_usual.pkl")
    print("scenes in S:", len(df), "| blocks:", df.block.value_counts().to_dict(), "| controls per scene median:", df.ctrl.apply(len).median())
    if len(df) < 20:
        print("S < 20: descriptive only")
    ma_s = df.d_scene.abs().mean(); ma_c = np.mean([np.mean(np.abs(c)) for c in df.ctrl])
    print(f"mean |gap|: scenes {ma_s:.2f} m vs controls {ma_c:.2f} m")
    obs, p = perm_test(df, abs)
    print(f"PRIMARY |gap| scene - control = {obs:+.2f} m, permutation p = {p:.4f}")
    obs2, p2 = perm_test(df, lambda x: x)
    print(f"SECONDARY signed gap scene - control = {obs2:+.2f} m (negative = deeper than usual), p = {p2:.4f}")
    claim = (p < 0.05) and (obs >= 1.0)
    print("VERDICT:", "overlay is informative" if claim else "no evidence that broken scenes deviate more from the usual line")
