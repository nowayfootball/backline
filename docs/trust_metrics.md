# Trust check: metric definitions and changes

The seven built-in metrics and the two validation checks were written and committed in the development repository
before any result was computed (rules committed 2026-10-15 16:50 ET, first results written 16:52 ET; the public repository has a fresh history). Definitions (`backline/trust.py`, `METRICS`):

- back-line height: median over frames of the mean x of the 4 deepest outfield players, + 52.5 (metres from own goal)
- back-line width: median y-range of the 4 deepest; back-line spread: median standard deviation of their x
- ball in front of back line: median of ball x − mean x of the 4 deepest
- defence–midfield gap: median of mean x of depth ranks 5–8 − mean x of ranks 1–4
- team length: median of x(10th deepest) − x(deepest); team width: median y-range of all 10 outfield players

Validation fixed in advance: (1) the trust check must reproduce the match report's reliability values (it does, to two
decimals); (2) an error placed only on off-camera frames of synthetic data must be recovered (it is).

## Change after an independent audit
The first version compared on-camera values with values from all moments. Because "all moments" contains the
on-camera ones, that difference shrinks towards zero as coverage rises (synthetic: the same +5 m error read as −4.95 m
at 20% coverage but −0.09 m at 70%). It was replaced by on-camera versus off-camera moments (at least one needed
player off camera), which recovers the error at any coverage. This was a fix of the method, applied to every metric.

## Power of the match-to-match test
`audit/trust_power.py` simulates the real design per metric and block, using only the team-matches that had a value
(1,000 runs, 500 permutations each). Results: `audit/trust_power.csv` and the table below.

| Metric | Block | Team-matches | ICC 0 (false positive) | 0.2 | 0.4 | 0.6 |
|---|---|---|---|---|---|---|
| back-line height (m from goal) | low | 40 | 0.05 | 0.14 | 0.48 | 0.84 |
| back-line height (m from goal) | medium | 40 | 0.06 | 0.15 | 0.48 | 0.84 |
| back-line width (m) | low | 40 | 0.04 | 0.13 | 0.47 | 0.85 |
| back-line width (m) | medium | 40 | 0.04 | 0.15 | 0.48 | 0.85 |
| back-line spread (m) | low | 40 | 0.05 | 0.12 | 0.46 | 0.83 |
| back-line spread (m) | medium | 40 | 0.05 | 0.15 | 0.47 | 0.83 |
| ball in front of back line (m) | low | 40 | 0.06 | 0.12 | 0.46 | 0.84 |
| ball in front of back line (m) | medium | 40 | 0.04 | 0.12 | 0.48 | 0.85 |
| defence-midfield gap (m) | low | 37 | 0.04 | 0.13 | 0.44 | 0.81 |
| defence-midfield gap (m) | medium | 37 | 0.06 | 0.13 | 0.43 | 0.78 |
| team length (m) | low | 23 | 0.04 | 0.06 | 0.15 | 0.41 |
| team length (m) | medium | 25 | 0.06 | 0.07 | 0.19 | 0.46 |
| team width (m) | low | 23 | 0.05 | 0.05 | 0.14 | 0.41 |
| team width (m) | medium | 25 | 0.05 | 0.07 | 0.19 | 0.44 |
| all 40 team-matches | - | 40 | 0.06 | 0.15 | 0.49 | 0.83 |

So a team effect explaining 40% of the variance is detected 43–48% of the time for 4- and 8-player metrics and 14–19% for 10-player metrics (an earlier version quoted 43% for all; that assumed all 40 team-matches were measurable).

## Same-ball-position comparison (rules fixed 2026-10-22, before running)
An independent review found that matching on ball x flips the sign of the back-line height difference. To report this
properly for every metric, the following was fixed before any result was computed.

- **Matched difference.** Within each team-match and block, frames are split by ball position: ball x in 5 m bins ×
  ball y in three bands (|y| ≤ 11 m, left, right). In every cell with at least 5 s on camera and 5 s off camera, the
  metric is computed on each side; the matched difference is the average of cell differences weighted by on-camera
  time. A team-match needs 60 s of on-camera time in usable cells. Frames without a ball position are dropped.
- **Uncertainty.** For raw and matched medians: 95% interval from resampling teams (2,000 draws).
- **Reading, fixed in advance.** (a) If the matched interval contains 0 and |matched| < ½|raw|, the raw difference is
  reported as mostly *which moments the camera shows* (ball position). (b) If the matched interval excludes 0, the
  remaining difference is reported as *not explained by ball position*: it mixes estimation error with players leaving
  the picture because of where they stand, and the data cannot separate those two. No claim that the remainder is
  estimation error. (c) Otherwise: unresolved.
- **Validation (synthetic, fixed in advance).** (1) Selection only: off-camera frames have a different ball position and
  the metric depends on the ball, no estimation error → raw difference ≠ 0, matched difference ≈ 0. (2) Error only:
  a bias on off-camera frames at the same ball positions → matched difference recovers the bias. Both must pass before
  real results are reported.

Also fixed: across-match r gets n and a 95% Fisher interval; first- vs second-half r goes into the table; the 14
across-match tests get Benjamini–Hochberg q; power is simulated per metric and block at the team-matches that were
actually measurable (1,000 runs); the permutation p uses (k+1)/(n+1).

### Results (2026-10-22)
Synthetic validation passed first (`tests/test_trust.py`: selection only → matched difference ≈ 0; error only → bias
recovered). Real data, on- minus off-camera, median over team-matches [95% interval from resampling teams]:

| Metric | Low: all moments → same ball position | Mid: all moments → same ball position | Reading |
|---|---|---|---|
| Back-line height | −2.8 [−4.2, −1.6] → +0.8 [0.4, 0.9] | −3.2 [−4.2, −1.6] → +3.0 [1.6, 4.9] | (b), sign reverses |
| Back-line width | −3.4 [−4.3, −2.6] → −0.9 [−2.1, −0.8] | −1.7 [−2.0, −1.5] → −0.6 [−0.9, −0.2] | (b), mostly ball position |
| Back-line spread | 0.1 [−0.1, 0.2] → 0.0 [−0.2, 0.1] | 0.5 [0.3, 0.6] → 0.3 [0.0, 0.5] | low: no difference; mid (b) |
| Ball in front of line | −6.7 [−7.6, −5.5] → −1.0 [−1.3, −0.6] | −12.8 [−14.3, −11.3] → −3.0 [−5.1, −2.0] | (b), mostly ball position |
| Defence–midfield gap | −1.3 [−1.8, −0.9] → −1.5 [−2.1, −0.7] | −1.0 [−1.3, −0.6] → −0.2 [−0.9, 0.1] | low (b); mid (a) |
| Team length | −7.6 [−11.0, −5.7] → −6.4 [−9.5, −4.5] | −3.3 [−4.1, −2.2] → −2.5 [−3.7, −1.9] | (b), not ball position |
| Team width | 0.1 [−0.8, 0.5] → 0.0 [−1.2, 0.1] | −0.2 [−1.1, 0.5] → 0.3 [−1.0, 1.2] | no difference |

Team-matches with enough time at matched ball positions: 11–28 of 40 (`team_matches_matched` in
`backline/trust_table.csv`). Reading (b) means the remainder is not explained by ball position; it is not claimed to
be estimation error.

## Changes after a second review (2026-10-23)
- The 95% Fisher interval for the match-to-match r (fixed above) was dropped: team-matches repeat the same 13 teams
  and share "other matches", so treating them as independent gave intervals that excluded 0 where the permutation p
  did not (e.g. back-line height, low block: p = 0.09). A team bootstrap did not agree with the permutation either.
  r is reported with n, permutation p and Benjamini–Hochberg q only; `audit/trust_power.py` gives the sensitivity.
- The "Use for" column in the README (✓ when coverage ≥ 50%; *ranking* when ρ ≥ 0.7) was defined after the results
  were seen. It is a reading aid, not a test.
- The same-ball-position rules above were fixed before running, but after an independent review had already seen
  the sign flip of back-line height with a simpler ball-x match. The full rules (two-dimensional cells, all metrics,
  synthetic validation) were new; the direction for height was not.
