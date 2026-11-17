# Registration of the confirmatory analysis: text for filing with an outside registry

This file holds the registration of the confirmatory analysis reported in the paper (Section "The Registered Confirmatory Analysis"), with the facts a registry needs. It is written for filing after the analysis, and it says so.

## Status, stated plainly

- The registration below was written on 14 November 2026 and committed and pushed to the public repository as commit `afad501ea817da0a9a2669dd3f4b0e24b9bf998e` at 2026-11-14T23:29:42Z.
- The confirmatory file was fetched once, at 2026-11-15T20:37:03Z, about 21 hours later. File: `upworthy-archive-confirmatory-packages-03.12.2020.csv`, 66,517,697 bytes, sha256 `b2a88288c88f2b67d40413c9bdbebe79a1c0b5d9a9354180549f59f3bfff685f`, from the node `jd64p` of the Upworthy Research Archive.
- The analysis ran once, at code state `0385aa4`. Its reports are in `paper/data/run10-confirmatory/`, and the README there lists every departure from the registration.
- No outside registry held this text before the analysis. A filing made from this file is therefore a deposit after the analysis of a record that was dated before it. The evidence for the date is the commit time and the push record of the hosting service, and nothing else.
- All three registered verdicts are null: the prior's lead with the quarters as the units is not shown, its skill against a smoothed base rate is not shown, and the text classifier is not shown to rank better than counting arms.

## The registered text, as committed at `afad501` and unchanged since

## Registration of the confirmatory reading (written 14 November 2026, before the confirmatory file is fetched)

The user approved the download on 14 November 2026, after four reviewers had accepted the exploratory paper at commit 0166151 (tag `paper-v2-freeze-2026-11-14`). This section replaces the list of primary readings in Part C where the two differ. It is committed and pushed before the file is fetched, and the commit that holds it is the registration.

### What has been seen

Every exploratory number in the paper at 0166151. Nothing from the confirmatory file: it has never been on this machine. The Brier skill against a smoothed base rate has not been computed on any split when this is written.

### Code state

`src/` stays as it is at 0166151. Two scripts are added before the fetch, each tested on the exploratory scores only: one that fetches the one confirmatory packages file and records its checksum, and `scripts/smoothed_base_skill.py`, which reads saved scores and runs no model. The exploratory result of the second script is a post hoc exploratory number and the paper will say so.

### The smoothed base rate (fixed here, before any result of it exists)

For a cell at an origin with `k` events among `n` visible rows, and with `p_pool` the share of events among the visible rows of all cells scored at that origin (the sum of `k` over those cells divided by the sum of `n`), the smoothed base rate is `(k + m * p_pool) / (n + m)` with `m = 30`. Thirty is the row count the paper already uses as the least for a quarter's level; it was not tuned. The values of `k` and `n` come from the saved scores (`p_base * n_visible_cell` and `n_visible_cell`). The skill of a rung against it is one minus the rung's summed Brier score over the summed Brier score of the smoothed base rate, on the realized event.

### Primary readings (three) and their rules

1. The prior's lead over the base rate on the log score: P1 minus P0, with the main run's settings. Reported pooled with its 90 percent interval by test, and with the Student-t 90 percent interval on the quarterly values. "Confirmed" needs the quarter-unit interval above zero. "Base rate ahead" if that interval lies below zero. "Not shown" otherwise.
2. The prior's Brier skill against the smoothed base rate, on the realized event. "Shown" needs both the 90 percent interval by test, Bonferroni-adjusted for three readings, above zero, and the Student-t interval on the quarterly skills above zero, each end read with the margin of the paper (an end at 0.0010 or closer to zero is not clear). The skill against the unsmoothed base rate is printed beside it and carries no verdict.
3. The text classifier's captured positive lift at a quarter budget minus the arm-count rule's, paired by test, all contrasts, as Part C states it. "Ranks better than counting arms" only if the 90 percent interval lies above zero.

A correction to the paper's introduction follows from the third: with one contrast per test the arm-count rule gives every test the same count and cannot order them, so that setting cannot hold the comparison with the arm-count rule. The primary reading stays on all contrasts, where the target is known to grow with the number of arms. The reading on a target without that structure is secondary: with one contrast per test, the text classifier's captured lift at a quarter budget minus that of the random order, and its AUC within pairs of origin and cell.

### Secondary readings (no verdict words)

The calibration percentile of P1 on both binnings; coverage of the 80 and 90 percent intervals; P2 minus P1 on the log score; P2's Brier skill; the three primary readings with the date rule off; the one-contrast reading above.

### What a result means

The confirmatory split covers the same calendar as the exploratory one, so it tests each claim on further tests of the same quarters and cannot speak to a new quarter. A null on all three is the paper's main finding and is reported as such. Whatever the result, the exploratory numbers stay as printed, and the confirmatory section says for each reading whether the two agree.

### Procedure

One fetch, checksum recorded. `scripts/confirmatory_ledger.py --decision 2026-11-14` builds the ledger once. One backtest with the main run's settings and the three challengers (quarterly origins, seed 0, 500 resamples), then the by-origin scripts, the extras that hold the paired ranking, and the smoothed-base script. Then the secondary runs. A crash is fixed only if the fix cannot change a number, and is reported. The reports go to `paper/data/run10-confirmatory/`.
