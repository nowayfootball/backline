"""Build the league reference from the provided A-League 24/25 matches.

python -m backline.league  ->  backline/league_reference.csv  (every team-match, whole match)
                               backline/reliability.json      (per metric: first-half vs second-half r, match-to-match
                                                               r within the same team, and on-camera vs estimate gap)
"""
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from . import data, frames, metrics

OUT = Path(__file__).with_name("league_reference.csv")
REL = Path(__file__).with_name("reliability.json")


def one(mid):
    f = frames.back_four(mid)
    rows = []
    for t in f.team_id.unique():
        rows.append(metrics.team_metrics(f, t, n_boot=200).assign(match_id=mid, team_id=t, half=0))
        for h in (1, 2):
            rows.append(metrics.team_metrics(f[f.period == h], t, n_boot=0).assign(match_id=mid, team_id=t, half=h))
        # what you would get by trusting off-camera estimates (every frame counted as measured)
        rows.append(metrics.team_metrics(f.assign(measured=True), t, n_boot=0).assign(match_id=mid, team_id=t, half=-1))
    print("league", mid, flush=True)
    return pd.concat(rows)


def reliability(all_rows: pd.DataFrame) -> dict:
    """Per metric: same-match 1st/2nd-half r, cross-match same-team r, and measured-vs-estimate gap."""
    a = all_rows[(all_rows.metric != "high_block")]
    out = {}
    for (m, b), g in a.groupby(["metric", "block"]):
        k = f"{m}|{b}"
        h = g[(g.half > 0) & g.measurable].pivot_table(index=["match_id", "team_id"], columns="half", values="value").dropna()
        if len(h) >= 8:
            out[k] = dict(r=round(float(np.corrcoef(h[1], h[2])[0, 1]), 2), n=int(len(h)))
        w = g[(g.half == 0) & g.measurable][["match_id", "team_id", "value"]].dropna().reset_index(drop=True)
        cnt = w.groupby("team_id").value.transform("size")
        oth = (w.groupby("team_id").value.transform("sum") - w.value) / (cnt - 1)
        ok = cnt > 1
        if ok.sum() >= 8:
            out.setdefault(k, {}).update(r_cross=round(float(np.corrcoef(w.value[ok], oth[ok])[0, 1]), 2), n_cross=int(ok.sum()))
        e = g[g.half == -1][["match_id", "team_id", "value"]].rename(columns={"value": "est"})
        j = w.merge(e, on=["match_id", "team_id"]).dropna()
        if len(j) >= 8:
            out.setdefault(k, {}).update(gap_median=round(float((j.value - j.est).median()), 2),
                                         r_measured_vs_estimate=round(float(np.corrcoef(j.value, j.est)[0, 1]), 2))
    return out


if __name__ == "__main__":
    with Pool(3) as p:
        allr = pd.concat(p.map(one, data.match_ids()), ignore_index=True)
    allr.to_csv(OUT.with_name("league_all_rows.csv"), index=False)
    allr[allr.half == 0].drop(columns="half").to_csv(OUT, index=False)
    rel = reliability(allr)
    REL.write_text(json.dumps(rel, indent=1))
    print("saved", OUT, REL, rel)
