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
`audit/trust_power.py` simulates the real design (13 teams, 1–7 matches each): false-positive rate 0.04; detection
rate 0.16, 0.43 and 0.85 for team effects explaining 20%, 40% and 60% of the variance.

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
