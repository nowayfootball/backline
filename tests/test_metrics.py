"""Fast tests on synthetic frames (no download)."""
import numpy as np
import pandas as pd

from backline import metrics


def _frames(n=2000, measured=True, block="medium_block"):
    rng = np.random.default_rng(0)
    d = dict(match_id=1, frame=np.arange(n), period=1, phase_id=np.arange(n) // 100, block=block, team_id=7, measured=measured,
             ball_x=rng.normal(-5, 3, n), ball_y=rng.normal(0, 10, n))
    for i, y in enumerate((-15, -5, 5, 15)):
        d[f"x{i}"] = -20 + rng.normal(0, .5, n)
        d[f"y{i}"] = y + 0.3 * d["ball_y"]
        d[f"x{i}_p5"] = d[f"x{i}"] - 1.0          # whole line drops 2 m/s together
        d[f"id{i}"] = i
    return pd.DataFrame(d)


def test_values_on_known_line():
    m = metrics.team_metrics(_frames(), 7).set_index(["metric", "block"])
    assert abs(m.loc[("height", "medium_block"), "value"] - 32.5) < 0.2       # x=-20 -> 32.5 m from goal
    assert abs(m.loc[("width", "medium_block"), "value"] - 30) < 0.5
    assert abs(m.loc[("shift", "all"), "value"] - 0.3) < 0.02
    assert m.loc[("lockstep", "all"), "value"] < 0.3


def test_unmeasured_frames_are_never_used():
    m = metrics.team_metrics(_frames(measured=False), 7)
    assert not m.measurable.any() and m.value.isna().all()
