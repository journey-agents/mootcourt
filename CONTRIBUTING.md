# Contributing

Thank you for helping. This project forecasts the outcome of an experiment from precedent and says so plainly when it
cannot. Contributions that keep that honesty are the ones that fit.

## Set up

```
uv sync --all-extras
uv run pytest -q
uv run ruff check src tests scripts
```

Python 3.11 or newer. Keep the clone and its environment on your internal disk: on an exFAT or other external volume macOS `._` sidecar files break the install, and `UV_PROJECT_ENVIRONMENT` set to a path on the internal disk is the cure (see `docs/troubleshooting.md`). The tests need no network and no data of your own. Tests that need the downloaded archives are
marked `realdata` and skip when the raw data folder is absent. Put large files, reports and caches under the data root
(`MOOTCOURT_DATA_ROOT`), never inside the repository.

## What a change needs

- A test that fails before the change and passes after it. Do not weaken an existing assertion to make a change pass.
- Code that matches the surrounding style. Lines are at most 150 characters and `ruff` must be clean.
- No model call and no network call in any default code path. Optional adapters run only when a user configures them.
- Forecasts and scores keep their units and their uncertainty. A new number in a report says what it is measured on.
- A line in `CHANGELOG.md` for anything a user can see.

## Writing rules

Tests scan every committed text file, file name, card text and command help.

- No em dash and no en dash. Use a comma, a colon or the word "to".
- Do not use the word for the role of the party that launches an experiment; write "the launching team".
- Do not name the employer, team or person the project was built for, and do not address a company as its intended
  reader. Company names appear only where they are a surveyed product, a citation or one export format among several
  (the related work pages, the importers and their documentation).

`uv run pytest tests/test_writing_rules.py` runs the scan.

## Pull requests

Describe what changed and why, and say what you ran. Keep a pull request to one idea. A change to the method needs an
entry in `docs/method.md` that says what was decided and what was measured.

## Submitting a report card from a new archive

The benchmark is maintained through this repository, by issues and pull requests. To submit the report card of an archive that is not in it yet, open a pull request that adds a run folder under `paper/data/` with its `README.md`. The README names the commit the run used, the stages that were run, the archive and its licence, and the command that regenerates every file in the folder. Keep the raw archive out of the repository, as above.

## Release

The checklist is in `docs/release.md`; `make release-check` runs it locally.
