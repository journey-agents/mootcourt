# The arXiv source package

`make arxiv` writes `paper/dist/arxiv-<date>.tar.gz` (not committed; this note and `metadata.md` are). arXiv compiles from the tarball's
root with `main.tex` as the main file, so the archive keeps the paper's own layout: `main.tex`, `main.bbl`, `references.bib`,
`sections/*.tex`, `tables/*.tex`, `figures/*.pdf`. Nothing else is in it: no run data, no reviews, no PDF, no provenance index
(`figures/figures.json` stays in the repository), no auxiliary file. The archive is reproducible (sorted members, user and group fields zeroed, fixed
timestamps), so two builds of the same sources give the same bytes.

## Which processor to select on arXiv, and why

Select **PDFLaTeX** (TeX Live 2025, arXiv's default as of November 2026). `main.tex` loads `acmart` with the options `sigconf` and
`nonacm`, plus `booktabs`, `graphicx`, `amsmath` and `xcolor`; it uses no `fontspec`, no Unicode font and no engine-specific package, and
the fonts `acmart` loads (Libertine and the matching mathematics) are in TeX Live 2025. arXiv's processor is chosen in the submission
interface ("you will be asked which of the processor you want to use"); no `00README` directive is needed. The paper is built day to day
with tectonic, which is XeTeX inside, and arXiv added XeLaTeX support in November 2025, so XeLaTeX would also compile it; pdfLaTeX is the
safer default because it is the processor arXiv has run longest and because nothing in the sources needs anything else.

## The bibliography

arXiv does not run BibTeX. The package carries the precompiled `main.bbl`, named after the main file as arXiv requires, written by
tectonic's BibTeX from `references.bib` with the `ACM-Reference-Format` style; `references.bib` is included beside it for the record and
is not used by arXiv. `make arxiv` rebuilds the paper first with `tectonic -X compile --keep-intermediates --keep-logs main.tex`, so the
`.bbl` is current with the sources. If a later edit adds or removes a citation, rerun `make arxiv`; a stale `.bbl` shows up as an
undefined citation in the check below.

## The compile check

`make arxiv-check` unpacks the tarball into a temporary folder, deletes `references.bib` there so that only the `.bbl` can resolve
citations, compiles three passes, reads the page count from the log and lists every undefined reference or citation; it exits 1 when the
count differs from the ordinary build's (`paper/main.log`) or anything is undefined. The engine is `pdflatex` where it is installed (the
way arXiv compiles) and otherwise tectonic in TeX-only passes (`--pass tex`, which leaves the `.bbl` untouched; tectonic's default pass
would run its own BibTeX and rewrite it). On the packaging machine, 4 November 2026, pdflatex was not installed: the check ran with
tectonic and gave 27 pages, the ordinary build's count, with no undefined reference and the `.bbl` unchanged. The pdflatex path is what
`tests/test_arxiv_package.py` runs wherever pdflatex is present and is the one to repeat before upload; the processor selected on arXiv
is pdfLaTeX either way.

## Before uploading

- Remove every `% PENDING-T0nn` marker from the sources (they name tasks whose numbers were not final at packaging time); the `% src:`
  provenance comments can stay, they name paths inside the repository.
- Figures are vector PDFs read through `graphicx`, which arXiv accepts as they are (PDF, PNG or JPEG; no conversion on arXiv's side).
- Run `make arxiv-check` once more on the final sources and paste the metadata from `metadata.md`.
