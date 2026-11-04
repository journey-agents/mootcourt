"""T-035 contracts: moot init, moot doctor and the quickstart."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
NOW_SAMPLE = pd.Timestamp("2025-12-30", tz="UTC").to_pydatetime()


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    return tmp_path


def _app(imp):
    return imp("mootcourt.cli").app


def _run(imp, *args):
    return CliRunner().invoke(_app(imp), list(args))


def test_init_writes_config_layout_sample_and_prints_three_commands(imp, project):
    res = _run(imp, "init")
    assert res.exit_code == 0, res.output
    cfg = tomllib.loads((project / "mootcourt.toml").read_text(encoding="utf-8"))
    assert cfg["storage"]["data_root"] == str((project / "mootcourt-data").resolve())
    assert cfg["cells"]["names"] == ["checkout_conversion", "pages_per_session", "revenue_per_user"]
    assert cfg["decision"]["action_threshold"] == 0.35 and cfg["gate"]["target_power"] == 0.90
    for sub in ("data/raw", "data/ledger", "reports", "models", "cards", "cache"):
        assert (project / "mootcourt-data" / sub).is_dir()
    assert (project / "mootcourt-data" / "data" / "sample-ledger.csv").is_file()
    gates = json.loads((project / "mootcourt-data" / "reports" / "gates.json").read_text())
    assert gates["decision_target"] == 0.9
    steps = re.findall(r"^\s+\d\. (moot .+)$", res.output, re.M)
    assert len(steps) == 3 and steps[0].startswith("moot ingest") and "moot backtest" in steps[1] and steps[2].startswith("moot card")


def test_init_refuses_to_overwrite_without_force_and_accepts_options(imp, project):
    assert _run(imp, "init").exit_code == 0
    again = _run(imp, "init")
    assert again.exit_code == 1 and "--force" in again.output
    ok = _run(imp, "init", "--force", "--cells", "a, b", "--name", "pilot", "--data-root", str(project / "elsewhere"))
    assert ok.exit_code == 0
    cfg = tomllib.loads((project / "mootcourt.toml").read_text(encoding="utf-8"))
    assert cfg["cells"]["names"] == ["a", "b"] and cfg["project"]["name"] == "pilot" and (project / "elsewhere" / "models").is_dir()


def test_the_written_config_is_read_back_by_the_settings_loader(imp, project):
    _run(imp, "init")
    s = imp("mootcourt.settings").load_settings(project)
    assert s["exists"] and s["decision"]["action_threshold"] == 0.35 and s["gate"]["target_power"] == 0.90 and len(s["cells"]) == 3
    (project / "mootcourt.toml").write_text('[decision]\naction_threshold = 7\n')
    with pytest.raises(ValueError, match="action_threshold"):
        imp("mootcourt.settings").load_settings(project)


def _pipeline(imp, project):
    for args in (["init"],
                 ["ingest", "--format", "generic", "--input", "mootcourt-data/data/sample-ledger.csv", "--source-name", "sample"],
                 ["fit", "--source", "sample"], ["backtest", "--source", "sample"]):
        res = _run(imp, *args)
        assert res.exit_code == 0, (args, res.output)


def test_doctor_on_a_healthy_project_exits_0_and_writes_a_report(imp, project):
    _pipeline(imp, project)
    ob = imp("mootcourt.onboarding")
    rep = ob.run_doctor(now=NOW_SAMPLE)
    assert rep["status"] == "ok" and ob.exit_code(rep) == 0, [c for c in rep["checks"] if c["status"] != "ok"]
    written = json.loads((project / "mootcourt-data" / "reports" / "doctor.json").read_text())
    names = {c["name"] for c in written["checks"]}
    assert {"python", "data root", "ledger", "model sample", "reliability sample", "cells"} <= names and "package numpy" in names


def test_doctor_warns_on_an_old_reliability_report_and_exits_1(imp, project):
    _pipeline(imp, project)
    res = _run(imp, "doctor")
    assert res.exit_code == 1 and "WARN" in res.output and "days old" in res.output


def test_doctor_warns_when_the_model_is_older_than_the_ledger(imp, project):
    _pipeline(imp, project)
    ex = imp("mootcourt.sources.synthetic")
    more = pd.read_csv(project / "mootcourt-data" / "data" / "sample-ledger.csv").iloc[:3].assign(experiment_id=["z1", "z2", "z3"])
    more.to_csv(project / "more.csv", index=False)
    assert _run(imp, "ingest", "--format", "generic", "--input", "more.csv", "--source-name", "sample").exit_code == 0
    rep = imp("mootcourt.onboarding").run_doctor(now=NOW_SAMPLE)
    model = next(c for c in rep["checks"] if c["name"] == "model sample")
    assert model["status"] == "warn" and "moot fit" in model["detail"] and ex is not None


def test_doctor_warns_under_10_gb_free(imp, project, monkeypatch):
    _pipeline(imp, project)
    real = shutil.disk_usage
    monkeypatch.setattr(shutil, "disk_usage", lambda p: type(real(p))(100 * 2**30, 99 * 2**30, 2**30))
    rep = imp("mootcourt.onboarding").run_doctor(now=NOW_SAMPLE)
    root = next(c for c in rep["checks"] if c["name"] == "data root")
    assert root["status"] == "warn" and "10 GB" in root["detail"]


def test_doctor_fails_on_a_missing_root_a_broken_ledger_and_an_unreachable_service(imp, project):
    _pipeline(imp, project)
    ob = imp("mootcourt.onboarding")
    led = project / "mootcourt-data" / "data" / "ledger" / "ledger.parquet"
    df = pd.read_parquet(led)
    df.drop(columns=["usable_after"]).to_parquet(led)
    rep = ob.run_doctor(now=NOW_SAMPLE)
    assert next(c for c in rep["checks"] if c["name"] == "ledger")["status"] == "fail" and ob.exit_code(rep) == 2
    cfg = (project / "mootcourt.toml").read_text(encoding="utf-8") + '\n[service]\nurl = "http://127.0.0.1:9"\n'
    (project / "mootcourt.toml").write_text(cfg)
    rep = ob.run_doctor(now=NOW_SAMPLE, write=False)
    assert next(c for c in rep["checks"] if c["name"] == "service")["status"] == "fail"
    shutil.rmtree(project / "mootcourt-data")
    gone = ob.run_doctor(now=NOW_SAMPLE, write=False)
    assert next(c for c in gone["checks"] if c["name"] == "data root")["status"] == "fail" and ob.exit_code(gone) == 2


def test_doctor_reports_a_service_that_answers(imp, project):
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        got = imp("mootcourt.onboarding").check_service(f"http://127.0.0.1:{srv.server_address[1]}")
    finally:
        srv.shutdown()
    assert got[0]["status"] == "ok"


def test_the_card_uses_the_configured_action_threshold(imp, project):
    _pipeline(imp, project)
    cfg = (project / "mootcourt.toml").read_text(encoding="utf-8").replace("action_threshold = 0.35", "action_threshold = 0.6")
    (project / "mootcourt.toml").write_text(cfg)
    res = _run(imp, "card", "--source", "sample", "--cell", "checkout_conversion", "--impressions", "20000",
               "--now", "2025-12-30T00:00:00+00:00", "--json")
    assert res.exit_code == 0, res.output
    assert json.loads(res.output)["robustness"]["action_threshold"] == 0.6


# ---------------------------------------------------------------- the quickstart, executed in a subprocess
def _quickstart_commands() -> list[str]:
    text = (ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")
    cmds = []
    for block in re.findall(r"```\n(.*?)```", text, re.S):
        for line in block.strip().splitlines():
            if line.startswith("moot "):
                cmds.append(line)
    return cmds


def test_quickstart_document_lists_the_whole_path():
    cmds = _quickstart_commands()
    assert [c.split()[1] for c in cmds] == ["init", "ingest", "fit", "backtest", "card", "doctor"]
    text = (ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")
    assert "ten minutes" in text and "pip install -e ." in text


def test_quickstart_runs_end_to_end_in_a_subprocess_without_network(tmp_path):
    bin_dir = str(Path(sys.executable).parent)
    env = {k: v for k, v in os.environ.items() if k != "MOOTCOURT_DATA_ROOT"}
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    env.update({"HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9", "NO_PROXY": ""})   # any network call would fail loudly
    t0 = time.perf_counter()
    last = None
    for cmd in _quickstart_commands():
        last = subprocess.run(cmd, shell=True, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)
        if cmd.startswith("moot doctor"):
            assert last.returncode in (0, 1), last.stdout + last.stderr           # warnings are expected on the static sample
        else:
            assert last.returncode == 0, f"{cmd}\n{last.stdout}\n{last.stderr}"
        if cmd.startswith("moot card"):
            card = last.stdout
    wall = time.perf_counter() - t0
    assert "Status: issue" in card or "Prediction" in card
    assert "No usable prediction" not in card, "the first card on the sample ledger must be an issued card"
    assert "P(significant and positive)" in card
    assert wall < 600, f"the quickstart took {wall:.0f} s"


# T6-plan row 4 (R2 minor 8, call 252): the doctor counts the cards no join will score
def _doctor_world(tmp_path, monkeypatch):
    """The sample ledger of ``moot init`` with one row made unadmitted, a data root, and the doctor's config pointing at it."""
    from mootcourt import onboarding
    from mootcourt.importers.ingest import import_file
    from mootcourt.importers.sample import sample_exchange
    from mootcourt.ledger import write_ledger
    from mootcourt.storage import storage_paths

    root = tmp_path / "mootcourt-data"
    layout = storage_paths(root=root)
    for folder in layout.named().values():
        folder.mkdir(parents=True, exist_ok=True)
    csv = tmp_path / "sample.csv"
    sample_exchange().to_csv(csv, index=False)
    ledger, _ = import_file("generic", csv, "sample")
    ledger = ledger.sort_values("usable_after").reset_index(drop=True)
    ids = ledger["row_id"].tolist()
    unadmitted = ids[5]
    ledger.loc[ledger["row_id"] == unadmitted, "status"] = "low_exposure"
    write_ledger(ledger, layout.ledger_path)
    (tmp_path / "mootcourt.toml").write_text(onboarding.config_text(data_root=Path(layout.root), cells=["checkout_conversion"], name="t6"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MOOTCOURT_DATA_ROOT", raising=False)
    now = pd.Timestamp(ledger["usable_after"].iloc[20]).to_pydatetime()
    past = [r for r in ids[:20] if r != unadmitted]
    future = ids[40]
    return layout, ledger, now, past, future, unadmitted


def _card_file(layout, card_id, row_id, source="sample"):
    (layout.cards).mkdir(parents=True, exist_ok=True)
    (layout.cards / f"{card_id}.json").write_text(json.dumps({"card_id": card_id, "source": source, "request": {"row_id": row_id}}))


def test_the_doctor_counts_cards_with_no_row_id_an_unknown_row_a_passed_horizon_and_an_unadmitted_test(tmp_path, monkeypatch):
    from mootcourt import onboarding

    layout, ledger, now, past, future, unadmitted = _doctor_world(tmp_path, monkeypatch)
    _card_file(layout, "c-norow", None)
    _card_file(layout, "c-unknown", "sample:exp-999:treatment::checkout_conversion")
    _card_file(layout, "c-due1", past[0])
    _card_file(layout, "c-due2", past[1])
    _card_file(layout, "c-done", past[2])
    (layout.cards / "outcomes").mkdir()
    (layout.cards / "outcomes" / "c-done.json").write_text(json.dumps({"card_id": "c-done", "source": "sample", "scored": True}))
    _card_file(layout, "c-open", future)
    _card_file(layout, "c-unadmitted", unadmitted)
    _card_file(layout, "c-other", None, source="elsewhere")
    doc = onboarding.run_doctor(now=now, write=False)
    check = next(c for c in doc["checks"] if c["name"] == "cards sample")
    assert check["status"] == "warn"
    for part in ("cards with no row id: 1", "cards with a row id absent from the ledger: 1", "cards past their horizon with no outcome: 2",
                 "cards on an unadmitted test: 1"):
        assert part in check["detail"], check["detail"]
    other = next(c for c in doc["checks"] if c["name"] == "cards elsewhere")
    assert "cards with no row id: 1" in other["detail"] and "absent from the ledger" not in other["detail"]


def test_the_doctor_adds_no_card_counts_when_every_card_can_be_scored(tmp_path, monkeypatch):
    from mootcourt import onboarding

    layout, ledger, now, past, future, unadmitted = _doctor_world(tmp_path, monkeypatch)
    _card_file(layout, "c-open", future)
    doc = onboarding.run_doctor(now=now, write=False)
    assert not [c for c in doc["checks"] if c["name"] == "cards sample"], "a card whose horizon has not passed is not a finding"
