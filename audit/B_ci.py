"""Audit B(1): phase-bootstrap interval for one team-match — phase counts, concentration, discreteness."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backline import metrics as M

src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bl_1886347.parquet"
team = int(sys.argv[2]) if len(sys.argv) > 2 else 4177
f = M._add_frame_cols(pd.read_parquet(src).query("team_id == @team"))
rng = np.random.default_rng(0)
for name, spec in M.METRICS.items():
    for blk in spec["blocks"]:
        a = f if blk == "all" else f[f.block == blk]
        m = a[a.measured]
        sz = m.groupby("phase_id").size().sort_values(ascending=False)
        groups = [g for _, g in m.groupby("phase_id")]
        bs = np.array([M._value(name, pd.concat([groups[i] for i in rng.integers(0, len(groups), len(groups))])) for _ in range(400)])
        lo, hi = np.nanquantile(bs, [.05, .95])
        # frame-iid bootstrap for comparison (ignores dependence)
        bi = np.array([M._value(name, m.sample(len(m), replace=True, random_state=k)) for k in range(200)])
        # contiguous-frame resolution: how many distinct values near the median?
        print(f"{name:9s} {blk:12s} sec={len(m)/10:5.0f} phases={len(sz):3d} top1={sz.iloc[0]/len(m):.0%} top3={sz.iloc[:3].sum()/len(m):.0%} "
              f"val={M._value(name, m):.2f} CI=[{lo:.2f},{hi:.2f}] w={hi-lo:.2f} uniq_boot={len(np.unique(np.round(bs,4)))} iidCIw={np.subtract(*np.nanquantile(bi,[.95,.05])):.2f}")
