# "Usual line" overlay: test written before running it

This test was written and committed in the development repository before any result was computed. Code: `audit/verify_usual.py`, feature code: `backline/usual.py` (kept, not used by the cards).

## Feature
For a scene (pass moment, defending team T, block B, ball position b), the "usual line" is the median left-to-right position of T's deepest four outfield players over T's on-camera frames in the same match, same block, with the ball within 6 m of b (10 m if too few), excluding 20 s either side of the scene. Fewer than 50 frames: not computed. Gap Δ = mean x of the actual back four − mean x of the usual line.

## Question
In scenes where a completed pass broke the last line, is the line further from its usual position than in comparable moments?

## Samples
- Scenes: completed last-line-breaking passes in an organised block, all four on camera, usual line computable.
- Controls: same match, team and block, on-camera frames with the ball within 6 m of the scene's ball position, at least 20 s away, and no opponent line-breaking pass in the next 3 s; up to 20 per scene (seed 7), each with its own usual line.

## Decision rule (fixed in advance)
- Primary: mean |Δ| scene minus mean |Δ| of its controls, permutation test swapping the scene label within each scene's set (5,000 permutations), two-sided.
- The overlay is "informative" only if p < 0.05 and the difference is at least 1.0 m. Otherwise it is not used in the cards.
- Fewer than 20 scenes: descriptive only.

## Result
54 scenes (27 low block, 27 mid block), median 20 controls each. Mean |Δ|: scenes 2.89 m, controls 3.51 m; difference −0.61 m, p = 0.12. Signed difference +0.58 m, p = 0.36. In ordinary moments the line is already 3 m or more from its usual position 46% of the time (median 2.66 m).

Decision: not informative, removed from the cards. This is a failure to find a difference, not evidence that there is none.
