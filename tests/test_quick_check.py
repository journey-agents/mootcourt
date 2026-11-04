"""Tier B and Tier C tooling: ``make quick-check`` (the sample ledger's backtest diffed against the committed report) and
``assemble_run_folder.py --update`` (the refusal of a stale dependent)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def qc():
    return _load("quick_check")


@pytest.fixture(scope="module")
def arf():
    return _load("assemble_run_folder")


def sample_root(tmp_path: Path, qc) -> Path:
    """A project root holding a copy of the committed sample report where ``quick_check`` looks for it."""
    root = tmp_path / "root"
    ref = root / qc.REFERENCE
    ref.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / qc.REFERENCE, ref)
    return root


def bump_one_value(path: Path) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    row = doc["tables"]["aggregate"][0]
    key = next(k for k, v in row.items() if isinstance(v, float) and k not in ("n",))
    row[key] = row[key] + 0.01
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_quick_check_passes_on_the_committed_sample_report(tmp_path, qc):
    res = qc.quick_check(sample_root(tmp_path, qc))
    assert res.ok, res.diffs[:5]
    assert res.diffs == [] and res.seconds > 0


def test_quick_check_fails_when_a_number_moved(tmp_path, qc):
    root = sample_root(tmp_path, qc)
    bump_one_value(root / qc.REFERENCE)
    res = qc.quick_check(root)
    assert res.ok is False and len(res.diffs) == 1 and "aggregate[0]" in res.diffs[0]


def test_the_diff_ignores_model_ids_creation_times_snapshot_dates_and_seconds_fields(qc):
    a = {"header": {"model_id": "aaa", "created_at": "2026-11-04", "snapshot_id": "20261104-b04b5b1dd18c", "seed": 0},
         "tables": {"x": [{"fit_seconds": 1.5, "v": 0.25}]}}
    b = {"header": {"model_id": "bbb", "created_at": "2026-11-05", "snapshot_id": "20261105-b04b5b1dd18c", "seed": 0},
         "tables": {"x": [{"fit_seconds": 9.0, "v": 0.25}]}}
    assert qc.diff_reports(a, b) == []
    b["tables"]["x"][0]["v"] = 0.26
    assert qc.diff_reports(a, b) == ["tables.x[0].v: 0.25 != 0.26"]
    b["tables"]["x"][0]["v"] = 0.25
    b["header"]["snapshot_id"] = "20261105-ffffffffffff"
    assert len(qc.diff_reports(a, b)) == 1, "a changed ledger digest is a change"
    b["header"]["snapshot_id"] = "20261105-b04b5b1dd18c"
    del b["tables"]["x"][0]["v"]
    assert qc.diff_reports(a, b) == ["tables.x[0].v: present in one report only"]


# ---------------------------------------------------------------------------------------------- assemble_run_folder --update
def _report(model_id: str, snap="20261103-aaaaaaaaaaaa", gates=None):
    gates = gates or {"0.90": {"n_200": 175, "n_400": 250}}
    return {"header": {"source": "upworthy", "snapshot_id": snap, "model_id": model_id, "gate_by_target": gates}, "tables": {}}


def _folder(tmp_path: Path) -> tuple[Path, Path]:
    run = tmp_path / "run"
    run.mkdir()
    (run / "gates.json").write_text(json.dumps({"by_target": {"0.90": {"n_200": 175, "n_400": 250}}}))
    (run / "backtest-upworthy-20261103-aaaaaaaaaaaa.json").write_text(json.dumps(_report("m1")))
    (run / "card-latency.json").write_text(json.dumps({"model_id": "m1"}))
    (run / "paper-extras-upworthy-20261103-aaaaaaaaaaaa.json").write_text(
        json.dumps({"header": {"snapshot_id": "20261103-aaaaaaaaaaaa", "created_at": "2026-11-04T19:00:00+00:00"}}))
    new = tmp_path / "new"
    new.mkdir()
    return run, new


def test_update_copies_only_the_named_reports(tmp_path, arf):
    run, new = _folder(tmp_path)
    (new / "card-latency.json").write_text(json.dumps({"model_id": "m1", "p50_ms": 3}))
    before = {p.name: p.read_bytes() for p in run.iterdir()}
    out = arf.update(run, [new / "card-latency.json"])
    assert out["changed"] == ["card-latency.json"]
    after = {p.name: p.read_bytes() for p in run.iterdir()}
    assert [n for n in after if after[n] != before[n]] == ["card-latency.json"]


def test_update_refuses_a_stale_dependent(tmp_path, arf):
    run, new = _folder(tmp_path)
    # a card-latency file measured on an older model than the backtest it depends on
    (new / "card-latency.json").write_text(json.dumps({"model_id": "m0"}))
    with pytest.raises(SystemExit) as exc:
        arf.update(run, [new / "card-latency.json"])
    assert "m0" in str(exc.value) and "m1" in str(exc.value)
    assert json.loads((run / "card-latency.json").read_text()) == {"model_id": "m1"}, "a refused update copies nothing"


def test_update_refuses_a_backtest_built_with_other_gates_than_the_folder_holds(tmp_path, arf):
    run, new = _folder(tmp_path)
    name = "backtest-upworthy-20261103-aaaaaaaaaaaa.json"
    (new / name).write_text(json.dumps(_report("m1", gates={"0.90": {"n_200": 100, "n_400": 150}})))
    with pytest.raises(SystemExit) as exc:
        arf.update(run, [new / name])
    assert "gates" in str(exc.value)


def test_update_refuses_a_new_backtest_that_leaves_a_dependent_on_the_old_model(tmp_path, arf):
    run, new = _folder(tmp_path)
    name = "backtest-upworthy-20261103-aaaaaaaaaaaa.json"
    (new / name).write_text(json.dumps(_report("m2")))
    with pytest.raises(SystemExit) as exc:
        arf.update(run, [new / name])
    assert "card-latency.json" in str(exc.value)
    (new / "card-latency.json").write_text(json.dumps({"model_id": "m2"}))
    out = arf.update(run, [new / name, new / "card-latency.json"])
    assert sorted(out["changed"]) == ["backtest-upworthy-20261103-aaaaaaaaaaaa.json", "card-latency.json"]
