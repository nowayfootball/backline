"""Back-line metrics for one team in one match, each with coverage and uncertainty.

Every metric is computed only on measured frames (all four back-line players detected).
A metric is reported as "not measurable" when it has less than MIN_SECONDS of measured play.
Uncertainty: 90% interval from resampling whole defensive phases (frames inside a phase are not independent).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

MIN_SECONDS = 60
FPS = 10
N_BOOT = 400

METRICS = {
    "height":    dict(blocks=("low_block", "medium_block"), unit="m"),
    # mid-block ball distance dropped: measured frames there are biased towards the ball being near the line
    # (measured vs estimate-inclusive values differ by ~9 m and reorder teams, audit/B_*.py)
    "line_ball": dict(blocks=("low_block",), unit="m"),
    "flatness":  dict(blocks=("low_block", "medium_block"), unit="m"),
    "width":     dict(blocks=("low_block", "medium_block"), unit="m"),
    "shift":     dict(blocks=("all",), unit=""),
    "lockstep":  dict(blocks=("all",), unit="m/s"),
}
# first-half vs second-half correlation across A-League 24/25 team-matches, written by `python -m backline.league`
from .data import league_dir
_REL = league_dir() / "reliability.json"
RELIABILITY = json.loads(_REL.read_text()) if _REL.exists() else {}


def _add_frame_cols(f: pd.DataFrame) -> pd.DataFrame:
    X = f[[f"x{i}" for i in range(4)]].values
    Y = f[[f"y{i}" for i in range(4)]].values
    V = (f[[f"x{i}_p5" for i in range(4)]].values - X) / 0.5
    return f.assign(height=X.mean(1) + 52.5,                 # metres from own goal line
                    line_ball=f.ball_x.values - X.mean(1),   # ball distance in front of the line
                    flatness=X.std(1),                        # how far the four are from one straight line
                    width=Y.max(1) - Y.min(1),
                    cy=Y.mean(1),
                    v_mean=V.mean(1), v_sd=V.std(1))


def _value(name: str, f: pd.DataFrame) -> float:
    if name == "shift":                                       # line centre y per metre of ball y
        g = f.dropna(subset=["ball_y"])
        return np.polyfit(g.ball_y, g.cy, 1)[0] if len(g) > 50 else np.nan
    if name == "lockstep":                                    # spread of the four players' x-velocity while the line moves
        g = f[np.abs(f.v_mean) > 1].dropna(subset=["v_sd"])
        return g.v_sd.median() if len(g) > 20 else np.nan
    return f[name].median()


def team_metrics(frames: pd.DataFrame, team_id: int, seed: int = 0, n_boot: int = N_BOOT) -> pd.DataFrame:
    """One row per metric and block for `team_id`: value on measured frames (all four on camera), seconds measured,
    90% interval from resampling defensive phases, and the league first-half/second-half and match-to-match r."""
    f = _add_frame_cols(frames[frames.team_id == team_id])
    rng = np.random.default_rng(seed)
    out = []
    for name, spec in METRICS.items():
        for blk in spec["blocks"]:
            allf = f[f.block.isin(("low_block", "medium_block"))] if blk == "all" else f[f.block == blk]
            m = allf[allf.measured]
            total_s, meas_s = len(allf) / FPS, len(m) / FPS
            rel = RELIABILITY.get(f"{name}|{blk}", {})
            row = dict(metric=name, block=blk, unit=spec["unit"], reliability=rel.get("r", np.nan), reliability_n=rel.get("n", 0),
                       reliability_cross=rel.get("r_cross", np.nan), reliability_n_cross=rel.get("n_cross", 0),
                       seconds_in_block=round(total_s), seconds_measured=round(meas_s),
                       coverage=meas_s / total_s if total_s else 0.0, value=np.nan, lo=np.nan, hi=np.nan,
                       measurable=meas_s >= MIN_SECONDS, n_phases=int(m.phase_id.nunique()))
            if row["measurable"]:
                row["value"] = _value(name, m)
            if row["measurable"] and n_boot:
                groups = [g for _, g in m.groupby("phase_id")]
                bs = [_value(name, pd.concat([groups[i] for i in rng.integers(0, len(groups), len(groups))]))
                      for _ in range(n_boot)]
                row["lo"], row["hi"] = np.nanquantile(bs, [.05, .95])
            out.append(row)
    # high block is listed only to say how much of it could be measured
    hb = f[f.block == "high_block"]
    out.append(dict(metric="high_block", block="high_block", seconds_in_block=round(len(hb) / FPS),
                    seconds_measured=round(hb.measured.sum() / FPS),
                    coverage=hb.measured.mean() if len(hb) else 0.0, measurable=hb.measured.sum() / FPS >= MIN_SECONDS))
    return pd.DataFrame(out)
