# Verification against the definition of done

Written by the tester on 3 November 2026 for task T-025. Every number below was measured in this session, on one laptop (Apple M1, 8 cores), with sockets blocked for the test suite and no download of any kind.

## Coverage map

One line per topic. Each line names the test functions that assert it; the suite checks that every name exists.

| Topic | Tests |
|---|---|
| admission statuses | test_columns_and_statuses_exact, test_every_exclusion_status_is_produced_and_rows_are_kept, test_each_status_comes_from_its_designed_fixture_test, test_excluded_rows_survive_write_and_read, test_nan_effect_allowed_only_on_excluded_rows |
| origin visibility | test_visible_rows_boundary_is_inclusive_to_the_microsecond, test_visible_rows_only_admitted_and_cell_filter, test_visible_rows_before_everything_is_empty, test_row_is_attached_at_the_first_join_at_or_after_its_horizon |
| leakage guard | test_leaky_factory_is_caught_by_the_audit, test_assert_no_leakage_both_directions, test_rolling_origin_raises_when_a_scored_row_was_already_usable, test_leakage_mutation_is_caught, test_scoring_a_row_at_an_origin_after_it_became_usable_is_flagged, test_clean_backtest_passes_with_a_written_log |
| P0 and P3 on known truth | test_p0_matches_cell_mean_and_variance, test_score_team_hand_computed, test_ladder_orders_on_known_truth |
| P1 recovery of mu and tau | test_recovers_mu_and_tau_per_cell_at_500_and_2000, test_recovery_on_2000_rows_within_spec_tolerance |
| P2 with lambda 0 equals P1 | test_lambda_zero_equals_p1_grid, test_moments_lambda_zero_returns_the_prior |
| P2 on known truth | test_text_signal_makes_p2_beat_p1_out_of_origin, test_no_text_signal_keeps_lambda_small_and_p2_not_worse |
| abstention triggers | test_each_trigger_fires_alone_and_control_fires_none, test_all_four_fire_at_once_and_all_reasons_listed, test_check_support_boundary, test_check_novelty_against_stored_threshold, test_check_reliability_each_way_to_fire, test_instability_fires_on_split_precedents_and_not_on_a_stable_set |
| calibration null | test_calibrated_predictor_lands_inside_the_central_90_percent_at_least_85_percent, test_miscalibrated_predictor_lands_above_the_99th_percentile, test_ece_null_has_requested_size_and_is_nonnegative |
| gate arithmetic | test_gate_status_arithmetic_on_both_sides_of_n, test_gate_status_never_hardcodes_200_or_400, test_no_gate_size_is_hardcoded_in_source |
| registry promotion | test_promotion_rule, test_high_skill_challenger_needs_the_n_200_gate, test_exact_margin_is_accepted_despite_float_noise, test_promotion_is_logged_and_clears_the_challenger |
| join miss typing | test_abstained_but_clear, test_abstained_and_not_clear_is_a_hit, test_confident_but_wrong_high_p_no_event, test_confident_but_wrong_low_p_with_event, test_direction_miss, test_magnitude_miss, test_hit, test_precedence_confident_beats_direction, test_precedence_abstained_beats_everything |
| card renderers | test_markdown_and_json_agree_and_footer_is_the_boundary, test_golden_markdown, test_json_schema_pins_keys, test_every_status_is_free_of_dashes_and_role_noun |
| service responses | test_post_card_returns_card_json_with_ids_and_boundary, test_same_request_via_cli_and_service_gives_identical_json, test_invalid_payload_is_422_and_unknown_source_is_404, test_routes_are_read_only_apart_from_post_card, test_preloaded_bundle_keeps_latency_under_one_second |
| MCP tool responses | test_tools_list_is_exactly_the_three_read_only_tools, test_each_tool_returns_valid_content_and_nothing_is_written, test_unknown_source_is_a_tool_error_not_a_crash |
| writing rules | test_writing_rules, test_injecting_a_pattern_into_a_copy_of_a_scanned_file_fails_with_file_and_line, test_tier_one_is_forbidden_everywhere_without_exception |
| end to end on a synthetic stream | test_fit_issue_freeze_join_type_drift_abstain_clear_issue |

The end to end test already existed in the integration test module, so no new test file was written. It fits on a synthetic stream, issues a card, freezes it, joins new rows, types the miss, rewrites the reliability report, forces drift, sees the card abstain, clears the drift and sees it issue again. It passes with the network blocked.

## Result per item

- **Item 1, clean clone timing: pass.** Total 766.2 s, main pipeline 365.8 s against the 30 minute budget.
- **Item 2, card latency: pass.** p95 is 18 to 21 ms with the bundle preloaded, in process and through the service. A fresh command line process takes about 1.2 s, which the plan scopes out.
- **Item 3, offline suite and coverage map: pass.** 905 tests, 905 passed, no skips, no failures, sockets blocked, 880.3 s.
- **Item 4, README numbers re-derived: pass.** 1759 printed numbers in 14 tables agree with the report JSON at printed precision.
- **Item 5, writing rules: pass.** The writing-rules tests pass and an independent grep over all 250 files finds no dash, no role noun and no digest token.
- **Anti-goal checks: pass.** The audit catches both leakage mutations, all 64 cards inspected carry the three identifiers, and the README shows the null and the abstention rate.

## Item 1: independent re-measurement on a clean clone

Command, run from the repository:

```
MOOTCOURT_DATA_ROOT="<external drive>/mootcourt-data/verification-clone/20261103-072326/root" \
  bash scripts/timed_run.sh <internal temp folder>/timed-work
```

- The clone is the files git would commit (tracked plus untracked and not ignored): 250 files, tree digest 00de6d82e9ff5c1d. The data root started empty except for the two raw archives and their checksum record, copied from the main data root. The `data` stage is therefore a **checksum verification, not a download**: the script reports 4.9 s of verification, and the stage's 60.3 s is that plus ingest of three sources. Nothing was fetched from the network.
- The work folder (with the clone) is on the internal disk and the data root is on the external drive, because installing a wheel on the exFAT volume trips over the `._` sidecar files it creates. This was the first attempt of this session. The run was the only job on the machine, and no other agent was running.

| stage | exit | seconds |
|---|---|---|
| setup | 0 | 1.9 |
| data (checksum verification and ingest) | 0 | 60.3 |
| power | 0 | 47.9 |
| fit-upworthy | 0 | 29.7 |
| backtest-upworthy | 0 | 192.6 |
| fit-asos | 0 | 1.9 |
| backtest-asos | 0 | 7.3 |
| fit-synthetic | 0 | 3.1 |
| backtest-synthetic | 0 | 21.1 |
| challenger-gbm | 0 | 371.0 |
| audit-upworthy | 0 | 3.1 |
| audit-asos | 0 | 0.6 |
| audit-synthetic | 0 | 0.6 |
| inventory | 0 | 3.7 |
| data-verify | 0 | 12.3 |
| latency | 0 | 9.1 |

Main pipeline (setup through backtest-synthetic) 365.8 s; compute 761.3 s; total 766.2 s. The run in the README, which also verified existing archives, reports a total of 764.7 s. Logs are in the clone folder next to `run-log.md` and `stages.txt`.

**Reproducibility.** Compared with the reports on the main data root, the ASOS and synthetic backtest JSON, the three reliability reports and the Upworthy challenger JSON from this independent run are equal, key for key and value for value (the challenger gate file differs only in its elapsed seconds, 41.4 against 47.7). The Upworthy backtest JSON is equal in every key and every non-float value, and its floating point values differ by at most 3.6e-11 in relative terms (summation order), far below the printed precision. The ASOS report on the main data root now equals the clean run's, so the stale report of defect BUG-006 has been refreshed.

## Item 2: card latency

Measured again by me on a quiet machine, Upworthy model 5f1c07efd730, 20000 impressions per arm. Raw numbers are in `card-latency-tester.json` and `curl_times_ms_x1000.txt` in the clone folder.

| path | calls | p50 ms | p95 ms | max ms |
|---|---|---|---|---|
| in process, bundle preloaded (repository script, clean run) | 30 | 17.3 | 18.0 | 25.5 |
| service on loopback (repository script, clean run) | 30 | 19.4 | 21.1 | 24.6 |
| service on loopback, timed independently with curl | 60 | 18.8 | 19.4 | 19.8 |
| command line, fresh process (repository script, clean run) | 3 | 1246.7 | 1246.8 | 1246.9 |

The criterion is p95 under one second with the index preloaded (plan-notes, card latency call), and it holds by a factor of about fifty. A fresh command line process takes 1.2 s because of interpreter and library imports; the README states this openly. All 60 cards written by the curl run carry the snapshot id, model id and feature hash.

## Item 3: offline suite

Command: `MOOTCOURT_DATA_ROOT="<external drive>/mootcourt-data" uv run pytest -q -p no:cacheprovider --junitxml=...` with the autouse network guard from the test configuration, which raises on any non-loopback connect and is itself asserted by `test_network_is_blocked_for_the_whole_suite`.

- 905 tests, 905 passed, 0 failed, 0 skipped, 880.3 s, 3 warnings (a numpy divide warning in a scikit-learn call and a pandas deprecation notice, neither from the project code under test).
- The coverage-map test, the writing-rules tests, the end to end test and the leakage tests were run again on their own: 113 passed, 0 failed.
- Lint: `ruff check .` reports no findings, and the lint test passes.
- Every topic in the task text has a line in the map above. Predictors on known truth: P0 against the cell mean, P1 recovers mu and tau, P2 equals P1 at lambda 0 and beats it on planted signal, P3 against hand-computed scores, and the ladder orders correctly on known truth.

## Item 4: README numbers re-derived

`scripts/verify_readme_numbers.py` uses only the standard library and pandas and imports nothing from the package. It parses every table in the README results block, re-derives each number from the report JSON under the data root and compares it at the printed precision. Where the report also keeps the row-level score table, it recomputes n, log score, abstention rate and 90 percent coverage from the rows as well. Brier skill points are recomputed as one minus the Brier score over the base-rate Brier score. Bootstrap interval ends are taken from the report, because a bootstrap cannot be re-derived from summaries.

```
MOOTCOURT_DATA_ROOT="<external drive>/mootcourt-data" uv run python scripts/verify_readme_numbers.py
```

Result: 14 tables, 1759 numbers checked, 0 mismatches; every table has at least 10 numbers checked (the task asks for three).

| table | numbers checked |
|---|---|
| Upworthy backtest | 288 |
| ASOS backtest | 301 |
| Synthetic backtest | 261 |
| Synthetic gate power | 43 |
| Challengers, Upworthy | 52 |
| Ablations, Upworthy | 168 |
| P2 admission guard, Upworthy | 11 |
| Ablations, ASOS | 56 |
| P2 admission guard, ASOS | 11 |
| The cautionary run | 81 |
| Learning curve, ASOS | 187 |
| Learning curve, Upworthy | 267 |
| Card latency | 10 |
| Run time | 23 |

Negative control: with one printed Brier skill changed by one unit in the last place in a copy of the README, the script reports four mismatches (the same number appears in four tables) and exits 1.

## Item 5: writing rules

- The writing-rules module (70 test cases) passed in the full run and again after this file was written.
- Independent grep, written separately from the test and run over `git ls-files --cached --others --exclude-standard`: 250 files listed, 236 text files scanned, 14 binary files skipped, `._*` files and ignored folders skipped. Checked: U+2014, U+2013, the role noun on word boundaries, and every lower-cased word and word pair hashed with SHA-256 against `tests/forbidden_terms.sha256` and `tests/restricted_terms.sha256`, with file names tokenised too, URLs removed first and the documented allow-list for the second digest file only.
- Result: 0 dashes of either kind, 0 role nouns, 0 forbidden-tier hits, 0 restricted-tier hits outside the documented allow-list (the second digest file matches only in the survey pages, the importers and their fixtures). The two digest files are byte-identical to the copies kept with the project plan.

## Anti-goal checks

- **No score from a model that saw the row.** The test `test_leakage_mutation_is_caught` makes the harness leaky and confirms the guard raises. In addition I mutated a copy of the real synthetic score table in a temporary folder (the repository was untouched): moving 5 percent of rows to a later origin gave 723 violations and exit 1, and stamping 5 percent of rows as usable 60 days early gave 453 violations and exit 1. The unmodified table gives 0 violations and exit 0. `make audit` passed for all three sources in the clean run (0 violations each).
- **Every issued card has snapshot id, model id and feature hash.** Checked on 64 cards written during this session on the clean run's Upworthy model (60 through the service, 4 through the command line): 64 of 64. In addition each frozen card id was recomputed independently as 16 hex characters of sha256 over the sorted-key JSON without the id and equals the file name; issuing the same request again returns byte-identical output and writes no new file; a frozen file altered by one field makes the same request exit 1 with the message that the card is frozen with different content; a later issue time gives a new id and leaves the first card untouched.
- **The README shows the null and the abstention rate.** It prints the percentile of the observed calibration error within the perfect-calibration null for each source (percentile 100.0 for both real archives, stated as worse than the null) and an abstention-rate column in every results table.

## Defects found during verification

Reproductions are in the fleet test artifacts folder, one script per defect.

| id | severity | summary |
|---|---|---|
| BUG-001 | high | `moot join` crashes on a `._*.json` sidecar file in the cards folder, which the external exFAT drive creates |
| BUG-002 | medium | A bulk-snapshot file for one vendor cannot be imported from the command line; the start-date flag is ignored |
| BUG-003 | medium | `effect_unit` is not validated and mixed units in one cell pass `ledger check` and `ingest` |
| BUG-004 | medium | The service and the MCP card tool require a headline and an image flag even for ledgers without text |
| BUG-005 | low | Several bad inputs end in a raw traceback instead of a one-line error |
| BUG-006 | low | The ASOS report on the main data root predates the multi-metric change and is stale |
| BUG-007 | low | `timed_run.sh` hard-codes "archives downloaded from OSF in this run" in the run log even when none were |

None of these changes a number in the README. T-025 is not blocked by them, but BUG-001 breaks the weekly loop on the storage layout the project recommends.
