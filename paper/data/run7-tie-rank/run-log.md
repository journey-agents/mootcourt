# Run log

A timed run of the pipeline. A run from a clean copy of the files git would commit says so on the `run` line;
any other run states how it differs there.

- archives: archives copied from /Volumes/Crucial X10/mootcourt-data, not downloaded; copy time 0.2 s (in place of a fetch time)
- commit: 82ba862 plus uncommitted changes (the digest above identifies the files that ran)
- data: verified checksums of existing archives; nothing was downloaded in this run
- files: 748
- load_end: 91.96 58.16 38.12
- load_start: 7.21 11.26 12.20
- machine: Apple M1, 8 cores
- python: Python 3.13.9
- run: clean copy of the files git would commit, data root /Volumes/Crucial X10/mootcourt-data/timed-run-7; the data line below says whether anything was downloaded; the Python environment came from the uv cache, so the setup stage is not a cold install
- seed: 0 for fit and backtest; 20261102 for the power run
- tree_sha256_16: 00b348180c492b75
- uv: uv 0.10.5 (5fa874f03 2026-02-24)

| stage | exit code | seconds |
|---|---|---|
| setup | 0 | 1.4 |
| data | 0 | 41.9 |
| power | 0 | 836.7 |
| fit-upworthy | 0 | 34.6 |
| backtest-upworthy | 0 | 279.2 |
| fit-asos | 0 | 3.5 |
| backtest-asos | 0 | 26.1 |
| fit-synthetic | 0 | 4.4 |
| backtest-synthetic | 0 | 36.1 |
| challenger-gbm | 0 | 706.1 |
| audit-upworthy | 0 | 11.9 |
| audit-asos | 0 | 1.1 |
| audit-synthetic | 0 | 1.3 |
| inventory | 0 | 8.4 |
| data-verify | 0 | 13.3 |
| latency | 0 | 18.2 |

Checksum verification 3.8 s, no download in this run (the download script's own timing). Compute 2020.4 s. Total 2024.2 s.
Main pipeline (setup, data, power, fit-upworthy, backtest-upworthy, fit-asos, backtest-asos, fit-synthetic, backtest-synthetic): 1263.9 s, against the 30 minute budget.
