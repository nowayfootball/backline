# backline — can you trust this defensive metric from broadcast tracking?

**In one line:** SkillCorner's tracking is built from broadcast video, so many defensive positions are off-camera estimates. `backline.trust` takes any team-level defensive metric and reports how much of it the camera actually saw, how different the off-camera moments look, and whether it repeats within and across matches. We ran it on seven common metrics (Table 1) and built scene cards (Figure 1) that show positions without verdicts.

## Why

Defensive shape needs several players at once; the camera follows the ball. Unchecked, estimates and noise pass as team identity.

## Check your own metric

```python
from backline import trust
gap = lambda d: ((d.x4 + d.x5 + d.x6 + d.x7) - (d.x0 + d.x1 + d.x2 + d.x3)).median() / 4
print(trust.check(gap, uses=range(8)))     # defence-midfield gap, needs the 8 deepest players
```

A metric gets one team's organised-defence frames in one match: `x0..x9`, `y0..y9` are the outfield players by depth (`x0` deepest, own goal at x = −52.5; the four deepest are not always defenders), `d0..d9` whether each was on camera. Per block, `check` reports coverage (time with every needed player on camera), on-camera versus off-camera values (difference, rank correlation), first-half versus second-half r, and same-team match-to-match r with a permutation p. A value needs 60 s per team-match. `python -m backline.trust` reproduces Table 1 (downloads all 20 matches, about 1.8 GB; a few minutes).

**Table 1.** Seven common metrics, 20 A-League 24/25 matches (40 team-matches)

| Metric (players needed) | All needed players on camera: low / mid / high block | On-camera minus off-camera value: low / mid (median) | Team-matches keep their order, mid (ρ) | Same team, other matches: low / mid (r) |
|---|---|---|---|---|
| Back-line height (4) | 71% / 31% / 3% | −2.8 / −3.2 m | 0.63 | 0.39 / 0.27 |
| Back-line width (4) | 71% / 31% / 3% | −3.4 / −1.7 m | 0.79 | 0.08 / −0.01 |
| Back-line spread (4) | 71% / 31% / 3% | 0.1 / 0.5 m | 0.58 | 0.22 / 0.40 |
| Ball in front of back line (4) | 71% / 31% / 3% | −6.7 / −12.8 m | 0.26 | 0.44 / 0.08 |
| Defence–midfield gap (8) | 54% / 26% / 3% | −1.3 / −1.0 m | 0.77 | 0.21 / 0.26 |
| Team length (10) | 25% / 18% / 2% | −7.6 / −3.3 m | 0.58 | 0.52 / −0.20 |
| Team width (10) | 25% / 18% / 2% | 0.1 / −0.2 m | 0.71 | −0.34 / 0.40 |

What it shows:

- **The high block cannot be checked on camera:** no team-match had 60 s with all needed players visible.
- **Whole-team compactness is the least visible.** All ten outfield players are on camera 18–25% of the time, and on- and off-camera moments differ in low-block team length by a median 7.6 m (up to 14 m).
- **On- and off-camera moments are different football.** In view, the back line sits deeper, closer to the ball and narrower (its spread slightly larger) and the team is shorter. The gap mixes which moments the camera shows with estimation error; this data cannot separate the two, so neither can stand in for the whole match.
- **No metric was confirmed as a team trait.** None of the 14 metric–block pairs repeated across matches at p < 0.05 (uncorrected; lowest p = 0.051). With 13 teams playing 1–7 matches each, a simulated moderate team effect (ICC 0.4) is detected only 43% of the time (`audit/trust_power.py`), so this is absence of evidence, not evidence of absence; the permutation also ignores opponents.

Synthetic tests: an off-camera-only error is recovered at 20–70% coverage; a planted team effect is detected, none is not (`tests/test_trust.py`).

## Scene cards: positions only, no verdicts

```bash
pip install .
python -m backline 1996435 --team 869 --scenes
```

This writes to `reports/` a match report (on-camera values, coverage, reliability) and scene cards: every completed opponent pass SkillCorner's event data tags as breaking the last line, between its players (through) or outside its widest player (around). Across the 20 matches there are 113 (58 through, 55 around).

![Figure 1](figures/fig1_scenes_en.png)

**Figure 1.** Sydney FC v Adelaide United, the first 4 of 9 cards (`--max-scenes 4`): match clock, passer and receiver, through or around, defensive phase, tracking frame (10 fps), any shot or goal, and positions at the moment of the pass. Faded players were off camera; cards with the back four and receiver on camera come first. Read positions as the rough shape, not metre-level gaps.

The cards make no judgement about fault, because the judgements we tried did not hold up. Replaying the 62 passes called offside, only 6 come out offside at the pass frame. A "defender left 2 m behind the line" flag fell apart: 8 of 14 flags used off-camera estimates and 5 vanished within ±0.5 s. A "usual line" overlay, tested with rules written before running it ([docs](docs/usual_line_test.md)), found no larger deviation in beaten scenes (2.9 m vs 3.5 m, p = 0.12).

## Other matches and leagues

Matches in the same SkillCorner open-data format should work (tested on these 20): point `BACKLINE_DATA` at a folder with `matches.json` and per-match `<id>/` files; rebuild league references with `python -m backline.league`. This submission uses only the matches provided for the Cup.

## Reproduce and test

- Data is not included; `backline/data.py` downloads it from a pinned commit.
- `pip install ".[test]"`, then `pytest` (4 synthetic, 5 on real matches), also run in GitHub Actions.
- `audit/`: research notes (not one-command reproductions).

## Notes

- Licence: MIT (`LICENSE.md`). Data: SkillCorner × PySport open data (A-League 24/25) only.
- AI use: Claude (Anthropic) helped write and review the code. Study design, judgements and final review are the author's.
