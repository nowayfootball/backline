"""Audit B(1-4): per team-match cells over all cached matches.

For each team-match x (metric, block): full value + phase-bootstrap SE, random phase-split halves,
first/second half values, coverage, and selection checks (measured vs unmeasured frames).
Output: /tmp/B_cells.parquet, /tmp/B_sel.parquet
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backline import metrics as M

rng = np.random.default_rng(1)
cells, sel = [], []
for p in sorted(Path("/tmp/B_frames").glob("*.parquet")):
    F = pd.read_parquet(p)
    mid = int(p.stem)
    for t in F.team_id.unique():
        f = M._add_frame_cols(F[F.team_id == t])
        for name, spec in M.METRICS.items():
            for blk in spec["blocks"]:
                a = f if blk == "all" else f[f.block == blk]
                m = a[a.measured]
                row = dict(match_id=mid, team_id=t, metric=name, block=blk, sec=len(m) / 10, sec_all=len(a) / 10,
                           nph=m.phase_id.nunique())
                if row["sec"] >= M.MIN_SECONDS:
                    row["value"] = M._value(name, m)
                    groups = [g for _, g in m.groupby("phase_id")]
                    bs = [M._value(name, pd.concat([groups[i] for i in rng.integers(0, len(groups), len(groups))])) for _ in range(200)]
                    row["lo"], row["hi"] = np.nanquantile(bs, [.05, .95])
                    row["se"] = np.nanstd(bs)
                    # random phase split
                    ph = m.phase_id.unique(); rng.shuffle(ph); hA = set(ph[: len(ph) // 2])
                    row["rA"] = M._value(name, m[m.phase_id.isin(hA)]); row["rB"] = M._value(name, m[~m.phase_id.isin(hA)])
                    # value on all frames incl. estimated coords, and on unmeasured only
                    row["v_all_est"] = M._value(name, a)
                    u = a[~a.measured]
                    row["v_unmeas_est"] = M._value(name, u) if len(u) > 200 else np.nan
                    # reweight measured frames to the ball-position distribution of all frames
                    if name in ("height", "line_ball", "width", "flatness"):
                        bx = pd.cut(a.ball_x, [-60, -36, -25, -15, -5, 5, 60]); by = pd.cut(a.ball_y.abs(), [0, 10, 20, 40])
                        key = bx.astype(str) + by.astype(str)
                        tgt = key.value_counts(normalize=True); src = key[a.measured].value_counts(normalize=True)
                        w = (tgt / src).reindex(key[a.measured]).values
                        v = m[name].values; o = np.argsort(v); cw = np.nancumsum(w[o]) / np.nansum(w)
                        row["v_reweight"] = v[o][np.searchsorted(cw, 0.5)]
                for h in (1, 2):
                    mh = m[m.period == h]
                    row[f"h{h}"] = M._value(name, mh) if len(mh) / 10 >= M.MIN_SECONDS else np.nan
                    row[f"h{h}_sec"] = len(mh) / 10
                cells.append(row)
        for blk in ("low_block", "medium_block", "high_block"):
            a = f[f.block == blk]
            for meas, g in a.groupby("measured"):
                sel.append(dict(match_id=mid, team_id=t, block=blk, measured=meas, n=len(g),
                                ball_x=g.ball_x.median(), ball_absy=g.ball_y.abs().median(),
                                ball_x_p10=g.ball_x.quantile(.1), ball_x_p90=g.ball_x.quantile(.9),
                                height=g.height.median(), line_ball=g.line_ball.median(), width=g.width.median(),
                                flat=g.flatness.median()))
    print("ok", mid, flush=True)
pd.DataFrame(cells).to_parquet("/tmp/B_cells.parquet")
pd.DataFrame(sel).to_parquet("/tmp/B_sel.parquet")
