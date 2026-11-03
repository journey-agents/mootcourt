# Bring a ledger

This is the short form. [Tutorial 2](../tutorials/02-your-own-archive.md) walks through it with every output shown, a worked mapping file and how to read the report card.

You need one row per variant per metric per experiment, with the effect, its standard error and the number of units per
arm. You do not need unit-level data.

1. Export results from your experimentation platform, or write them in the exchange format. The columns, the units and the
   vendor mappings are in [Ledger format](../ledger-format.md).
2. Check the file: `moot ledger check my-results.csv`.
3. Preview what would be admitted: `moot ingest --format generic --input my-results.csv --source-name mine --dry-run`.
4. Import it: `moot ingest --format generic --input my-results.csv --source-name mine`. The ledger gains the new rows and a
   snapshot is written. Importing the same file again changes nothing.
5. Fit and back-test: `moot fit --source mine`, then `moot backtest --source mine`.
6. Read the report in `reports/` and run [the benchmark](../benchmark.md) for the one-page summary.

If your results have no headline text, the models use the cell as the only feature and the report says so. If the ledger
holds fewer tests than the gates in the report, the answer to every comparison is undecidable, and that is the honest answer.
