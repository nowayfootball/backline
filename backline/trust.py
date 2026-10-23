"""Can I trust this defensive metric from broadcast tracking?

`check(metric, uses)` runs any team-level defensive metric over the matches and reports:
- coverage: share of organised-defence time in which every player the metric needs is on camera;
- on-camera vs off-camera: the metric on moments when every needed player is on camera vs on moments when at
  least one is off camera (estimated). The difference mixes which moments the camera shows with estimation error;
  unlike a comparison with "all moments" it does not shrink as coverage rises. Median and largest difference,
  and whether team-matches keep their order (Spearman rho);
- same ball position: the on- vs off-camera difference again, but only between moments with the ball in the same
  place (5 m along × three bands across), so the part due to which moments the camera shows is taken out. What is
  left mixes estimation error with players being off camera because of where they stand;
- within-match repeatability: first half vs second half (Pearson r);
- across-match repeatability: this match vs the same team's other matches (Pearson r, with a permutation p
  from shuffling team labels; this null ignores match and opponent structure). With ~3 matches per team only
  strong team effects are detectable (audit/trust_power.py), so a non-significant r is not evidence of no trait.

Notes: ranks are depth order, so x0..x3 are the four deepest outfield players, not necessarily defenders (a back
five loses a wing-back). Frames with fewer than 8 outfield players are skipped, and a metric needing ranks that
are missing (e.g. after a red card) skips those frames. Each value needs MIN_SECONDS of play per team-match.
`procs > 1` needs a picklable metric (a module-level function, not a lambda).

A metric is a function DataFrame -> float, computed on the frames of one team in one match (and block).
Frames come from `frames.team_frames`: x0..x9 / y0..y9 are the defending outfield players ordered by depth
(x0 deepest, defending team attacks +x, own goal at x = -52.5); d0..d9 say whether each was on camera.
`uses` lists the depth ranks the metric needs (e.g. range(4) for the back four).

Columns returned by `check` (one row per block):
    coverage                      share of time with every needed player on camera
    team_matches(_measurable)     team-matches in the block / with 60 s on camera
    gap_median, gap_ci_lo/hi      on- minus off-camera value, median over team-matches, 95% interval (resampling teams)
    gap_max_abs                   largest absolute on/off difference for one team-match
    matched_gap_median, _ci_lo/hi the same at the same ball position; team_matches_matched = how many had enough time
    rank_rho                      Spearman correlation of on-camera and off-camera values across team-matches
    r_halves, n_halves            first half vs second half
    r_cross, n_cross, p_cross     this match vs the same team's other matches, permutation p (no interval: team-matches
                                  repeat teams, so they are not independent); `python -m backline.trust` adds q_cross
                                  (Benjamini-Hochberg over the low- and mid-block tests)

    python -m backline.trust            # the built-in metric set, all provided matches -> trust_table.csv
"""
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data, frames

FPS = 10
MIN_SECONDS = 60
BLOCKS = ("low_block", "medium_block", "high_block")


@lru_cache(maxsize=None)
def _frames(mid: int) -> pd.DataFrame:
    """Team frames for one match: downloaded on first use, then cached as a pickle (no extra dependencies)."""
    cache = data.data_dir() / "_cache" / f"team_frames_{mid}.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    data.download([mid], verbose=False)
    f = frames.team_frames(mid)
    cache.parent.mkdir(parents=True, exist_ok=True)
    f.to_pickle(cache)
    return f


def _X(df, ranks):
    return df[[f"x{i}" for i in ranks]].values


def _Y(df, ranks):
    return df[[f"y{i}" for i in ranks]].values


# ---- built-in metrics (definitions fixed before results were looked at; see docs/trust_metrics.md) ----
METRICS = {
    "back-line height (m from goal)": (range(4), lambda d: np.median(_X(d, range(4)).mean(1)) + 52.5),
    "back-line width (m)":            (range(4), lambda d: np.median(np.ptp(_Y(d, range(4)), 1))),
    "back-line spread (m)":           (range(4), lambda d: np.median(_X(d, range(4)).std(1))),
    "ball in front of back line (m)": (range(4), lambda d: np.nanmedian(d.ball_x.values - _X(d, range(4)).mean(1))),
    "defence-midfield gap (m)":       (range(8), lambda d: np.median(_X(d, range(4, 8)).mean(1) - _X(d, range(4)).mean(1))),
    "team length (m)":                (range(10), lambda d: np.median(_X(d, [9]).ravel() - _X(d, [0]).ravel())),
    "team width (m)":                 (range(10), lambda d: np.median(np.ptp(_Y(d, range(10)), 1))),
}


def _team_values(args):
    mid, metric, uses, blocks = args
    return _values(_frames(mid), mid, metric, uses, blocks)


def _values(f: pd.DataFrame, mid, metric, uses, blocks):
    need = [f"d{i}" for i in uses]
    seen = f[need].all(axis=1) & f[[f"x{i}" for i in uses]].notna().all(axis=1)
    out = []
    for (team, blk), g in f[f.block.isin(blocks)].groupby(["team_id", "block"]):
        m = g[seen.loc[g.index]]
        full = g[g[[f"x{i}" for i in uses]].notna().all(axis=1)]
        row = dict(match_id=mid, team_id=team, block=blk, seconds=len(full) / FPS, seconds_seen=len(m) / FPS)
        ok = lambda d: len(d) / FPS >= MIN_SECONDS
        off = full[~seen.loc[full.index]]
        row["seconds_off"] = len(off) / FPS
        row["seen"] = metric(m) if ok(m) else np.nan
        row["off"] = metric(off) if ok(off) else np.nan
        row["matched"], row["seconds_matched"] = _matched(metric, m, off)
        for h in (1, 2):
            mh = m[m.period == h]
            row[f"half{h}"] = metric(mh) if ok(mh) else np.nan
        out.append(row)
    return out


CELL_SECONDS = 5


def _ball_cell(d: pd.DataFrame) -> pd.Series:
    """Ball position cell: 5 m along the pitch x three bands across (|y| <= 11 m, left, right)."""
    band = np.select([d.ball_y > 11, d.ball_y < -11], [1, -1], 0)
    return pd.Series(np.floor(d.ball_x.values / 5).astype("int64") * 3 + band, index=d.index)


def _matched(metric, seen: pd.DataFrame, off: pd.DataFrame):
    """On- minus off-camera value between moments with the ball in the same cell, weighted by on-camera time."""
    seen, off = seen.dropna(subset=["ball_x", "ball_y"]), off.dropna(subset=["ball_x", "ball_y"])
    if not len(seen) or not len(off):
        return np.nan, 0.0
    cs, co = _ball_cell(seen), _ball_cell(off)
    diffs, w = [], []
    for c, g in seen.groupby(cs):
        o = off[co == c]
        if len(g) / FPS >= CELL_SECONDS and len(o) / FPS >= CELL_SECONDS:
            diffs.append(metric(g) - metric(o))
            w.append(len(g))
    secs = sum(w) / FPS
    if secs < MIN_SECONDS:
        return np.nan, secs
    return float(np.average(diffs, weights=w)), secs


FRAME_COLUMNS = (["match_id", "team_id", "block", "period", "ball_x", "ball_y"]
                 + [f"{c}{i}" for c in "xyd" for i in range(10)])


def team_values(metric, uses, matches=None, blocks=BLOCKS, procs=1, frames=None) -> pd.DataFrame:
    """Per team-match and block: on-camera value, off-camera value, half values, seconds.

    `frames`: your own frames instead of the SkillCorner matches (any provider, e.g. built from a kloppy dataset):
    one row per frame (10 fps) of a defending team, with FRAME_COLUMNS - x/y in metres with the defending team
    attacking +x, players ordered by depth (x0 deepest), d0..d9 True when on camera, block one of BLOCKS."""
    if frames is not None:
        missing = [c for c in FRAME_COLUMNS if c not in frames.columns]
        if missing:
            raise ValueError(f"frames is missing columns: {missing}")
        rows = [_values(g, mid, metric, tuple(uses), tuple(blocks)) for mid, g in frames.groupby("match_id")]
        return pd.DataFrame([r for rr in rows for r in rr])
    mids = matches or data.match_ids()
    jobs = [(m, metric, tuple(uses), tuple(blocks)) for m in mids]
    if procs > 1:
        with Pool(procs) as p:
            rows = p.map(_team_values, jobs)
    else:
        rows = [_team_values(j) for j in jobs]
    return pd.DataFrame([r for rr in rows for r in rr])


def _cross_r(v: pd.DataFrame, rng, n_perm=2000):
    """This match vs mean of the same team's other matches; permutation p by shuffling team labels, (k+1)/(n+1)."""
    v = v.dropna(subset=["seen"]).reset_index(drop=True)
    x = v.seen.values.astype(float)
    codes = pd.factorize(v.team_id)[0]
    def stat(c):
        cnt = np.bincount(c)[c]
        ok = cnt > 1
        if ok.sum() < 8:
            return np.nan, int(ok.sum())
        oth = (np.bincount(c, weights=x)[c] - x)[ok] / (cnt[ok] - 1)
        return np.corrcoef(x[ok], oth)[0, 1], int(ok.sum())
    r, n = stat(codes)
    if np.isnan(r):
        return r, n, np.nan
    null = np.array([stat(rng.permutation(codes))[0] for _ in range(n_perm)])
    return r, n, float(((np.abs(null) >= abs(r)).sum() + 1) / (n_perm + 1))


def _team_boot(d: pd.Series, teams: pd.Series, rng, n_boot=2000):
    """95% interval of the median difference, resampling teams."""
    d, teams = d.values, teams.values
    if len(d) < 8:
        return np.nan, np.nan
    groups = [d[teams == t] for t in np.unique(teams)]
    meds = [np.median(np.concatenate([groups[k] for k in rng.integers(0, len(groups), len(groups))]))
            for _ in range(n_boot)]
    return tuple(float(q) for q in np.percentile(meds, [2.5, 97.5]))


def summarise(v: pd.DataFrame, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = []
    for blk, g in v.groupby("block"):
        both = g.dropna(subset=["seen", "off"])
        mt = g.dropna(subset=["matched"])
        halves = g.dropna(subset=["half1", "half2"])
        r_cross, n_cross, p_cross = _cross_r(g, rng)
        gap = both.seen - both.off
        out.append(dict(
            block=blk,
            coverage=g.seconds_seen.sum() / g.seconds.sum() if g.seconds.sum() else 0.0,
            team_matches_measurable=int(g.seen.notna().sum()), team_matches=len(g),
            team_matches_compared=len(both),
            gap_median=float(gap.median()) if len(both) else np.nan,
            gap_ci=_team_boot(gap, both.team_id, rng),
            gap_max_abs=float(gap.abs().max()) if len(both) else np.nan,
            matched_gap_median=float(mt.matched.median()) if len(mt) else np.nan,
            matched_gap_ci=_team_boot(mt.matched, mt.team_id, rng),
            team_matches_matched=len(mt),
            rank_rho=float(both.seen.rank().corr(both.off.rank())) if len(both) >= 8 else np.nan,
            r_halves=float(np.corrcoef(halves.half1, halves.half2)[0, 1]) if len(halves) >= 8 else np.nan,
            n_halves=len(halves), r_cross=r_cross, n_cross=n_cross,
            p_cross=p_cross))
    t = pd.DataFrame(out)
    for c in ("gap_ci", "matched_gap_ci"):
        t[[c + "_lo", c + "_hi"]] = pd.DataFrame(t.pop(c).tolist(), index=t.index)
    return t


def bh_q(p: pd.Series) -> pd.Series:
    """Benjamini-Hochberg q values (NaN kept)."""
    ok = p.dropna().sort_values()
    m = len(ok)
    q = (ok * m / np.arange(1, m + 1))[::-1].cummin()[::-1].clip(upper=1)
    return q.reindex(p.index)


def check(metric, uses, matches=None, blocks=BLOCKS, procs=1, frames=None) -> pd.DataFrame:
    """Trust report for one metric: one row per block. Pass `frames` to check your own data (see team_values)."""
    return summarise(team_values(metric, uses, matches, blocks, procs, frames))


if __name__ == "__main__":
    import sys
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    with Pool(procs) as p:                                  # warm the frame cache in parallel
        p.map(_frames, data.match_ids())
    tables = []
    for name, (uses, fn) in METRICS.items():
        t = check(fn, uses).assign(metric=name, players_needed=len(list(uses)))
        print(t.round(2).to_string(index=False), flush=True)
        tables.append(t)
    res = pd.concat(tables, ignore_index=True)
    res["q_cross"] = bh_q(res.p_cross.where(res.block != "high_block"))
    res.to_csv("trust_table.csv", index=False)
    print("saved trust_table.csv")
