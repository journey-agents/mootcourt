"""The tables of the simulated readers (docs/superpowers/plans/2026-11-18-simulated-readers.md, Task 16, and
docs/superpowers/plans/2026-11-19-simulated-readers-api-run.md).

Both runs are side runs, so every table here reads two explicit folders, ``RUN11`` (the calls through the command line tool) and ``RUN12``
(the same requests through the vendor's API), and ``make tables RUN=...`` can never point them at another run. The words of the three
readings are chosen by code from the adjusted interval of the primary model in run 11, as the plan fixed before the first call, and the
report's own verdict key must agree with them.
"""
from pathlib import Path

from summary_tables import Raw, Report, Reports, Table, derived, join, n, v
from summary_tables.experiments import _heading, sci

DATA = Path(__file__).resolve().parents[1] / "data"
RUN11, RUN11_NAME = DATA / "run11-simulated-readers", "paper/data/run11-simulated-readers"
RUN12, RUN12_NAME = DATA / "run12-simulated-readers-api", "paper/data/run12-simulated-readers-api"
COMMITS = {RUN11_NAME: "942b8e85f565f5ac2387b9e32ff88d217bcdcc7f", RUN12_NAME: "87163a63ec24ae5e7699ddb4697aea8eb1a0e52a"}
MODELS = (("claude-opus-5-5", "Opus"), ("claude-sonnet-5-5", "Sonnet"), ("claude-haiku-5-5", "Haiku"))
PRIMARY = "claude-opus-5-5"
AGREEMENT = "simulated-readers-agreement-*.json"
READINGS = (("plain_minus_always_reference", "1. Plain panel minus the earliest-arm rule"),
            ("weights_minus_plain", "2. Panel with reader weights minus the plain panel"),
            ("text_with_panel_minus_text", "3. Text classifier with the panel minus the text classifier alone"))
# the words fixed in the design for an adjusted interval above zero, containing zero and below zero
WORDS = {"plain_minus_always_reference": ("more often", "not shown to match more often", "less often"),
         "weights_minus_plain": ("raised", "not shown to raise", "lowered"),
         "text_with_panel_minus_text": ("raised", "not shown to raise", "lowered")}
KEY_OF_WORD = {"above": 0, "contains_zero": 1, "below": 2}
METHODS = (("direction_map", "1. direction map"), ("reader_weights", "2. reader weights"), ("audience_matching", "3. audience matching"),
           ("error_correction", "4. error correction"), ("text_with_panel", "5. text classifier with the panel"),
           ("examples_in_prompt", "6. earlier results in the prompt"), ("audience_brief", "7. audience brief"))
RUN_HEADINGS = ((RUN11_NAME, "Run 11, through the command line tool"), (RUN12_NAME, "Run 12, through the vendor's API"))


class FolderReport(Report):
    """A report of a named run folder; its keys carry the folder's path, since ``$RUN6`` stands for the run of the build."""

    folder: str = ""

    def ref(self, key):
        return f"{self.folder}/{self.name} {key}"


def _folder(root, name):
    reports = Reports(root)

    def get(pattern):
        rep = reports(pattern)
        out = FolderReport(rep.name, rep.doc)
        out.folder = name
        return out

    return get


def run11():
    return _folder(RUN11, RUN11_NAME)


def run12():
    return _folder(RUN12, RUN12_NAME)


def _runs():
    return {RUN11_NAME: run11(), RUN12_NAME: run12()}


def model_report(get, model):
    return get(f"simulated-readers-{model}-*.json")


def transport_report(model):
    return run12()(f"simulated-readers-transport-{model}-*.json")


def reading_word(name, adjusted_lo, adjusted_hi):
    """The fixed words of one reading: the first needs the adjusted interval above zero, the last needs it below zero."""
    above, contains, below = WORDS[name]
    if adjusted_lo > 0:
        return above
    if adjusted_hi < 0:
        return below
    return contains


def word_cell(rep, name):
    """The words of a reading with the keys that chose them; the report's verdict key must say the same."""
    at = f"readings.{name}"
    word = reading_word(name, rep.get(f"{at}.adjusted_lo"), rep.get(f"{at}.adjusted_hi"))
    if WORDS[name][KEY_OF_WORD[rep.get(f"{at}.verdict")]] != word:
        raise ValueError(f"{rep.name} {at}: the verdict key does not agree with the adjusted interval")
    return derived(word, rep.ref(f"{at}.adjusted_lo"), rep.ref(f"{at}.adjusted_hi"), rep.ref(f"{at}.verdict"))


def _interval(rep, row, lo="lo", hi="hi"):
    """An estimate with its interval at four places, or five where an end would print as zero at four and so hide its sign."""
    try:
        return sci(rep, row, "estimate", 4, lo, hi)
    except ValueError:
        return sci(rep, row, "estimate", 5, lo, hi)


def _check():
    """The two folders are the two runs, on the same rows, with the bootstrap and the family the captions name."""
    runs = _runs()
    first = model_report(runs[RUN11_NAME], PRIMARY)
    for name, get in runs.items():
        for model, _ in MODELS:
            rep = model_report(get, model)
            if rep.get("commit") != COMMITS[name] or rep.get("model") != model or rep.get("snapshot") != first.get("snapshot"):
                raise ValueError(f"{name}: {rep.name} is not a report of this run, model and snapshot")
            if (name == RUN12_NAME) != (rep.doc.get("run_label") == "run12-api"):
                raise ValueError(f"{name}: {rep.name} carries the wrong run label")
            if rep.get("counts.contrasts") != first.get("counts.contrasts") or rep.get("counts.blocks") != 63:
                raise ValueError(f"{name}: the captions say the same contrasts in 63 blocks")
            for key in ("always_reference", "text_lr", "ceiling"):
                if abs(rep.get(f"baselines.{key}.accuracy") - first.get(f"baselines.{key}.accuracy")) > 1e-12:
                    raise ValueError(f"{name}: the references of the cell differ between reports")
            for reading, _ in READINGS:
                if rep.get(f"readings.{reading}.family_size") != 3 or rep.get(f"readings.{reading}.resamples") != 500:
                    raise ValueError(f"{name}: the captions say a family of three and 500 resamples")
            if rep.get("primary") != (model == PRIMARY):
                raise ValueError(f"{name}: the primary model is {PRIMARY}")
    for model, _ in MODELS:
        rep = transport_report(model)
        if rep.get("commits.tool") != COMMITS[RUN11_NAME] or rep.get("commits.api") != COMMITS[RUN12_NAME]:
            raise ValueError(f"{rep.name} does not compare the two runs")
    return runs


def readings(r):
    """The three readings for the three models in both runs, under the references of the cell; words for the primary model of run 11."""
    runs = _check()
    both = [runs[RUN11_NAME], runs[RUN12_NAME]]

    def pair(model, fn):
        return [fn(model_report(get, model)) for get in both]

    rows = [_heading("Share of contrasts whose direction is matched", 4)]
    for label, key in (("the earliest-arm rule", "always_reference"), ("the text classifier", "text_lr"), ("the direction ceiling", "ceiling")):
        rows.append([rf"\quad {label}", *pair(PRIMARY, lambda rep, key=key: v(rep, f"baselines.{key}.accuracy", 4)), ""])
    for model, short in MODELS:
        rows.append([rf"\quad plain panel, {short}", *pair(model, lambda rep: v(rep, "plain.accuracy", 4)), ""])
    for name, label in READINGS:
        rows += [Raw(r"\midrule"), _heading(label, 4)]
        for model, short in MODELS:
            word = word_cell(model_report(both[0], model), name) if model == PRIMARY else ""
            rows.append([rf"\quad {short}", *pair(model, lambda rep, name=name: _interval(rep, f"readings.{name}", "adjusted_lo", "adjusted_hi")),
                         word])
    return Table("fmt-readers-readings", r"p{4.9cm}rrp{2.5cm}", ["reading and model & run 11 & run 12 & fixed words,", " & & & Opus in run 11"], rows,
                 source=f"the report keys named above each row (readers); it reads {RUN11_NAME} and {RUN12_NAME}")


def _methods(name, get, table_name):
    rows = []
    for at, (model, short) in enumerate(MODELS):
        rep = model_report(get, model)
        rows += ([Raw(r"\midrule")] if at else []) + [_heading(short, 4)]
        rows.append([r"\quad plain panel", v(rep, "plain.accuracy", 4), "", _interval(rep, "readings.plain_minus_always_reference")])
        for key, label in METHODS:
            rows.append([rf"\quad {label}", v(rep, f"methods.{key}.accuracy", 4), _interval(rep, f"methods.{key}.minus_plain"),
                         _interval(rep, f"methods.{key}.minus_always_reference")])
    return Table(table_name, r"p{4.6cm}rrr", ["model and method & share matched & minus the plain panel & minus the earliest-arm rule"], rows,
                 source=f"the report keys named above each row (readers); it reads {name}")


def methods(r):
    """The plain panel and the seven methods for each model in run 11."""
    return _methods(RUN11_NAME, _check()[RUN11_NAME], "fmt-readers-methods")


def methods_api(r):
    """The same table for run 12."""
    return _methods(RUN12_NAME, _check()[RUN12_NAME], "fmt-readers-methods-api")


def transport(r):
    """The plain panels of the two runs against each other, one row per model."""
    _check()
    rows = []
    for model, short in MODELS:
        rep = transport_report(model)
        rows.append([short, v(rep, "plain.accuracy_tool", 4), v(rep, "plain.accuracy_api", 4), _interval(rep, "plain.accuracy_api_minus_tool"),
                     v(rep, "plain.agree_share", 3), n(rep, "plain.n")])
    return Table("fmt-readers-transport", r"lrrrrr",
                 ["model & run 11 & run 12 & run 12 minus run 11 & same direction, & contrasts", " & & & & share & compared"], rows,
                 source=f"the report keys named above each row (readers); it reads {RUN12_NAME}")


def _per_model(get, fn):
    return [fn(model_report(get, model)) for model, _ in MODELS]


def probes(r):
    """The three probes for earlier exposure to the archive, by model, for each run."""
    runs = _check()
    rows = []
    for at, (name, heading) in enumerate(RUN_HEADINGS):
        get = runs[name]

        def each(fn, get=get):
            return _per_model(get, fn)

        rows += ([Raw(r"\midrule")] if at else []) + [
            _heading(heading, 4),
            ["tests probed", *each(lambda rep: n(rep, "probes.units"))],
            ["completion: pairs of headlines scored", *each(lambda rep: n(rep, "probes.completion.n_pairs"))],
            ["completion: token F1, the winning headline", *each(lambda rep: v(rep, "probes.completion.f1_winner", 3))],
            ["completion: token F1, another headline of the test", *each(lambda rep: v(rep, "probes.completion.f1_other", 3))],
            ["completion: winner minus other (standard error)",
             *each(lambda rep: join("{} ({})", v(rep, "probes.completion.f1_difference", 3), v(rep, "probes.completion.f1_difference_se", 3)))],
            ["familiarity: contrasts scored", *each(lambda rep: n(rep, "probes.familiarity.n"))],
            ["familiarity: the headline rated more familiar won, share", *each(lambda rep: v(rep, "probes.familiarity.direction_accuracy", 3))],
            ["familiarity: same direction as the plain panel, share", *each(lambda rep: v(rep, "probes.familiarity.agreement_with_panel", 3))],
            ["named publisher: which headline of a pair won, share right", *each(lambda rep: v(rep, "probes.pairs.direction_accuracy", 3))],
        ]
    return Table("fmt-readers-probes", r"p{7.6cm}rrr", ["probe and measure & " + " & ".join(short for _, short in MODELS)], rows,
                 source=f"the report keys named above each row (readers); it reads {RUN11_NAME} and {RUN12_NAME}")


def _pair_key(a, b):
    return f'pairs["{a}__{b}"].agree_share'


def _more(name, get, table_name):
    def each(fn):
        return _per_model(get, fn)

    agreement = get(AGREEMENT)
    opus, sonnet, haiku = (model for model, _ in MODELS)
    rows = [
        ["plain panel minus one half", *each(lambda rep: _interval(rep, "plain.accuracy_minus_half"))],
        ["decisive contrasts", *each(lambda rep: n(rep, "plain.decisive.n"))],
        ["plain panel, share matched on decisive contrasts", *each(lambda rep: v(rep, "plain.decisive.accuracy", 4))],
        ["the two halves of the panel give the same direction, share", *each(lambda rep: v(rep, "plain.split_half.agree_share", 3))],
        ["contrasts on which the plain panel is tied", *each(lambda rep: n(rep, "plain.ties"))],
        ["contrasts left with no reader", *each(lambda rep: n(rep, "plain.no_reader"))],
        ["direction map, Brier skill", *each(lambda rep: v(rep, "methods.direction_map.brier_skill", 4))],
        ["text classifier minus the earliest-arm rule", *each(lambda rep: _interval(rep, "baselines.text_lr_minus_always_reference"))],
        Raw(r"\midrule"),
        _heading("Captured lift at a quarter budget", 4),
        ["units ranked", *each(lambda rep: n(rep, "ranking.n_units"))],
        ["plain panel", *each(lambda rep: v(rep, "ranking.panel.estimate", 3))],
        ["arm-count rule", *each(lambda rep: v(rep, "ranking.arm_count.estimate", 3))],
        ["random order matched on arm count", *each(lambda rep: v(rep, "ranking.matched_random.estimate", 3))],
        ["plain panel minus the arm-count rule", *each(lambda rep: _interval(rep, "ranking.panel_minus_arm_count"))],
        ["plain panel minus the matched random order", *each(lambda rep: _interval(rep, "ranking.panel_minus_matched_random"))],
        Raw(r"\midrule"),
        _heading("Plain panels of two models give the same direction, share", 4),
        ["with Opus", "", v(agreement, _pair_key(opus, sonnet), 3), v(agreement, _pair_key(opus, haiku), 3)],
        ["with Sonnet", "", "", v(agreement, _pair_key(sonnet, haiku), 3)],
        Raw(r"\midrule"),
        _heading("Calls", 4),
        ["planned", *each(lambda rep: n(rep, "counts.calls_planned"))],
        ["usable replies", *each(lambda rep: n(rep, "counts.calls_ok"))],
        ["invalid after three attempts", *each(lambda rep: n(rep, "counts.calls_invalid"))],
        ["declined", *each(lambda rep: n(rep, "counts.calls_refusal"))],
    ]
    return Table(table_name, r"p{6.6cm}rrr", ["measure & " + " & ".join(short for _, short in MODELS)], rows,
                 source=f"the report keys named above each row (readers); it reads {name}")


def more(r):
    """The remaining described measures of run 11."""
    return _more(RUN11_NAME, _check()[RUN11_NAME], "fmt-readers-more")


def more_api(r):
    """The same measures for run 12."""
    return _more(RUN12_NAME, _check()[RUN12_NAME], "fmt-readers-more-api")


TABLES = [readings, methods, transport, probes, methods_api, more, more_api]
