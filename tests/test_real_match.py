"""End-to-end on one real match (downloads ~90 MB of SkillCorner open data unless cached).
Set BACKLINE_OFFLINE=1 to skip."""
import os

import pytest

from backline import data, frames, metrics, report
from backline.league import OUT as LEAGUE

pytestmark = pytest.mark.skipif(os.environ.get("BACKLINE_OFFLINE") == "1", reason="offline")
MID, TEAM = 1886347, 4177


@pytest.fixture(scope="module")
def f():
    data.download([MID], verbose=False)
    return frames.back_four(MID)


def test_orientation_and_blocks(f):
    m = metrics.team_metrics(f, TEAM, n_boot=0).set_index(["metric", "block"])
    low, mid = m.loc[("height", "low_block"), "value"], m.loc[("height", "medium_block"), "value"]
    assert 5 < low < mid < 52.5            # own goal is at height 0; a low block sits deeper than a mid block
    assert (f.groupby("block").measured.mean()["high_block"] < 0.2)   # broadcast camera rarely shows a high line


def test_only_measured_frames_and_report(f, tmp_path):
    import pandas as pd
    met = metrics.team_metrics(f, TEAM, n_boot=50)
    assert (met.seconds_measured <= met.seconds_in_block).all()
    out = report.render(f, met, TEAM, "Auckland FC", "Newcastle", pd.read_csv(LEAGUE), tmp_path / "r.png")
    assert out.exists() and out.stat().st_size > 50_000
