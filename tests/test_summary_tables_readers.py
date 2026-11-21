"""The tables of the simulated readers: each reads run 11 and run 12 from their own folders, each number names its key,
and the words of the three readings are chosen by code from the adjusted interval of the primary model in run 11.
One row of the two tables of remaining measures reads the main run, run 9, also from its own folder."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
RUN = PAPER / "data" / "run9-visible-exposure"
sys.path.insert(0, str(PAPER))
import summary_tables as st  # noqa: E402
from summary_tables import readers  # noqa: E402

R11, R12 = "paper/data/run11-simulated-readers/", "paper/data/run12-simulated-readers-api/"
R9 = "paper/data/run9-visible-exposure/"
RULE_ON_DECISIVE = "the earliest-arm rule, share matched on decisive contrasts"          # the one row that reads the main run
RULE_KEY = "tables.aggregate[cell=headline_only,rung=always_reference].direction_accuracy_decisive"
NUMBER = re.compile(r"-?\d[\d,]*\.?\d*")


def _rows(table):
    return [row for row in table.rows if not isinstance(row, st.Raw)]


def _row(table, label, nth=0):
    hits = [row for row in _rows(table) if str(row[0]).endswith(label)]
    assert len(hits) > nth, (label, len(hits))
    return hits[nth]


def _leaves(cell):
    return [k.split(" ", 1)[1] for k in cell.keys]


def _value(key):
    """The report leaf a key names, read from the folder the key names."""
    path, leaf = key.split(" ", 1)
    folder, name = path.rsplit("/", 1)
    return st.Reports(ROOT / folder)(name).get(leaf)


def test_the_folders_are_fixed_whatever_run_the_build_is_given():
    assert readers.RUN11 == PAPER / "data" / "run11-simulated-readers"
    assert readers.RUN12 == PAPER / "data" / "run12-simulated-readers-api"
    assert readers.RUN9 == PAPER / "data" / "run9-visible-exposure"
    assert [m for m, _ in readers.MODELS] == ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]
    assert readers.PRIMARY == "claude-opus-5-5"


def test_the_words_of_each_reading_follow_the_adjusted_interval():
    assert readers.reading_word("plain_minus_always_reference", 0.001, 0.02) == "more often"
    assert readers.reading_word("plain_minus_always_reference", -0.017, 0.026) == "not shown to match more often"
    assert readers.reading_word("plain_minus_always_reference", -0.07, -0.02) == "less often"
    for name in ("weights_minus_plain", "text_with_panel_minus_text"):
        assert readers.reading_word(name, 0.0004, 0.0276) == "raised"
        assert readers.reading_word(name, -0.0035, 0.0254) == "not shown to raise"
        assert readers.reading_word(name, 0.0, 0.0254) == "not shown to raise"          # an end at zero is not above zero
        assert readers.reading_word(name, -0.03, -0.001) == "lowered"
    assert readers.KEY_OF_WORD == {"above": 0, "contains_zero": 1, "below": 2}


def test_every_table_of_the_group_reads_only_its_fixed_folders_and_every_first_number_is_its_first_key():
    reports = st.Reports(RUN)
    names = []
    for fn in readers.TABLES:
        table = fn(reports)
        names.append(table.name)
        text = table.render()
        assert "$RUN6/" not in text, table.name
        assert "% src: " + R11 in text or "% src: " + R12 in text, table.name
        for row in _rows(table):
            for cell in row[1:]:
                keys = getattr(cell, "keys", ())
                allowed = (R11, R12, R9) if str(row[0]) == RULE_ON_DECISIVE else (R11, R12)
                assert all(k.startswith(allowed) for k in keys), (table.name, row[0])
                if keys and NUMBER.match(str(cell)):
                    printed = NUMBER.match(str(cell)).group().replace(",", "")
                    places = len(printed.split(".")[1]) if "." in printed else 0
                    assert float(printed) == pytest.approx(round(_value(keys[0]), places), abs=1e-9), (table.name, row[0], str(cell))
    assert names == ["fmt-readers-readings", "fmt-readers-methods", "fmt-readers-transport", "fmt-readers-probes",
                     "fmt-readers-methods-api", "fmt-readers-more", "fmt-readers-more-api"]


def test_the_readings_table_sets_the_two_runs_side_by_side_and_words_only_the_primary_model_of_run_11():
    table = readers.readings(st.Reports(RUN))
    rows = _rows(table)
    assert all(len(row) == 4 for row in rows)
    worded = [row for row in rows if str(row[3])]
    assert len(worded) == 3 and all(str(row[0]).endswith("Opus") for row in worded)
    for name, words in readers.WORDS.items():
        at = f"readings.{name}"
        row = next(r for r in worded if _leaves(r[1])[0] == f"{at}.estimate")
        assert _leaves(row[1]) == [f"{at}.estimate", f"{at}.adjusted_lo", f"{at}.adjusted_hi"]
        assert _leaves(row[2]) == _leaves(row[1])
        assert row[1].keys[0].startswith(R11 + "simulated-readers-claude-opus-5-5-") and row[2].keys[0].startswith(R12)
        assert "run12-api" in row[2].keys[0] and "run12-api" not in row[1].keys[0]
        assert str(row[3]) in words and _leaves(row[3]) == [f"{at}.adjusted_lo", f"{at}.adjusted_hi", f"{at}.verdict"]
        assert all(k.startswith(R11) for k in row[3].keys)          # the words come from run 11
        assert re.fullmatch(r"-?\d\.\d{4,5} \(-?\d\.\d{4,5}, -?\d\.\d{4,5}\)", str(row[1])), str(row[1])
        lo = _value(row[1].keys[1])
        assert ("(-" in str(row[1])) == (lo < 0)          # an end below zero keeps its sign
    # nine reading rows: three readings for three models
    assert sum(1 for row in rows if _leaves(row[1])[0].startswith("readings.")) == 9
    # the references of the cell stand above them, the same in both runs
    for label, key in (("the earliest-arm rule", "baselines.always_reference.accuracy"), ("the text classifier", "baselines.text_lr.accuracy"),
                       ("the direction ceiling", "baselines.ceiling.accuracy")):
        row = _row(table, label)
        assert _leaves(row[1]) == [key] and str(row[1]) == str(row[2])


def test_the_methods_tables_hold_the_plain_panel_and_seven_methods_for_each_model_in_each_run():
    for fn, folder in ((readers.methods, R11), (readers.methods_api, R12)):
        table = fn(st.Reports(RUN))
        rows = _rows(table)
        assert len(rows) == 24 and all(len(row) == 4 for row in rows)
        assert all(k.startswith(folder) for row in rows for cell in row[1:] for k in getattr(cell, "keys", ()))
        for nth, (model, _) in enumerate(readers.MODELS):
            plain = _row(table, "plain panel", nth)
            assert _leaves(plain[1]) == ["plain.accuracy"] and str(plain[2]) == "" and model in plain[1].keys[0]
            at = "readings.plain_minus_always_reference"
            assert _leaves(plain[3]) == [f"{at}.estimate", f"{at}.lo", f"{at}.hi"]          # the interval of one comparison, not the adjusted one
            brief = _row(table, "7. audience brief", nth)
            assert _leaves(brief[1]) == ["methods.audience_brief.accuracy"]
            assert _leaves(brief[2])[0] == "methods.audience_brief.minus_plain.estimate"
            assert _leaves(brief[3])[0] == "methods.audience_brief.minus_always_reference.estimate"
    assert [label for _, label in readers.METHODS] == [
        "1. direction map", "2. reader weights", "3. audience matching", "4. error correction", "5. text classifier with the panel",
        "6. earlier results in the prompt", "7. audience brief"]


def test_the_remaining_measures_set_the_earliest_arm_rule_beside_the_plain_panel_on_decisive_contrasts():
    seen = []
    for fn, folder in ((readers.more, R11), (readers.more_api, R12)):
        table = fn(st.Reports(RUN))
        labels = [str(row[0]) for row in _rows(table)]
        at = labels.index(RULE_ON_DECISIVE)
        assert labels.count(RULE_ON_DECISIVE) == 1 and labels[at - 1] == "plain panel, share matched on decisive contrasts"
        row, panel = _rows(table)[at], _rows(table)[at - 1]
        assert len(row) == 4 and len({str(cell) for cell in row[1:]}) == 1          # one rule, the same under each model
        for cell in row[1:]:
            assert len(cell.keys) == 1 and cell.keys[0].startswith(R9 + "backtest-upworthy-")
            assert _leaves(cell) == [RULE_KEY]
            assert float(str(cell)) == pytest.approx(round(_value(cell.keys[0]), 4), abs=1e-9)
        # the rule and the panel are scored on the same decisive contrasts
        counts = _row(table, "decisive contrasts")
        assert _leaves(counts[1]) == ["plain.decisive.n"]
        assert _value(row[1].keys[0].replace(".direction_accuracy_decisive", ".n_decisive")) == _value(counts[1].keys[0])
        assert all(_leaves(cell) == ["plain.decisive.accuracy"] and cell.keys[0].startswith(folder) for cell in panel[1:])
        # no other row of the table reads the main run
        others = [k for other in _rows(table) if str(other[0]) != RULE_ON_DECISIVE for cell in other[1:] for k in getattr(cell, "keys", ())]
        assert others and all(k.startswith(folder) for k in others)
        seen.append(str(row[1]))
    assert seen[0] == seen[1]          # the same reference in both runs


def test_a_main_run_on_other_contrasts_stops_the_build():
    rep = st.Report("x.json", {"counts": {"contrasts": 1}, "plain": {"decisive": {"n": 1}}, "baselines": {"always_reference": {"accuracy": 0.5}}})
    with pytest.raises(ValueError, match="not on the contrasts"):
        readers.reference_on_decisive(rep)


def test_the_transport_table_reads_the_comparison_reports_of_run_12():
    table = readers.transport(st.Reports(RUN))
    rows = _rows(table)
    assert len(rows) == 3
    for row, (model, _) in zip(rows, readers.MODELS):
        assert all(f"simulated-readers-transport-{model}-" in k and k.startswith(R12) for cell in row[1:] for k in cell.keys)
        at = "plain.accuracy_api_minus_tool"
        assert [_leaves(c) for c in row[1:]] == [["plain.accuracy_tool"], ["plain.accuracy_api"], [f"{at}.estimate", f"{at}.lo", f"{at}.hi"],
                                                 ["plain.agree_share"], ["plain.n"]]


def test_the_probe_table_names_the_third_probe_as_a_question_and_not_as_a_reader():
    table = readers.probes(st.Reports(RUN))
    text = table.render()
    assert "simulated reader" not in text
    for nth, folder in enumerate((R11, R12)):
        row = _row(table, "which headline of a pair won, share right", nth)
        assert [_leaves(c) for c in row[1:]] == [["probes.pairs.direction_accuracy"]] * 3
        assert all(k.startswith(folder) for c in row[1:] for k in c.keys)
        difference = _row(table, "winner minus other (standard error)", nth)
        assert _leaves(difference[1]) == ["probes.completion.f1_difference", "probes.completion.f1_difference_se"]


def test_a_report_whose_verdict_key_disagrees_with_its_interval_stops_the_build():
    rep = st.Report("x.json", {"readings": {"weights_minus_plain": {"adjusted_lo": 0.001, "adjusted_hi": 0.02, "verdict": "contains_zero"}}})
    with pytest.raises(ValueError, match="verdict"):
        readers.word_cell(rep, "weights_minus_plain")
