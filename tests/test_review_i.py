"""Chunk I: trigger-removal ablation (E3), score by calendar year (E7) and the review H backlog (REV-H-001 to REV-H-003).

The weekly replay (E7) is tested in test_replay.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
TRIGGERS = ("support", "novelty", "reliability", "instability")
GATES = {"n_200": 20, "n_400": 30, "target_power": 0.9, "decision_target": 0.9,
         "by_target": {"0.80": {"n_200": 15, "n_400": 25}, "0.90": {"n_200": 20, "n_400": 30}}}


def _ledger(make_synth):
    return make_synth(seed=61, n_tests=260, variants_per_test=2)[0]


def _scores(imp, ledger, **kw):
    h = imp("mootcourt.harness")
    return h.rolling_origin(ledger, h.default_rungs("synthetic", ledger), h.quarterly_origins(ledger), source="synthetic", **kw)


def _reasons(scores):
    p2 = scores[scores["rung"] == "P2"].sort_values("row_id")
    return p2["row_id"].tolist(), [set(filter(None, r.split(","))) for r in p2["abstain_reasons"]], p2["abstain"].tolist()


def _cli(imp, args, root):
    return CliRunner().invoke(imp("mootcourt.cli").app, args, env={"MOOTCOURT_DATA_ROOT": str(root)})


@pytest.fixture
def root(imp, tmp_path, make_synth):
    r = tmp_path / "root"
    imp("mootcourt.ledger").write_ledger(_ledger(make_synth), r / "data" / "ledger" / "ledger.parquet")
    (r / "reports").mkdir(parents=True)
    (r / "reports" / "gates.json").write_text(json.dumps(GATES))
    return r


# ------------------------------------------------------------------ E3: drop one trigger
def test_the_abstain_config_validates_the_disabled_triggers(imp):
    ab = imp("mootcourt.abstain")
    assert ab.AbstainConfig().disabled == frozenset()
    assert ab.AbstainConfig(disabled=("support", "novelty")).disabled == frozenset({"support", "novelty"})
    with pytest.raises(ValueError, match="unknown trigger"):
        ab.AbstainConfig(disabled=("support", "vibes"))


def test_decide_skips_a_disabled_trigger_and_keeps_the_others(imp, reliability_factory):
    from conftest import FROZEN_NOW

    ab = imp("mootcourt.abstain")
    kw = dict(n_support=3, density=0.1, density_threshold=1.0, reliability_report=None, cell="c", now=FROZEN_NOW)
    full = ab.decide(**kw)
    assert set(full.reasons) == {"support", "novelty", "reliability"}
    for t in ("support", "novelty", "reliability"):
        d = ab.decide(**kw, config=ab.AbstainConfig(disabled=(t,)))
        assert set(d.reasons) == set(full.reasons) - {t}, t
        assert t not in d.details
    none_left = ab.decide(**kw, config=ab.AbstainConfig(disabled=("support", "novelty", "reliability", "instability")))
    assert none_left.status == "issue" and none_left.reasons == ()


@pytest.mark.parametrize("trigger", TRIGGERS)
def test_a_backtest_without_one_trigger_loses_exactly_that_trigger(imp, make_synth, trigger):
    ledger = _ledger(make_synth)
    ids, base, base_flag = _reasons(_scores(imp, ledger))
    assert any(trigger in r for r in base), f"the fixture must fire {trigger} at least once"
    ids2, got, flag = _reasons(_scores(imp, ledger, drop_triggers=(trigger,)))
    assert ids2 == ids
    assert all(trigger not in r for r in got)
    assert got == [r - {trigger} for r in base]                       # every other trigger is untouched, row by row
    assert flag == [bool(r) for r in got]                              # the abstain flag follows the remaining reasons
    assert sum(flag) <= sum(base_flag)                                  # equal when every row it flagged was also flagged by another trigger


def test_scoring_columns_do_not_depend_on_which_triggers_are_dropped(imp, make_synth):
    ledger = _ledger(make_synth)
    a, b = _scores(imp, ledger), _scores(imp, ledger, drop_triggers=("support", "novelty", "reliability", "instability"))
    cols = ["logscore", "crps", "p_sig", "brier_event", "lo90", "hi90", "point"]
    pd.testing.assert_frame_equal(a[["row_id", "rung", *cols]].reset_index(drop=True), b[["row_id", "rung", *cols]].reset_index(drop=True))
    assert not b["abstain"].any()


def test_the_harness_refuses_an_unknown_trigger_name(imp, make_synth):
    with pytest.raises(ValueError, match="unknown trigger"):
        _scores(imp, _ledger(make_synth), drop_triggers=("nope",))


def test_the_cli_names_dropped_triggers_in_the_file_header_and_note(imp, root):
    res = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--drop-trigger", "support", "--drop-trigger", "novelty"], root)
    assert res.exit_code == 0, res.output
    files = list((root / "reports" / "ablations").glob("backtest-synthetic-*--drop-trigger-novelty-support.json"))
    assert len(files) == 1, [p.name for p in (root / "reports" / "ablations").iterdir()]
    doc = json.loads(files[0].read_text())
    assert doc["header"]["variant"] == {"drop_trigger": ["novelty", "support"]}
    assert "--drop-trigger novelty --drop-trigger support" in doc["header"]["command"]
    ab = {r["cell"]: r for r in doc["tables"]["abstention"]}["ALL"]
    assert ab["support"] == 0 and ab["novelty"] == 0 and ab["reliability"] > 0
    assert "Disabled for this run: novelty, support" in doc["notes"]["abstention_triggers"]
    assert not list((root / "reports").glob("backtest-synthetic-*.json")), "an ablation never replaces the main report"
    # one flag, one name
    one = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--drop-trigger", "instability"], root)
    assert one.exit_code == 0
    assert list((root / "reports" / "ablations").glob("backtest-synthetic-*--drop-trigger-instability.json"))


def test_the_cli_refuses_an_unknown_trigger_and_a_repeat_is_not_an_error(imp, root):
    bad = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--drop-trigger", "vibes"], root)
    assert bad.exit_code != 0 and "support" in bad.output
    twice = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20", "--drop-trigger", "support", "--drop-trigger", "support"], root)
    assert twice.exit_code == 0
    assert list((root / "reports" / "ablations").glob("backtest-synthetic-*--drop-trigger-support.json"))


# ------------------------------------------------------------------ E7: score by calendar year
def test_score_by_year_partitions_the_scored_rows_by_the_year_the_test_started(imp, root, make_synth):
    res = _cli(imp, ["backtest", "--source", "synthetic", "--bootstrap", "20"], root)
    assert res.exit_code == 0, res.output
    path = next((root / "reports").glob("backtest-synthetic-*.json"))
    doc = json.loads(path.read_text())
    by_year = pd.DataFrame(doc["tables"]["score_by_year"])
    assert {"year", "cell", "rung", "n", "n_tests", "logscore", "logscore_lo", "logscore_hi", "brier_skill", "brier_skill_lo",
            "brier_skill_hi", "direction_accuracy", "abstention_rate"} <= set(by_year.columns)
    scores = pd.read_parquet(next((root / "reports").glob("scores-synthetic-*.parquet")))
    ledger = _ledger(make_synth).set_index("row_id")
    scores["year"] = ledger.loc[scores["row_id"], "started_at"].dt.year.to_numpy()
    assert sorted(by_year["year"].unique()) == sorted(scores["year"].unique()) and len(scores["year"].unique()) >= 2
    for rung, g in scores.groupby("rung"):
        got = by_year[(by_year["rung"] == rung) & (by_year["cell"] == "ALL")].set_index("year")["n"]
        assert got.to_dict() == g.groupby("year").size().to_dict(), rung                     # the year groups partition the scored rows
        assert got.sum() == len(g)
        for cell, gc in g.groupby("cell"):
            part = by_year[(by_year["rung"] == rung) & (by_year["cell"] == cell)].set_index("year")["n"]
            assert part.to_dict() == gc.groupby("year").size().to_dict()
    agg = {(r["cell"], r["rung"]): r for r in doc["tables"]["aggregate"]}
    for rung in scores["rung"].unique():
        assert by_year[(by_year["rung"] == rung) & (by_year["cell"] == "ALL")]["n"].sum() == agg[("ALL", rung)]["n"]
    p2 = scores[scores["rung"] == "P2"]
    y = by_year[(by_year["rung"] == "P2") & (by_year["cell"] == "ALL")].set_index("year")
    for year, g in p2.groupby("year"):
        assert y.loc[year, "abstention_rate"] == pytest.approx(g["abstain"].mean())
        assert y.loc[year, "n_tests"] == g["test_id"].nunique()
        assert y.loc[year, "logscore"] == pytest.approx(g["logscore"].mean())
    assert "by calendar year" in path.with_suffix(".md").read_text().lower()


def test_score_by_year_leaves_the_other_tables_unchanged(imp, make_synth):
    rep = imp("mootcourt.report")
    ledger = _ledger(make_synth)
    scores = _scores(imp, ledger)
    doc = rep.build_document(scores, ledger=ledger, source="synthetic", snapshot_id="s", model_id="m", feature_hash="f",
                             command="c", seed=0, gates=GATES, B=20)
    assert "score_by_year" in doc["tables"]
    hs = imp("mootcourt.harness_stats")
    agg = hs.aggregate_scores(scores, GATES, B=20, seed=0)
    agg.insert(2, "kind", agg["rung"].map(rep.rung_kind))
    assert doc["tables"]["aggregate"] == rep.clean(agg)


# ------------------------------------------------------------------ REV-H-001: JPEG and GIF scanning
def _tiff_exif(ascii_tags: dict[int, bytes], thumbnail: bytes = b"", user_comment: bytes = b"") -> bytes:
    """A little-endian Exif APP1 body: IFD0 with ASCII tags, an optional UserComment in an Exif IFD, and IFD1 pointing at a thumbnail."""
    import struct

    entries = []
    blob = b""
    n0 = len(ascii_tags) + (1 if user_comment else 0)
    ifd0_len = 2 + 12 * n0 + 4
    exif_ifd_len = 2 + 12 + 4 if user_comment else 0
    ifd1_len = 2 + 12 + 4 if thumbnail else 0
    data_at = 8 + ifd0_len + exif_ifd_len + ifd1_len
    for tag, text in sorted(ascii_tags.items()):
        text += b"\x00"
        if len(text) <= 4:
            entries.append(struct.pack("<HHI4s", tag, 2, len(text), text.ljust(4, b"\x00")))
        else:
            entries.append(struct.pack("<HHII", tag, 2, len(text), data_at + len(blob)))
            blob += text
    exif_at = 8 + ifd0_len
    if user_comment:
        entries.append(struct.pack("<HHII", 0x8769, 4, 1, exif_at))
    next_ifd = 8 + ifd0_len + exif_ifd_len if thumbnail else 0
    ifd0 = struct.pack("<H", n0) + b"".join(sorted(entries, key=lambda e: struct.unpack("<H", e[:2])[0])) + struct.pack("<I", next_ifd)
    out = ifd0
    if user_comment:
        uc = b"ASCII\x00\x00\x00" + user_comment
        out += struct.pack("<H", 1) + struct.pack("<HHII", 0x9286, 7, len(uc), data_at + len(blob)) + struct.pack("<I", 0)
        blob += uc
    if thumbnail:
        out += struct.pack("<H", 1) + struct.pack("<HHII", 0x0201, 4, 1, data_at + len(blob)) + struct.pack("<I", 0)
        blob += thumbnail
    return b"Exif\x00\x00II*\x00\x08\x00\x00\x00" + out + blob


def test_an_exif_thumbnail_and_binary_application_payloads_are_not_read_as_text(imp):             # REV-H-001
    from test_writing_rules import _digest, _jpeg, scan_binary

    digests = {_digest("qzx")}
    thumb = b"\x00\x01qzx\x02\x03 junk qzx \x04"                       # compressed picture bytes that happen to spell a blocked short word
    exif = _tiff_exif({0x010F: b"Acme Camera"}, thumbnail=thumb)
    assert scan_binary(_jpeg((0xE1, exif)), ".jpg", digests) == []
    for payload in (b"\x00qzx\x00" * 50, bytes(range(256)) * 40):    # APP2 (an ICC profile or multi-picture data) and APP11 binary
        assert scan_binary(_jpeg((0xE2, b"ICC_PROFILE\x00" + payload), (0xEB, payload)), ".jpg", digests) == []


def test_text_that_lives_in_a_comment_an_exif_text_tag_or_an_xmp_packet_is_still_found(imp):     # REV-H-001
    from test_writing_rules import _digest, _jpeg, scan_binary

    digests = {_digest("qzx")}
    hit = ["forbidden term"]
    assert scan_binary(_jpeg((0xFE, b"made by qzx")), ".jpg", digests) == hit
    assert scan_binary(_jpeg((0xE1, _tiff_exif({0x010E: b"a photo by qzx"}))), ".jpg", digests) == hit
    assert scan_binary(_jpeg((0xE1, _tiff_exif({0x010F: b"Acme"}, user_comment=b"qzx"))), ".jpg", digests) == hit
    assert scan_binary(_jpeg((0xE1, _tiff_exif({0x010F: b"Acme"}, thumbnail=b"\x00\xff"))), ".jpg", digests) == []
    xmp = b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta><dc:creator>qzx</dc:creator></x:xmpmeta>"
    assert scan_binary(_jpeg((0xE1, xmp)), ".jpeg", digests) == hit


def test_a_real_looking_jpeg_with_a_thumbnail_does_not_trip_the_real_digests_by_chance(imp):      # REV-H-001
    """The measured failure: random payloads in a thumbnail gave a tier 1 hit about once in three files."""
    from test_writing_rules import DIGEST_FILE, RESTRICTED_FILE, _jpeg, scan_binary

    def load(p):
        return {ln.split()[0] for ln in p.read_text().splitlines() if ln.strip() and not ln.startswith("#")}

    tier1, tier2 = load(DIGEST_FILE), load(RESTRICTED_FILE)
    rng = np.random.default_rng(7)
    for _ in range(40):
        thumb = rng.integers(0, 256, 60000, dtype=np.uint8).tobytes()
        mpf = b"MPF\x00" + rng.integers(0, 256, 4000, dtype=np.uint8).tobytes()
        data = _jpeg((0xE1, _tiff_exif({0x010F: b"Acme"}, thumbnail=thumb)), (0xE2, mpf))
        assert scan_binary(data, ".jpg", tier1, tier2) == []


# ------------------------------------------------------------------ REV-H-002: env -S, --split-string and -P
def test_the_data_root_refusal_reads_env_split_string_and_path_options(imp, tmp_path, monkeypatch):    # REV-H-002
    from test_simulators import _info

    stdio, base = imp("mootcourt.simulators.stdio"), imp("mootcourt.simulators")
    root = tmp_path / "dataroot"
    root.mkdir()
    (root / "agent.py").write_text("print('null')\n")
    ok = tmp_path / "ok.py"
    ok.write_text("print('null')\n")
    monkeypatch.setenv("MOOTCOURT_DATA_ROOT", str(root))
    inside = f"python3 {root / 'agent.py'}"
    bad = [
        ["env", "-S", f"sh -c '{inside}'"],                                         # env -S splits one string into words
        ["env", "--split-string", f"sh -c '{inside}'"],
        ["env", "--split-string=" + inside],
        ["env", "-S", inside],
        ["env", "-iS", inside],
        ["env", "-S" + inside],                                                     # the value attached to the option
        ["env", "FOO=1", "-S", f"bash -c '{inside}'"],
        ["env", "-P", "/usr/bin", "sh", "-c", inside],                              # -P takes a value, so sh is the program
        ["env", "-P", "/usr/bin", "-S", inside],
        ["/usr/bin/env", "-S", f"env -S '{inside}'"],                                # nested
    ]
    for command in bad:
        with pytest.raises(base.SimulatorError, match="data root"):
            stdio.StdioSimulator(command, _info(imp))
    stdio.StdioSimulator(["env", "-S", f"{sys.executable} {ok}"], _info(imp))
    stdio.StdioSimulator(["env", "-P", "/usr/bin", "sh", "-c", f"python3 {ok}"], _info(imp))
    stdio.StdioSimulator(["env", "--split-string=" + f"python3 {ok}"], _info(imp))


# ------------------------------------------------------------------ REV-H-003: the stated limits of the HTTP adapter
def test_the_http_limits_are_stated_in_the_user_docs_and_the_docstring(imp):                       # REV-H-003
    doc = (ROOT / "docs" / "simulators.md").read_text()
    section = doc.split("## Attach an agent behind HTTP", 1)[1].split("\n## ", 1)[0].replace("\n", " ")
    assert "may still be sent" in section and "caller" in section and "timed out" in section, section
    assert "name resolution" in section and "--allow-remote" in section
    assert "one cap per address" in imp("mootcourt.simulators.http").__doc__.replace("\n", " ")
    assert "may still be sent" in imp("mootcourt.simulators.http").__doc__.replace("\n", " ")


def test_the_http_worker_does_not_send_after_an_abort_that_arrived_during_the_connect(imp):         # REV-H-003
    from test_simulators import _info

    httpmod = imp("mootcourt.simulators.http")
    sent = []

    class Conn:
        sock = None

        def __init__(self, *a, **k):
            pass

        def connect(self):
            box["aborted"] = True                                                     # the caller's cap was reached while connecting

        def request(self, *a, **k):
            sent.append(a)

        def close(self):
            pass

    box: dict = {}
    sim = httpmod.HttpSimulator("http://127.0.0.1:9/x", _info(imp), time_cap_s=2.0)
    orig = httpmod.http.client.HTTPConnection
    httpmod.http.client.HTTPConnection = Conn
    try:
        sim._exchange(b"{}", 2.0, 1e18, box)
    finally:
        httpmod.http.client.HTTPConnection = orig
    assert sent == [] and "exc" not in box


# ------------------------------------------------------------------ found by the replay on ASOS: outcome times of mixed precision
def test_outcome_times_of_mixed_precision_are_read_by_the_reliability_report(imp):
    """``Timestamp.isoformat`` drops a zero fraction and keeps nanoseconds, so one batch holds strings of different shapes."""
    import datetime as dt

    rel = imp("mootcourt.reliability")
    now = dt.datetime(2019, 8, 1, tzinfo=dt.timezone.utc)
    ats = ["2019-07-04T12:00:00+00:00", "2019-07-05T12:00:00.123456+00:00", "2019-07-04T12:00:00.000000001+00:00"] * 4
    outcomes = [{"cell": "a", "at": at, "logscore": -2.0, "p0_logscore": -2.0, "brier": 0.2, "p0_brier": 0.2} for at in ats]
    report = rel.build_reliability(None, outcomes, now)
    assert report["cells"]["a"]["n"] == 12
