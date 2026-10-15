# audit/

Research scripts behind Table 1 of the main README, kept for transparency. They are notes, not one-command
reproductions: several read intermediate files written by earlier steps (relative `data/` folder) and some target
features that were later removed (e.g. `R1B_robust.py` tests the dropped "defender left behind" flag).

- `A_*`, `R1A_*`: independent reimplementation of the metrics and scene selection.
- `B_*`, `R2B_claims.py`: checks of every claim in the report and cards.
- `R1B_robust.py`: robustness of the dropped "left behind" flag (off-camera share, ±0.5 s timing).
- `offside_diag.py`: offside replay (uses `backline.breaks` with `which="validation"` to build its input).
- `R2A_*`: code audit of the scene cards (reception frame, period sign, ordering).
- `verify_usual.py`: the pre-written "usual line" test (`docs/usual_line_test.md`).
