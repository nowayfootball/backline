"""Scene cards on one real match (uses the same cached download as test_real_match)."""
import os

import pytest

from backline import cards, data, scenes

pytestmark = pytest.mark.skipif(os.environ.get("BACKLINE_OFFLINE") == "1", reason="offline")


def test_scene_cards(tmp_path):
    data.download([1886347], verbose=False)
    sc = scenes.scenes(1886347, 1805)
    for s in sc:
        assert s["outcome"] == "successful" and len(s["back_four"]) == 4
        if s["reception_frame"] is not None:            # reception follows the pass closely (no later possession)
            assert 0 < s["reception_frame"] - s["frame"] <= scenes.MAX_RECEPTION_GAP
    out = cards.render(sc, "Newcastle", "Auckland FC", tmp_path / "c.png")
    assert out.exists()


def test_reception_does_not_jump_to_later_possession():
    import numpy as np
    data.download([1996435, 1927964], verbose=False)
    s = {x["event_id"]: x for x in scenes.scenes(1996435, 869)}["8_103"]   # next possession was the opponent's
    assert s["reception_frame"] is not None and s["reception_frame"] - s["frame"] <= scenes.MAX_RECEPTION_GAP
    rx, ry = s["receiver_at_reception"]
    assert np.hypot(rx - s["ball_reception"][0], ry - s["ball_reception"][1]) < 2.0
    ev = data.events(1927964)
    pp = ev[ev.event_type == "player_possession"]
    for x in scenes.scenes(1927964, 957034):                              # 8_235: must stop before the next possession
        nxt = pp[pp.frame_start > x["frame"]].frame_start.min()
        assert x["reception_frame"] is None or x["reception_frame"] <= nxt
