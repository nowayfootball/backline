# backline — can you trust this defensive metric from broadcast tracking?

**Short answer, for 20 A-League 24/25 matches: only in the low block, and not yet as a team trait.**

- **The high block is out of sight.** All four deepest defenders are on camera 3% of the time; whole-team shape 2%.
- **What the camera misses is different football.** Moments with a needed player off camera differ from on-camera
  moments by up to 13 m (median). Comparing only moments with the ball in the same place removes most of this for "ball in
  front of the line" and back-line width, and *reverses* back-line height: at the same ball position, the line is 0.8–3 m
  deeper when one of the four is off camera. Team length stays 2.5–6.4 m apart.
- **No metric repeated as a team trait**, but with 1–7 matches per team a moderate team effect would usually be
  missed: absence of evidence, not evidence of absence.

`backline.trust` runs these checks on any team-level defensive metric, so an analyst knows whether a number belongs
in an opposition report before it is read as "how this team defends".

## Why

Defensive shape needs several players at once; the camera follows the ball, so off-camera defenders are estimates.
Broadcast visibility limits (Bassek et al., *Sci. Med. Football*, 2025) and metric repeatability checks (Franks et
al., "Meta-analytics", 2016) are known; this combines both for defensive shape, per block, for any metric.

## Quickstart

```bash
git clone https://github.com/nowayfootball/backline && cd backline
python3 -m venv .venv && source .venv/bin/activate   # Python 3.10 or newer
pip install -e ".[test]"                             # tested versions: constraints.txt
pytest                                               # 11 tests, downloads 3 matches (~1 min)
python -m backline.trust                             # Table 1 -> trust_table.csv (20 matches, 1.8 GB, ~5 min)
python -m backline.trust_figure                      # Figure 1 -> figures/fig1_trust.png
```

Data (not included) downloads from a pinned SkillCorner open-data commit to `~/.cache/backline` (`BACKLINE_DATA`).

## Check your own metric

```python
from backline import trust
gap = lambda d: ((d.x4 + d.x5 + d.x6 + d.x7) - (d.x0 + d.x1 + d.x2 + d.x3)).median() / 4
print(trust.check(gap, uses=range(8)))     # defence-midfield gap, needs the 8 deepest players
```

The function gets one team's organised-defence frames from one match: `x0..x9`, `y0..y9` (outfield players by depth,
own goal at x = −52.5), `d0..d9` (on camera?), `ball_x`, `ball_y`. Blocks are SkillCorner's phase tags. `check`
returns, per block, every number in Table 1 plus intervals and n (columns: `backline.trust` docstring).

## Results

![Figure 1](figures/fig1_trust.png)

**Figure 1.** A: share of organised-defence time with every needed player on camera. B: on- minus off-camera
value; hollow = all moments, filled = same ball position (5 m along × three bands across).

**Table 1.** Seven common metrics, low / mid block (40 team-matches)

| Metric (players needed) | On camera | On − off, same ball position | Order kept on/off (ρ) | Same team, other matches (r) | Use for |
|---|---|---|---|---|---|
| Back-line height (4) | 71% / 31% | +0.8 / +3.0 m | 0.33 / 0.63 | 0.39 / 0.27 | low ✓ · mid ✗ |
| Back-line width (4) | 71% / 31% | −0.9 / −0.6 m | 0.77 / 0.79 | 0.08 / −0.01 | low ✓ · mid ranking |
| Back-line spread (4) | 71% / 31% | 0.0 / +0.3 m | 0.58 / 0.58 | 0.22 / 0.40 | low ✓ · mid ✗ |
| Ball in front of line (4) | 71% / 31% | −1.0 / −3.0 m | 0.58 / 0.26 | 0.44 / 0.08 | low ✓ · mid ✗ |
| Defence–midfield gap (8) | 54% / 26% | −1.5 / −0.2 m | 0.50 / 0.77 | 0.21 / 0.26 | low ✓ · mid ranking |
| Team length (10) | 25% / 18% | −6.4 / −2.5 m | 0.65 / 0.58 | 0.52 / −0.20 | ✗ · ✗ |
| Team width (10) | 25% / 18% | 0.0 / +0.3 m | 0.44 / 0.71 | −0.34 / 0.40 | ✗ · mid ranking |

How to read it:

- **Use for** (our rule of thumb). ✓: needed players on camera at least half the time. *Ranking*: less, but
  team-matches keep their order on and off camera (ρ ≥ 0.7), so compare matches rather than quote metres. ✗: neither.
  High block: ✗ for all.
- **Sign**: negative means smaller on camera (deeper line, narrower, ball closer, shorter team).
- **Same ball position** removes *which* moments the camera shows. The rest mixes estimation error with players
  being off camera *because of where they stand* (a defender dropping deep leaves the picture); the data cannot
  separate them. Rules fixed before running, checked on synthetic data ([docs](docs/trust_metrics.md)).
- **Team trait**: no match-to-match r reached q < 0.1 (Benjamini–Hochberg over 14; lowest p = 0.05); intervals span
  ±0.3, more for 10-player metrics (n = 18–20). At the team-matches measured, a team effect explaining 40% of the
  variance is detected 14–48% of the time (`audit/trust_power.py`).

## Scene cards

`python -m backline 1996435 --team 869 --scenes` draws a match report and a card for each completed opponent pass
SkillCorner tags as breaking the last line (113 in 20 matches; [example](figures/fig_scenes_en.png)). Cards blame no
one: of 62 passes called offside only 6 look offside at the pass frame, and a "defender left behind" flag and a
"usual line" overlay both failed ([test](docs/usual_line_test.md)).

## Other matches and leagues

Same SkillCorner open-data format (tested only on these 20): put `matches.json` (`[{"id": ...}]`) and `<id>/`
folders in `BACKLINE_DATA`, run `python -m backline.league --out my_league`, then
`BACKLINE_LEAGUE=my_league python -m backline <id>`. This submission uses only the provided matches.

## Notes

- Tests: synthetic (off-camera error, ball-position selection, planted team effect) and real matches; CI on Python
  3.10–3.12. `audit/`: research notes.
- Licence: MIT (`LICENSE.md`). Data: SkillCorner × PySport open data (A-League 24/25) only.
- AI use: Claude (Anthropic) helped write and review the code. Study design, judgements and final review are the author's.
