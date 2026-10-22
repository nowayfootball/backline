# audit/

Research scripts behind Table 1 of the main README, kept for transparency. They are notes, not one-command
reproductions: several read or write intermediate files (under `data/` or `/tmp`), and some test features that were
later removed, so they do not all run against the current code.

- `A_*`, `R1A_*`: independent reimplementation of the metrics and scene selection.
- `B_*`, `R2B_claims.py`: checks of the claims in the report and cards.
- `R1B_robust.py`: robustness of the dropped "defender left behind" flag (refers to the removed `scenes.OUT_OF_LINE`).
- `offside_diag.py`: offside replay. Its input is built with
  `backline.breaks.all_breaks(which="validation").to_parquet("data/offside_validation.parquet")`.
- `R2A_*`: code audit of the scene cards (reception frame, period sign, ordering).
- `verify_usual.py`: the "usual line" test (`docs/usual_line_test.md`).
- `trust_power.py` → `trust_power.csv`: power of the match-to-match test per metric and block at the team-matches
  actually measured (~20 min on 3 cores after `python -m backline.trust` has built the frame cache).
