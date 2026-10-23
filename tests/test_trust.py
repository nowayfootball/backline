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


def _fake_ball(mid, rng, bias=0.0, n=24000):
    """Line height follows the ball; the camera loses players more often when the ball is high up the pitch."""
    rows = []
    for team in (1, 2, 3, 4):
        bx = rng.uniform(-40, 40, n)
        by = rng.uniform(-30, 30, n)
        off = rng.random(n) < np.where(bx > 0, 0.75, 0.25)          # selection: which moments are off camera
        d = pd.DataFrame(dict(match_id=mid, frame=np.arange(n), period=np.repeat([1, 2], n // 2), phase_id=0,
                              block="low_block", team_id=team, ball_x=bx, ball_y=by))
        for i in range(10):
            d[f"x{i}"] = -35 + 0.4 * (bx + 40) + 3 * i + rng.normal(0, 0.3, n) + np.where(off, bias, 0.0)
            d[f"y{i}"] = -20 + 4 * i + rng.normal(0, 0.3, n)
            d[f"d{i}"] = ~off
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


def test_same_ball_position_removes_selection_only(monkeypatch):
    rng = np.random.default_rng(3)
    _, s = _run(monkeypatch, {m: _fake_ball(m, rng) for m in (1, 2, 3)})
    assert abs(s.gap_median) > 5                       # raw difference is all selection
    assert abs(s.matched_gap_median) < 0.5
    assert s.matched_gap_ci_lo < 0 < s.matched_gap_ci_hi


def test_same_ball_position_recovers_estimation_error(monkeypatch):
    rng = np.random.default_rng(4)
    _, s = _run(monkeypatch, {m: _fake_ball(m, rng, bias=3.0) for m in (1, 2, 3)})
    assert abs(s.matched_gap_median - (-3.0)) < 0.5    # on minus off = -bias at the same ball position
    assert s.matched_gap_ci_hi < 0


def test_own_matches_json_is_kept(tmp_path, monkeypatch):
    """A short user-made matches.json (other matches or leagues) must not be replaced by SkillCorner's list."""
    from backline import data
    monkeypatch.setenv("BACKLINE_DATA", str(tmp_path))
    (tmp_path / "matches.json").write_text('[{"id": 1996435}]')
    assert data.match_ids() == [1996435]
