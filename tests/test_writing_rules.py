"""T-024 contracts: writing rules enforced on committed text, card text and CLI help.

Rules, applied to every file git would commit (tracked, or untracked and not ignored) with no allow-list for the first three
(the approved spec included; it was reworded so that it needs none)
  * no U+2014 and no U+2013 anywhere in committed text (test sources included),
  * the role noun named in spec section 14 item 5 nowhere, matched at word boundaries; the pattern is
    assembled from parts so this file is itself clean,
  * tier 1: no lower-cased word or bigram whose sha256 appears in tests/forbidden_terms.sha256, in any file, anywhere,
  * tier 2: no word or bigram whose sha256 appears in tests/restricted_terms.sha256, except in the files listed in
    TIER2_FILES and under TIER2_PREFIXES.
Spellings: a term is found in any case, in camelCase or PascalCase, with underscores or digits attached, in fullwidth letters,
with zero-width characters, soft hyphens or accents, across a line break, and as a run of up to three words. A word that mixes
script is reported (a homoglyph disguise), a word written in look-alike letters is also hashed as the Latin word it imitates, and
any Unicode dash punctuation other than the hyphen-minus counts as a dash (as does anything that folds to an em or en dash). A URL
that names a tier 1 term in its host or path fails the scan, after its percent-escapes are decoded. A committed file that is not
UTF-8 text must be a picture or a Parquet file, must start with the magic bytes of its type, and has its text payload (PNG text
chunks, JPEG comment and application segments, GIF extensions, Parquet metadata and every text or binary value including dictionary,
list and struct children, printable runs of the bytes) scanned. The two dash characters and the role noun are built
with chr() for the same reason. URLs are removed from a file before it is tokenized, because
a cited link is a citation and not prose. The path components of every committed file are tokenized and held to the same
tiers and allow-lists as the contents.

Tier 2 holds company names that are legitimate survey subjects. A surveyed product may be named in the landscape page and in
the related-work files, and as one vendor export format among several in the importers, their mappings, their fixtures and
the page that documents the exchange format. A tier 2 name may be surveyed or cited, but is never addressed as the intended
reader: it stays out of the README, DATA.md, the method page, the quickstart, the spec, the top-level command help and every
paper file other than the four related-work files.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import functools
import hashlib
import importlib
import json
import os
import re
import subprocess
import unicodedata
import urllib.parse
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EM, EN = chr(0x2014), chr(0x2013)
DIGEST_FILE = ROOT / "tests" / "forbidden_terms.sha256"
RESTRICTED_FILE = ROOT / "tests" / "restricted_terms.sha256"
DIGEST_FILES = (Path("tests/forbidden_terms.sha256"), Path("tests/restricted_terms.sha256"))
SPEC = ROOT / "docs" / "superpowers" / "specs" / "2026-11-02-mootcourt-design.md"
# The role noun and its plural, built with chr() so this file never spells the word; matched on whole tokens (see tokens_of),
# so the plural, identifier forms (snake_case and PascalCase) and capitals are caught while the longer words that merely contain it are not.
ROLE_WORDS = {"".join(map(chr, (111, 119, 110, 101, 114))), "".join(map(chr, (111, 119, 110, 101, 114, 115)))}
SKIP_PARTS = {".git"}
# A URL ends at whitespace, brackets, quotes, commas, semicolons and angle brackets, and a final period or colon is not part of it.
URL = re.compile(r"https?://[^\s<>\"'`(),;\[\]{}|\\^]*[^\s<>\"'`(),;\[\]{}|\\^.:!?]")
# Files that are binary on purpose; any other committed file that is not UTF-8 text fails the scan with its path.
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".parquet"}
ZERO_WIDTH = {ord(c): None for c in (chr(0x200B), chr(0x200C), chr(0x200D), chr(0x2060), chr(0xFEFF), chr(0x00AD))}
# The first bytes a file of each binary type must start with; a file whose suffix and content disagree is a hit.
MAGIC = {".png": (b"\x89PNG\r\n\x1a\n",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",), ".gif": (b"GIF87a", b"GIF89a"),
         ".ico": (b"\x00\x00\x01\x00",), ".parquet": (b"PAR1",)}
# Letters that look like a Latin letter in another script (a hand-picked part of the Unicode confusables table, TR39, for Cyrillic,
# Greek, Armenian and the Latin dotless i). A text is also hashed with these mapped to the Latin letter, so a word written wholly in
# look-alikes is still the word. The map is applied to lower- and upper-case forms alike.
_CONFUSABLE_PAIRS = {
    "a": "\u0430\u03b1", "c": "\u0441\u03f2\u0581", "d": "\u0501", "e": "\u0435\u0451\u04bd", "g": "\u0261\u0581", "h": "\u04bb\u0570",
    "i": "\u0456\u0131\u03b9\u0269\u0561", "j": "\u0458\u03f3", "k": "\u043a\u03ba", "l": "\u04cf", "m": "\u043c", "n": "\u0578\u057c",
    "o": "\u043e\u03bf\u0585\u03c3\u0ce6", "p": "\u0440\u03c1", "q": "\u051b", "s": "\u0455", "t": "\u0442", "u": "\u057d\u03c5\u0446",
    "v": "\u03bd\u0475", "w": "\u051d\u0461", "x": "\u0445\u03c7", "y": "\u0443\u03b3\u04af",
}
CONFUSABLES = {ord(look): latin for latin, looks in _CONFUSABLE_PAIRS.items() for look in looks}
CONFUSABLES.update({ord(look.upper()): latin.upper() for latin, looks in _CONFUSABLE_PAIRS.items() for look in looks if look.upper() != look})
SI_UNITS = {"s", "m", "g", "l", "L", "A", "F", "H", "V", "W", "J", "N", "Hz", "mol", "K", "Pa", "C", "T", "B", "b", "Wh", "Sv"}
# Where a tier 2 name is allowed: the survey pages, and the importers (one vendor export format among several).
TIER2_FILES = {"docs/landscape.md", "paper/related-work.md", "paper/sections/related-work.tex", "paper/references.bib",
               "docs/ledger-format.md", "tests/test_importers.py"}
TIER2_PREFIXES = ("src/mootcourt/importers/", "examples/mappings/", "tests/fixtures/importers/")


# ------------------------------------------------------------------ scanner
def load_digests(path: Path = DIGEST_FILE) -> set[str]:
    return {ln.strip().lower() for ln in path.read_text().splitlines() if re.fullmatch(r"[0-9a-fA-F]{64}", ln.strip())}


def _digest(term: str) -> str:
    return hashlib.sha256(term.encode("utf-8")).hexdigest()


def tracked_text_files(root: Path = ROOT) -> list[Path]:
    """Every file git would commit. Names are read NUL separated and decoded with surrogateescape, so a non-ASCII name is not
    quoted away and dropped; a listed path that is missing and is not a deletion fails the call."""
    def listing(*args):
        raw = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files", "-z", *args], cwd=root, capture_output=True, check=True).stdout
        return [os.fsdecode(n) for n in raw.split(b"\0") if n]

    deleted = set(listing("--deleted"))
    files = []
    for rel in listing("--cached", "--others", "--exclude-standard"):
        p = root / rel
        if SKIP_PARTS & set(Path(rel).parts):
            continue
        if not p.is_file():
            assert rel in deleted or p.is_dir(), f"git lists {rel!r} but it is not a file and not a deletion"
            continue
        files.append(p)
    return files


def load_restricted(path: Path = RESTRICTED_FILE) -> set[str]:
    return load_digests(path)


def classify(path: Path, root: Path = ROOT) -> set[str]:
    """Which rules apply to this file: all of them, except the two digest files themselves (they hold only hashes)."""
    if path.relative_to(root) in DIGEST_FILES:
        return set()
    return {"dash", "role", "tokens"}


def tier2_allowed(rel: str) -> bool:
    """True for the files and folders where a tier 2 name may appear (see the module docstring)."""
    rel = rel.replace("\\", "/")
    return rel in TIER2_FILES or rel.startswith(TIER2_PREFIXES)


def strip_urls(text: str) -> str:
    return URL.sub(" ", text)


def fold(text: str) -> str:
    """Unicode normalisation before tokenizing: NFKC (fullwidth and compatibility forms become plain letters), zero-width
    characters and soft hyphens removed, combining marks dropped after NFKD. Case is kept for the camelCase split."""
    text = unicodedata.normalize("NFKC", text).translate(ZERO_WIDTH)
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def _split_run(run: str) -> list[str]:
    """Split one run of letters and digits at letter/digit boundaries and at camelCase and PascalCase boundaries."""
    parts: list[str] = []
    for chunk in re.findall(r"[^\W\d_]+|\d+", run):
        if chunk[0].isdigit():
            parts.append(chunk)
            continue
        tail = ""
        if len(chunk) > 3 and chunk.endswith("s") and chunk[:-1].isupper():       # an all-caps word with a lower-case plural s: ZEBRAFOOs
            chunk, tail = chunk[:-1], "s"
        cut = 0
        for i in range(1, len(chunk)):
            prev, cur = chunk[i - 1], chunk[i]
            nxt = chunk[i + 1] if i + 1 < len(chunk) else ""
            if (prev.islower() and cur.isupper()) or (prev.isupper() and cur.isupper() and nxt.islower()):
                parts.append(chunk[cut:i])
                cut = i
        parts.append(chunk[cut:])
        if tail:
            parts.append(tail)
    return parts


def tokens_of(text: str) -> list[tuple[str, int, str]]:
    """``(folded part, 1-based line, folded whole run)`` for every word part of the text, in order.

    A run is a stretch of letters and digits (underscores and punctuation end it). camelCase, PascalCase, digit-attached and
    underscore forms all become separate parts, so ``ZebraFoo``, ``zebra_foo`` and ``zebrafoo2`` expose the same parts.
    """
    out = []
    for n, line in enumerate(fold(text).splitlines(), 1):
        for run in re.findall(r"[^\W_]+", line):
            whole = run.casefold()
            out += [(part.casefold(), n, whole) for part in _split_run(run)]
    return out


def skeleton(text: str) -> str:
    """``text`` folded, with look-alike letters of other scripts replaced by the Latin letter they imitate."""
    return fold(text).translate(CONFUSABLES)


def all_tokens(text: str) -> list[tuple[str, int, str]]:
    """``tokens_of`` for the text as written and, when it holds a look-alike letter, for its skeleton as well."""
    out = tokens_of(text)
    sk = skeleton(text)
    return out + tokens_of(sk) if sk != fold(text) else out


def candidates(text: str) -> list[tuple[str, int]]:
    """Every string that is hashed, with the line of its first part: parts, whole runs, 2- and 3-grams joined by a space (across
    line breaks), and the concatenation of 2 and 3 adjacent parts (an identifier or a spaced pair written as one word)."""
    sk = skeleton(text)
    if sk != fold(text):                                  # a look-alike letter: hash the word as written and as it reads
        return _candidates(tokens_of(text)) + _candidates(tokens_of(sk))
    return _candidates(tokens_of(text))


def _candidates(toks: list[tuple[str, int, str]]) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for i, (w, n, whole) in enumerate(toks):
        out.append((w, n))
        if whole != w:
            out.append((whole, n))
        for k in (2, 3):
            if i + k <= len(toks):
                group = [toks[j][0] for j in range(i, i + k)]
                out.append((" ".join(group), n))
                out.append(("".join(group), n))
    return out


def _grams(text: str) -> list[str]:
    return [g for g, _n in candidates(text)]


def _script(ch: str) -> str:
    return unicodedata.name(ch, "X").split()[0]


def _is_micro_unit(run: str) -> bool:
    """A Greek mu directly before an SI unit: NFKC folds the micro sign (U+00B5) to it, as in "5 \u00b5s"."""
    return run[:1] == "\u03bc" and run[1:] in SI_UNITS


def mixed_script_lines(text: str) -> list[int]:
    """Lines holding a word made of letters from more than one script: the shape of a homoglyph disguise. A word that is in
    one script entirely is hashed through its skeleton instead (see ``skeleton``). The micro sign before an SI unit is exempt."""
    out = []
    for n, line in enumerate(fold(text).splitlines(), 1):
        for run in re.findall(r"[^\W\d_]+", line):
            if len({_script(ch) for ch in run}) > 1 and not _is_micro_unit(run):
                out.append(n)
                break
    return out


def _unquoted(url: str) -> str:
    """The URL with percent-escapes and plus signs decoded until nothing changes (%2520 is %20 is a space)."""
    for _ in range(8):
        again = urllib.parse.unquote_plus(url)
        if again == url:
            break
        url = again
    return url


def url_hits(text: str, digests: set[str]) -> list[int]:
    """Lines whose URL names a tier 1 term in its host or path (a cited link may still point at a page that names a person)."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        for url in URL.findall(line):
            if any(_digest(g) in digests for g in _grams(_unquoted(re.sub(r"^https?://", "", url)))):
                out.append(n)
                break
    return out


def _has_dash(line: str) -> bool:
    """True when the line holds an em or en dash, written or folded to one (NFKC), or any Unicode dash punctuation other than U+002D."""
    folded = unicodedata.normalize("NFKC", line)
    return EM in folded or EN in folded or any(unicodedata.category(ch) == "Pd" and ch != "-" for ch in line)


def scan_text(text: str, rules: set[str], digests: set[str], restricted: set[str] | None = None) -> list[tuple[int, str]]:
    """Hits as ``(line number, what)``. ``restricted`` is the tier 2 digest set; pass it only for files where tier 2 is not allowed.

    A term of one, two or three words is found whatever its spelling: case, camelCase, underscores, digits, fullwidth letters,
    zero-width characters, accents, a line break inside a pair. Digests are of lower-cased, single-space-joined n-grams (n up to 3).
    """
    found = []
    if "dash" in rules:
        found += [(n, "dash character") for n, line in enumerate(text.splitlines(), 1) if _has_dash(line)]
    if "role" in rules:
        found += [(n, "role noun") for w, n, _whole in all_tokens(text) if w in ROLE_WORDS]
    if "tokens" in rules and (digests or restricted):
        body = strip_urls(text)
        for gram, n in candidates(body):
            h = _digest(gram)
            if digests and h in digests:
                found.append((n, "forbidden term"))
            if restricted and h in restricted:
                found.append((n, "restricted term"))
        found += [(n, "mixed-script word") for n in mixed_script_lines(body)]
        if digests:
            found += [(n, "forbidden term in a URL") for n in url_hits(text, digests)]
    return sorted(set(found))


def scan_name(rel: str, digests: set[str], restricted: set[str] | None = None) -> list[str]:
    """Hits in the path components of a committed file, held to the same tiers and allow-lists as its contents."""
    grams = _grams(" ".join(Path(rel).parts))
    hits = []
    if digests and any(_digest(g) in digests for g in grams):
        hits.append("forbidden term in the file name")
    if restricted and not tier2_allowed(rel) and any(_digest(g) in restricted for g in grams):
        hits.append("restricted term in the file name")
    return hits


def _png_texts(data: bytes) -> list[str]:
    """The text of every tEXt, zTXt and iTXt chunk of a PNG (compressed ones inflated, at most a megabyte each)."""
    out, pos = [], 8
    while pos + 8 <= len(data):
        size, kind = int.from_bytes(data[pos:pos + 4], "big"), data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + size]
        pos += 12 + size
        try:
            if kind == b"tEXt":
                out.append(body.decode("latin-1"))
            elif kind == b"zTXt":
                key, rest = body.split(b"\0", 1)
                out.append(key.decode("latin-1") + " " + zlib.decompressobj().decompress(rest[1:], 1 << 20).decode("utf-8", "replace"))
            elif kind == b"iTXt":
                key, rest = body.split(b"\0", 1)
                flag, rest = rest[0], rest[2:]
                _lang, rest = rest.split(b"\0", 1)
                translated, rest = rest.split(b"\0", 1)
                text = zlib.decompressobj().decompress(rest, 1 << 20) if flag else rest
                out.append(" ".join((key.decode("latin-1"), translated.decode("utf-8", "replace"), text.decode("utf-8", "replace"))))
        except (ValueError, IndexError, zlib.error):
            continue
        if kind == b"IEND":
            break
    return out


def _arrow_texts(arr, out: list[str], limit: int = 100000) -> None:
    """Add the distinct text values of an Arrow array to ``out``: a dictionary column by its value type, list, map and struct
    children flattened, and binary values decoded as latin-1 and as UTF-8 (a short term must not hide behind the value type)."""
    import pyarrow as pa
    import pyarrow.compute as pc

    if isinstance(arr, pa.ChunkedArray):
        for chunk in arr.chunks:
            _arrow_texts(chunk, out, limit)
        return
    t = arr.type
    if pa.types.is_dictionary(t):
        _arrow_texts(arr.dictionary, out, limit)
    elif pa.types.is_struct(t):
        for i in range(t.num_fields):
            out.append(t.field(i).name)
            _arrow_texts(arr.field(i), out, limit)
    elif pa.types.is_map(t):
        _arrow_texts(arr.keys, out, limit)
        _arrow_texts(arr.items, out, limit)
    elif pa.types.is_list(t) or pa.types.is_large_list(t) or pa.types.is_fixed_size_list(t):
        _arrow_texts(arr.flatten(), out, limit)
    elif pa.types.is_string(t) or pa.types.is_large_string(t):
        out += [str(v) for v in pc.unique(arr).to_pylist()[:limit] if v is not None]
    elif pa.types.is_binary(t) or pa.types.is_large_binary(t) or pa.types.is_fixed_size_binary(t):
        for v in pc.unique(arr).to_pylist()[:limit]:
            if v is not None:
                out += [v.decode("latin-1"), v.decode("utf-8", "replace")]


def _parquet_texts(data: bytes) -> list[str]:
    """Column names, key-value metadata and every text or binary value of a Parquet file; empty when unreadable (the raw bytes are scanned anyway)."""
    import io

    try:
        import pyarrow.parquet as pq

        table = pq.read_table(io.BytesIO(data))
        out = list(table.schema.names)
        out += [f"{k.decode('utf-8', 'replace')} {v.decode('utf-8', 'replace')}" for k, v in (table.schema.metadata or {}).items()]
        for name in table.schema.names:
            try:
                _arrow_texts(table[name], out)
            except Exception:  # noqa: BLE001  (a column type that cannot be read is skipped; the others still are)
                continue
        return out
    except Exception:  # noqa: BLE001  (a file pyarrow cannot read is still scanned as bytes)
        return []


def _jpeg_texts(data: bytes) -> list[str]:
    """The body of every comment (COM) and application (APP0 to APP15) segment of a JPEG, as latin-1 text (EXIF, XMP and captions live there)."""
    out, pos = [], 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker == 0xFF:                                           # fill byte
            pos += 1
            continue
        if marker in (0x00, 0x01) or 0xD0 <= marker <= 0xD8:        # no length
            pos += 2
            continue
        if marker == 0xD9:
            break
        size = int.from_bytes(data[pos + 2:pos + 4], "big")
        body = data[pos + 4:pos + 2 + size]
        if marker == 0xFE or 0xE0 <= marker <= 0xEF:
            out.append(body.decode("latin-1"))
        pos += 2 + max(size, 2)
        if marker == 0xDA:                                           # entropy-coded data: skip to the next real marker
            while pos + 1 < len(data) and not (data[pos] == 0xFF and data[pos + 1] not in (0x00, 0xFF) and not 0xD0 <= data[pos + 1] <= 0xD7):
                pos += 1
    return out


def _gif_texts(data: bytes) -> list[str]:
    """The text of every comment, application and plain-text extension of a GIF (its sub-blocks joined), skipping image data."""
    out = []
    try:
        pos = 13
        if data[10] & 0x80:
            pos += 3 * (2 << (data[10] & 7))                         # the global colour table

        def sub_blocks(p: int) -> tuple[bytes, int]:
            chunks = []
            while data[p]:
                chunks.append(data[p + 1:p + 1 + data[p]])
                p += 1 + data[p]
            return b"".join(chunks), p + 1

        while pos < len(data) and data[pos] != 0x3B:
            if data[pos] == 0x21:
                label = data[pos + 1]
                if label in (0xFE, 0xFF, 0x01):
                    start = pos + 2
                    if label != 0xFE:
                        start += 1 + data[pos + 2]                    # a fixed-size block opens these two (the application id, the text grid)
                        out.append(data[pos + 3:start].decode("latin-1"))
                    text, pos = sub_blocks(start)
                    out.append(text.decode("latin-1"))
                else:
                    _text, pos = sub_blocks(pos + 2)
            elif data[pos] == 0x2C:
                flags = data[pos + 9]
                pos += 10 + (3 * (2 << (flags & 7)) if flags & 0x80 else 0) + 1
                _text, pos = sub_blocks(pos)
            else:
                break
    except IndexError:
        pass
    return out


def scan_binary(data: bytes, suffix: str, digests: set[str], restricted: set[str] | None = None) -> list[str]:
    """What is wrong with a picture or Parquet file: content that does not match its suffix, and blocked terms in its text payload.

    The payload is the printable runs of the raw bytes (a stored caption or metadata value is readable there), plus the text chunks of a PNG
    the comment and application segments of a JPEG, the extensions of a GIF, and the column names, metadata and text or binary values of a Parquet
    file (nested and dictionary columns included), which a compressor hides from the raw bytes. The dash and
    role-noun rules are for prose and do not apply to pictures.
    """
    found = []
    if not any(data.startswith(m) for m in MAGIC.get(suffix, ())) or (suffix == ".parquet" and not data.endswith(b"PAR1")):
        found.append("file content does not match its suffix")
    # Raw bytes: only runs of 6 or more printable characters, and only words of 4 or more letters, are read, because a short word
    # appears in compressed pixel data by chance. The structured text below is read in full.
    raw = "\n".join(m.decode("ascii") for m in re.findall(rb"[\x20-\x7e]{6,}", data))
    texts = [(raw, 4)]
    structured = {".png": _png_texts, ".parquet": _parquet_texts, ".jpg": _jpeg_texts, ".jpeg": _jpeg_texts, ".gif": _gif_texts}
    texts += [(t, 0) for t in (structured[suffix](data) if suffix in structured else [])]
    for text, shortest in texts:
        for gram, _n in candidates(text):
            if len(gram.replace(" ", "")) < shortest:
                continue
            h = _digest(gram)
            if digests and h in digests:
                found.append("forbidden term")
            if restricted and h in restricted:
                found.append("restricted term")
    return sorted(set(found))


def scan_file(path: Path, digests: set[str], root: Path = ROOT, rules: set[str] | None = None, restricted: set[str] | None = None):
    """Hits in one file as ``(relative path, line, what)``. Tier 2 applies only when ``restricted`` is given and the file is not allowed it.

    A file that is not UTF-8 text is a hit unless its type is on the binary allow-list. A file of an allowed binary type must start
    with that type's magic bytes, and its text payload is scanned against the digests (see ``scan_binary``).
    """
    rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    data = path.read_bytes()
    suffix = path.suffix.lower()
    tier2 = None if tier2_allowed(rel) else restricted
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    binary = suffix in BINARY_SUFFIXES
    if text is None and not binary:
        return [(rel, 0, "binary or undecodable file that is not on the allow-list")]
    hits = []
    if binary:
        hits += [(rel, 0, what) for what in scan_binary(data, suffix, digests, tier2)]
    if text is not None and not (binary and not any(what.startswith("file content") for _r, _n, what in hits)):
        hits += [(rel, n, what) for n, what in scan_text(text, classify(path, root) if rules is None else rules, digests, tier2)]
    return hits


def scan_repo(root: Path, files: list[Path], digests: set[str], restricted: set[str]) -> list[tuple[str, int, str]]:
    """Every hit in the given files: contents and file names, both tiers. File-name hits carry line 0."""
    out = []
    for path in files:
        rel = str(path.relative_to(root))
        out += [(rel, 0, what) for what in scan_name(rel, digests, restricted)]
        out += scan_file(path, digests, root, restricted=restricted)
    return out


# ------------------------------------------------------------------ digest file
def test_digest_file_present_and_well_formed():
    assert DIGEST_FILE.exists()
    lines = [ln for ln in DIGEST_FILE.read_text().splitlines() if ln.strip()]
    assert lines and all(re.fullmatch(r"[0-9a-f]{64}", ln.strip()) for ln in lines)
    fleet = ROOT / ".claude" / "fleet" / "forbidden-terms.sha256"
    assert not fleet.exists() or DIGEST_FILE.read_text() == fleet.read_text()


def test_restricted_digest_file_is_a_copy_of_the_fleet_file():
    assert RESTRICTED_FILE.exists()
    lines = [ln for ln in RESTRICTED_FILE.read_text().splitlines() if ln.strip()]
    assert lines and all(re.fullmatch(r"[0-9a-f]{64}", ln.strip()) for ln in lines)
    fleet = ROOT / ".claude" / "fleet" / "restricted-terms.sha256"
    assert not fleet.exists() or RESTRICTED_FILE.read_text() == fleet.read_text()
    assert load_restricted().isdisjoint(load_digests()), "a term is in one tier only"


# ------------------------------------------------------------------ negative tests of the scanner
@pytest.mark.parametrize("injected,what", [
    (f"a sentence {EM} with an em dash", "dash character"),
    (f"a range 1{EN}2", "dash character"),
    ("The Own" + "er approves it", "role noun"),
    ("zebrafoo launches it", "forbidden term"),
    ("and then zebra foo returns", "forbidden term"),
])
def test_scanner_reports_file_and_line_for_each_forbidden_pattern(tmp_path, injected, what):
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs" / "page.md"
    target.write_text("clean line\nsecond clean line\n" + injected + "\n", encoding="utf-8")
    digests = {_digest("zebrafoo"), _digest("zebra foo")}
    hits = scan_file(target, digests, root=tmp_path, rules={"dash", "role", "tokens"})
    assert hits and hits[0][0] == "docs/page.md" and hits[0][1] == 3 and hits[0][2] == what


def test_scanner_passes_clean_text_and_word_boundaries():
    assert scan_text("townhouse and own" + "ership are fine", {"role"}, set()) == []
    assert scan_text("a plain hyphen-ated word and a comma, ok", {"dash", "role", "tokens"}, {_digest("zzz")}) == []


def test_no_file_is_allow_listed(tmp_path):
    assert classify(SPEC) == {"dash", "role", "tokens"}
    assert classify(ROOT / "README.md") == {"dash", "role", "tokens"}
    assert classify(ROOT / "tests" / "test_card.py") == {"dash", "role", "tokens"}
    assert classify(DIGEST_FILE) == set()
    assert scan_file(SPEC, load_digests()) == [], "the spec must pass every rule with nothing allow-listed"


# ------------------------------------------------------------------ the committed repository
def test_writing_rules():
    """The positive control: what git would commit passes every rule, contents and file names, both tiers."""
    digests, restricted = load_digests(), load_restricted()
    assert digests and restricted, "both digest files must hold at least one digest"
    files = tracked_text_files()
    assert any(p.name == "README.md" for p in files), "README.md must exist"
    violations = scan_repo(ROOT, files, digests, restricted)
    assert violations == [], "\n".join(f"{f}:{n}: {what}" for f, n, what in violations)


def _raw_listing(*args) -> list[str]:
    raw = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files", "-z", *args], cwd=ROOT, capture_output=True, check=True).stdout
    return [os.fsdecode(n) for n in raw.split(b"\0") if n]


def test_claude_directory_is_excluded_and_ignored():
    """Asserted on git's own listing: nothing under the tool folder is tracked or untracked-and-not-ignored."""
    listed = _raw_listing("--cached", "--others", "--exclude-standard")
    assert listed and not [rel for rel in listed if ".claude" in Path(rel).parts], "files of the tool folder would be committed"
    assert ".claude/" in (ROOT / ".gitignore").read_text()
    assert subprocess.run(["git", "check-ignore", "-q", ".claude/fleet/anything.json"], cwd=ROOT).returncode == 0


def test_the_built_paper_pdf_is_ignored_and_not_committed():
    assert "paper/main.pdf" not in _raw_listing("--cached", "--others", "--exclude-standard")
    assert subprocess.run(["git", "check-ignore", "-q", "paper/main.pdf"], cwd=ROOT).returncode == 0


def test_every_committed_file_is_text_or_an_allowed_binary():
    odd = []
    for path in tracked_text_files():
        try:
            path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            if path.suffix.lower() not in BINARY_SUFFIXES:
                odd.append(str(path.relative_to(ROOT)))
    assert not odd, f"binary or non-UTF-8 files that are not pictures or Parquet: {odd}"


def test_generated_report_markdown_is_scanned_when_present():
    digests = load_digests()
    reports = [p for p in (ROOT / "reports").glob("*.md")] if (ROOT / "reports").exists() else []
    for path in reports:
        assert scan_file(path, digests, rules={"dash", "role", "tokens"}) == [], path.name


# ------------------------------------------------------------------ rendered card text
@functools.lru_cache(maxsize=1)
def _issued_card():
    syn = importlib.import_module("mootcourt.sources.synthetic")
    ledger, _ = syn.generate(syn.SyntheticConfig(seed=111, n_tests=250, variants_per_test=2))
    bundle = importlib.import_module("mootcourt.bundle").fit_bundle(
        ledger, "synthetic", "20261102-999999999999", as_of=dt.datetime(2014, 7, 15, 12, tzinfo=dt.timezone.utc))
    card = importlib.import_module("mootcourt.card")
    now = dt.datetime(2014, 7, 15, 12, tzinfo=dt.timezone.utc)
    report = {"source": "synthetic", "as_of": (now - dt.timedelta(days=1)).isoformat(), "cells": {"headline_only": {
        "as_of": (now - dt.timedelta(days=1)).isoformat(), "rolling_logscore": -2.0, "p0_rolling_logscore": -2.1,
        "brier_skill": 0.1, "n": 300, "drifted": False, "consecutive_below": 0}}}
    req = card.CardRequest(source="synthetic", headline="what happened next will surprise you", image_changed=False,
                           impressions=20000, origin=now)
    return card.build_card(bundle, req, reliability=report, now=now)


@pytest.mark.parametrize("reason", [None, "support", "novelty", "reliability", "instability"])
def test_rendered_card_text_obeys_the_rules(reason):
    card = importlib.import_module("mootcourt.card")
    ab = importlib.import_module("mootcourt.abstain")
    c = _issued_card()
    if reason:
        c = dataclasses.replace(c, abstention=ab.AbstainDecision(status="abstain", reasons=(reason,),
                                                                 details={reason: f"{reason} trigger fired"}))
    text = card.to_markdown(c) + "\n" + json.dumps(card.to_json(c), ensure_ascii=False)
    assert scan_text(text, {"dash", "role", "tokens"}, load_digests(), load_restricted()) == []


# The commands that list or read vendor export formats may name them, matched on the whole command path from the root, so a command
# that merely shares a word with one of them (``moot simulate ledger``) is not exempt. A path inside one of these groups is exempt too.
IMPORTER_COMMANDS = {("moot", "ingest"), ("moot", "ledger")}


def importer_command(path: tuple[str, ...]) -> bool:
    return any(path[: len(c)] == c for c in IMPORTER_COMMANDS)


def tier2_set_for_help(path: tuple[str, ...], restricted: set[str]) -> set[str] | None:
    """The tier 2 digests a command's help text is held to: none for an importer command, which may name a surveyed export format."""
    return None if importer_command(path) else restricted


def test_cli_help_text_obeys_the_rules():
    import click
    import typer

    app = importlib.import_module("mootcourt.cli").app
    root_cmd = typer.main.get_command(app)
    texts = []

    def walk(cmd, ctx_name, path=()):
        ctx = click.Context(cmd, info_name=ctx_name)
        texts.append((path + (ctx_name,), cmd.get_help(ctx)))
        for name, sub in getattr(cmd, "commands", {}).items():
            walk(sub, name, path + (ctx_name,))

    walk(root_cmd, "moot")
    assert len(texts) >= 8, "expected the root plus data, fit, backtest, card, serve, mcp, join, promote, simulate ..."
    digests, restricted = load_digests(), load_restricted()
    for path, text in texts:
        tier2 = tier2_set_for_help(path, restricted)                      # only the importer commands may name a surveyed export format
        assert scan_text(text, {"dash", "role", "tokens"}, digests, tier2) == [], " ".join(path)


# ------------------------------------------------------------------ the two tiers, URLs and file names (T-024)
# The scanners take their digest sets as arguments, so these tests use made-up words and never spell a real term.
T1, T2 = {_digest("zebrafoo")}, {_digest("yakcorp")}


def _tree(tmp_path, files: dict[str, str]) -> list[Path]:
    out = []
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        out.append(p)
    return out


def _copy_with(tmp_path, rel: str, injected: str) -> list[Path]:
    """A temporary copy of a real committed file with one line added at the end; returns the scanned files."""
    text = (ROOT / rel).read_text(encoding="utf-8").rstrip("\n") + "\n" + injected + "\n"
    return _tree(tmp_path, {rel: text})


@pytest.mark.parametrize("rel", ["README.md", "docs/method.md", "src/mootcourt/cli.py", "tests/test_card.py"])
@pytest.mark.parametrize("injected,what", [
    (f"an inserted {EM} sentence", "dash character"),
    (f"an inserted range 1{EN}2", "dash character"),
    ("the Own" + "er decides", "role noun"),
    ("then zebrafoo appears", "forbidden term"),
    ("then YakCorp appears", "restricted term"),
])
def test_injecting_a_pattern_into_a_copy_of_a_scanned_file_fails_with_file_and_line(tmp_path, rel, injected, what):
    files = _copy_with(tmp_path, rel, injected)
    last = len(files[0].read_text(encoding="utf-8").splitlines())
    hits = scan_repo(tmp_path, files, T1, T2)
    assert (rel, last, what) in hits, hits


def test_tier_one_is_forbidden_everywhere_without_exception(tmp_path):
    for rel in ("docs/landscape.md", "paper/related-work.md", "src/mootcourt/importers/vendors.py", "docs/ledger-format.md",
                "tests/test_importers.py", "examples/mappings/m.toml", "tests/fixtures/importers/x.csv"):
        files = _tree(tmp_path, {rel: "a line with zebrafoo in it\n"})
        assert scan_repo(tmp_path, files, T1, T2) == [(rel, 1, "forbidden term")], rel


@pytest.mark.parametrize("rel", sorted(TIER2_FILES) + [p + "x.py" for p in TIER2_PREFIXES])
def test_tier_two_may_appear_where_a_product_is_surveyed_or_is_one_export_format(tmp_path, rel):
    files = _tree(tmp_path, {rel: "YakCorp is surveyed here\n"})
    assert scan_repo(tmp_path, files, T1, T2) == []


@pytest.mark.parametrize("rel", ["README.md", "DATA.md", "docs/method.md", "docs/quickstart.md", "docs/simulators.md", "docs/index.md",
                                 "docs/superpowers/specs/2026-11-02-mootcourt-design.md", "paper/main.tex", "paper/sections/method.tex",
                                 "src/mootcourt/cli.py", "tests/test_card.py", ".github/workflows/ci.yml", "Dockerfile", "mkdocs.yml"])
def test_tier_two_is_forbidden_outside_the_allowed_files(tmp_path, rel):
    files = _tree(tmp_path, {rel: "Built for YakCorp\n"})
    assert scan_repo(tmp_path, files, T1, T2) == [(rel, 1, "restricted term")]


def test_a_url_is_a_citation_not_prose(tmp_path):
    fixture = _tree(tmp_path, {"docs/a.md": "See [the page](https://example.org/zebrafoo/page.html) and https://zebrafoo.example/x for details.\n"})
    assert scan_repo(tmp_path, fixture, T1, T2) == [("docs/a.md", 1, "forbidden term in a URL")], \
        "a tier 1 token inside a URL is not prose, but a link that names it is reported as a URL hit (REV-048)"
    prose = _tree(tmp_path, {"docs/b.md": "See https://example.org/zebrafoo/page.html and note that zebrafoo matters.\n"})
    assert scan_repo(tmp_path, prose, T1, T2) == [("docs/b.md", 1, "forbidden term"), ("docs/b.md", 1, "forbidden term in a URL")], \
        "the same token in prose fails, and the link that names it is reported as well"
    assert strip_urls("x (https://a.b/c) y").split() == ["x", "(", ")", "y"]
    assert strip_urls("x https://a.b/c d").split() == ["x", "d"]
    only_url_brackets = _tree(tmp_path, {"docs/c.md": "(https://zebrafoo.example/x) [https://zebrafoo.example/y] and plain text\n"})
    assert scan_repo(tmp_path, only_url_brackets, T1, T2) == [("docs/c.md", 1, "forbidden term in a URL")]


def test_a_url_in_a_tier_two_file_name_or_text_is_also_stripped(tmp_path):
    files = _tree(tmp_path, {"README.md": "Docs at https://yakcorp.example/docs only\n"})
    assert scan_repo(tmp_path, files, T1, T2) == []


def test_file_names_are_tokenized_and_held_to_the_same_tiers(tmp_path):
    bad_t1 = _tree(tmp_path, {"tests/fixtures/zebrafoo-sample.csv": "a,b\n"})
    assert scan_repo(tmp_path, bad_t1, T1, T2) == [("tests/fixtures/zebrafoo-sample.csv", 0, "forbidden term in the file name")]
    bad_dir = _tree(tmp_path, {"docs/zebrafoo/notes.md": "plain\n"})
    assert scan_repo(tmp_path, bad_dir, T1, T2) == [("docs/zebrafoo/notes.md", 0, "forbidden term in the file name")]
    ok = _tree(tmp_path, {"tests/fixtures/importers/yakcorp_view.csv": "a,b\n"})
    assert scan_repo(tmp_path, ok, T1, T2) == [], "a vendor fixture under the importer allow-list passes"
    bad_t2 = _tree(tmp_path, {"docs/yakcorp_notes.md": "plain\n"})
    assert scan_repo(tmp_path, bad_t2, T1, T2) == [("docs/yakcorp_notes.md", 0, "restricted term in the file name")]
    assert scan_name("zebra-fox.txt", T1) == []                                  # a different token is not a match
    assert scan_name("a/zebra_foo.txt", {_digest("zebra foo")}) == ["forbidden term in the file name"]      # bigrams across separators


def test_the_real_vendor_fixture_name_is_accepted_under_the_importer_allow_list():
    names = [p.relative_to(ROOT).as_posix() for p in tracked_text_files() if p.relative_to(ROOT).as_posix().startswith("tests/fixtures/importers/")]
    assert names, "the importer fixtures are committed"
    for rel in names:
        assert scan_name(rel, load_digests(), load_restricted()) == [], rel
    assert tier2_allowed("tests/fixtures/importers/anything.csv") and not tier2_allowed("tests/fixtures/other/anything.csv")


def test_tier_two_allow_list_is_exactly_the_documented_one():
    assert TIER2_FILES == {"docs/landscape.md", "paper/related-work.md", "paper/sections/related-work.tex", "paper/references.bib",
                           "docs/ledger-format.md", "tests/test_importers.py"}
    assert TIER2_PREFIXES == ("src/mootcourt/importers/", "examples/mappings/", "tests/fixtures/importers/")
    for rel in ("README.md", "DATA.md", "docs/method.md", "docs/quickstart.md", "docs/superpowers/specs/2026-11-02-mootcourt-design.md",
                "paper/main.tex", "paper/sections/introduction.tex"):
        assert not tier2_allowed(rel), rel


def test_the_spec_needs_no_allow_list_for_the_role_noun():
    """The spec was reworded to avoid the word, so every rule applies to it in full."""
    assert scan_file(SPEC, load_digests(), restricted=load_restricted()) == []


def test_the_top_level_command_help_names_no_surveyed_company():
    import click
    import typer

    app = importlib.import_module("mootcourt.cli").app
    root_cmd = typer.main.get_command(app)
    text = root_cmd.get_help(click.Context(root_cmd, info_name="moot"))
    assert scan_text(text, {"dash", "role", "tokens"}, load_digests(), load_restricted()) == []


def test_the_benchmark_report_card_text_obeys_the_rules(tmp_path):
    syn = importlib.import_module("mootcourt.sources.synthetic")
    ledger, _ = syn.generate(syn.SyntheticConfig(seed=57, n_tests=200, variants_per_test=2))
    path = tmp_path / "org-ledger.parquet"
    importlib.import_module("mootcourt.ledger").write_ledger(ledger, path)
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "gates.json").write_text(json.dumps({"n_200": 20, "n_400": 30, "target_power": 0.9, "decision_target": 0.9, "by_target": {
        "0.80": {"n_200": 15, "n_400": 25}, "0.90": {"n_200": 20, "n_400": 30}}}))
    card = importlib.import_module("mootcourt.benchmark").run_report_card(path, tmp_path / "reports", bootstrap=40)
    text = Path(card["paths"]["md"]).read_text(encoding="utf-8") + Path(card["paths"]["json"]).read_text(encoding="utf-8")
    assert scan_text(text, {"dash", "role", "tokens"}, load_digests(), load_restricted()) == []


# ------------------------------------------------------------------ spellings, file names and binaries (chunk E review)
T3 = {_digest("zebrafoo"), _digest("zebra foo"), _digest("alpha beta gamma"), _digest("strasse")}


def _spelled(*codes: int) -> str:
    return "".join(map(chr, codes))


def _fullwidth(word: str) -> str:
    return "".join(chr(ord(c) + 0xFEE0) for c in word)


ROLE, ROLES = sorted(ROLE_WORDS, key=len)


@pytest.mark.parametrize("injected,what", [
    ("then ZebraFoo appears", "forbidden term"),                              # PascalCase
    ("then zebraFoo appears", "forbidden term"),                              # camelCase
    ("then ZEBRAFoo appears", "forbidden term"),                              # acronym boundary
    ("then zebra_foo appears", "forbidden term"),                             # snake case
    ("then ZEBRA_FOO appears", "forbidden term"),
    ("then zebrafoo2 appears", "forbidden term"),                             # digit attached
    ("then 2zebrafoo appears", "forbidden term"),
    ("then zebra-foo appears", "forbidden term"),
    ("then zebra\nfoo appears", "forbidden term"),                            # a pair split by a line break
    ("then alpha beta gamma appears", "forbidden term"),                      # a term of three words
    ("then alpha\nbeta\ngamma appears", "forbidden term"),
    ("then alpha_beta_gamma appears", "forbidden term"),
    (f"then {_fullwidth('zebrafoo')} appears", "forbidden term"),             # fullwidth letters
    (f"then zebra{chr(0x200B)}foo appears", "forbidden term"),                # zero-width space
    (f"then zebra{chr(0x2060)}foo appears", "forbidden term"),                # word joiner
    (f"then zebra{chr(0x00AD)}foo appears", "forbidden term"),                # soft hyphen
    (f"then zebra{chr(0x0301)}foo appears", "forbidden term"),                # combining mark
    (f"then Stra{chr(0x00DF)}e appears", "forbidden term"),                   # case folding of the sharp s
    (f"then zebr{chr(0x0430)}foo appears", "mixed-script word"),              # a Cyrillic letter inside a Latin word
    (f"then {ROLES} decide", "role noun"),                                    # the plural of the role noun
    (f"then data_{ROLE} decides", "role noun"),                               # identifier forms
    (f"then {ROLE.capitalize()}Name decides", "role noun"),
    (f"then {ROLE.upper()} decides", "role noun"),
])
def test_each_spelling_of_a_blocked_term_is_found(injected, what):
    hits = scan_text("a clean first line\n" + injected + "\n", {"dash", "role", "tokens"}, T3)
    assert what in {w for _n, w in hits}, hits
    assert min(n for n, w in hits if w == what) in (2, 3, 4), hits


@pytest.mark.parametrize("text", ["townhouse and " + _spelled(111, 119, 110, 101, 114) + "ship are fine", "a zebra and a foo apart: zebra, the foo",
                                  "alpha, beta; gamma is not a triple", "the Greek alpha and the Latin beta are separate words",
                                  "pi, π and sigma σ each alone are fine"])
def test_close_neighbours_of_a_blocked_term_pass(text):
    hits = scan_text(text, {"dash", "role", "tokens"}, T3)
    # words apart are not a pair, but a three-word run split by punctuation only is still the three-word term
    assert [h for h in hits if h[1] != "forbidden term"] == []
    assert bool([h for h in hits if h[1] == "forbidden term"]) == (text == "alpha, beta; gamma is not a triple")


def test_a_pair_split_by_a_line_break_reports_the_line_of_its_first_word():
    assert (2, "forbidden term") in scan_text("clean\nzebra\nfoo\n", {"tokens"}, T3)


def test_a_file_name_in_fullwidth_letters_or_with_hidden_characters_is_caught():
    assert scan_name(f"docs/{_fullwidth('zebrafoo')}.md", T3) == ["forbidden term in the file name"]
    assert scan_name(f"docs/zebra{chr(0x200B)}foo.md", T3) == ["forbidden term in the file name"]
    assert scan_name("docs/ZebraFoo-notes.md", T3) == ["forbidden term in the file name"]
    assert scan_name("docs/clean-notes.md", T3) == []


def test_a_non_ascii_file_name_is_listed_and_scanned(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    odd = tmp_path / f"caf{chr(0xE9)}-{_fullwidth('zebrafoo')}.md"
    odd.write_text("clean\n", encoding="utf-8")
    (tmp_path / "plain.md").write_text("clean\n", encoding="utf-8")
    files = tracked_text_files(tmp_path)
    assert {p.name for p in files} == {odd.name, "plain.md"}, "a name git would quote is still listed"
    assert scan_repo(tmp_path, files, T3, set()) == [(odd.name, 0, "forbidden term in the file name")]


def test_a_listed_path_that_does_not_exist_fails_the_listing(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    gone = tmp_path / "gone.md"
    gone.write_text("x\n")
    subprocess.run(["git", "add", "gone.md"], cwd=tmp_path, check=True)
    gone.unlink()
    assert tracked_text_files(tmp_path) == []                       # a tracked deletion is not an error
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir" / "a.md").write_text("x\n")
    assert [p.name for p in tracked_text_files(tmp_path)] == ["a.md"]


def test_a_binary_file_must_be_a_picture_or_parquet(tmp_path):
    blob = b"\xff\xfe\x00\x01\x80binary"
    files = _tree(tmp_path, {"docs/data.bin": "", "docs/shot.png": "", "tests/fixtures/x.parquet": "", "paper/main.pdf": ""})
    magic = {"docs/shot.png": b"\x89PNG\r\n\x1a\n", "tests/fixtures/x.parquet": b"PAR1"}      # a picture or Parquet file says so in its first bytes
    for f in files:
        rel = str(f.relative_to(tmp_path))
        f.write_bytes(magic.get(rel, b"") + blob + (b"PAR1" if rel.endswith(".parquet") else b""))
    got = scan_repo(tmp_path, files, T3, set())
    assert sorted(h[0] for h in got) == ["docs/data.bin", "paper/main.pdf"]
    assert all(h[2].startswith("binary or undecodable file") for h in got)
    text = _tree(tmp_path, {"docs/ok.md": "plain text\n"})
    assert scan_repo(tmp_path, text, T3, set()) == []


def test_a_url_that_names_a_blocked_term_in_its_path_fails_but_a_clean_url_passes(tmp_path):
    bad = _tree(tmp_path, {"docs/a.md": "See https://example.org/people/zebra-foo/profile for details.\n"})
    assert ("docs/a.md", 1, "forbidden term in a URL") in scan_repo(tmp_path, bad, T3, set())
    ok = _tree(tmp_path, {"docs/b.md": "See https://example.org/docs/page.html. Then (https://example.org/x) and https://example.org/y, done.\n"})
    assert scan_repo(tmp_path, ok, T3, set()) == []
    assert strip_urls("see https://a.b/c.").split() == ["see", "."]       # a final period is prose, not part of the URL
    assert strip_urls("(https://a.b/c) and https://a.b/d, then").split() == ["(", ")", "and", ",", "then"]


def test_a_term_glued_to_the_end_of_a_url_is_still_prose(tmp_path):
    files = _tree(tmp_path, {"docs/c.md": "Read https://example.org/page,zebrafoo matters here\n"})
    assert ("docs/c.md", 1, "forbidden term") in scan_repo(tmp_path, files, T3, set())


def test_the_digest_format_note_is_in_the_module_documentation():
    assert "lower-cased, single-space-joined n-grams" in scan_text.__doc__


# ------------------------------------------------------------ REV-G-002: Parquet value types, JPEG and GIF comments
def _short_term_hits(data: bytes, suffix: str) -> list[str]:
    return scan_binary(data, suffix, {_digest("qzx")})


def _parquet_blob(table) -> bytes:
    import io

    import pyarrow.parquet as pq

    buf = io.BytesIO()
    pq.write_table(table, buf, compression="gzip")
    return buf.getvalue()


def test_a_short_blocked_term_in_a_dictionary_list_struct_or_binary_column_is_found():             # REV-G-002
    import pyarrow as pa

    clean = pa.table({"a": [1, 2]})
    assert _short_term_hits(_parquet_blob(clean), ".parquet") == []
    cases = {
        "dictionary": pa.table({"c": pa.array(["fine", "qzx"]).dictionary_encode()}),
        "list": pa.table({"c": pa.array([["fine"], ["met qzx today", "x"]])}),
        "large_list": pa.table({"c": pa.array([["qzx"], []], type=pa.large_list(pa.string()))}),
        "struct": pa.table({"c": pa.array([{"inner": "fine"}, {"inner": "qzx"}])}),
        "struct_of_list": pa.table({"c": pa.array([{"inner": ["qzx"]}, {"inner": []}])}),
        "binary": pa.table({"c": pa.array([b"fine", b"qzx"], type=pa.binary())}),
        "large_binary": pa.table({"c": pa.array([b"fine", b"a qzx b"], type=pa.large_binary())}),
        "dictionary_of_binary": pa.table({"c": pa.array([b"fine", b"qzx"], type=pa.binary()).dictionary_encode()}),
    }
    for name, table in cases.items():
        assert _short_term_hits(_parquet_blob(table), ".parquet") == ["forbidden term"], name


def _jpeg(*segments: tuple[int, bytes]) -> bytes:
    out = b"\xff\xd8"
    for marker, body in segments:
        out += b"\xff" + bytes([marker]) + (len(body) + 2).to_bytes(2, "big") + body
    return out + b"\xff\xda\x00\x02" + b"\x12\x34\x56" + b"\xff\xd9"


def _gif(*blocks: bytes) -> bytes:
    return b"GIF89a" + b"\x01\x00\x01\x00\x00\x00\x00" + b"".join(blocks) + b"\x3b"


def _gif_ext(label: int, *chunks: bytes) -> bytes:
    return b"\x21" + bytes([label]) + b"".join(bytes([len(c)]) + c for c in chunks) + b"\x00"


def test_jpeg_comment_and_application_segments_and_gif_extensions_are_scanned():                    # REV-G-002
    assert _short_term_hits(_jpeg((0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")), ".jpg") == []
    assert _short_term_hits(_jpeg((0xFE, b"a plain comment")), ".jpeg") == []
    assert _short_term_hits(_jpeg((0xFE, b"made by qzx")), ".jpg") == ["forbidden term"]
    assert _short_term_hits(_jpeg((0xE1, b"Exif\x00\x00 qzx")), ".jpg") == ["forbidden term"]
    assert _short_term_hits(_jpeg((0xE0, b"JFIF\x00"), (0xED, b"Photoshop 3.0\x00 qzx")), ".jpg") == ["forbidden term"]
    clean_gif = _gif(_gif_ext(0xFE, b"just a comment"))
    assert _short_term_hits(clean_gif, ".gif") == []
    assert _short_term_hits(_gif(_gif_ext(0xFE, b"made by ", b"qzx")), ".gif") == ["forbidden term"]
    assert _short_term_hits(_gif(_gif_ext(0xFF, b"NETSCAPE2.0", b"qzx")), ".gif") == ["forbidden term"]
    image = b"\x2c" + b"\x00" * 8 + b"\x00" + b"\x02" + b"\x03" + b"\x01\x02\x03" + b"\x00"       # an image block before the comment
    assert _short_term_hits(_gif(image, _gif_ext(0xFE, b"qzx")), ".gif") == ["forbidden term"]
