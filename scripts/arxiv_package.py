#!/usr/bin/env python3
"""Pack the paper's arXiv source tarball and check that it compiles the way arXiv does (``make arxiv``, ``make arxiv-check``).

The package (``paper/dist/arxiv-<date>.tar.gz``) holds exactly what arXiv compiles from, with ``main.tex`` at the root: ``main.tex``, the
sections, the tables, the figure PDFs, the precompiled bibliography ``main.bbl`` (arXiv does not run BibTeX; it uses the ``.bbl`` whose name
matches the main file) with ``references.bib`` beside it for the record, and any local class, style or bibliography-style file that sits at
the top of the paper folder (none at present: the paper uses ``acmart`` from TeX Live). Nothing else: no data, no reviews, no PDF, no
provenance index, no auxiliary file. Every ``\\input`` and ``\\includegraphics`` target of the sources must be in the package, or the build
fails. The archive is reproducible: members sorted, user and group fields zeroed, timestamps fixed, so the same sources give the same bytes.

The check unpacks the tarball into a fresh folder, removes ``references.bib`` so that only the ``.bbl`` can resolve citations, and compiles
three passes with ``pdflatex`` where it is installed (arXiv's default processor) or, failing that, with tectonic in TeX-only passes (``--pass
tex``, which leaves the ``.bbl`` alone; tectonic's default pass would run its own BibTeX and rewrite it). It reads the page count from the
log and lists every undefined reference or citation; ``main()`` compares the count with the ordinary build's log and exits 1 on a mismatch.

Use: ``python scripts/arxiv_package.py --paper paper --out paper/dist [--date YYYYMMDD] [--check [--engine pdflatex|tectonic]]``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import io
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

LOCAL_SUFFIXES = (".sty", ".cls", ".bst")
PAGES = re.compile(r"Output written on \S+ \((\d+) pages?")
UNDEFINED = re.compile(r"undefined", re.I)
FIXED_MTIME = 1_700_000_000  # a fixed, plausible timestamp (2023) so the archive bytes do not depend on when it was packed


def sources(paper: Path) -> list[tuple[str, Path]]:
    """``(archive name, path)`` of every file the package holds, sorted by archive name; raises when a referenced file is missing."""
    paper = Path(paper)
    if not (paper / "main.tex").is_file():
        raise FileNotFoundError(f"{paper / 'main.tex'} is missing")
    if not (paper / "main.bbl").is_file():
        raise FileNotFoundError(f"{paper / 'main.bbl'} is missing: build the paper first (tectonic -X compile --keep-intermediates main.tex)")
    files = [("main.tex", paper / "main.tex"), ("main.bbl", paper / "main.bbl")]
    if (paper / "references.bib").is_file():
        files.append(("references.bib", paper / "references.bib"))
    files += [(f"sections/{p.name}", p) for p in sorted((paper / "sections").glob("*.tex"))]
    files += [(f"tables/{p.name}", p) for p in sorted((paper / "tables").glob("*.tex"))]
    files += [(f"figures/{p.name}", p) for p in sorted((paper / "figures").glob("*.pdf"))]
    files += [(p.name, p) for p in sorted(paper.iterdir()) if p.is_file() and p.suffix in LOCAL_SUFFIXES]
    names = {n for n, _ in files}
    text = "\n".join(p.read_text(encoding="utf-8") for n, p in files if n.endswith(".tex"))
    missing = [t for t in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text) if t not in names]
    missing += [t for t in re.findall(r"\\input\{([^}]+)\}", text) if f"{t}.tex" not in names and t not in names]
    if missing:
        raise FileNotFoundError(f"the sources reference files that are not in the package: {sorted(set(missing))}")
    return sorted(files)


def build_package(paper: Path, out_dir: Path, date: str | None = None) -> Path:
    """Write ``out_dir/arxiv-<date>.tar.gz`` (date in YYYYMMDD, default today in UTC) and return its path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    date = date or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    target = out_dir / f"arxiv-{date}.tar.gz"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name, path in sources(paper):
            info = tarfile.TarInfo(name)
            data = path.read_bytes()
            info.size, info.mtime, info.mode = len(data), FIXED_MTIME, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    with open(target, "wb") as fh, gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0) as gz:
        gz.write(buf.getvalue())
    return target


def pages_of(log_path: Path) -> int:
    """The page count of the last 'Output written on ...' line of a TeX log (pdflatex writes the PDF, tectonic the XDV)."""
    hits = PAGES.findall(Path(log_path).read_text(encoding="utf-8", errors="replace"))
    if not hits:
        raise ValueError(f"no 'Output written on' line in {log_path}")
    return int(hits[-1])


def undefined_in(log_path: Path) -> list[str]:
    """Every log line that reports an undefined reference or citation."""
    return [line.strip() for line in Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines() if UNDEFINED.search(line)]


def _extract(tarball: Path, folder: Path) -> None:
    with tarfile.open(tarball) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(folder, filter="data")
        else:  # pragma: no cover - Python 3.11 without the filter
            tar.extractall(folder)


def compile_check(tarball: Path, workdir: Path, engine: str = "auto", passes: int = 3) -> dict:
    """Unpack ``tarball`` under ``workdir``, drop the ``.bib`` and compile with ``engine``; return the engine, pages and undefined lines."""
    if engine == "auto":
        engine = "pdflatex" if shutil.which("pdflatex") else "tectonic"
    if engine not in ("pdflatex", "tectonic"):
        raise ValueError("engine must be pdflatex, tectonic or auto")
    if shutil.which(engine) is None:
        raise FileNotFoundError(f"{engine} is not on the path")
    folder = Path(workdir) / "arxiv"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    _extract(Path(tarball), folder)
    bib = folder / "references.bib"
    removed = bib.exists()
    if removed:
        bib.unlink()
    if engine == "pdflatex":
        cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"]
    else:
        cmd = ["tectonic", "-X", "compile", "--pass", "tex", "--keep-intermediates", "--keep-logs", "main.tex"]
    for _ in range(passes):
        run = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
        if run.returncode != 0:
            raise RuntimeError(f"{engine} failed in {folder}:\n{run.stdout[-3000:]}\n{run.stderr[-3000:]}")
    log = folder / "main.log"
    return {"engine": engine, "pages": pages_of(log), "undefined": undefined_in(log), "bib_removed": removed, "folder": str(folder),
            "pdf": str(folder / "main.pdf"), "log": str(log)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--paper", default="paper")
    ap.add_argument("--out", default="paper/dist")
    ap.add_argument("--date", default=None, help="YYYYMMDD; default today (UTC)")
    ap.add_argument("--check", action="store_true", help="unpack the tarball in a temporary folder and compile it as arXiv does")
    ap.add_argument("--engine", default="auto", help="pdflatex, tectonic or auto (pdflatex when installed)")
    ap.add_argument("--keep", default=None, help="with --check: keep the compiled folder here instead of a temporary one")
    args = ap.parse_args(argv)
    paper = Path(args.paper)
    tarball = build_package(paper, Path(args.out), args.date)
    names = [n for n, _ in sources(paper)]
    print(f"wrote {tarball} ({tarball.stat().st_size} bytes, {len(names)} files)")
    if not args.check:
        return 0
    import tempfile

    work = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix="arxiv-check-"))
    got = compile_check(tarball, work, engine=args.engine)
    line = f"compiled with {got['engine']}: {got['pages']} pages, {len(got['undefined'])} undefined, .bib removed: {got['bib_removed']}"
    ref_log = paper / "main.log"
    code = 0
    if got["undefined"]:
        code = 1
        line += "\n" + "\n".join(got["undefined"][:10])
    if ref_log.exists():
        ref = pages_of(ref_log)
        line += f"; the ordinary build has {ref} pages"
        if ref != got["pages"]:
            code = 1
    else:
        line += "; no paper/main.log to compare the page count with (build the paper first)"
    print(line + (f"; compiled folder kept at {work}" if args.keep else ""))
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
