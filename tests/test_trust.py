"""backline.trust on synthetic frames."""
import os

import numpy as np
import pandas as pd

from backline import trust


def _fake(mid, rng, bias=5.0, off_share=0.8, n=4000, team_effect=None):
    rows = []
    for team in (1, 2, 3, 4):
        base = -30.0 + (team_effect[team] if team_effect else rng.normal(0, 0.5))
        d = pd.DataFrame(dict(match_id=mid, frame=np.arange(n), period=np.repeat([1, 2], n // 2), phase_id=0,
                              block="low_block", team_id=team, ball_x=base + 10, ball_y=0.0))
        off = rng.random(n) < off_share
        for i in range(10):
            d[f"x{i}"] = base + 3 * i + rng.normal(0, 0.3, n) + np.where(off, bias, 0.0)
            d[f"y{i}"] = -20 + 4 * i + rng.normal(0, 0.3, n)
            d[f"d{i}"] = ~off
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


def _run(monkeypatch, fakes):
    monkeypatch.setattr(trust, "_frames", lambda mid: fakes[mid])
    uses, fn = trust.METRICS["back-line height (m from goal)"]
    v = trust.team_values(fn, uses, matches=list(fakes), blocks=("low_block",))
    return v, trust.summarise(v).iloc[0]


def test_off_camera_error_is_found_at_any_coverage(monkeypatch):
    for off_share in (0.8, 0.5, 0.3):                      # coverage 20%, 50%, 70%
        rng = np.random.default_rng(0)
        v, s = _run(monkeypatch, {m: _fake(m, rng, off_share=off_share) for m in (1, 2, 3)})
        assert abs(s.gap_median - (-5.0)) < 0.3, off_share  # on-camera minus off-camera = -bias
        assert abs(s.coverage - (1 - off_share)) < 0.03


def test_team_effect_detected_and_absent_when_none(monkeypatch):
    rng = np.random.default_rng(1)
    eff = {1: -4.0, 2: -1.5, 3: 1.5, 4: 4.0}               # strong, stable team effect
    _, s = _run(monkeypatch, {m: _fake(m, rng, team_effect=eff, off_share=0.3) for m in range(1, 7)})
    assert s.r_cross > 0.8 and s.p_cross < 0.05
    rng = np.random.default_rng(2)
    _, s = _run(monkeypatch, {m: _fake(m, rng, off_share=0.3) for m in range(1, 7)})   # no team effect
    assert s.p_cross > 0.05


def test_trust_runs_from_an_empty_data_folder(tmp_path, monkeypatch):
    """The README path: no data, no cache -> trust.check downloads, builds the cache and returns a table."""
    if os.environ.get("BACKLINE_OFFLINE") == "1":
        return
    from backline import data
    monkeypatch.setattr(data, "data_dir", lambda: tmp_path)
    trust._frames.cache_clear()
    uses, fn = trust.METRICS["back-line height (m from goal)"]
    t = trust.check(fn, uses, matches=[1886347], blocks=("low_block",))
    assert (tmp_path / "_cache" / "team_frames_1886347.pkl").exists()
    assert t.iloc[0].team_matches == 2 and 0 < t.iloc[0].coverage <= 1
    trust._frames.cache_clear()
