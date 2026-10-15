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
