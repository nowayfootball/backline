# backline — the passes that beat your last line, found straight after the match

**In one line:** `backline` turns SkillCorner broadcast tracking into a page of scene cards for every completed pass SkillCorner tags as breaking a team's last line, plus a back-line match report. We also tested what we could not reproduce from this data, and kept those features out.

## Why

Moments when the back line is beaten are a natural starting point for a defensive review. `backline` lists them with the match clock, so they can be found in the video without scrubbing.

## Use

```bash
pip install .
python -m backline 1996435 --team 869 --scenes
```

The first run downloads that match (about 90 MB) from a pinned commit of the SkillCorner open data. Leave out `--team` to get both teams. Each team gets two pages:

1. **Scene cards** (Figure 1): every completed pass that SkillCorner tags as breaking the last defensive line, either between its players (through) or outside its widest player (around). Incomplete attempts, dribbles and runs are not included. Across the 20 A-League 24/25 matches there are 0 to 9 per team-match, 113 in total (58 through, 55 around).
2. **Match report**: line height, width and front-to-back spread for low and mid blocks, plus ball-side shift and moving together, each set against the league distribution.

![Figure 1](figures/fig1_scenes_en.png)

**Figure 1.** Sydney FC v Adelaide United, the first 4 of 9 cards (`--max-scenes 4`). Each card shows the half and match clock, passer and receiver, through or around the line, the defensive block, the video frame number, and whether the move ended in a shot or goal. The pitch shows player positions at the moment of the pass (players more than 32 m into the opponents' half are not drawn), the ball's path (dashed arrow) and the receiver's run (dotted). Faded players were off camera, so their positions are estimates. Cards where the back four and the receiver were on camera come first.

### Other matches and leagues

It should run on any match in the same SkillCorner open-data format (tested on the 20 A-League 24/25 matches): point `BACKLINE_DATA` at a folder holding `<id>_tracking_extrapolated.jsonl`, `<id>_dynamic_events.csv`, `<id>_phases_of_play.csv` and `<id>_match.json` for each match. The report's league dots and reliability figures are A-League 24/25 values; rebuild them for another league with `python -m backline.league`. Event-only data cannot be used. (This submission itself uses only the matches provided for the Cup.)

## Only what the camera saw

SkillCorner tracking is built from broadcast video. The camera follows the ball, and players outside the frame get estimated positions. All four back-line players are on camera in 71% of low-block frames, 31% of mid-block frames and 3% of high-block frames overall; a typical team-match had about 2 seconds of its roughly 4 minutes of high block on camera. So `backline`:

- computes report metrics only from moments when all four are on camera, prints how many seconds that was, and marks the high block "not calculated". Mid-block values therefore describe moments with the ball near the line;
- shows each number with the sampling error among this match's on-camera moments (90%, resampling defensive phases; tracking error and camera selection are not included), against league dots that come from different amounts of on-camera time;
- gives every metric's league reliability, both first half against second half and match to match within the same team. For line width, ball-side shift and moving together, repetition across matches was not detectable (r −0.28 to 0.08, 13 teams), and no metric is presented as a team's habit.

## What we tried and dropped

Each extra feature was tested against the data; anything that failed was left out.

**Table 1.** Features tested and dropped

| Feature | Test | Result | Decision |
|---|---|---|---|
| "Would have been offside if the line had held" | Replay the 62 passes called offside | Only 6 of 62 come out offside at the pass frame; targeted receivers a median +4 m onside (position, event timing or receiver identity may be off) | Dropped; cards warn not to read metre-level gaps |
| Flag a defender left 2 m+ behind the line | On-camera status and timing sensitivity of the 14 flags | 8 used off-camera estimates; 5 vanished within ±0.5 s (1 more could not be checked) | Dropped |
| Overlay the team's "usual line" in that match | Test written before running ([docs](docs/usual_line_test.md)): 54 beaten scenes vs similar moments | Gap from usual 2.9 m vs 3.5 m (p = 0.12); 46% of ordinary moments are already 3 m+ away | Dropped |
| Mid-block "ball in front of line" | On-camera value vs value including estimates | On-camera moments are biased towards the ball being near the line; typically ~9 m apart (up to ~18 m), teams reorder | Removed from the report |

So `backline` does not judge who was at fault: it shows which moments these were and where everyone stood, and leaves the judgement to the coach watching the video.

## Reproduce and test

- Data is not included. `backline/data.py` downloads it from a pinned commit of the SkillCorner open data.
- League reference values and metric reliability are rebuilt with `python -m backline.league` (`league_reference.csv`, `reliability.json`).
- Tests: `pip install ".[test]"` then `pytest` (2 synthetic tests plus 4 on real matches), also run in GitHub Actions.
- `audit/` holds the research scripts behind Table 1 (reimplementation, robustness, offside replay, usual-line test). They are notes rather than one-command reproductions: some read intermediate files written by earlier steps.

## Notes

- Licence: MIT (`LICENSE.md`).
- Data: only the SkillCorner × PySport open data (A-League 24/25).
- AI use: Claude (Anthropic) helped write and review the code. Study design, judgements and final review are the author's.
