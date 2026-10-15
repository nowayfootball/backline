"""Independent re-implementation of backline metrics for one match (audit A)."""
import json, sys
import numpy as np, pandas as pd
D = '<data>/matches'
mid = int(sys.argv[1]) if len(sys.argv) > 1 else 1886347
INCL_END = '--incl' in sys.argv
B = ['low_block', 'medium_block', 'high_block']
m = json.load(open(f'{D}/{mid}/{mid}_match.json'))
home, away = m['home_team']['id'], m['away_team']['id']
pteam = {p['id']: p['team_id'] for p in m['players']}
isgk = {p['id']: p['player_role']['acronym'] == 'GK' for p in m['players']}
ph = pd.read_csv(f'{D}/{mid}/{mid}_phases_of_play.csv')
ph = ph[ph.team_out_of_possession_phase_type.isin(B)]
fr = {}  # frame -> (phase idx, block, def team)
for r in ph.itertuples():
    dt = away if r.team_in_possession_id == home else home
    end = r.frame_end + (1 if INCL_END else 0)
    for f in range(r.frame_start, end):
        fr[f] = (r.index, r.team_out_of_possession_phase_type, dt)
rows = []; pos = {}  # pos[frame][pid] = (x, det)
with open(f'{D}/{mid}/{mid}_tracking_extrapolated.jsonl') as fh:
    for line in fh:
        d = json.loads(line); f = d['frame']
        if d['period'] is None: continue
        need = f in fr or (f - 5) in fr
        if not need: continue
        side = m['home_team_side'][d['period'] - 1]
        pos[f] = {}
        for t in (home, away):
            pass
        for p in d['player_data']:
            t = pteam.get(p['player_id'])
            home_ltr = side == 'left_to_right'
            team_ltr = home_ltr if t == home else not home_ltr
            s = 1 if team_ltr else -1
            pos[f][p['player_id']] = (s * p['x'], s * p['y'], p['is_detected'], t, d['period'])
        if f in fr:
            pi, blk, dt = fr[f]
            s = 1 if ((side == 'left_to_right') == (dt == home)) else -1
            bx, by = d['ball_data']['x'], d['ball_data']['y']
            rows.append(dict(frame=f, period=d['period'], phase=pi, block=blk, team=dt,
                             bx=None if bx is None else s * bx, by=None if by is None else s * by,
                             bdet=d['ball_data']['is_detected']))
# back four
out = []
for r in rows:
    f = r['frame']; P = [(pid, *v) for pid, v in pos[f].items() if v[3] == r['team'] and not isgk.get(pid, False)]
    if len(P) < 4: continue
    P.sort(key=lambda z: z[1]); b4 = P[:4]
    r = dict(r); r['ids'] = [z[0] for z in b4]; r['x'] = np.array([z[1] for z in b4]); r['y'] = np.array([z[2] for z in b4])
    r['meas'] = all(z[3] for z in b4); r['n_out'] = len(P)
    # lockstep (variant: t+5 same players, any detection; strict: same phase & detected)
    g = pos.get(f + 5, {})
    if all(i in g for i in r['ids']) and g[r['ids'][0]][4] == r['period']:
        x2 = np.array([g[i][0] for i in r['ids']]); r['v'] = (x2 - r['x']) / 0.5
        r['v_samephase'] = fr.get(f + 5, (None,))[0] == r['phase']
        r['v_det'] = all(g[i][2] for i in r['ids'])
    else: r['v'] = None
    out.append(r)
df = pd.DataFrame(out)
def report(team):
    t = df[df.team == team]; M = t[t.meas]
    print(f'== team {team} frames={len(t)} measured={len(M)} outfield n range {t.n_out.min()}-{t.n_out.max()}')
    for blk in B:
        s = M[M.block == blk]; sec = len(s) / 10
        tot = (t.block == blk).sum() / 10
        if sec < 60: print(f'  {blk}: {tot:.0f}s, measured {sec:.0f}s -> not measurable'); continue
        h = np.median([x.mean() + 52.5 for x in s.x])
        sb = s[s.bx.notna()]
        lb = np.median([bx - x.mean() for bx, x in zip(sb.bx, sb.x)])
        fl = np.median([x.std() for x in s.x]); w = np.median([y.max() - y.min() for y in s.y])
        print(f'  {blk}: {tot:.0f}s meas {sec:.0f}s height={h:.3f} line_ball={lb:.3f} flat={fl:.4f} width={w:.3f}  ballx med={np.median(sb.bx):.1f}')
    sb = M[M.bx.notna()]
    cy = np.array([y.mean() for y in sb.y]); print(f'  shift={np.polyfit(sb.by.astype(float), cy, 1)[0]:.4f} (n={len(sb)})')
    V = M[M.v.notna()]
    for name, sel in [('any', V), ('samephase', V[V.v_samephase]), ('det', V[V.v_det]), ('samephase+det', V[V.v_samephase & V.v_det])]:
        sd = [v.std() for v in sel.v if abs(v.mean()) > 1]
        print(f'  lockstep[{name}]={np.median(sd):.4f} n={len(sd)}')
    return t
for team in (home, away): report(team)
df.to_pickle(f'/tmp/audit_A_df_{mid}{"_incl" if INCL_END else ""}.pkl')
