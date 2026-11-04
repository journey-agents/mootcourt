"""Where the heavy directories live: one resolver for every module that reads or writes them.

Precedence for the data root: the environment variable ``MOOTCOURT_DATA_ROOT``, then the ``data_root`` key
of the ``[storage]`` table in ``mootcourt.toml`` in the working directory, then nothing. With no root the
paths are the repo-local relative ones, so a clean clone works unchanged. With a root, every heavy
directory sits beneath it under the same names.

External volumes are often exFAT: no symlinks, no hard links, and permission changes may fail or do
nothing. ``safe_chmod`` therefore never raises, and the write paths in this package never depend on it.
"""
from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path

ENV_VAR = "MOOTCOURT_DATA_ROOT"
CONFIG_FILE = "mootcourt.toml"
# The README links to figures in the repository, whatever the data root is (the figures are small and committed).
README_FIGURES = "reports/figures"
LOW_SPACE_BYTES = 10 * 1024**3


class SidecarEnvironmentError(RuntimeError):
    """The Python environment holds macOS ``._`` sidecar files (an install on an exFAT volume), which break the plotting library."""


def sidecar_message(detail: str) -> str:
    """One line for a sidecar failure: what it is, what it breaks and the cure (round 01, R6; docs/method.md call 226)."""
    return ("the Python environment holds macOS `._` sidecar files, which an install on an exFAT volume leaves beside every file, and the "
            f"plotting library cannot read one of them ({detail}); make the environment on the internal disk and install there, or delete "
            "the sidecars (find <site-packages> -name '._*' -type f -delete); `moot doctor` reports this condition")

# Names under the root (or under the working directory when there is no root).
LAYOUT = {
    "data": "data",
    "raw": "data/raw",
    "ledger": "data/ledger",
    "reports": "reports",
    "models": "models",
    "cards": "cards",
    "cache": "cache",
    "experiments": "experiments",
}


@dataclass(frozen=True)
class StoragePaths:
    """The resolved heavy directories; ``root`` is None when the repo-local defaults are in force."""

    root: Path | None
    data: Path
    raw: Path
    ledger_dir: Path
    reports: Path
    models: Path
    cards: Path
    cache: Path
    experiments: Path

    @property
    def ledger_path(self) -> Path:
        return self.ledger_dir / "ledger.parquet"

    @property
    def gates_path(self) -> Path:
        return self.reports / "gates.json"

    def named(self) -> dict[str, Path]:
        return {"raw": self.raw, "ledger": self.ledger_dir, "reports": self.reports, "models": self.models,
                "cards": self.cards, "cache": self.cache, "experiments": self.experiments}


def data_root(environ=None, cwd: Path | None = None) -> Path | None:
    """The configured data root, or None for the repo-local defaults."""
    env = os.environ if environ is None else environ
    value = (env.get(ENV_VAR) or "").strip()
    if value:
        return Path(value).expanduser()
    conf = Path(cwd if cwd is not None else Path.cwd()) / CONFIG_FILE
    if conf.is_file():
        doc = tomllib.loads(conf.read_text(encoding="utf-8"))
        value = str(doc.get("storage", {}).get("data_root", "")).strip()
        if value:
            return Path(value).expanduser()
    return None


def storage_paths(root: Path | str | None = None, environ=None, cwd: Path | None = None) -> StoragePaths:
    """Resolve every heavy directory. An explicit ``root`` wins over the environment and the toml file."""
    base = Path(root).expanduser() if root is not None else data_root(environ, cwd)
    prefix = base if base is not None else Path()
    p = {k: prefix / v for k, v in LAYOUT.items()}
    return StoragePaths(root=base, data=p["data"], raw=p["raw"], ledger_dir=p["ledger"], reports=p["reports"],
                        models=p["models"], cards=p["cards"], cache=p["cache"], experiments=p["experiments"])


def is_hidden(name) -> bool:
    """True for dot files, which include the ``._name`` AppleDouble companions macOS writes on exFAT volumes."""
    return Path(name).name.startswith(".")


def visible_glob(directory, pattern: str) -> list[Path]:
    """Sorted ``directory.glob(pattern)`` without dot files (``._*`` sidecars, ``.DS_Store``); [] when the folder is absent.

    Every read of a folder under the data root goes through this helper, because the recommended layout is an
    exFAT volume where each file may have a binary ``._`` companion.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob(pattern) if not any(part.startswith(".") for part in p.relative_to(directory).parts))


def sidecar_files(directory) -> list[Path]:
    """The macOS ``._name`` sidecar files directly inside ``directory`` (an install or a copy on an exFAT volume leaves one beside every
    file), sorted; empty when the directory does not exist. The one listing in the package that looks for dot files on purpose (call 226)."""
    d = Path(directory)
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if p.name.startswith("._") and p.is_file())


def visible_iterdir(directory) -> list[Path]:
    """Sorted entries of a folder without dot files; [] when the folder is absent."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if not is_hidden(p))


def safe_chmod(path, mode: int) -> bool:
    """Best-effort permission change; returns False instead of raising (exFAT and some network volumes refuse)."""
    try:
        os.chmod(path, mode)
    except (OSError, NotImplementedError):
        return False
    return True


def dir_size(path: Path) -> int:
    """Total bytes of the regular files beneath ``path`` (0 when it does not exist)."""
    total = 0
    if not path.exists():
        return 0
    for dirpath, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def _existing_parent(path: Path) -> Path:
    p = path.resolve()
    while not p.exists() and p != p.parent:
        p = p.parent
    return p


def storage_report(paths: StoragePaths) -> list[dict]:
    """One row per directory: path, exists, size in bytes, free bytes of its volume, low-space flag."""
    rows = []
    for name, path in paths.named().items():
        free = shutil.disk_usage(_existing_parent(path)).free
        rows.append({"name": name, "path": str(path.resolve()), "exists": path.exists(), "bytes": dir_size(path),
                     "free_bytes": int(free), "low_space": free < LOW_SPACE_BYTES})
    return rows


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
