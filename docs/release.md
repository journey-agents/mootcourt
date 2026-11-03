# Release

Moot Court follows [semantic versioning](https://semver.org). Before 1.0.0 a minor version may change a command line option,
the ledger schema or the card schema; the change is listed in `CHANGELOG.md` and the schema versions are bumped. A patch
version fixes a defect and changes no interface.

## Checklist

`make release-check` runs the automatic part of this list. The rest is by hand. The wheel check installs the wheel with its dependencies from the package index, so the command needs network access (or a warm uv cache); every other check is local.

1. The version in `pyproject.toml` equals `mootcourt.__version__` and heads the newest entry of `CHANGELOG.md`.
2. `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `LICENSE` and `README.md` exist.
3. `uv run ruff check src tests scripts` is clean.
4. `uv run pytest -q` passes with no network and no data root. The writing-rules test is part of it.
5. `uv build` produces a wheel and a source archive, and the wheel installs in a clean environment and runs `moot --version`.
6. `make docs` builds the documentation with no warnings.
7. The image builds and runs `moot doctor`. The `docker` job of the CI workflow does this on every push and pull request; `make docker-check` does it locally where a Docker daemon is available.
8. The reference reports in the data root were produced at the commit being released: `scripts/render_readme_results.py --check`
   passes and `paper/data` holds the same JSON.
9. By hand: read the README top to bottom as a stranger would, tag the commit `v<version>`, and publish.

## Continuous integration

`.github/workflows/ci.yml` runs on every push to `main` and every pull request: lint, the tests on Python 3.11, 3.12 and 3.13
(no network, no data root), the writing-rules test on its own, a wheel build that installs the wheel in a clean environment, the
documentation build with warnings as errors, and a `docker` job that builds the image and runs `moot doctor` inside it (exit code
0 or 1 passes; 1 is the expected answer on an empty data root). Actions are pinned by commit SHA with the version in a comment,
every `uv sync` is `--locked`, and `.github/dependabot.yml` proposes updates to the actions, the Python dependencies and the base image.

## The image

The `Dockerfile` builds a CPU image on a slim Python base, installs exactly the versions in `uv.lock` (`uv sync --locked --no-dev`,
with uv pinned in the build stage) into a virtual environment, runs as a non-root user and declares `/data` as the data root and as a
volume. The base image is pinned by tag, not by digest, because a digest cannot be looked up without a registry; the dependabot
configuration keeps the tag current.

```
docker build -t mootcourt .
docker run --rm -v "$PWD/mootcourt-data:/data" mootcourt
```

With no command the container runs `moot doctor`. On an empty data root it reports warnings (no ledger, no model) and exits
with code 1; that is the expected first answer. Mount a data root with a ledger and fitted models to get a healthy report.
Other commands go after the image name, for example `docker run --rm -v "$PWD/mootcourt-data:/data" mootcourt moot storage`.

## What was checked on which machine

The first release was prepared on a machine where the Docker daemon was not running, so the image was not built there. The image is
verified by the `docker` job of the CI workflow on a hosted runner: that job is the evidence that the `Dockerfile` builds and that
`moot doctor` runs in it, and a release is tagged only after it has passed. The same job and the rest of the workflow have not
run yet, because the workflow was written on that machine against the commands that `make release-check` runs locally. `make
docker-check` repeats the build and the doctor run where a daemon is available.

Project URLs (home page, repository, issues, changelog) live under `[project.urls]` in `pyproject.toml` and point at the
GitHub repository `journey-agents/mootcourt`. Update them if the repository moves.
