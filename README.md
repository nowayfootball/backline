# backline — find every pass played in behind your last line, straight after the match

**In one line:** `backline` turns SkillCorner broadcast tracking into a one-page set of scene cards showing every completed pass played in behind a team's last line, plus a back-line match report. Just as important, we tested what this data **cannot** support and kept those features out.

## Why

The first clips a defensive coach looks for after a match are the moments the line was beaten. Today that means scrubbing through 90 minutes of video. Give `backline` one match and it lists those moments with the match clock, so the coach can jump straight to them.

## Use

```bash
pip install .
python -m backline 1996435 --team 869 --scenes
```

The first run downloads that match (about 90 MB) from a pinned commit of the SkillCorner open data. Each team gets two pages:

1. **Scene cards** (Figure 1): every completed pass that SkillCorner tags as breaking the last defensive line, either through it or around it into the space behind. Across the 20 A-League 24/25 matches there are 0 to 9 per team-match, 113 in total (58 through, 55 around).
2. **Match report**: line height, width and front-to-back spread for low and mid blocks, plus ball-side shift and moving together, each set against the league distribution.

![Figure 1](figures/fig1_scenes_en.png)

**Figure 1.** Sydney FC v Adelaide United. Each card shows the half and match clock, passer and receiver, through or around the line, the defensive block, the video frame number, and whether the move ended in a shot or goal. The pitch shows all 22 players at the moment of the pass, the ball's path (dashed arrow) and the receiver's run (dotted). Faded players were off camera, so their positions are estimates. Scenes where the back four and the receiver were all on camera come first.

### Other matches and leagues

Any match in SkillCorner's format works: point `BACKLINE_DATA` at a folder holding `<id>_tracking_extrapolated.jsonl`, `<id>_dynamic_events.csv`, `<id>_phases_of_play.csv` and `<id>_match.json` for each match. Scene cards need nothing else. The report's grey comparison dots and reliability figures are A-League 24/25 values, so for another league rebuild them from its matches with `python -m backline.league`. Event-only data (no tracking) cannot be used.

## Only what the camera saw

SkillCorner tracking is built from broadcast video. The camera follows the ball, and players outside the frame get estimated positions. All four back-line players are on camera in 71% of low-block frames, 31% of mid-block frames and 3% of high-block frames (a median of 2 seconds per match). So `backline`:

- computes report metrics only from moments when all four are on camera. It prints how many seconds that was, and marks the high block "not calculated";
- shows each number with this match's sampling error (90%, resampling defensive phases) and the metric's league-wide reliability, both first-half against second-half and match-to-match;
- describes line width, ball-side shift and moving together as "this match only". The same team barely repeats them from one match to the next (match-to-match r −0.28 to 0.08), so the report never calls them a team's habit.

## What we tried and dropped

We wanted the tool to say more. Each extra feature was tested against the data, and anything that failed was left out.

**Table 1.** Features tested and dropped

| Feature | Test | Result | Decision |
|---|---|---|---|
| "Would have been offside if the line had held" | 62 passes called offside vs 761 legal passes to players near the line | AUC 0.64; players flagged offside came out a median +4 m onside | Dropped; cards warn not to read metre-level gaps |
| Flag a defender left 2 m+ behind the line | On-camera status and timing sensitivity of the 14 flags | 8 used off-camera estimates; 6 vanished within ±0.5 s | Dropped |
| Overlay the team's "usual line" in that match | Pre-registered test: 54 beaten scenes vs similar moments | Gap from usual 2.9 m vs 3.5 m (p = 0.12); 46% of ordinary moments are already 3 m+ away | Dropped |
| Mid-block "ball in front of line" | On-camera value vs value including estimates | On-camera moments are biased towards the ball being near the line; up to ~9 m difference, teams reorder | Removed from the report |

So `backline` does not judge who was at fault. It quickly pulls out what the data supports, namely which moments these were and where everyone stood, and leaves the judgement to the coach watching the video.

## Reproduce and test

- Data is not included. `backline/data.py` downloads it from a pinned commit of the SkillCorner open data.
- League reference values and metric reliability are rebuilt with `python -m backline.league` (`league_reference.csv`, `reliability.json`).
- Tests: `pytest` (2 synthetic plus 4 on a real match), run in GitHub Actions.
- Audit scripts (independent reimplementation, robustness, offside reproduction, usual-line test) are in `audit/`.

## Notes

- Licence: MIT (`LICENSE.md`).
- Data: only the SkillCorner × PySport open data (A-League 24/25).
- AI use: Claude (Anthropic) helped write and review the code. Study design, judgements and final review are the author's.
