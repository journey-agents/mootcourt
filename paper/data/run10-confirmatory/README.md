Run 10 (15 November 2026): the registered confirmatory analysis, run once on the confirmatory split of the Upworthy Research Archive. It is not a successor of run 9. Run 9 (`paper/data/run9-visible-exposure`) stays the exploratory main run and the source of every other table of the paper; `make tables` reads run 9 by default, and only the table `fmt-confirmatory` reads this folder, through an explicit path in `paper/summary_tables/confirmatory.py`.

The decision. The user decided on 14 November 2026 that the confirmatory split is opened once, after the code is frozen and the readings are registered, and approved the download the same day (`docs/superpowers/plans/2026-11-14-run9-visible-exposure-main.md`, the fourth decision and the section "Registration of the confirmatory reading"). No other use of the file is authorized. The holdout file and the undeployed-packages file were not fetched, opened or scored.

The registration. The readings and their rules are the section "Registration of the confirmatory reading" of that plan, at commit afad501 (committed 14 November 2026, 23:29:42 UTC, and pushed to `origin/paper-v2` two seconds later), with Part C of the same plan where the two do not differ. That is about 21 hours before the fetch. The registration is a dated commit in this repository. It was not lodged with an outside registry and no journal reviewed it.

The fetch (`confirmatory-fetch-record.json`, written by `scripts/fetch_confirmatory.py --decision 2026-11-14`): the file `upworthy-archive-confirmatory-packages-03.12.2020.csv` of OSF node `jd64p`, 66,517,697 bytes, SHA-256 `b2a88288c88f2b67d40413c9bdbebe79a1c0b5d9a9354180549f59f3bfff685f`, fetched at 20:37:03 UTC on 15 November 2026. The fetch script does not open the file.

The ledger (`confirmatory-record.json`, written by `scripts/confirmatory_ledger.py --decision 2026-11-14`, the one script that reads the file): read at 20:38:25 UTC on 15 November 2026, the same size and digest, 82,810 rows of 22,743 tests, 51,151 rows admitted, snapshot `20261115-b5929079f639`. The ledger holds the confirmatory rows only. The date rule on the archive's randomization window is applied as on the exploratory split.

The code. Every report here was written at commit 0385aa4104d9ed70f1e7b0df414f7b3d8e3cb962 (`run-commit.txt`), by `scripts/run_confirmatory.sh`, which refuses to start while `src/` or `scripts/` differ from the commit and refuses a second run. `src/` at that commit is byte-identical to the frozen commit 0166151 (tag `paper-v2-freeze-2026-11-14`), at which four reviewers had accepted the exploratory paper. Against 0166151 the commit adds three scripts and changes no other: `scripts/fetch_confirmatory.py` and `scripts/smoothed_base_skill.py` (commit b031ed8, pushed on 14 November, before the fetch) and the driver `scripts/run_confirmatory.sh` (commit 0385aa4). `scripts/confirmatory_ledger.py` was already part of 0166151.

The stages, from `run-log.txt` (UTC; the run began at 20:38:32 on 15 November 2026 and ended at 01:33:21 on 16 November, every stage with exit code 0, none restarted):

| stage | what it ran | start | seconds |
|---|---|---|---|
| gates | `moot simulate gate-power`, run 9's command and seed | 20:38:32 | 1,054 |
| fit | `moot fit --source upworthy` | 20:56:06 | 110 |
| main | the one backtest: quarterly origins, the three challengers, seed 0, 500 resamples | 20:57:56 | 2,107 |
| by-origin | `scripts/by_origin_difference.py` | 21:33:03 | 5 |
| by-origin-skill | `scripts/by_origin_skill.py` | 21:33:08 | 19 |
| extras | `scripts/paper_extras.py --source upworthy --verbose` | 21:33:27 | 654 |
| null-size | `scripts/calibration_null_size.py`, 400 repetitions, seed 20261113 | 21:44:21 | 13,365 |
| smoothed-base | `scripts/smoothed_base_skill.py` | 01:27:06 | 4 |
| one-contrast | the main command line with `--contrasts one` | 01:27:10 | 371 |

Size: 13,822 tests and 50,195 rows scored at seven quarterly origins, April 2013 to April 2015, the same origins as the exploratory split (2,949 tests and 10,697 rows there). The split adds tests and no quarter.

The three primary readings and their registered verdicts (the numbers are in `paper/tables/fmt-confirmatory.tex`, each with its key):

1. P1 minus P0 on the log score: the Student-t interval with the seven quarters as units contains zero. Verdict: not shown.
2. P1's Brier skill against the smoothed base rate: the interval by test, adjusted for three readings, lies above zero with the registered margin, and the Student-t interval with the quarters as units does not (its lower end is below zero). The rule needs both. Verdict: not shown.
3. The text classifier's captured lift at a quarter budget minus the arm-count rule's: the interval contains zero. Verdict: not shown to rank better than counting arms.

Each verdict is the one the same rule gives on the exploratory split.

Deviations from the registration, and other things a reader should know:

- The registered secondary reading with the date rule off was not run. The ledger with the rule off has to be rebuilt from the packages file. The one script that does so (`scripts/rebuild_upworthy_ledger.py --window off`) reads the exploratory file only, and `scripts/confirmatory_ledger.py` has no option for the rule. No script that existed at the fetch can build that ledger for this split, and scripts were not to change after the fetch, so the reading is missing and no number of it exists.
- The driver `scripts/run_confirmatory.sh` was committed and pushed at 20:37:44 and 20:37:46 UTC on 15 November 2026, about 40 seconds after the fetch finished and before the file was read into a ledger (20:38:25). The registration says the two scripts it names are added before the fetch, and they were. The driver is a third script that the registration does not name; it only calls scripts and commands that existed before, and it was written and tested while the file was not on this machine. No result existed when it was committed.
- The report headers carry no commit field. The commit is in `run-commit.txt` and in the first line of `run-log.txt`.
- `gates.json` was simulated again by the driver with run 9's command and seed. It equals run 9's file except for its `seconds` field.
- The extras report was written by the stage of run 9's driver, so it has keys that read ablations and controls this run does not hold; they are null here (among them `exposure_realized`, `gates_by_stratum` and the positive-control keys), and it has no `sizing_evaluation` key. Nothing in the paper reads them from this folder.
- With one contrast per test, the exploratory run carried no challengers, so the secondary reading of the text classifier against the random order has no exploratory counterpart in run 9.
- The registration's procedure lists "the decision-value table" (Part C) and "the extras that hold the paired ranking". Both are in the main report and the extras report. No leakage audit, learning curve, replay or sizing run was registered, and none was run.
- Not copied here: the score tables (`scores-*.parquet`, 34 MB and 9 MB), the fitted models, the ledger and the raw file, which stay on the data root, and the four figure files and the empty folders that the stages of `scripts/run_experiments.sh` leave behind.

Files: `backtest-upworthy-20261115-b5929079f639.json` and `.md` (the main report), `by-origin-*.json`, `by-origin-skill-*.json`, `smoothed-base-skill-*.json`, `paper-extras-*.json`, `calibration-null-size-*.json`, `gates.json`, `reliability-upworthy.json`, `ablations/backtest-upworthy-20261115-b5929079f639--contrasts-one.json` and `.md`, the two records, `run-commit.txt` and `run-log.txt`.
