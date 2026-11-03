Run 3 (round 00 fixes, 3 Nov 2026): every report of the full rerun after the code fixes of task T-054 (chunk L), from `scripts/run_experiments.sh`. The method changed, so this is a new folder beside `run2-prelaunch-clean`.

- The three main backtests include the challengers and their recalibrated rungs (`GBM+cal`, `local_eb+cal`, `text_lr+cal`).
- `ablations/` holds every ablation, including the guard-off variants (`<ablation>+p2-guard-off`), `pairwise-off`, `admission-prelaunch` and the cautionary run; `p2-guard-*.json` are the guarded against unguarded comparisons.
- `positive-control/` is the synthetic archive with a planted text signal of 1.0 percent lift.
- `gates.json` holds the gates by test at base rates 0.09, 0.14 and 0.30 (90 percent interval); the earlier per-row gates at base rate 0.3 are in `run2-prelaunch-clean`.
- The cautionary run's per-row scores (`scores-upworthy-*effect-scale-relative*.parquet`) stay on the data root; `paper/build_tables.py` reads them from there.
