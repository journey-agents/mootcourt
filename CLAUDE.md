# Moot Court

Python package and command line (`moot`) that forecasts what an experiment will show from concluded experiments, scores every forecast, and abstains when the record says too little. This repository also holds the paper (`paper/`) and every run behind its numbers (`paper/data/`).

Active work: paper version 2 on branch `paper-v2`. Read `.claude/fleet/HANDOVER.md` first (local, not in git).

## Where things are

- `src/mootcourt/`: the package. `tests/`: suite. `scripts/`: run driver, extras, audits. `docs/`: manual; `docs/method.md` records numbered design decisions; `docs/superpowers/plans/` holds plans written before results.
- `paper/main.tex`, `paper/sections/`: the paper. `paper/summary_tables/` and `paper/build_tables.py` write `paper/tables/` (generated; never edit). `paper/data/<run>/`: each run's reports; the highest numbered is current, older ones are history.
- `paper/reviews/`: claims register, rubric, earlier review rounds. `paper/dist/`: arXiv metadata.
- Local and untracked: `.claude/fleet/` (working notes; `archive-v1/` holds release 1.0.0's), `.claude/skills/`, `.claude/hooks/`, `.claude/tools/status.py`, `.claude/settings.json`.

Skills: `paper-check` after paper edits, `run-experiments` before any run, `paper-review` for an independent reading. A hook checks the writing rules after each edit. `python3 .claude/tools/status.py` gives the paper's state in one screen.

## Commands

```bash
# MOOTCOURT_DATA_ROOT is set by .claude/settings.json; large data lives there, not on the internal disk
uv sync --all-extras
uv run pytest -p no:cacheprovider            # about 50 minutes; pyproject already sets -q, do not add it
make tables                                  # every generated table, from RUN (default: the current run folder)
make paper                                   # figures, tables and the PDF at paper/main.pdf
make arxiv-check                             # arXiv tarball, compiled as arXiv does
make selfcheck                               # the release gate, about one hour
uv run python scripts/paper_audit.py         # each printed number against its source line
uv run python scripts/claims_audit.py paper/reviews/claims.md paper/data/<run>
scripts/run_experiments.sh --list            # the experiment stages; --only NAME runs one, --dry-run prints
```

## Rules that bind every file

- No em dash, no en dash, no other Unicode dash. Write "to" for ranges and "minus" in prose.
- Do not use the common word for a person who possesses or is responsible for something. Write "the launching team" or "the maintainers".
- `tests/forbidden_terms.sha256` (tier 1) and `tests/restricted_terms.sha256` (tier 2) are checked by digest, in file names too. `tests/test_writing_rules.py` enforces all of this.
- Committed PDFs are rejected.
- No LLM calls in the default path. No download except a clone and `uv sync` unless the user approves that download.
- Never open an Upworthy file named holdout, confirmatory or undeployed without a recorded decision from the user. `scripts/` refuses them.

## Paper rules

- A number is never typed into a results table. Tables come from report keys through `paper/build_tables.py` and `paper/summary_tables/`. Only tables in `summary_tables.HAND_TYPED` are hand-typed, and each carries its reason.
- Each line of prose with a number has a `% src:` block directly above it naming the report and key. The digit audit can pass on a wrong source that shares digits, so read the key and confirm it is the quantity the sentence claims.
- Every claim has a row in `paper/reviews/claims.md`.
- Numbers live in tables and short lists, at most two per sentence. Prose says what to conclude. Write for a reader who knows neither archive; define terms before use.
- Decisions about an analysis are written down before its result exists. If a run changes after results are seen, the paper says so.
- A run's results come from one committed code state: commit first, then run, and record the commit in the run folder. Do not edit `src/` or `scripts/` during a run.

## Git

Commit only when asked. Do not push to `main` without a green CI run; a post-release commit once broke `main`. Fast-forward with `git push origin <branch>:main`. Large pushes may need `git config http.postBuffer 524288000`.
