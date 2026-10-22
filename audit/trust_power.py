"""Power of trust's match-to-match test at the team-matches that were actually measurable, per metric and block.

Values = team effect (variance ICC) + noise (variance 1 - ICC) on the real design (which teams have a value);
share of 1,000 simulations with permutation p < .05. Also the full design (all 40 team-matches) for reference.
python audit/trust_power.py  (uses the frame cache built by `python -m backline.trust`; ~20 min on 3 cores)
"""
from multiprocessing import Pool

import numpy as np
import pandas as pd

from backline import data, trust

ICCS = (0.0, 0.2, 0.4, 0.6)
RUNS, PERM = 1000, 500


def power(design: pd.DataFrame, rng) -> dict:
    teams = design.team_id.unique()
    out = {}
    for icc in ICCS:
        hits = 0
        for _ in range(RUNS):
            eff = dict(zip(teams, rng.normal(0, np.sqrt(icc), len(teams))))
            v = design.assign(seen=design.team_id.map(eff) + rng.normal(0, np.sqrt(1 - icc), len(design)))
            r, n, p = trust._cross_r(v, rng, n_perm=PERM)
            hits += bool(p < 0.05)
        out[f"power_icc{icc}"] = hits / RUNS
    return out


def _job(args):
    seed, metric, block, design = args
    out = dict(metric=metric, block=block, team_matches=len(design), teams=design.team_id.nunique(),
               **power(design, np.random.default_rng(seed)))
    print(out, flush=True)
    return out


if __name__ == "__main__":
    jobs = []
    for name, (uses, fn) in trust.METRICS.items():
        v = trust.team_values(fn, uses, blocks=("low_block", "medium_block"))
        for blk, g in v.groupby("block"):
            jobs.append((len(jobs), name, blk, g.dropna(subset=["seen"])[["match_id", "team_id"]]))
    jobs.append((len(jobs), "all 40 team-matches", "-", v[v.block == "low_block"][["match_id", "team_id"]]))
    with Pool(3) as p:
        rows = p.map(_job, jobs)
    pd.DataFrame(rows).to_csv("trust_power.csv", index=False)
