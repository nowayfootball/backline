"""Audit B: summarise /tmp/B_cells.parquet and /tmp/B_sel.parquet."""
import json
from pathlib import Path
import numpy as np, pandas as pd
c = pd.read_parquet("/tmp/B_cells.parquet"); s = pd.read_parquet("/tmp/B_sel.parquet")
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
ok = c.dropna(subset=["value"])
print("== (1) phases per measurable cell, CI calibration via random phase split  z=(A-B)/(2*se) should have sd~1")
g = ok.groupby(["metric", "block"])
print(pd.DataFrame(dict(n=g.size(), nph_min=g.nph.min(), nph_med=g.nph.median(), sec_min=g.sec.min(),
      sd_z_split=g.apply(lambda d: ((d.rA - d.rB) / (2 * d.se)).std()),
      sd_z_half=g.apply(lambda d: ((d.h1 - d.h2) / (2 * d.se)).std()),
      ci_w_med=g.apply(lambda d: (d.hi - d.lo).median()))).round(2))
print("\n== (2) grey spread vs noise: reliability-like share = 1 - mean(se^2)/var(value); value~sec corr")
print(pd.DataFrame(dict(sd_vals=g.value.std(), rms_se=g.se.apply(lambda x: np.sqrt((x**2).mean())),
      signal_share=g.apply(lambda d: 1 - (d.se**2).mean() / d.value.var()),
      r_val_sec=g.apply(lambda d: np.corrcoef(d.value, d.sec)[0, 1]),
      r_val_cov=g.apply(lambda d: np.corrcoef(d.value, d.sec / d.sec_all)[0, 1]),
      sec_range=g.sec.apply(lambda x: f"{x.min():.0f}-{x.max():.0f}"))).round(2))
print("\n== (3) first vs second half, both >=60s")
for (m, b), d in c.groupby(["metric", "block"]):
    d = d.dropna(subset=["h1", "h2"])
    if len(d) >= 3:
        r = np.corrcoef(d.h1, d.h2)[0, 1]
        # bootstrap over team-matches
        rs = [np.corrcoef(*d.sample(len(d), replace=True, random_state=k)[["h1", "h2"]].values.T)[0, 1] for k in range(1000)]
        # Spearman-Brown to full match, and team-level (same team across matches) check
        print(f"{m:9s} {b:12s} n={len(d):2d}/{len(c[(c.metric==m)&(c.block==b)])} r={r:.2f} 95%[{np.nanquantile(rs,.025):.2f},{np.nanquantile(rs,.975):.2f}] SB_full={2*r/(1+r):.2f} medsec_half={d[['h1_sec','h2_sec']].stack().median():.0f}")
print("\n   between-match same-team consistency (ICC-ish: corr of a team's value in one match vs its mean in other matches)")
for (m, b), d in ok.groupby(["metric", "block"]):
    xs, ys = [], []
    for _, r in d.iterrows():
        o = d[(d.team_id == r.team_id) & (d.match_id != r.match_id)]
        if len(o):
            xs.append(r.value); ys.append(o.value.mean())
    print(f"{m:9s} {b:12s} n={len(xs):2d} r={np.corrcoef(xs, ys)[0,1]:.2f} teams={d.team_id.nunique()}")
print("\n== (4) selection: measured vs unmeasured frames (median over team-matches)")
p = s.pivot_table(index=["match_id", "team_id", "block"], columns="measured", values=["ball_x", "ball_absy", "height", "line_ball", "width", "flat", "n"])
for blk in ("low_block", "medium_block", "high_block"):
    q = p.xs(blk, level="block")
    cov = (q["n"][True] / (q["n"][True] + q["n"][False])).median()
    print(blk, f"coverage_med={cov:.2f}", {k: f"meas {q[k][True].median():.1f} / unmeas {q[k][False].median():.1f} (diff med {(q[k][True]-q[k][False]).median():+.1f})" for k in ["ball_x", "ball_absy", "height", "line_ball", "width", "flat"]})
print("\n   measured-only value vs (a) all frames incl. estimates, (b) ball-position-reweighted measured")
for (m, b), d in ok[ok.metric.isin(["height", "line_ball", "width", "flatness"])].groupby(["metric", "block"]):
    print(f"{m:9s} {b:12s} meas-allest med {(d.value-d.v_all_est).median():+.2f} [IQR {(d.value-d.v_all_est).quantile(.25):+.2f},{(d.value-d.v_all_est).quantile(.75):+.2f}]  "
          f"meas-unmeas_est {(d.value-d.v_unmeas_est).median():+.2f}  meas-reweight {(d.value-d.v_reweight).median():+.2f}  rms_se {np.sqrt((d.se**2).mean()):.2f}  "
          f"corr(meas, allest)={np.corrcoef(d.value, d.v_all_est)[0,1]:.2f}")
print("\n== (5) high block")
hb = s[s.block == "high_block"].groupby(["match_id", "team_id"]).apply(lambda d: pd.Series(dict(tot=d.n.sum() / 10, meas=d[d.measured].n.sum() / 10)))
print(hb.describe().round(1)); print("cells >=60s measured:", (hb.meas >= 60).sum(), "of", len(hb), " pooled coverage", round(hb.meas.sum() / hb.tot.sum(), 3))
rel = Path(__file__).resolve().parents[1] / "backline" / "reliability.json"
print("\nreliability.json:", rel.read_text() if rel.exists() else "absent")
lr = pd.read_csv(Path(__file__).resolve().parents[1] / "backline" / "league_reference.csv")
x = lr[(lr.match_id == 1886347) & (lr.team_id == 4177)][["metric", "block", "value", "seconds_measured"]]
print("league_ref row for 1886347/4177 (target included in grey):\n", x.merge(ok[(ok.match_id == 1886347) & (ok.team_id == 4177)][["metric", "block", "value"]], on=["metric", "block"], suffixes=("_ref", "_now")))
