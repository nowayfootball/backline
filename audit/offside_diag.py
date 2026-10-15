import numpy as np, pandas as pd
from multiprocessing import Pool
from backline import data
v=pd.read_parquet('<data>/offside_validation.parquet')
def one(mid):
    m=data.meta(mid); team,gk,home,side=data.roster(m)
    vv=v[v.match_id==mid]
    want={int(f)+s for f in vv.frame for s in range(-30,11)}
    S={}
    for fr in data.tracking(mid,want):
        b=fr.get('ball_data') or {}
        S[fr['frame']]=(fr['period'],b.get('x'),b.get('y'),{q['player_id']:(q['x'],q['y'],q['is_detected']) for q in fr['player_data']})
    out=[]
    for r in vv.itertuples():
        best=None; rows={}
        for s in range(-30,11):
            sn=S.get(r.frame+s)
            if not sn or sn[1] is None: continue
            per,bx,by,pl=sn; sg=1 if ((side[per]=='left_to_right')==(r.defending_team==home)) else -1
            D=sorted(sg*x for pid,(x,y,d) in pl.items() if team.get(pid)==r.defending_team)
            A=[sg*x for pid,(x,y,d) in pl.items() if team.get(pid)==r.attacking_team]
            line=min(D[1],sg*bx,0.0)
            rows[s]=dict(adv=min(A)-line, bx=sg*bx)
        if 0 not in rows: continue
        # release frame: largest ball displacement over 0.3s within window before/at frame_end
        bxs={s:rows[s]['bx'] for s in rows}
        sp={s:abs(bxs.get(s+3,np.nan)-bxs[s]) for s in bxs if s+3 in bxs}
        rel=max(sp,key=sp.get) if sp else 0
        out.append(dict(match_id=mid,event_id=r.event_id,outcome=r.outcome,adv0=rows[0]['adv'],rel=rel,adv_rel=rows.get(rel,{}).get('adv',np.nan),min_w10=min(rows[k]['adv'] for k in rows if -10<=k<=2),min_w30=min(rows[k]['adv'] for k in rows if -30<=k<=5)))
    return pd.DataFrame(out)
if __name__=='__main__':
    with Pool(3) as p: o=pd.concat(p.map(one,sorted(v.match_id.unique())))
    o.to_parquet('/tmp/offdiag.parquet')
    for c in ['adv0','adv_rel','min_w10','min_w30']:
        print(c, o.groupby('outcome')[c].quantile([.1,.25,.5,.75]).unstack().round(2))
    print('share any attacker offside (<-0.5m):', o.assign(a=o.min_w30<-0.5).groupby('outcome').a.mean().round(2).to_dict()); print('release offset (frames) quantiles', o.rel.quantile([.1,.25,.5,.75,.9]).to_dict())
