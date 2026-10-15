# backline — can you trust this defensive metric from broadcast tracking?

**In one line:** SkillCorner's tracking is built from broadcast video, so many defensive positions are off-camera estimates. `backline.trust` takes any team-level defensive metric and reports how much of it the camera actually saw, how much the estimates move it, and whether it repeats within and across matches. We ran it on seven common metrics (Table 1), then built scene cards (Figure 1) only from what held up.

## Why

Line height or compactness needs several players at once, but the camera follows the ball. Unchecked, estimates and match-to-match noise can pass as a team's defensive identity.

## Check your own metric

```python
from backline import trust
gap = lambda d: ((d.x4 + d.x5 + d.x6 + d.x7) - (d.x0 + d.x1 + d.x2 + d.x3)).median() / 4
print(trust.check(gap, uses=range(8)))     # defence-midfield gap, needs the 8 deepest players
```

A metric gets one team's organised-defence frames in one match: `x0..x9`, `y0..y9` are the defending outfield players by depth (`x0` deepest; own goal at x = −52.5), `d0..d9` whether each was on camera. Per block, `check` reports coverage (time with every needed player on camera), on-camera versus all-moments values (difference, rank correlation), first-half versus second-half r, and same-team match-to-match r with a permutation p. A value needs 60 s on camera. `python -m backline.trust` reproduces Table 1; matches download automatically (about 90 MB each).

**Table 1.** Seven common metrics, 20 A-League 24/25 matches (40 team-matches)

| Metric (players needed) | All needed players on camera: low / mid / high block | On-camera minus all-moments value: low / mid (median) | Teams keep their order, mid (ρ) | Same team, other matches: low / mid (r) |
|---|---|---|---|---|
| Back-line height (4) | 71% / 31% / 3% | −0.6 / −1.9 m | 0.82 | 0.39 / 0.27 |
| Back-line width (4) | 71% / 31% / 3% | −0.7 / −1.3 m | 0.81 | 0.08 / −0.01 |
| Back-line spread (4) | 71% / 31% / 3% | 0.0 / 0.3 m | 0.76 | 0.22 / 0.40 |
| Ball in front of back line (4) | 71% / 31% / 3% | −1.3 / −9.5 m | 0.32 | 0.44 / 0.08 |
| Defence–midfield gap (8) | 54% / 26% / 3% | −0.4 / −0.6 m | 0.86 | 0.21 / 0.26 |
| Team length (10) | 25% / 18% / 2% | −4.0 / −2.2 m | 0.58 | 0.52 / −0.20 |
| Team width (10) | 25% / 18% / 2% | 0.1 / −0.2 m | 0.86 | −0.34 / 0.40 |

What it shows:

- **The high block cannot be measured:** no team-match reached 60 s with all needed players on camera.
- **Whole-team compactness is the least visible.** All ten outfield players are on camera 18–25% of the time; estimates change low-block team length by a median 4 m (up to 11 m).
- **On-camera moments look more compact** (mostly negative differences): consistent with the camera framing play where players are close together, so on-camera values are a selected sample, not the whole match.
- **No metric was confirmed as a team trait.** Across the 14 metric–block pairs with data, none repeated across matches with p < 0.05 (lowest p: ball in front of back line, low block, r 0.44, p = 0.05), and the "ball in front of back line" mid-block ranking barely survives the estimates (ρ 0.32).

Two checks support the tool: it reproduces the independently computed reliability values of the match report, and with a +5 m error placed only off camera (synthetic) it reports −5.0 m while the on-camera value is unchanged (`tests/test_trust.py`).

## Scene cards built on what held up

```bash
pip install .
python -m backline 1996435 --team 869 --scenes
```

This writes to `reports/` a back-line match report (on-camera values, coverage and reliability) and scene cards: every completed opponent pass SkillCorner's event data tags as breaking the last line, between its players (through) or outside its widest player (around). Across the 20 matches there are 113 (58 through, 55 around).

![Figure 1](figures/fig1_scenes_en.png)

**Figure 1.** Sydney FC v Adelaide United, the first 4 of 9 cards (`--max-scenes 4`): match clock, passer and receiver, through or around, defensive phase, tracking frame (10 fps), any shot or goal, and positions at the moment of the pass. Faded players were off camera; fully on-camera cards come first. Read positions as the rough shape, not metre-level gaps.

The cards make no judgement about fault, because the judgements we tried did not hold up. Replaying the 62 passes called offside, only 6 come out offside at the pass frame. A "defender left 2 m behind the line" flag fell apart: 8 of 14 flags used off-camera estimates and 5 vanished within ±0.5 s. A "usual line" overlay, tested with rules written before running it ([docs](docs/usual_line_test.md)), found no larger deviation in beaten scenes (2.9 m vs 3.5 m, p = 0.12).

## Other matches and leagues

Matches in the same SkillCorner open-data format should work (tested on these 20): point `BACKLINE_DATA` at a folder with `matches.json` and per-match `<id>/` files; rebuild league references with `python -m backline.league`. This submission uses only the matches provided for the Cup.

## Reproduce and test

- Data is not included; `backline/data.py` downloads it from a pinned commit.
- `pip install ".[test]"`, then `pytest` (3 synthetic, 4 on real matches), also run in GitHub Actions.
- `audit/` holds research notes behind the dropped features (not one-command reproductions).

## Notes

- Licence: MIT (`LICENSE.md`). Data: SkillCorner × PySport open data (A-League 24/25) only.
- AI use: Claude (Anthropic) helped write and review the code. Study design, judgements and final review are the author's.
