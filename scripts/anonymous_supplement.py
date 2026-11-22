"""Build the anonymized supplement for a double-blind venue: the code, the reports, the plans and the registration.

The anonymous version of the paper (``scripts/tmlr_build.py``) says that the code, the reports and the plan are in
the anonymized supplementary material. This script writes that material as one zip archive from the tracked files:

* It takes the package, the scripts, the tests, the manual with its plans, the run folders and the code that writes the
  tables. It leaves out every file whose job is to say who made the project: the top-level notes, the license, the
  citation file, the paper's own sources and the continuous-integration settings.
* It rewrites text. The package's name becomes a neutral one, in file names too, so the code still runs. Links to the
  repository, the archive of releases and the registry, electronic addresses, and every commit of this repository are
  replaced by a phrase that says they are withheld.
* It then reads every file it is about to pack and stops, writing no archive, if a string of ``FORBIDDEN`` is still
  there. A stop names the file, so the file can be fixed or left out.

Usage: ``python scripts/anonymous_supplement.py --out paper/dist`` writes ``supplement-anonymous-<date>.zip``.
No model is called and nothing is fetched.
"""
from __future__ import annotations

import argparse
import functools
import importlib.util
import lzma
import re
import subprocess
import sys
import tomllib
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tmlr_build", Path(__file__).with_name("tmlr_build.py"))
_tmlr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tmlr)

# the strings the anonymous paper may not typeset, and three more that only files outside the paper hold
# "journey" alone is a common word in the manual, so the two forms that name the project stand in for it here
ORGANIZATION = "journey-agents"
OWN_REGISTRATION = ("jf5ds",)          # the registry page of this project; the registry pages of the public archives are kept
FORBIDDEN = tuple(dict.fromkeys((*(w for w in _tmlr.FORBIDDEN if w != "journey"), ORGANIZATION, "journey-ai", *OWN_REGISTRATION,
                                 "claude.ai/code")))
INCLUDED = ("src/", "scripts/", "tests/", "docs/", "examples/", "paper/data/", "paper/summary_tables/")
INCLUDED_FILES = ("paper/build_tables.py", "pyproject.toml", "uv.lock", "Makefile", "DATA.md", "mootcourt.toml")
# files that exist to handle identity, so they name what they withhold; and pages of the manual about the project itself
EXCLUDED = ("docs/release.md", "scripts/anonymous_supplement.py", "tests/test_anonymous_supplement.py", "scripts/tmlr_build.py",
            "tests/test_tmlr_build.py",
            "scripts/arxiv_package.py", "tests/test_arxiv_package.py")
TOP = "supplement"
REPLIES = "paper/dist/stored-replies"          # one archive of stored model replies per run; kept out of git, which holds text only
FIXED_TIME = (1980, 1, 1, 0, 0, 0)          # the archive records no time of the build

_LINK = re.compile(r"(?:https?://|git@)?[A-Za-z0-9.-]*(?:github\.com|githubusercontent\.com|github\.io|zenodo\.org|doi\.org/10\.5281|osf\.io/(?:"
                   + "|".join(OWN_REGISTRATION) + r"))[^\s<>\"'`\\)\]}|]*")
_IDENTIFIER = re.compile(r"10\.5281/zenodo\.\d+")
_ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_HEX = re.compile(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])")
_NAMES = ((re.compile("Moot Court"), "AnonTool"), (re.compile("MOOTCOURT"), "ANONTOOL"), (re.compile("mootcourt"), "anontool"),
          (re.compile("Mootcourt"), "Anontool"), (re.compile(r"\bmoot\b"), "anontool"), (re.compile(r"\bMoot\b"), "AnonTool"))
_OTHER = ((re.compile(re.escape(ORGANIZATION) + r"(?:/[A-Za-z0-9_.-]+)?"), "(repository withheld)"), (re.compile("(?i)zenodo"), "(archive withheld)"),
          (re.compile("|".join(OWN_REGISTRATION)), "(registration withheld)"))
ADDRESS = "withheld@example.invalid"          # still an address in form, so a file that must hold one stays valid

NOTE = """# Supplementary material

This archive holds the code, the reports and the plans behind the submission, made anonymous for review.

- `src/anontool/`: the package. `scripts/`: the run drivers and the audits. `tests/`: the test suite.
- `docs/`: the manual. `docs/method.md` records the numbered design decisions, `docs/superpowers/plans/` holds the plans
  written before results, and `docs/confirmatory-registration.md` is the registration of the confirmatory analysis.
- `paper/data/<run>/`: the reports behind every number of the paper, one folder per run, each with a README.
- `paper/summary_tables/` and `paper/build_tables.py`: the code that writes the paper's tables from those reports.

What was changed for review. The package's name is replaced by a neutral one, in file names too. Links to the
repository, to the archive of releases and to the registry are withheld, and so are electronic addresses and the
identifiers of commits. Files that say who made the project are left out, and so are the paper's own sources. Nothing
else differs from the code the paper's numbers came from.

- `stored-replies/`: the stored replies of the language models, one archive per run of the simulated readers, when the
  build found them. Each holds one file per request with the request and the reply, and the run folder's README gives
  its checksum. Unpack one and pass its `transcripts` folder to the scoring stages to rebuild that run's reports.

To install and test: `uv sync --all-extras`, then `uv run pytest -p no:cacheprovider`. A test that checks a link, a
commit or the package's name against the public project can fail in this archive for that reason alone.
"""


def included(path: str) -> bool:
    """Whether a tracked file goes into the supplement."""
    if path in EXCLUDED:
        return False
    return path in INCLUDED_FILES or path.startswith(INCLUDED)


@functools.lru_cache(maxsize=4)
def _commit_prefixes(commits: frozenset) -> frozenset[str]:
    return frozenset(c[:n] for c in commits for n in range(7, len(c) + 1))


def people(root: Path) -> tuple[str, ...]:
    """The names the project's metadata gives its authors and maintainers, read at build time so no name is written here."""
    try:
        project = tomllib.loads((Path(root) / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    except (OSError, ValueError):
        return ()
    return tuple(dict.fromkeys(str(p["name"]) for key in ("authors", "maintainers") for p in project.get(key, []) if p.get("name")))


def _person_patterns(names) -> list[re.Pattern]:
    """Each full name, then every word of a name of five letters or more, alone or run together with other letters."""
    words = {w for name in names for w in re.findall(r"[A-Za-z]{5,}", name)}
    return [re.compile(re.escape(name)) for name in names] + [re.compile(rf"(?i)[A-Za-z0-9_.]*{re.escape(w)}[A-Za-z0-9_.]*") for w in sorted(words)]


def scrub(text: str, commits, names=()) -> str:
    """The text with links, addresses, commits and the authors' names withheld and the package's name replaced."""
    known = _commit_prefixes(frozenset(commits))

    def link(m: re.Match) -> str:
        tail = re.search(r"[.,;:]+$", m.group())
        return "(link withheld)" + (tail.group() if tail else "")

    text = _LINK.sub(link, text)
    text = _IDENTIFIER.sub("(identifier withheld)", text)
    text = _ADDRESS.sub(ADDRESS, text)
    for pattern in _person_patterns(names):
        text = pattern.sub("(name withheld)", text)
    for pattern, new in _OTHER:
        text = pattern.sub(new, text)
    text = _HEX.sub(lambda m: "(commit withheld)" if m.group() in known else m.group(), text)
    for pattern, new in _NAMES:
        text = pattern.sub(new, text)
    return text


def anonymous_path(path: str) -> str:
    for pattern, new in _NAMES:
        path = pattern.sub(new, path)
    return path


def identity_hits(name: str, data: bytes) -> list[str]:
    """The forbidden strings a packed file still holds, in its path or in its bytes."""
    low = name.lower().encode() + b"\n" + data.lower()
    return [f"{name}: {word!r}" for word in FORBIDDEN if word.encode() in low]


def _tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files"], check=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line]


def _commits(root: Path) -> frozenset[str]:
    out = subprocess.run(["git", "-C", str(root), "rev-list", "--all"], check=True, capture_output=True, text=True).stdout
    return frozenset(line for line in out.split() if line)


def build(root, out, files=None, commits=None) -> Path:
    """Write the archive at ``out`` and return its path; stop without an archive when a file still names the project."""
    root, out = Path(root), Path(out)
    files = _tracked(root) if files is None else list(files)
    commits = _commits(root) if commits is None else commits
    names = people(root)
    packed: dict[str, tuple[bytes, int]] = {f"{TOP}/README.md": (NOTE.encode("utf-8"), 0o644)}
    for path in sorted(p for p in files if included(p)):
        source = root / path
        if not source.is_file():
            continue          # tracked and deleted in the working tree
        data = source.read_bytes()
        try:
            data = scrub(data.decode("utf-8"), commits, names).encode("utf-8")
        except UnicodeDecodeError:
            pass          # a binary file is packed as it is and still checked below
        packed[f"{TOP}/{anonymous_path(path)}"] = (data, 0o755 if path.endswith(".sh") else 0o644)
    hits = [hit for name, (data, _) in packed.items() for hit in identity_hits(name, data)]
    replies = sorted((root / REPLIES).glob("*.tar.xz")) if (root / REPLIES).is_dir() else []
    for source in replies:          # compressed, so the check reads the unpacked bytes
        data = source.read_bytes()
        hits += identity_hits(f"{TOP}/stored-replies/{source.name}", lzma.decompress(data))
        packed[f"{TOP}/stored-replies/{source.name}"] = (data, 0o644)
    if hits:
        raise SystemExit("not written: these files still name the project\n  " + "\n  ".join(hits[:60])
                         + (f"\n  and {len(hits) - 60} more" if len(hits) > 60 else ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(packed):
            data, mode = packed[name]
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = mode << 16
            z.writestr(info, data)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", required=True, help="the folder the archive is written into")
    args = parser.parse_args(argv)
    path = build(args.root, Path(args.out) / f"supplement-anonymous-{date.today():%Y%m%d}.zip")
    with zipfile.ZipFile(path) as z:
        print(f"wrote {path} ({path.stat().st_size} bytes, {len(z.namelist())} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
