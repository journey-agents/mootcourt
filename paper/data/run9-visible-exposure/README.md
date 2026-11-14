Run 9 (14 November 2026): the pipeline of run 8 with two defaults changed, plus the additions of its plan (`docs/superpowers/plans/2026-11-14-run9-visible-exposure-main.md`). Run 8 is kept in `paper/data/run8-randomization-window`, and its reports and models stay on the data root under `reports.old-run8` and `models.old-run8`.

What changed against run 8, and why. A review of the paper by four fresh readers found that the main run read each test's realized traffic as its planned exposure, a stand-in that carries information about the result. The user decided on 14 November 2026 that the run with exposure fixed on visible rows becomes the main run. Two defaults of `moot backtest` changed: `--exposure` is `cell-median-visible` for the headline archive (every row gets the median exposure of its cell over the rows visible at its origin; `planned` stays as a diagnostic), and `--base-density` is `t` (a Student-t base rate; `normal` stays as an ablation). Nothing else about the method changed. The ladder's numbers under the new main setting were already known from three ablations of run 8; the plan lists what had and had not been seen when it was written.

One code state: every file here was written at commit b2e3713 of branch `paper-v2` (the same `src/` and `scripts/` as 85f2bb4), with `git status` for `src` and `scripts` clean at the start and no edit to them during the run, by `scripts/run_experiments.sh` (83 stages, `stages.txt`) and then `scripts/run_run9_extras.sh` (24 stages, `stages-additions.txt`), except the three files named in the next paragraph. The run started at 11:30 UTC. Its process group was suspended from 11:35 to 12:31 UTC at the request of another session on the same machine and then continued; no stage was restarted. The gate simulations in `gates.json` were reused from run 8 (same command and seed).

Three exceptions, at commit d58cb89, which changes two scripts and no file under `src/`:

- `leakage-audit-upworthy.json`. The audit stage failed in the run (exit code 1 in `stages.txt`): the script recomputed each row's `s_star` from that row's own exposure, the default before this run, so every row differed. The script now takes `--exposure cell-median-visible` and recomputes the fixed exposure itself from the rows visible at each origin, without the package's view. Rerun on the unchanged scores, it reports zero violations. A test shows that an exposure fixed on the whole ledger, which reads later rows, is flagged.
- `horizon-14/by-origin-*.json` and `horizon-28/by-origin-*.json`. These were not planned. They were added after the 28-day result was seen, to put on record that its large gap comes from the first origin (see below).

Checks made before anything was read:

- The main report's ladder rows equal run 8's ablation with the same setting (`exposure-cell-median-visible+base-density-t`) to 1e-9, as the plan required.
- Both stage files end with their done marker, and no stage but the audit has a nonzero exit code.

New against run 8:

- `horizon-14/` and `horizon-28/`: the ladder on a ledger rebuilt with each test's end assumed 14 and 28 days after its last arm was created, where the main ledger assumes seven days (`scripts/rebuild_upworthy_ledger.py --horizon-days`).
- Ablations `exposure-planned` (the realized-traffic diagnostic), `exposure-planned+base-density-normal` (run 8's main setting) and `base-density-normal`, each with its `by-origin` and `no-history` report.
- The key `exposure_realized` in the headline archive's extras report.

Removed against run 8: the ablations `base-density-t`, `exposure-cell-median-visible` and its two combinations (now the main run), and the three whole-ledger variants `exposure-cell-median*` (a diagnostic that reads later rows; it leaves the paper, and run 8 keeps its reports). `run-log.json` and `run-log.md` are carried over unchanged from the earlier folders: they describe the timed pipeline of run 7, which was not repeated.

Repeated at this run's commit, with the reading rules of `docs/superpowers/plans/2026-11-13-reviewer-runs.md`: the calibration size check, the planted control at seeds 7 to 11 (`positive-control-seeds.json`, `positive-control/seeds/`), the learning curve at all seven origins (`learning-curve-origins/`) and the split-half spread.

Snapshot ids: the headline archive (20261106-2dc461f52ea4), the retailer's archive (20261103-6bb5a15c5ff0) and the synthetic ledger (20261103-bf4fd286e2b2) are unchanged. The planted ledgers and the ledger with the date rule off were rebuilt on 14 November and carry that date with the content digests of run 8. The two horizon ledgers are new (20261114-65fd0788a1b7 and 20261114-3fc2dcaeb6f5).

What the 28-day run shows, found after the result: the fitted prior's lead over the base rate on the log score is 0.119 nats there against 0.007 in the main run. At the first origin the image-only cell has two visible rows under a 28-day end, the base rate fitted on two rows scores about minus 6.7 nats per row on that cell's 213 rows, and the fitted prior does not degrade. With the first origin left out the lead is 0.003 nats with an interval that spans zero. The plan's post-run notes give each pre-set rule and the branch it took.

Files against run 8, by `scripts/assemble_run_folder.py`: the three main backtests, the learning curves, the extras and every ablation changed; the two replays, `gates.json` and the audits of the other two sources are byte-identical.
