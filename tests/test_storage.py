"""T-033 contracts: one resolver for the heavy directories, exFAT-safe writes, `moot storage`."""
import datetime as dt
import json
import os
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("raw", "ledger_dir", "reports", "models", "cards", "cache", "experiments")


def _paths(imp, **kw):
    return imp("mootcourt.storage").storage_paths(**kw)


# ------------------------------------------------------------------ resolver
def test_unset_variable_gives_the_repo_local_defaults(imp, tmp_path):
    p = _paths(imp, environ={}, cwd=tmp_path)
    assert p.root is None
    assert p.raw == Path("data/raw") and p.ledger_dir == Path("data/ledger") and p.ledger_path == Path("data/ledger/ledger.parquet")
    assert p.reports == Path("reports") and p.models == Path("models") and p.cards == Path("cards")
    assert p.cache == Path("cache") and p.experiments == Path("experiments")


def test_environment_variable_moves_every_heavy_directory(imp, tmp_path):
    p = _paths(imp, environ={"MOOTCOURT_DATA_ROOT": str(tmp_path / "x")}, cwd=tmp_path)
    assert p.root == tmp_path / "x"
    for name in NAMES:
        assert tmp_path / "x" in getattr(p, name).parents, name
    assert p.ledger_path.parent == p.ledger_dir and p.gates_path == p.reports / "gates.json"


def test_toml_is_used_when_the_variable_is_unset_and_the_variable_wins(imp, tmp_path):
    (tmp_path / "mootcourt.toml").write_text(f'[storage]\ndata_root = "{tmp_path / "from_toml"}"\n', encoding="utf-8")
    assert _paths(imp, environ={}, cwd=tmp_path).root == tmp_path / "from_toml"
    both = _paths(imp, environ={"MOOTCOURT_DATA_ROOT": str(tmp_path / "from_env")}, cwd=tmp_path)
    assert both.root == tmp_path / "from_env"


def test_no_module_hardcodes_a_heavy_directory(imp):
    pat = re.compile(r"""Path\(\s*["'](data|reports|models|cards|cache|experiments)["']|["'](data|reports|models|cards)["']\s*\)?\s*/""")
    offenders = []
    for base in (ROOT / "src" / "mootcourt", ROOT / "scripts"):
        for f in sorted(base.rglob("*.py")):
            if f.name == "storage.py":
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if pat.search(line):
                    offenders.append(f"{f.relative_to(ROOT)}:{n}: {line.strip()}")
    assert not offenders, "\n".join(offenders)


# ------------------------------------------------------------------ exFAT
def _issued_card(imp, make_synth, reliability_factory, frozen_clock):
    ledger_mod, bundle_mod, card_mod = imp("mootcourt.ledger"), imp("mootcourt.bundle"), imp("mootcourt.card")
    full, _ = make_synth(seed=311, n_tests=120, variants_per_test=1)
    bundle = bundle_mod.fit_bundle(full, "synthetic", ledger_mod.snapshot_id(full, today=dt.date(2014, 7, 1)))
    origin = full["usable_after"].max().to_pydatetime()
    now = origin + dt.timedelta(days=1)
    report = reliability_factory(as_of=now - dt.timedelta(days=1), n=500)
    r = full.iloc[0]
    req = card_mod.CardRequest(source="synthetic", headline=json.loads(r["features_json"])["headline"], image_changed=False,
                               impressions=20000, origin=origin, row_id=r["row_id"])
    return card_mod.build_card(bundle, req, reliability=report, now=now), full


def test_write_paths_survive_chmod_that_raises_and_never_link_or_symlink(imp, tmp_path, make_synth, reliability_factory, frozen_clock, monkeypatch):
    card_mod, ledger_mod, loop = imp("mootcourt.card"), imp("mootcourt.ledger"), imp("mootcourt.loop")
    card, full = _issued_card(imp, make_synth, reliability_factory, frozen_clock)

    def refuse(*a, **k):
        raise PermissionError("exFAT: operation not permitted")

    monkeypatch.setattr(os, "chmod", refuse)
    monkeypatch.setattr(Path, "chmod", refuse)
    monkeypatch.setattr(os, "symlink", refuse)
    monkeypatch.setattr(os, "link", refuse)          # exFAT has no hard links either
    path = card_mod.freeze_card(card, tmp_path / "cards")
    assert json.loads(path.read_text())["card_id"] == card.card_id
    with pytest.raises(card_mod.CardFrozenError):
        card_mod.freeze_card(card, tmp_path / "cards")
    sid = ledger_mod.write_snapshot(full, tmp_path / "ledger", today=dt.date(2014, 7, 1))
    assert (tmp_path / "ledger" / "snapshots" / sid / "ledger.parquet").exists()
    loop._atomic_write(tmp_path / "cards" / "outcomes" / "x.json", "{}", read_only=True)
    assert (tmp_path / "cards" / "outcomes" / "x.json").exists()
    assert not [p for p in tmp_path.rglob("*") if p.is_symlink()]


def test_safe_chmod_returns_false_instead_of_raising(imp, tmp_path, monkeypatch):
    storage = imp("mootcourt.storage")
    f = tmp_path / "f"
    f.write_text("x")
    assert storage.safe_chmod(f, 0o444) is True
    monkeypatch.setattr(os, "chmod", lambda *a, **k: (_ for _ in ()).throw(PermissionError("no")))
    assert storage.safe_chmod(f, 0o644) is False


# ------------------------------------------------------------------ CLI
def _run(imp, args, env=None):
    return CliRunner().invoke(imp("mootcourt.cli").app, args, env=env)


def test_moot_storage_prints_paths_sizes_and_free_space(imp, tmp_path):
    root = tmp_path / "root"
    (root / "reports").mkdir(parents=True)
    (root / "reports" / "a.txt").write_bytes(b"x" * 2048)
    res = _run(imp, ["storage"], env={"MOOTCOURT_DATA_ROOT": str(root)})
    assert res.exit_code == 0, res.output
    flat = re.sub(r"[│╭╰╮╯─\s]+", " ", res.output)
    assert str(root.resolve()) in flat.replace("\n", "") or str(root) in flat
    assert "free" in flat.lower() and "2.0 KB" in flat and "MOOTCOURT_DATA_ROOT" in flat


def test_moot_storage_warns_below_ten_gigabytes(imp, tmp_path, monkeypatch):
    import shutil
    usage = shutil._ntuple_diskusage(100 * 1024**3, 95 * 1024**3, 5 * 1024**3)
    monkeypatch.setattr(shutil, "disk_usage", lambda p: usage)
    res = _run(imp, ["storage"], env={"MOOTCOURT_DATA_ROOT": str(tmp_path / "r")})
    assert res.exit_code == 0 and "warning" in res.output.lower() and "10 GB" in res.output


def test_commands_write_under_the_root_when_the_variable_is_set(imp, tmp_path):
    root = tmp_path / "root"
    res = _run(imp, ["ingest", "--source", "synthetic", "--n-tests", "40"], env={"MOOTCOURT_DATA_ROOT": str(root)})
    assert res.exit_code == 0, res.output
    assert (root / "data" / "ledger" / "ledger.parquet").exists()
    res = _run(imp, ["fit", "--source", "synthetic"], env={"MOOTCOURT_DATA_ROOT": str(root)})
    assert res.exit_code == 0, res.output
    assert list((root / "models").glob("*/manifest.json"))


def test_docs_and_makefile_explain_the_variable(imp):
    for rel in ("README.md", "docs/method.md", "Makefile"):
        assert "MOOTCOURT_DATA_ROOT" in (ROOT / rel).read_text(encoding="utf-8"), rel
    assert "external" in (ROOT / "README.md").read_text(encoding="utf-8").lower()
