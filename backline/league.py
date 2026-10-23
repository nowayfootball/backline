"""Build the league reference from the provided A-League 24/25 matches.

python -m backline.league [--out DIR]  ->  DIR/league_reference.csv  (every team-match, whole match)
                                          DIR/reliability.json      (per metric: first-half vs second-half r and
                                                                     match-to-match r within the same team)
DIR defaults to ./league. Point BACKLINE_LEAGUE at DIR to make reports use it instead of the packaged A-League files.
The on-camera vs off-camera comparison lives in backline.trust.
"""
import argparse
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from . import data, frames, metrics

OUT = data.league_dir() / "league_reference.csv"        # read by reports
REL = data.league_dir() / "reliability.json"


def one(mid):
    f = frames.back_four(mid)
    rows = []
    for t in f.team_id.unique():
        rows.append(metrics.team_metrics(f, t, n_boot=200).assign(match_id=mid, team_id=t, half=0))
        for h in (1, 2):
            rows.append(metrics.team_metrics(f[f.period == h], t, n_boot=0).assign(match_id=mid, team_id=t, half=h))
    print("league", mid, flush=True)
    return pd.concat(rows)


def reliability(all_rows: pd.DataFrame) -> dict:
    """Per metric: same-match 1st/2nd-half r and cross-match same-team r."""
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
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Rebuild the league reference from the matches in BACKLINE_DATA")
    ap.add_argument("--out", default="league")
    out = Path(ap.parse_args().out); out.mkdir(parents=True, exist_ok=True)
    with Pool(3) as p:
        allr = pd.concat(p.map(one, data.match_ids()), ignore_index=True)
    allr[allr.half == 0].drop(columns="half").to_csv(out / "league_reference.csv", index=False)
    rel = reliability(allr)
    if not rel:
        print("note: reliability.json is empty - first/second-half and match-to-match r need at least 8 team-matches "
              "with a value (and, across matches, teams with 2+ matches)")
    (out / "reliability.json").write_text(json.dumps(rel, indent=1))
    print("saved", out / "league_reference.csv", out / "reliability.json")
    print(f"use it: BACKLINE_LEAGUE={out} python -m backline MATCH_ID")
