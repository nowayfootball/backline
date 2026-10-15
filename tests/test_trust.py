"""backline.trust on synthetic frames: an error placed only on off-camera frames must show up as the
estimate effect, and must not touch the on-camera value."""
import numpy as np
import pandas as pd

from backline import trust


def _fake(mid, rng, bias=5.0, off_share=0.8, n=4000):
    rows = []
    for team, base in ((1, -30.0), (2, -20.0)):
        d = pd.DataFrame(dict(match_id=mid, frame=np.arange(n), period=np.repeat([1, 2], n // 2), phase_id=0,
                              block="low_block", team_id=team, ball_x=base + 10, ball_y=0.0))
        off = rng.random(n) < off_share
        for i in range(10):
            d[f"x{i}"] = base + 3 * i + rng.normal(0, 0.3, n) + np.where(off, bias, 0.0)
            d[f"y{i}"] = -20 + 4 * i + rng.normal(0, 0.3, n)
            d[f"d{i}"] = ~off
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


def test_estimate_effect_is_detected(monkeypatch):
    rng = np.random.default_rng(0)
    fakes = {m: _fake(m, rng) for m in (1, 2, 3)}
    monkeypatch.setattr(trust, "_frames", lambda mid: fakes[mid])
    uses, fn = trust.METRICS["back-line height (m from goal)"]
    v = trust.team_values(fn, uses, matches=[1, 2, 3], blocks=("low_block",))
    s = trust.summarise(v).iloc[0]
    assert abs(s.gap_median - (-5.0)) < 0.3                  # on-camera minus all-moments = -bias
    seen = v.groupby("team_id").seen.mean()
    assert abs(seen[1] - (-30 + 4.5 + 52.5)) < 0.2           # on-camera value untouched by the bias
    assert abs(s.coverage - 0.2) < 0.03
