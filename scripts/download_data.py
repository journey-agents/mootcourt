#!/usr/bin/env python3
"""Download the two public experiment archives from OSF and keep a checksum record.

Standard library only. Files are listed through the OSF API v2 at run time (no file id is written in this
script), streamed to ``<name>.part`` and renamed only when complete. The sha256 and byte size of every file
go into ``<data-dir>/CHECKSUMS.json`` on first download and are verified on every later run; ``--refresh`` is
the only way to re-record. Downloaded files are untrusted data: they are never imported or executed, zip
archives are checked for path traversal and size before a single byte is written, and everything lands under
``<data-dir>/raw/<source>/``.

Which files. The Upworthy archive also holds a holdout, a confirmatory and an undeployed file. The archive
asks researchers to pre-register before touching the first two, so any file whose name contains ``holdout``,
``confirmatory`` or ``undeployed`` is refused outright (``DENIED``). When the listing holds the preferred
files of a source (``PREFERRED``) only those are fetched. When the listing holds no file matching a preferred name the script
stops with exit code 4 and names the approved file it could not find; it never falls back to the other files of the node
(code review finding REV-006).
A file larger than ``--max-file-bytes`` is refused.

Exit codes: 0 success, 2 checksum mismatch, 3 OSF unreachable or in maintenance, 4 refused or failed
download or extraction, 1 anything else.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_BASE_URL = "https://api.osf.io"
NODES = {"upworthy": "jd64p", "asos": "64jsb"}
PREFERRED = {
    "upworthy": ["exploratory"],
    "asos": ["asos_digital_experiments_dataset.parquet", "datasheet"],
}
# The pattern that must match exactly one file per source (the data file); the others in PREFERRED are optional documentation.
REQUIRED = {"upworthy": ["exploratory"], "asos": ["asos_digital_experiments_dataset.parquet"]}
DENIED = ("holdout", "confirmatory", "undeployed")
# Hosts the script contacts: the OSF API and file hosts. ``--base-url`` (a local stub in tests) adds its own host.
ALLOWED_HOSTS = {"api.osf.io", "osf.io", "files.osf.io"}
_extra_hosts: set[str] = set()
DEFAULT_MAX_FILE_BYTES = 100 * 1024 * 1024
DEFAULT_MAX_EXTRACT_BYTES = 500 * 1024 * 1024
TIMEOUT = 60
CHUNK = 1 << 20
MAX_FOLDER_DEPTH = 3


class DownloadError(Exception):
    """A failure with an exit code."""

    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


# ------------------------------------------------------------------ http
class _SameSchemeRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect may not leave https for http (a stub on http may stay on http)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(req.full_url).scheme == "https" and urllib.parse.urlsplit(newurl).scheme != "https":
            raise DownloadError(f"refusing a redirect from https to {newurl}", 4)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_SameSchemeRedirect)


def _open(url: str):
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise DownloadError(f"refusing a non-http(s) url: {url}", 4)
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    if host not in ALLOWED_HOSTS | _extra_hosts:
        raise DownloadError(f"refusing {url}: the host {parts.hostname!r} is not an OSF host (allowed: {sorted(ALLOWED_HOSTS)})", 4)
    if parts.scheme == "http" and (host in ALLOWED_HOSTS or host not in _extra_hosts):
        # Plain http is for the local stub named by --base-url; the archive and its checksum are never taken over it from OSF.
        raise DownloadError(f"refusing {url}: the OSF hosts are reached over https only", 4)
    url = urllib.parse.urlunsplit(parts._replace(path=urllib.parse.quote(parts.path, safe="/%:@+,;=~")))
    req = urllib.request.Request(url, headers={"User-Agent": "mootcourt-download/1.0", "Accept": "application/json, */*"})
    try:
        return _OPENER.open(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as exc:
        if exc.code in (502, 503, 504):
            raise DownloadError(f"OSF is unavailable or in maintenance (HTTP {exc.code}) at {url}", 3) from exc
        raise DownloadError(f"HTTP {exc.code} from {url}", 3) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise DownloadError(f"cannot reach OSF at {url}: {exc}", 3) from exc


def _get_json(url: str) -> dict:
    with _open(url) as resp:
        try:
            return json.loads(resp.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise DownloadError(f"{url} did not return JSON", 3) from exc


def _safe_name(name: str) -> bool:
    bad_chars = "\\" in name or "\x00" in name
    return bool(name) and name == os.path.basename(name) and not bad_chars and name not in (".", "..") and not name.startswith(".")


def list_files(base_url: str, node: str, depth: int = 0, url: str | None = None) -> list[dict]:
    """Every file under the node's osfstorage, folders included: ``[{"name", "size", "url"}]``."""
    url = url or f"{base_url.rstrip('/')}/v2/nodes/{node}/files/osfstorage/"
    out: list[dict] = []
    while url:
        doc = _get_json(url)
        for item in doc.get("data", []):
            attrs = item.get("attributes", {})
            kind = attrs.get("kind")
            if kind == "folder":
                href = (((item.get("relationships") or {}).get("files") or {}).get("links") or {}).get("related", {})
                href = href.get("href") if isinstance(href, dict) else href
                if href and depth < MAX_FOLDER_DEPTH:
                    out += list_files(base_url, node, depth + 1, href)
            elif kind == "file":
                link = (item.get("links") or {}).get("download")
                if link:
                    out.append({"name": str(attrs.get("name", "")), "size": attrs.get("size"), "url": link})
        url = (doc.get("links") or {}).get("next")
    return out


def select_files(files: list[dict], source: str) -> tuple[list[dict], list[str]]:
    """Apply the deny list and the preferred list; returns the files to fetch and the names refused."""
    refused = [f["name"] for f in files if any(d in f["name"].lower() for d in DENIED)]
    allowed = [f for f in files if f["name"] not in refused and _safe_name(f["name"])]
    preferred = [f for f in allowed if any(p in f["name"].lower() for p in PREFERRED[source])]
    for pattern in REQUIRED[source]:
        hits = [f["name"] for f in preferred if pattern in f["name"].lower()]
        if not hits:          # a renamed data file must not leave only the documentation behind with an exit code of 0
            raise DownloadError(f"no approved file for {source} matches {pattern!r} in the listing of OSF node {NODES[source]}; nothing was "
                                f"downloaded (the listing holds {sorted(f['name'] for f in files)}). Check the node before changing the pattern", 4)
        if len(hits) > 1:     # approved names are matched by substring, so more than one hit is ambiguous and nothing is fetched
            raise DownloadError(f"the approved pattern {pattern!r} for {source} matches more than one file {sorted(hits)}; nothing was downloaded. "
                                "Narrow the pattern in the script after checking which file is meant", 4)
    return preferred, refused


# ------------------------------------------------------------- checksums
def sha256_of(path: Path) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
            n += len(block)
    return h.hexdigest(), n


def load_checksums(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_checksums(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")
    try:
        os.chmod(tmp, 0o644)
    except OSError:   # exFAT and some network volumes refuse permission changes
        pass
    os.replace(tmp, path)


def verify_file(path: Path, entry: dict) -> str | None:
    """None when the file matches its record, else a message naming the file."""
    if not path.exists():
        return f"{path.name}: recorded in CHECKSUMS.json but missing on disk"
    digest, size = sha256_of(path)
    if size != entry["size"] or digest != entry["sha256"]:
        return (f"{path.name}: checksum mismatch (recorded size {entry['size']} sha256 {entry['sha256'][:12]}..., "
                f"found size {size} sha256 {digest[:12]}...). Use --refresh only if you mean to re-record.")
    return None


# -------------------------------------------------------------- download
def fetch(url: str, dest: Path, expected: int | None) -> tuple[str, int]:
    """Stream ``url`` to ``dest.part`` and rename on completion; returns (sha256, size)."""
    part = dest.with_name(dest.name + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    h, n = hashlib.sha256(), 0
    try:
        with _open(url) as resp, part.open("wb") as fh:
            declared = resp.headers.get("Content-Length")
            for block in iter(lambda: resp.read(CHUNK), b""):
                h.update(block)
                fh.write(block)
                n += len(block)
            fh.flush()
            os.fsync(fh.fileno())
        if declared is not None and int(declared) != n:
            raise DownloadError(f"{dest.name}: received {n} bytes, server declared {declared}", 4)
        if isinstance(expected, int) and expected != n:
            raise DownloadError(f"{dest.name}: received {n} bytes, the listing says {expected}", 4)
        os.replace(part, dest)
    except DownloadError:
        part.unlink(missing_ok=True)
        raise
    except Exception as exc:        # IncompleteRead, connection reset, disk full
        part.unlink(missing_ok=True)
        raise DownloadError(f"{dest.name}: download failed: {exc}", 4) from exc
    return h.hexdigest(), n


# ------------------------------------------------------------ extraction
def extract_zip(archive: Path, target: Path, max_bytes: int) -> list[str]:
    """Extract a zip into ``target`` after checking every member; nothing is written when a check fails."""
    try:
        zf = zipfile.ZipFile(archive)
    except zipfile.BadZipFile as exc:
        raise DownloadError(f"{archive.name}: not a valid zip file", 4) from exc
    with zf:
        root = target.resolve()
        plan = []
        total = 0
        for info in zf.infolist():
            name = info.filename
            if name.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", name) or "\x00" in name:
                raise DownloadError(f"{archive.name}: unsafe member name {name!r} (absolute path)", 4)
            parts = re.split(r"[\\/]+", name)
            if ".." in parts:
                raise DownloadError(f"{archive.name}: unsafe member name {name!r} (path traversal)", 4)
            dest = (root / name).resolve()
            if root != dest and root not in dest.parents:
                raise DownloadError(f"{archive.name}: member {name!r} would leave the target directory", 4)
            if info.is_dir():
                continue
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise DownloadError(f"{archive.name}: symbolic link member {name!r} refused", 4)
            total += info.file_size
            if total > max_bytes:
                raise DownloadError(f"{archive.name}: extracted size would exceed {max_bytes} bytes", 4)
            plan.append((info, dest))
        written, done = 0, []
        try:
            for info, dest in plan:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, dest.open("wb") as out:
                    for block in iter(lambda: src.read(CHUNK), b""):
                        written += len(block)
                        if written > max_bytes:
                            raise DownloadError(f"{archive.name}: extracted size exceeded {max_bytes} bytes", 4)
                        out.write(block)
                done.append(dest)
        except Exception:
            for d in done:
                d.unlink(missing_ok=True)
            raise
    return [str(d.relative_to(root)) for d in done]


# ------------------------------------------------------------------ main
def run(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir)
    checks_path = data_dir / "CHECKSUMS.json"
    record = load_checksums(checks_path)
    sources = list(NODES) if args.source == "all" else [args.source]
    _extra_hosts.add((urllib.parse.urlsplit(args.base_url).hostname or "").lower())
    t0, n_new, n_ok, n_bytes = time.monotonic(), 0, 0, 0
    problems: list[str] = []
    for source in sources:
        raw = data_dir / "raw" / source
        prefix = f"raw/{source}/"
        if args.verify_only:
            if not any(k.startswith(prefix) for k in record):
                problems.append(f"{source}: CHECKSUMS.json records no file for this source, so nothing was verified; run without --verify-only")
            for key, entry in sorted(record.items()):
                if key.startswith(prefix):
                    msg = verify_file(data_dir / key, entry)
                    if msg:
                        problems.append(msg)
                    else:
                        n_ok += 1
                        print(f"verified  {key}")
            continue
        listing = list_files(args.base_url, NODES[source])
        chosen, refused = select_files(listing, source)
        for name in refused:
            print(f"refused   {source}/{name}: deliberately not used (the archive asks for pre-registration before touching it)")
        if not chosen:
            raise DownloadError(f"no approved file for {source} in the listing of OSF node {NODES[source]}: expected a file whose name contains "
                                f"one of {PREFERRED[source]}; nothing was downloaded (other files of the node are never fetched)", 4)
        for f in chosen:
            name, key = f["name"], prefix + f["name"]
            dest = raw / name
            size = f.get("size")
            if isinstance(size, int) and size > args.max_file_bytes:
                raise DownloadError(f"{name}: {size} bytes exceeds --max-file-bytes {args.max_file_bytes}", 4)
            entry = record.get(key)
            if entry is not None and not args.refresh:
                msg = verify_file(dest, entry) if dest.exists() else None
                if msg:
                    problems.append(msg)
                    continue
                if dest.exists():
                    n_ok += 1
                    print(f"verified  {key}")
                    if dest.suffix == ".zip":
                        extract_zip(dest, raw, args.max_extract_bytes)
                    continue
            digest, n = fetch(f["url"], dest, size if isinstance(size, int) else None)
            if entry is not None and not args.refresh and (digest != entry["sha256"] or n != entry["size"]):
                dest.unlink(missing_ok=True)
                problems.append(f"{name}: re-downloaded file does not match the recorded checksum")
                continue
            record[key] = {"sha256": digest, "size": n, "osf_node": NODES[source]}
            save_checksums(checks_path, record)
            n_new += 1
            n_bytes += n
            print(f"downloaded {key}  {n} bytes  sha256 {digest[:12]}...")
            if dest.suffix == ".zip":
                extract_zip(dest, raw, args.max_extract_bytes)
    if problems:
        for p in problems:
            print(f"ERROR {p}", file=sys.stderr)
        return 2
    print(f"ok: {n_new} downloaded ({n_bytes} bytes), {n_ok} verified, {time.monotonic() - t0:.1f} s")
    return 0


def default_data_dir() -> str:
    """The data directory under the storage root, resolved like ``mootcourt.storage`` (this script is standalone).

    Order: the environment variable MOOTCOURT_DATA_ROOT, then data_root under [storage] in mootcourt.toml in the
    working directory, then the repo-local ``data`` folder.
    """
    value = os.environ.get("MOOTCOURT_DATA_ROOT", "").strip()
    conf = Path.cwd() / "mootcourt.toml"
    if not value and conf.is_file():
        import tomllib

        value = str(tomllib.loads(conf.read_text(encoding="utf-8")).get("storage", {}).get("data_root", "")).strip()
    if value:
        return str(Path(value).expanduser() / "data")
    return str(Path(__file__).resolve().parents[1] / "data")


def parse(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", choices=["upworthy", "asos", "all"], default="all")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OSF API root; tests point this at a local stub")
    ap.add_argument("--data-dir", default=default_data_dir())
    ap.add_argument("--refresh", action="store_true", help="re-download and re-record checksums (the only way to re-record)")
    ap.add_argument("--verify-only", action="store_true", help="check files on disk against CHECKSUMS.json without any network access")
    ap.add_argument("--max-extract-bytes", type=int, default=DEFAULT_MAX_EXTRACT_BYTES)
    ap.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse(argv)
    try:
        return run(args)
    except DownloadError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
