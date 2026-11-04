# Uses uv when present, falls back to a plain virtualenv and pip.
# MOOTCOURT_DATA_ROOT moves every heavy folder (data, models, reports, cards, caches) to another volume.
# Set it in the environment or in an untracked .env file; unset means the repo-local folders.
# The shell variable wins: .env is read only when the variable is not already set (make assignments beat the environment).
ifndef MOOTCOURT_DATA_ROOT
-include .env
endif
export MOOTCOURT_DATA_ROOT
STORE := $(if $(MOOTCOURT_DATA_ROOT),$(MOOTCOURT_DATA_ROOT)/,)
REPORTS := $(STORE)reports
LEDGER := $(STORE)data/ledger/ledger.parquet
SOURCE ?= upworthy
HEADLINE ?= Example headline
IMPRESSIONS ?= 20000
JOBS ?= 3

ifeq ($(shell command -v uv 2>/dev/null),)
PY := .venv/bin/python
DOCS_PY := .venv/bin/python
SETUP := python3 -m venv .venv && .venv/bin/pip install -e '.[dev,docs]'
else
PY := uv run python
DOCS_PY := uv run --extra docs python
SETUP := uv sync --extra dev --extra docs
endif
MOOT := $(PY) -m mootcourt.cli

.PHONY: storage setup data fit backtest challenger challengers ablations learning-curve replay card serve test lint power audit docs docs-serve build docker-check release-check quick-check selfcheck paper-figures tables paper arxiv arxiv-check

setup:
	$(SETUP)

data:
	$(PY) scripts/download_data.py
	$(MOOT) ingest --source all

fit:
	$(MOOT) fit --source $(SOURCE)

backtest:
	$(MOOT) backtest --source $(SOURCE) --origins quarterly

# The challengers (gradient-boosted, local empirical Bayes, text-only classifier) are rungs of the main report, with their recalibrated "+cal" rungs, so this
# target is the main backtest with the challenger flags; there is no separate folder any more.
challenger challengers:
	$(MOOT) backtest --source $(SOURCE) --origins quarterly $(CHALLENGER_FLAGS)

# Ablation backtests (reports/ablations) and the learning curve (reports/learning-curve-*).
ablations:
	PY="$(PY)" scripts/run_ablations.sh $(SOURCE) $(JOBS)

# ASOS has no headline text, so the text-only classifier is left out there.
CHALLENGER_FLAGS := --challenger gbm --challenger local_eb $(if $(filter asos,$(SOURCE)),,--challenger text_lr)

learning-curve:
	$(MOOT) backtest --source $(SOURCE) --learning-curve 0.05,0.1,0.25,0.5,1 --seeds 3 $(CHALLENGER_FLAGS)

# The weekly replay of the archive (reports/replay-<source>-<snapshot>.json): what the weekly loop would have done and flagged.
replay:
	$(PY) scripts/replay_weekly.py --source $(SOURCE)

audit:
	for f in "$(REPORTS)"/scores-$(SOURCE)-*.parquet; do $(PY) scripts/leakage_audit.py --ledger "$(LEDGER)" --scores "$$f" --out "$(REPORTS)/leakage-audit-$(SOURCE).txt"; done

storage:
	$(MOOT) storage

card:
	$(MOOT) card --source $(SOURCE) --headline "$(HEADLINE)" --image-changed false --impressions $(IMPRESSIONS)

serve:
	$(MOOT) serve

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

power:
	$(MOOT) simulate gate-power

# The documentation site. The command line page is generated from the commands, then mkdocs builds with warnings as errors.
docs:
	$(DOCS_PY) scripts/gen_cli_docs.py --write
	$(DOCS_PY) -m mkdocs build --strict

docs-serve:
	$(DOCS_PY) -m mkdocs serve

build:
	uv build

# Builds the image and runs `moot doctor` in it. Needs a running Docker daemon; docs/release.md says what was and was not checked.
docker-check:
	docker build -t mootcourt:check .
	docker run --rm mootcourt:check moot --version
	work=$$(mktemp -d); trap 'rm -rf "$$work"' EXIT; \
		root="$$work/data"; mkdir -p "$$root"; chmod a+rwx "$$root"; \
		code=0; docker run --rm -v "$$root:/data" mootcourt:check moot doctor > "$$work/doctor.txt" 2>&1 || code=$$?; \
		cat "$$work/doctor.txt"; bash scripts/check_doctor_output.sh $$code "$$work/doctor.txt"

# Every check a release needs, locally: lint, tests, the writing rules, the wheel, the documentation and the version and file checks.
release-check:
	$(PY) scripts/release_check.py

# Tier B: regenerates the sample ledger's backtest in a temporary project and diffs it against tests/fixtures/quick-check/backtest-sample.json, apart
# from model ids, creation times, seconds fields and the date of a snapshot id. Exit 1 when a number moved. About two minutes.
quick-check:
	$(PY) scripts/quick_check.py

# The gate before a review round: pending markers, number audit, source resolution, writing rules, forbidden terms, the paper build, the tables,
# the generated docs, the claims register and the release checks, all run; exit 1 if any fails. Writes .claude/fleet/selfcheck-<date>.md.
selfcheck:
	$(PY) scripts/review_selfcheck.py

# Regenerates the paper's figures (vector PDFs and figures.json) from a run folder; no data root or network needed.
# Usage: make paper-figures [RUN=paper/data/run6-forward-chaining] [FIGURES=paper/figures]
RUN ?= paper/data/run6-forward-chaining
FIGURES ?= paper/figures
paper-figures:
	$(PY) scripts/paper_figures.py --run $(RUN) --out $(FIGURES)

# Rebuilds every LaTeX table of the paper from the run folder (no data root needed); each table's first line names its source relative
# to that folder. Usage: make tables [RUN=paper/data/run6-forward-chaining]
tables:
	$(PY) paper/build_tables.py --reports $(RUN) --out paper/tables

# The whole paper PDF in one command: figures and tables from the run folder, then tectonic (as the writer builds it; a first run on a
# clean machine lets tectonic fetch its LaTeX bundle). Writes paper/main.pdf, which git ignores. RUN= selects the run folder for all
# three targets; nothing here reads the data root.
paper: paper-figures tables
	cd paper && tectonic -X compile main.tex

# The arXiv source package: paper/dist/arxiv-<date>.tar.gz holds main.tex, the sections, the tables, the figure PDFs and the precompiled
# main.bbl (with references.bib beside it), nothing else; the paper is built first with tectonic keeping its intermediates so the .bbl and the
# figures are current. arxiv-check unpacks the tarball into a temporary folder and compiles it as arXiv does (pdflatex where installed,
# otherwise tectonic in TeX-only passes), requiring the page count of the ordinary build and no undefined reference. See paper/dist/README-arxiv.md.
arxiv: paper-figures tables
	cd paper && tectonic -X compile --keep-intermediates --keep-logs main.tex
	$(PY) scripts/arxiv_package.py --paper paper --out paper/dist

arxiv-check: arxiv
	$(PY) scripts/arxiv_package.py --paper paper --out paper/dist --check
