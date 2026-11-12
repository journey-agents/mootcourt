# The anonymized single-column version

The paper has one set of sources. `make paper` builds the named preprint from `paper/main.tex`. `make tmlr` builds a second, anonymized
version for a double-blind venue from the same text, so the two cannot drift apart.

## How it is made

`scripts/tmlr_build.py` writes `paper/tmlr-submission.tex` (not committed) and compiles it. It changes five things:

- **Preamble.** `paper/tmlr/preamble.tex` replaces the class and the title block. It names no author.
- **Abstract.** `paper/sections/abstract-tmlr.tex`, one paragraph kept with the sections so the number audit reads it, replaces the structured abstract.
- **Order.** Blocks marked `%% tmlr:move-begin ID` to `%% tmlr:move-end ID` in the sources move to the start of the appendix. A line
  `%% tmlr:stub ID TEXT` gives the sentence left in the body.
- **Bibliography style.** `plainnat`, or the venue's style when its file is present.
- **Layout and name.** Floats are placed where they are cited, tables keep their natural size, and the package's name is withheld.

Text that would name the author, the repository, a release or a commit is written in the sources as `\iftmlr ANONYMOUS\else NAMED\fi`.
The script refuses to write a file in which a forbidden string would still be typeset.

## The venue's style file

The venue requires its own style file. `tmlr.sty` and `tmlr.bst` are not committed (git ignores them); fetch them into this folder from
the venue's public template, which the user approved on 11 November 2026:

```bash
for f in tmlr.sty tmlr.bst; do curl -sSL -o paper/tmlr/$f https://raw.githubusercontent.com/JmlrOrg/tmlr-style-file/main/$f; done
```

With the files present `make tmlr` uses them and the first page reads "Under review as submission to TMLR". Without them the build
falls back to a plain single-column layout of the same text width, which is enough to check the text, the order and the page count.

## Decisions recorded here

- The package's name leads to the repository, so the build replaces the name, the import name and the command with neutral ones
  (`withhold_name` in the script). Two reviewers of the first anonymous build named this as the clearest leak.
- Commit identifiers, the archive DOI, release numbers and the public copy of the plan appear only in the named branch of an
  `\iftmlr` conditional. The anonymous branch says the code, the reports and the plan are in the anonymized supplementary material.
- Floats take `[!htbp]` and tables keep their natural size up to the text width. The sources ask for the top of a column, which in one
  column sent most tables behind the references.
- Citations are parenthetical in the anonymous build.
- Repository paths such as `paper/build_tables.py` stay. They identify nothing without the name.
