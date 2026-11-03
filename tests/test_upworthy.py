"""T-020 contracts: Upworthy loader and contrast ledger (offline, inline fixture)."""
import csv
import json

import numpy as np
import pandas as pd
import pytest

FORMER_STAFF = ("square", "significance", "first_place", "winner", "updated_at")
SENTINEL = "STAFF_SENTINEL_VALUE"
COLUMNS = ["created_at", "test_week", "clickability_test_id", "impressions", "clicks", "headline", "eyecatcher_id",
           "problem", "excerpt", "lede", "slug", "share_text", *FORMER_STAFF]


def _row(test, created, imp, clicks, headline, eye, problem=False):
    return {"created_at": created, "test_week": "201426", "clickability_test_id": test, "impressions": imp,
            "clicks": clicks, "headline": headline, "eyecatcher_id": eye, "problem": problem,
            "excerpt": f"ex {headline}", "lede": f"lede {headline}", "slug": f"slug-{test}",
            "share_text": f"share {headline}", "square": SENTINEL, "significance": SENTINEL,
            "first_place": SENTINEL, "winner": SENTINEL, "updated_at": "2099-01-01 00:00:00"}


T = "2014-09-28 10:00:00"
ROWS = [
    # T_ADM: reference + headline_only + image_only + both  -> 3 admitted
    _row("T_ADM", T, 5000, 100, "H0", "e1"), _row("T_ADM", "2014-09-28 11:00:00", 5000, 150, "H1", "e1"),
    _row("T_ADM", "2014-09-28 11:00:00", 5000, 120, "H0", "e2"), _row("T_ADM", "2014-09-28 11:00:00", 5000, 90, "H2", "e3"),
    # T_LOW: variant below 1000 impressions
    _row("T_LOW", T, 5000, 100, "L0", "e1"), _row("T_LOW", "2014-09-28 11:00:00", 500, 10, "L1", "e1"),
    # T_ZERO: zero-click reference arm (fewer than 10 clicks: low_clicks)
    _row("T_ZERO", T, 5000, 0, "Z0", "e1"), _row("T_ZERO", "2014-09-28 11:00:00", 5000, 50, "Z1", "e1"),
    # T_IMB: randomization imbalance flag on the variant
    _row("T_IMB", T, 5000, 100, "I0", "e1"), _row("T_IMB", "2014-09-28 11:00:00", 5000, 100, "I1", "e1", problem=True),
    # T_MISS: empty headline
    _row("T_MISS", T, 5000, 100, "M0", "e1"), _row("T_MISS", "2014-09-28 11:00:00", 5000, 100, "", "e1"),
    # T_SINGLE: one package only
    _row("T_SINGLE", T, 5000, 100, "S0", "e1"),
    # T_DUP: identical headline and image
    _row("T_DUP", T, 5000, 100, "D0", "e1"), _row("T_DUP", "2014-09-28 11:00:00", 5000, 110, "D0", "e1"),
    # T_TIE: two packages share the earliest created_at; the first row is the reference
    _row("T_TIE", T, 10000, 200, "X0", "e1"), _row("T_TIE", T, 10000, 300, "X1", "e1"),
    _row("T_TIE", "2014-09-28 12:00:00", 10000, 400, "X2", "e1"),
]
EXPECTED_COUNTS = {"admitted": 5, "low_exposure": 1, "low_clicks": 1, "imbalance_flag": 1, "missing_text": 1, "single_arm": 1, "duplicate_arm": 1}


@pytest.fixture
def mini_csv(tmp_path):
    path = tmp_path / "upworthy_mini.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(ROWS)
    return path


@pytest.fixture
def loaded(imp, mini_csv):
    return imp("mootcourt.sources.upworthy").load_upworthy(mini_csv)


def test_loader_output_is_a_valid_ledger(imp, loaded):
    imp("mootcourt.ledger").validate_ledger(loaded)
    assert set(loaded["source"]) == {"upworthy"}


def test_every_exclusion_status_is_produced_and_rows_are_kept(loaded):
    counts = loaded["status"].value_counts().to_dict()
    assert counts == EXPECTED_COUNTS
    assert len(loaded) == sum(EXPECTED_COUNTS.values())


def test_each_status_comes_from_its_designed_fixture_test(loaded):
    by_test = loaded.groupby("test_id")["status"].agg(lambda s: set(s)).to_dict()
    assert by_test["T_LOW"] == {"low_exposure"} and by_test["T_ZERO"] == {"low_clicks"}
    assert by_test["T_IMB"] == {"imbalance_flag"} and by_test["T_MISS"] == {"missing_text"}
    assert by_test["T_SINGLE"] == {"single_arm"} and by_test["T_DUP"] == {"duplicate_arm"}
    assert by_test["T_ADM"] == {"admitted"} and by_test["T_TIE"] == {"admitted"}


def test_former_staff_columns_never_reach_the_ledger(loaded):
    blob = loaded.to_json()
    assert SENTINEL not in blob and "2099-01-01" not in blob
    for col in FORMER_STAFF:
        assert col not in loaded.columns and col not in " ".join(loaded["features_json"])


def test_loader_never_reads_former_staff_columns(imp, mini_csv):
    up = imp("mootcourt.sources.upworthy")
    assert set(getattr(up, "COLUMNS_USED")) == {"created_at", "test_week", "clickability_test_id", "impressions", "clicks",
                                                  "headline", "eyecatcher_id", "problem", "excerpt", "lede", "slug",
                                                  "share_text"}
    # the staff columns are corrupted to non-parsable junk; the loader must not care
    df = pd.read_csv(mini_csv)
    for col in FORMER_STAFF:
        df[col] = "\x00junk"
    junk = mini_csv.with_name("junk.csv")
    df.to_csv(junk, index=False)
    assert len(up.load_upworthy(junk)) == sum(EXPECTED_COUNTS.values())


def test_reference_is_earliest_created_and_ties_use_first_package(loaded):
    adm = loaded[loaded["test_id"] == "T_ADM"]
    assert len(adm) == 3 and (adm["row_id"].str.startswith("upworthy:T_ADM:")).all()
    tie = loaded[loaded["test_id"] == "T_TIE"].sort_values("y")
    np.testing.assert_allclose(tie["y"].to_numpy(), [1.0, 2.0], rtol=1e-9)   # ref ctr 0.02; others 0.03, 0.04: absolute points


def test_effect_and_standard_error_match_hand_calculation(imp, tmp_path):
    rows = [_row("H", T, 10000, 200, "a", "e1"), _row("H", "2014-09-28 11:00:00", 10000, 300, "b", "e1")]
    path = tmp_path / "h.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    out = imp("mootcourt.sources.upworthy").load_upworthy(path)
    assert len(out) == 1
    assert out["y"].iloc[0] == pytest.approx(1.0, rel=1e-12)             # 100 * (0.03 - 0.02) points
    assert out["s"].iloc[0] == pytest.approx(0.22068076490713906, rel=1e-9)   # binomial: 100 sqrt(.03*.97/1e4 + .02*.98/1e4)
    assert out["n_ref"].iloc[0] == 10000 and out["n_var"].iloc[0] == 10000


def test_standard_error_matches_empirical_sd_of_simulated_lifts(imp):
    up = imp("mootcourt.sources.upworthy")
    rng = np.random.default_rng(0)
    n, pr, pv = 20000, 0.02, 0.025
    cr, cv = rng.binomial(n, pr, 4000), rng.binomial(n, pv, 4000)
    ys, ss = [], []
    for a, b in zip(cr, cv):
        if a == 0:
            continue
        y, s = up.lift_and_se(a, n, b, n)
        ys.append(y)
        ss.append(s)
    assert np.mean(ss) == pytest.approx(np.std(ys), rel=0.05)


def test_cell_is_kind_of_change(loaded):
    adm = loaded[loaded["test_id"] == "T_ADM"].set_index("variant_id")
    cells = sorted(adm["cell"])
    assert cells == ["both", "headline_only", "image_only"]


def test_time_fields_follow_the_seven_day_horizon(loaded):
    adm = loaded[loaded["status"] == "admitted"]
    created = pd.Timestamp("2014-09-28 11:00:00", tz="UTC")      # the later of the two arms (reference 10:00, variants 11:00), REV-001
    ref_rows = adm[adm["test_id"] == "T_ADM"]
    assert ((ref_rows["final_read_at"] - created) == pd.Timedelta(days=7)).all()
    assert (ref_rows["usable_after"] == ref_rows["final_read_at"]).all()
    assert (ref_rows["period"] == "2014Q4").all(), "period is the quarter of the final read, not of creation"
    assert adm[["usable_after", "final_read_at", "period"]].notna().all().all()


def test_rows_of_one_test_share_test_id(loaded):
    assert loaded[loaded["test_id"] == "T_ADM"]["test_id"].nunique() == 1
    assert loaded.groupby("test_id").size()["T_ADM"] == 3


def test_features_json_contents(loaded):
    f = json.loads(loaded[loaded["test_id"] == "T_ADM"].iloc[0]["features_json"])
    assert {"headline", "excerpt", "lede", "slug", "share_text", "image_changed", "headline_changed"} <= set(f)


def test_loader_is_offline_and_takes_the_path_as_argument(imp, tmp_path):
    with pytest.raises(FileNotFoundError):
        imp("mootcourt.sources.upworthy").load_upworthy(tmp_path / "missing.csv")
