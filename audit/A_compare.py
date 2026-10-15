"""Compare audit A reimplementation frames with original backline.frames.back_four."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '<repo>')
from backline import frames, metrics
mid = 1886347
import os
o = pd.read_pickle('/tmp/audit_A_orig.pkl') if os.path.exists('/tmp/audit_A_orig.pkl') else frames.back_four(mid); o.to_pickle('/tmp/audit_A_orig.pkl')
a = pd.read_pickle(f'/tmp/audit_A_df_{mid}_incl.pkl')
k = ['frame', 'team']
print('orig rows', len(o), 'mine rows', len(a))
mo = o.set_index(['frame', 'team_id']); ma = a.set_index(['frame', 'team'])
print('only orig', len(mo.index.difference(ma.index)), 'only mine', len(ma.index.difference(mo.index)))
j = mo.join(ma[['meas', 'x', 'bx', 'phase']].join(ma[['block']].rename(columns={'block': 'blk_a'})), how='inner')
print('measured mismatch', (j.measured != j.meas).sum(), 'block mismatch', (j.block != j.blk_a).sum())
print('x0 diff max', np.nanmax(np.abs(j.x0 - np.array([x[0] for x in j.x]))))
print('ball diff max', np.nanmax(np.abs(j.ball_x - j.bx.astype(float))))
# lockstep variants from original frames
for t in (4177, 1805):
    f = metrics._add_frame_cols(o[o.team_id == t]); m = f[f.measured]
    g = m[np.abs(m.v_mean) > 1].dropna(subset=['v_sd'])
    # cross-phase / cross-block contamination
    nxt = o.set_index(['team_id', 'frame'])[['phase_id', 'block']]
    idx = list(zip([t] * len(g), g.frame + 5))
    ph5 = nxt.reindex(idx)
    same_ph = ph5.phase_id.values == g.phase_id.values
    same_blk = ph5.block.values == g.block.values
    print(t, 'lockstep orig', g.v_sd.median(), 'n', len(g), 'cross-phase', (~same_ph).sum(), 'cross-block', (~same_blk).sum(),
          'samephase-only', g[same_ph].v_sd.median())
    # back-four membership change between t and t+5: ids at t+5 equal?
    print(' phases', m.phase_id.nunique(), 'median frames/phase', m.groupby('phase_id').size().median())
