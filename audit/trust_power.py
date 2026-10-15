"""Power of trust's match-to-match test on the real design (which teams played in which of the 20 matches).

Values = team effect (variance ICC) + noise (variance 1 - ICC); share of simulations with permutation p < .05.
python audit/trust_power.py  (needs the match metadata; downloads matches.json + match.json files only)
"""
import numpy as np
import pandas as pd

from backline import data, trust


def design():
    rows = []
    for mid in data.match_ids():
        m = data.meta(mid) if (data.data_dir() / str(mid) / f"{mid}_match.json").exists() else None
        if m is None:
            data._fetch(f"{data.RAW}/matches/{mid}/{mid}_match.json", data.data_dir() / str(mid) / f"{mid}_match.json")
            m = data.meta(mid)
        rows += [dict(match_id=mid, team_id=m["home_team"]["id"]), dict(match_id=mid, team_id=m["away_team"]["id"])]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    d = design()
    teams = d.team_id.unique()
    print("team-matches", len(d), "teams", len(teams), "matches per team", d.team_id.value_counts().sort_values().tolist())
    rng = np.random.default_rng(7)
    for icc in (0.0, 0.2, 0.4, 0.6):
        hits = []
        for _ in range(200):
            eff = dict(zip(teams, rng.normal(0, np.sqrt(icc), len(teams))))
            v = d.assign(seen=d.team_id.map(eff) + rng.normal(0, np.sqrt(1 - icc), len(d)))
            r, n, p = trust._cross_r(v, rng, n_perm=400)
            hits.append(p < 0.05)
        print(f"ICC {icc:.1f}: share p<.05 = {np.mean(hits):.2f}")
