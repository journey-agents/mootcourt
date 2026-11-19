# Simulated Readers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an opt-in module that plays a panel of ten simulated readers over headline-only story cards, aligns it with earlier tests by seven methods, runs it once per model for three models on the exploratory split, and reports the result in the paper's body.

**Architecture:** A new subpackage `mootcourt.simulators.readers` holds the fixed protocol (seed, prompts, profiles), the feed builder, a wrapper around `claude -p`, a transcript store, the panel score, the alignment methods, the probes and the measures. One script, `scripts/simulated_readers.py`, has three stages: `plan` (no model), `run` (model calls, behind a flag) and `score` (no model). Scoring reads only transcripts, the ledger and run 9's saved row scores.

**Tech Stack:** Python 3.11+, pandas, numpy, scipy, scikit-learn (all already dependencies), the `claude` command line tool at version 2.1.327 as an external program. No new dependency.

**Spec:** `docs/superpowers/specs/2026-11-18-llm-simulated-readers-design.md` (commit `a4406b3`). The spec binds; this plan fixes its exact values.

## Written before any result

Written 18 November 2026. What had been seen: everything the spec lists, plus the counts in the next section, which read run 9's saved scores and the ledger for row counts, arm counts and dates only. One outcome figure was printed while counting and is therefore known: the earliest-arm rule's direction accuracy on the 5,966 headline-only contrasts is 0.570. No simulated reader has been run on any archive headline, and no prompt has been tried on one.

## Facts located for this plan

Inputs, both on the data root (`MOOTCOURT_DATA_ROOT`):

- `reports/scores-upworthy-20261106-2dc461f52ea4.parquet`: run 9's row scores. For `cell == "headline_only"` each rung has 5,966 rows in 1,770 tests. Columns used: `row_id`, `test_id`, `origin`, `rung`, `y`, `s`, `direction_correct`, `dir_ceiling_row`, `p_win`, `s_star`. The rungs `always_reference` and `text_lr` carry `direction_correct` per row, so both baselines and the ceiling are read from this file and nothing is regenerated.
- `data/ledger/ledger.parquet`: per `row_id`, `usable_after`, `n_ref`, `n_var` and `features_json` with `headline`, `reference_headline` and `post_launch.clicks_ref`, `post_launch.clicks_var`.

Counts (the `plan` stage must reproduce every one of them, and stops if it does not):

| Origin | Units | Contrasts | Blocks | Feeds | Earlier contrasts visible | Earlier units visible |
|---|---|---|---|---|---|---|
| 2013-04-01 | 163 | 399 | 6 | 22 | 0 | 0 |
| 2014-01-01 | 214 | 687 | 8 | 43 | 399 | 163 |
| 2014-04-01 | 299 | 1,026 | 10 | 48 | 1,025 | 357 |
| 2014-07-01 | 439 | 1,550 | 15 | 73 | 2,011 | 645 |
| 2014-10-01 | 422 | 1,544 | 15 | 77 | 3,506 | 1,073 |
| 2015-01-01 | 182 | 604 | 7 | 34 | 5,176 | 1,526 |
| 2015-04-01 | 52 | 156 | 2 | 11 | 5,785 | 1,708 |
| Total | 1,771 | 5,966 | 63 | 308 | | |

Three facts the spec did not know, and the rule this plan sets for each:

- One test has contrasts at two origins. The unit of a feed is therefore a pair of test and origin, and there are 1,771 units for 1,770 tests. The reference arm of that test is shown in both units.
- In 50 tests, two or more scored contrasts carry the same variant headline (145 contrasts). A card shows a headline only, so an arm is a distinct headline within a unit, and contrasts with the same headline share one arm and one panel score. An arm's clicks and impressions are summed over the rows that share its headline.
- Sixteen headlines have fewer than six words. The completion probe skips an arm of fewer than eight words and counts the skips.

`usable_after` is the same for every row of a test, and no `y` is exactly zero.

## Calls made in this plan that the user may change

1. A failed transport (nonzero exit, timeout, a usage-limit message) is not a reply. It is never recorded as missing. After five such failures in a row the `run` stage stops, and a later `run` resumes. Only a reply that fails the schema twice more, or a refusal, is recorded as missing.
2. Method 2 follows the spec's wording: one intercept for all arms. A model with one intercept per test would read only differences within a test and may suit direction better. It is not run, because the spec fixes the form and reading 2 rests on it.
3. Method 4's monotone map is a logistic curve, which has no flat steps, and not an isotonic fit, which would produce many ties.
4. Method 5 gives the panel difference the value zero on training rows that have no panel answer, with no indicator column.
5. Methods 6 and 7 reuse the plain panel's blocks and feeds exactly, and one draw of examples serves every feed of an origin.
6. The block bootstrap resamples the 63 blocks pooled over origins.
7. The probes batch their items: 10 completions, 30 familiarity ratings or 10 pairs to a call.

## Global Constraints

- No em dash, en dash or other Unicode dash in any file. Write "to" and "minus".
- Do not use the common word for a person who possesses or is responsible for something; write "the maintainers" or "the launching team". `tests/test_writing_rules.py` enforces both rules and the digest lists, in file names too.
- No model call in the default path, in the test suite or in CI. `run` refuses without `--allow-model-calls`.
- Never open an Upworthy file named holdout, confirmatory or undeployed.
- Do not edit any existing file under `src/` except `src/mootcourt/simulators/__init__.py` if an export is needed. Run 9's code paths stay byte-identical.
- One committed code state for the run: commit, then run, record the commit in the run folder, and do not touch `src/` or `scripts/` during the run.
- Any trial of prompts or flags uses synthetic headlines only. Nothing is scored until every planned call of all three models is stored or recorded as missing.
- Seed: `20261118`. Every random draw uses `numpy.random.default_rng([20261118, stream, *keys])` with the stream numbers of Task 1.
- Models: `claude-opus-5-5` (primary), `claude-sonnet-5-5`, `claude-haiku-5-5`.
- Run folder: `paper/data/run11-simulated-readers`. Transcripts: `$MOOTCOURT_DATA_ROOT/experiments/run11-simulated-readers/`.
- Commit only the files a task names. Do not push to `main`.
- Run commands with `nice -n 19`. Use `uv run pytest -p no:cacheprovider`; do not add `-q`.

## Review Focus

1. A reader's reply holds the right count of numbers but one is outside 0 to 100, or is a string. It must fail the schema and be retried, never clipped. (Task 4)
2. A usage-limit message arrives as text with exit code 0. It must be treated as a transport failure and not stored as a reply or as missing. (Task 4)
3. A reader is missing one feed of a block. That reader must drop out of every arm of the block, and the block's other readers must still be scored. (Task 5)
4. An alignment method at an origin sees a unit whose `usable_after` is later than the origin. It must not enter the fit; a planted future unit with a decisive signal must leave the fitted values unchanged. (Task 6)
5. `score` is started while calls are outstanding for one model. It must refuse and name the count outstanding. (Task 11)

---

### Task 1: The protocol and the inputs

**Files:**
- Create: `src/mootcourt/simulators/readers/__init__.py`, `src/mootcourt/simulators/readers/protocol.py`, `src/mootcourt/simulators/readers/inputs.py`
- Test: `tests/test_readers_inputs.py`

**Interfaces:**
- Produces, in `protocol.py`: `SEED = 20261118`; `STREAMS = {"blocks": 1, "arms": 2, "positions": 3, "probe_set": 4, "examples": 5, "brief_draw": 6, "bootstrap": 7, "probe_items": 8}`; `rng(stream: str, *keys: int) -> numpy.random.Generator`; `MODELS = ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5")`; `PRIMARY_MODEL = MODELS[0]`; `BLOCK_SIZE = 30`; `N_READERS = 10`; `HALVES = ((1, 2, 3, 4, 5), (6, 7, 8, 9, 10))`; `CELL = "headline_only"`; `Z = 1.96`; `PROFILES` (Task 3); the prompts (Tasks 3, 8, 9).
- Produces, in `inputs.py`: `load_units(ledger: pd.DataFrame, scores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]` returning `(arms, contrasts)`.
  - `arms` columns: `unit_id` (`"<test_id>@<origin as YYYY-MM-DD>"`), `test_id`, `origin`, `origin_index` (0 to 6), `arm_id` (`"<unit_id>#<k>"`, `k = 0` for the reference, then variants in order of first `row_id`), `headline`, `is_reference`, `clicks`, `impressions`, `usable_after`.
  - `contrasts` columns: `row_id`, `unit_id`, `test_id`, `origin`, `origin_index`, `arm_id`, `ref_arm_id`, `y`, `s`, `decisive` (`abs(y) > 1.96 * s`), `usable_after`, `ref_correct` (the saved `direction_correct` of `always_reference`), `text_lr_correct` (of `text_lr`), `dir_ceiling_row`, `s_star`.
- `load_units` raises `ValueError` when a scored row is absent from the ledger, when a unit has two reference headlines, or when a variant headline equals its reference.

- [ ] **Step 1: Write the failing tests** in `tests/test_readers_inputs.py`, on a small hand-built ledger and scores frame (three tests; one with two contrasts that share a headline; one whose contrasts sit at two origins):

```python
def test_arms_are_distinct_headlines_and_share_clicks(frames):
    arms, contrasts = load_units(*frames)
    u = arms[arms.test_id == "t_dup"]
    assert list(u.is_reference) == [True, False, False]          # three rows, two variant headlines
    shared = u[u.headline == "Same words"].iloc[0]
    assert (shared.clicks, shared.impressions) == (30 + 50, 1000 + 1000)
    assert contrasts[contrasts.test_id == "t_dup"].arm_id.nunique() == 2

def test_a_test_at_two_origins_makes_two_units(frames):
    arms, _ = load_units(*frames)
    assert arms[arms.test_id == "t_span"].unit_id.nunique() == 2
    assert arms[(arms.test_id == "t_span") & arms.is_reference].shape[0] == 2

def test_baseline_columns_come_from_the_saved_rungs(frames):
    _, contrasts = load_units(*frames)
    assert set(contrasts.ref_correct.unique()) <= {0.0, 1.0}
    assert contrasts.decisive.equals(contrasts.y.abs() > 1.96 * contrasts.s)

def test_only_the_headline_only_cell_is_read(frames):
    _, contrasts = load_units(*frames)
    assert "row_other_cell" not in set(contrasts.row_id)

def test_rng_streams_are_independent_and_repeatable():
    assert rng("blocks", 0).integers(1 << 30) == rng("blocks", 0).integers(1 << 30)
    assert rng("blocks", 0).integers(1 << 30) != rng("arms", 0).integers(1 << 30)
```

- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_readers_inputs.py`. Expected: FAIL, the module does not exist.
- [ ] **Step 3: Implement** `protocol.py` (constants and `rng` only for now) and `inputs.py`. `origin_index` is the rank of the origin among the sorted distinct origins of the headline-only rows.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** the three source files and the test: "Add the protocol constants and the input loader of the simulated readers".

### Task 2: Blocks and matched feeds

**Files:**
- Create: `src/mootcourt/simulators/readers/feeds.py`
- Test: `tests/test_readers_feeds.py`

**Interfaces:**
- Consumes: `arms` from Task 1, `rng`, `BLOCK_SIZE`.
- Produces: `build_feeds(arms: pd.DataFrame) -> pd.DataFrame` with columns `block_id` (`"<origin_index>-<k:02d>"`), `origin_index`, `feed_index` (0-based), `position` (1-based), `unit_id`, `arm_id`; and `feeds_checksum(feeds: pd.DataFrame) -> str` (SHA-256 of the frame sorted by block, feed and position, as CSV).

Rules, exactly:
- Within an origin, units are ordered by arm count ascending. Within a count the order is `rng("blocks", origin_index).permutation` of the units sorted by `unit_id`. The ordered list is cut into blocks of 30.
- A block has `F` feeds, `F` being its largest arm count.
- A unit's arm sequence is drawn with `rng("arms", origin_index, block number, rank of the unit within the block)`: independent permutations of its arms, joined end to end, cut to length `F`.
- Positions: one `rng("positions", origin_index, block number).permutation` of the block's units, the same in every feed.

- [ ] **Step 1: Write the failing tests:**

```python
def test_every_feed_of_a_block_holds_the_same_units_in_the_same_positions(feeds):
    for _, b in feeds.groupby("block_id"):
        layouts = {tuple(f.sort_values("position").unit_id) for _, f in b.groupby("feed_index")}
        assert len(layouts) == 1

def test_each_arm_appears_and_no_arm_twice_before_all_appeared(arms, feeds):
    for (block, unit), g in feeds.groupby(["block_id", "unit_id"]):
        k = arms[arms.unit_id == unit].shape[0]
        seq = list(g.sort_values("feed_index").arm_id)
        assert set(seq[:k]) == set(arms[arms.unit_id == unit].arm_id) or len(seq) < k
        assert len(set(seq[:k])) == min(k, len(seq))

def test_blocks_stay_within_an_origin_and_hold_at_most_30(feeds):
    assert feeds.groupby("block_id").origin_index.nunique().max() == 1
    assert feeds.groupby("block_id").unit_id.nunique().max() <= 30

def test_feed_count_is_the_largest_arm_count(arms, feeds):
    n = arms.groupby("unit_id").size()
    for block, b in feeds.groupby("block_id"):
        assert b.feed_index.nunique() == n[b.unit_id.unique()].max()

def test_two_builds_are_identical(arms):
    assert feeds_checksum(build_feeds(arms)) == feeds_checksum(build_feeds(arms))
```

  The `arms` fixture is synthetic: two origins, 70 and 31 units, arm counts 2 to 6.
- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_readers_feeds.py`. Expected: FAIL.
- [ ] **Step 3: Implement** `build_feeds` and `feeds_checksum`.
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit**: "Add blocks and matched feeds".

### Task 3: Prompts, profiles and reply schemas

**Files:**
- Modify: `src/mootcourt/simulators/readers/protocol.py`
- Create: `src/mootcourt/simulators/readers/prompts.py`
- Test: `tests/test_readers_prompts.py`

**Interfaces:**
- Produces: `reader_prompt(profile: str, headlines: list[str], preface: str = "") -> str`; `clicks_schema(n: int) -> dict`; `parse_clicks(text: str, n: int) -> list[float]` (raises `ReplyError` on anything but `n` numbers from 0 to 100); `class ReplyError(ValueError)`; `is_refusal(text: str) -> bool` (no JSON object in the reply).

Exact copy for `protocol.py`.

`SYSTEM_PROMPT`:

```
You are playing one person who is browsing the web at some time between 2013 and 2015. You will be given a short description of that person and then a feed of story headlines from a news and entertainment site, numbered, one per line. For each headline, give the probability from 0 to 100 that this person would click on it at this moment. Judge each headline as this person would on a quick scroll. Most people click on few of the stories they scroll past. Reply with one JSON object and nothing else.
```

`READER_TEMPLATE` (the preface, when present, comes first and is followed by one blank line):

```
The reader: {profile}

The feed:
{numbered headlines, "1. <headline>" and so on}

Reply as {"clicks": [...]} with exactly {n} numbers, one for each headline in order, each from 0 to 100.
```

`PROFILES` (reader 1 to reader 10):

1. You are between 19 and 24 and a college student. You like music, campus politics and funny videos. You are putting off an assignment and are a little bored. You are on your phone, and a friend shared this in your social feed.
2. You are between 25 and 34 and work in an office. You follow national news, technology and personal finance. You are on a short lunch break and want something quick. You are at your desktop, and the story came up in your social feed.
3. You are between 25 and 34 and have two small children. You care about parenting, health and stories that end well. It is late in the evening and you are tired. You are on your phone, and a relative shared this in your social feed.
4. You are between 35 and 44 and teach at a public school. You care about education, science and your local community. You are relaxed after dinner. You are at your desktop, and the story arrived in an email newsletter from the site.
5. You are between 35 and 44 and work as a nurse. You like stories about health, animals and ordinary people. You have five minutes of a break and are in a hurry. You are on your phone, and the story came up in your social feed.
6. You are between 45 and 54 and manage a small business. You follow the economy, politics and sports. You are sceptical of anything that sounds exaggerated. You are at your desktop, and someone you follow posted the link.
7. You are between 45 and 54 and at home with two teenagers. You care about family, faith and cooking. You are unhurried and in a good mood. You are at your desktop, and a neighbour shared this in your social feed.
8. You are between 55 and 64 and recently retired. You like gardening, history and news about your grandchildren's generation. You have plenty of time. You are at your desktop, and a friend forwarded the story by email.
9. You are between 18 and 24 and work shifts in a shop. You like celebrities, video games and comedy. You are restless and scrolling fast. You are on your phone, and the story came up in your social feed.
10. You are between 25 and 34 and work for a charity. You care about the environment, equal rights and documentaries. You are curious and willing to read something serious. You are on your phone, and you are on the site's front page.

`clicks_schema(n)` returns `{"type": "object", "properties": {"clicks": {"type": "array", "items": {"type": "number", "minimum": 0, "maximum": 100}, "minItems": n, "maxItems": n}}, "required": ["clicks"], "additionalProperties": False}`.

- [ ] **Step 1: Write the failing tests:**

```python
def test_prompt_shows_headlines_only_and_no_identifier():
    p = reader_prompt(PROFILES[0], ["Alpha beta", "Gamma delta"])
    assert "1. Alpha beta\n2. Gamma delta" in p and "exactly 2 numbers" in p
    assert not re.search(r"[0-9a-f]{24}|#\d|@20", p)

def test_no_profile_and_no_prompt_names_a_year_or_the_publisher():
    for text in (*PROFILES, READER_TEMPLATE):
        assert not re.search(r"\b20\d\d\b|upworthy", text, re.I)
    assert "between 2013 and 2015" in SYSTEM_PROMPT and "upworthy" not in SYSTEM_PROMPT.lower()

def test_there_are_ten_distinct_profiles():
    assert len(PROFILES) == 10 == len(set(PROFILES))

@pytest.mark.parametrize("text", ['{"clicks": [10, 101]}', '{"clicks": [10]}', '{"clicks": [10, "20"]}', '{"clicks": [10, null]}', "I would click the first."])
def test_bad_replies_are_rejected_and_never_clipped(text):
    with pytest.raises(ReplyError):
        parse_clicks(text, 2)

def test_a_good_reply_inside_other_text_is_read():
    assert parse_clicks('Here: {"clicks": [0, 100]}', 2) == [0.0, 100.0]

def test_a_reply_without_json_is_a_refusal():
    assert is_refusal("I cannot play this role.") and not is_refusal('{"clicks": [1]}')
```

- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_readers_prompts.py`. Expected: FAIL.
- [ ] **Step 3: Implement.** `parse_clicks` takes the first JSON object found in the text; booleans are not numbers.
- [ ] **Step 4: Run** again, then `uv run pytest -p no:cacheprovider tests/test_writing_rules.py`. Expected: PASS for both.
- [ ] **Step 5: Commit**: "Fix the prompts, the ten reader profiles and the reply schema".

### Task 4: The command wrapper and the transcript store

**Files:**
- Create: `src/mootcourt/simulators/readers/command.py`, `src/mootcourt/simulators/readers/transcripts.py`
- Create: `tests/fixtures/fake_reader_tool.py` (a stand-in for the tool: reads the prompt on standard input, prints a tool-shaped JSON reply whose behaviour is set by environment variables: fixed probabilities, a bad reply for the first K attempts, a refusal, a usage-limit text, a nonzero exit, a sleep)
- Test: `tests/test_readers_command.py`

**Interfaces:**
- Produces, in `command.py`:
  - `build_command(model: str, system: str, schema: dict, program: str = "claude") -> list[str]`
  - `call(model: str, system: str, prompt: str, schema: dict, *, program: str = "claude", time_cap_s: float = 180.0) -> ToolReply` with `ToolReply(text: str, reported_model: str | None, tool_version: str | None, seconds: float)`; raises `TransportError` on a nonzero exit, a timeout, an unreadable tool envelope, or a reply that matches `USAGE_LIMIT_PATTERN`.
  - `class TransportError(RuntimeError)`
- Produces, in `transcripts.py`:
  - `request_hash(model, kind, system, prompt, schema) -> str`
  - `class Transcripts(root)` with `get(model, kind, h) -> dict | None`, `put(model, kind, h, record) -> Path`, `count(model, kind) -> dict[str, int]` by status; it wraps `mootcourt.simulators.cache.SimulationCache` with `provider_id = model` and `version = kind`.
  - `ask(transcripts, model, kind, system, prompt, schema, parse, *, program="claude", allow_model_calls=False) -> dict`: returns the stored record when one exists; otherwise, only when `allow_model_calls` is true, calls up to three times (the first call and two retries with the same input), stores and returns a record with `status` one of `"ok"`, `"invalid"`, `"refusal"`, plus `request`, `reply_text`, `parsed`, `attempts`, `reported_model`, `tool_version`, `seconds`, `stored_at`. A `TransportError` propagates and stores nothing. With `allow_model_calls` false and no stored record it raises `ModelCallsNotAllowed`.

Command requirements (the spec's "How the model is called"): the working directory is a new empty directory from `tempfile.mkdtemp`, which must lie outside the repository and outside the data root (check both, and call `refuse_data_root_command`); the environment is `scrub_env(os.environ, declared=LOGIN_ENV)`; the child leads its process group and `kill_group` ends it on timeout. The starting flags are:

```
claude -p --model <id> --system-prompt <text> --tools "" --strict-mcp-config --mcp-config {"mcpServers":{}}
       --setting-sources "" --no-session-persistence --disable-slash-commands --output-format json --json-schema <schema>
```

`--bare` is not used, because it reads no login of a subscription. The exact flags, `LOGIN_ENV` and where the tool's JSON envelope carries the reply text, the model identifier and the version are settled in Task 13 on synthetic headlines; until then the fake tool defines the envelope, and `command.py` keeps the envelope's field names in one place (`ENVELOPE`).

- [ ] **Step 1: Write the failing tests** (all against the fake tool; none starts `claude`):

```python
def test_command_turns_tools_servers_settings_and_sessions_off():
    c = build_command("claude-opus-5-5", "S", {"type": "object"})
    assert c[:2] == ["claude", "-p"] and c[c.index("--model") + 1] == "claude-opus-5-5"
    assert c[c.index("--tools") + 1] == "" and "--strict-mcp-config" in c and "--no-session-persistence" in c
    assert c[c.index("--setting-sources") + 1] == "" and c[c.index("--system-prompt") + 1] == "S"
    assert "--bare" not in c and "--append-system-prompt" not in c

def test_child_runs_in_an_empty_directory_outside_the_repository(fake):
    r = call("m", "S", "P", clicks_schema(2), program=fake(echo_cwd=True))
    cwd = Path(json.loads(r.text)["cwd"])
    assert list(cwd.iterdir()) == [] and ROOT not in cwd.parents and cwd != ROOT

def test_credentials_in_the_environment_do_not_reach_the_child(fake, monkeypatch):
    monkeypatch.setenv("SOME_API_KEY", "secret")
    r = call("m", "S", "P", clicks_schema(2), program=fake(echo_env=True))
    assert "SOME_API_KEY" not in json.loads(r.text)["env"]

def test_a_stored_reply_is_read_back_without_a_call(fake, tmp_path):
    t = Transcripts(tmp_path)
    a = ask(t, "m", "plain", "S", "P", clicks_schema(2), lambda s: parse_clicks(s, 2), program=fake(clicks=[10, 20]), allow_model_calls=True)
    b = ask(t, "m", "plain", "S", "P", clicks_schema(2), lambda s: parse_clicks(s, 2), program="/nonexistent")
    assert a["status"] == "ok" and b["parsed"] == [10.0, 20.0]

def test_without_the_flag_no_call_is_made(tmp_path, fake):
    with pytest.raises(ModelCallsNotAllowed):
        ask(Transcripts(tmp_path), "m", "plain", "S", "P", clicks_schema(2), lambda s: parse_clicks(s, 2), program=fake(clicks=[1, 2]))

def test_a_bad_reply_is_retried_twice_then_recorded_invalid(fake, tmp_path):
    ok = ask(Transcripts(tmp_path / "a"), "m", "plain", "S", "P", clicks_schema(2), lambda s: parse_clicks(s, 2), program=fake(bad_first=2, clicks=[1, 2]), allow_model_calls=True)
    bad = ask(Transcripts(tmp_path / "b"), "m", "plain", "S", "P", clicks_schema(2), lambda s: parse_clicks(s, 2), program=fake(bad_first=3, clicks=[1, 2]), allow_model_calls=True)
    assert (ok["status"], ok["attempts"]) == ("ok", 3) and (bad["status"], bad["attempts"]) == ("invalid", 3)

def test_an_out_of_range_number_is_invalid_and_not_clipped(fake, tmp_path):
    r = ask(Transcripts(tmp_path), "m", "plain", "S", "P", clicks_schema(2), lambda s: parse_clicks(s, 2), program=fake(clicks=[10, 140]), allow_model_calls=True)
    assert r["status"] == "invalid" and r["parsed"] is None

def test_a_refusal_is_recorded_as_a_refusal(fake, tmp_path):
    r = ask(Transcripts(tmp_path), "m", "plain", "S", "P", clicks_schema(2), lambda s: parse_clicks(s, 2), program=fake(refuse=True), allow_model_calls=True)
    assert r["status"] == "refusal"

@pytest.mark.parametrize("mode", ["exit_nonzero", "usage_limit_text_exit_zero", "sleep_past_cap"])
def test_transport_failures_store_nothing(fake, tmp_path, mode):
    t = Transcripts(tmp_path)
    with pytest.raises(TransportError):
        ask(t, "m", "plain", "S", "P", clicks_schema(2), lambda s: parse_clicks(s, 2), program=fake(**{mode: True}), allow_model_calls=True)
    assert t.count("m", "plain") == {}
```

  `USAGE_LIMIT_PATTERN` starts as `re.compile(r"usage limit|rate limit|limit reached|try again (later|at)", re.I)` and is applied only to a reply that holds no JSON object. `sleep_past_cap` passes `time_cap_s=1`.
- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_readers_command.py`. Expected: FAIL.
- [ ] **Step 3: Implement** both modules and the fake tool.
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit**: "Add the wrapper around the command line tool and the transcript store".

### Task 5: The panel score

**Files:**
- Create: `src/mootcourt/simulators/readers/panel.py`
- Test: `tests/test_readers_panel.py`

**Interfaces:**
- Consumes: `feeds` (Task 2), `contrasts` (Task 1).
- Produces:
  - `answers_frame(records: Iterable[dict]) -> pd.DataFrame` with columns `block_id`, `feed_index`, `reader`, `position`, `prob` (NaN for every position of a call whose status is not `"ok"`).
  - `reader_scores(feeds, answers) -> pd.DataFrame`: one row per `arm_id` and `reader`, columns `centred` (the mean over the arm's repeats of the probability minus its call's mean) and `raw` (the same mean without centring). A reader with any call of a block not `"ok"` has no row for any arm of that block.
  - `panel_scores(reader_scores, weights: np.ndarray | None = None, readers: tuple[int, ...] | None = None) -> pd.Series` indexed by `arm_id`: the mean, or the weighted mean with weights renormalised over the readers present, of `centred`.
  - `directions(contrasts, arm_score: pd.Series) -> pd.DataFrame` with `row_id`, `diff` (variant minus reference, NaN when either arm has no reader), `correct` (1.0, 0.0, or 0.5 for a tie), `tie` (`diff == 0`), `no_reader` (`diff` is NaN; counted as a tie with `correct = 0.5`).
  - `split_half_agreement(contrasts, reader_scores) -> dict` with `agree_share` (the share of contrasts whose two half-panel differences have the same nonzero sign) and `n`. It reads no outcome.

- [ ] **Step 1: Write the failing tests:**

```python
def test_centring_removes_a_call_s_level(feeds2, base_answers):
    shifted = base_answers.assign(prob=lambda d: d.prob + np.where((d.reader == 3) & (d.feed_index == 0), 20, 0))
    a, b = reader_scores(feeds2, base_answers), reader_scores(feeds2, shifted)
    pd.testing.assert_series_equal(panel_scores(a), panel_scores(b))

def test_repeats_of_an_arm_are_averaged(feeds2, base_answers):
    # unit u1 has two arms in a block of three feeds, so one arm is read twice by every reader
    s = reader_scores(feeds2, base_answers)
    assert s[(s.arm_id == "u1#0") & (s.reader == 1)].shape[0] == 1

def test_a_reader_missing_one_feed_leaves_the_whole_block(feeds2, base_answers):
    holed = base_answers.copy()
    holed.loc[(holed.reader == 4) & (holed.block_id == "0-00") & (holed.feed_index == 1), "prob"] = np.nan
    s = reader_scores(feeds2, holed)
    assert 4 not in set(s[s.arm_id.str.startswith(("u1", "u2"))].reader)   # the units of block 0-00
    assert 4 in set(s[s.arm_id.str.startswith("u9")].reader)               # a unit of another block
    assert s[s.arm_id == "u1#0"].reader.nunique() == 9

def test_tie_counts_half_and_no_reader_is_counted_apart(contrasts2):
    d = directions(contrasts2, pd.Series({"u1#0": 1.0, "u1#1": 1.0, "u2#0": 0.0, "u2#1": 2.0}))
    assert list(d.correct[:2]) == [0.5, 1.0] and bool(d.tie[0]) and not bool(d.no_reader[0])
    assert bool(d.no_reader.iloc[-1]) and d.correct.iloc[-1] == 0.5

def test_direction_is_the_sign_of_variant_minus_reference(contrasts2):
    d = directions(contrasts2, pd.Series({"u1#0": 0.0, "u1#1": -3.0, "u2#0": 0.0, "u2#1": 2.0}))
    assert d.correct[0] == float(contrasts2.y[0] < 0)

def test_split_half_reads_no_outcome(contrasts2, feeds2, base_answers):
    s = reader_scores(feeds2, base_answers)
    assert split_half_agreement(contrasts2, s) == split_half_agreement(contrasts2.assign(y=-contrasts2.y), s)
```

- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_readers_panel.py`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit**: "Add the panel score, the tie rule and the two rules for missing replies".

### Task 6: Alignment methods 1 to 4

**Files:**
- Create: `src/mootcourt/simulators/readers/align.py`
- Test: `tests/test_readers_align.py`

**Interfaces:**
- Consumes: `arms`, `contrasts`, `reader_scores`, `panel_scores`, `directions`.
- Produces:
  - `visible_before(frame: pd.DataFrame, origin) -> pd.DataFrame`: rows with `origin < origin` and `usable_after <= origin`. Every fit below takes its training rows through this function and nothing else.
  - `traits(headline: str) -> np.ndarray` of four values: the count of whitespace-separated words, 1.0 if the headline holds `?`, 1.0 if it holds a digit, 1.0 if `re.search(r"\byou\b", headline, re.I)`.
  - `direction_map(arms, contrasts, reader_scores) -> pd.DataFrame` (method 1): per `row_id`, `p_variant` and `correct`, and frame attributes or a second return holding per origin the training share `base` of contrasts with `y > 0`.
  - `reader_weights(arms, contrasts, reader_scores) -> tuple[pd.DataFrame, dict]` (method 2): per `row_id` `diff` and `correct`; the dict maps origin index to the ten weights, the intercept and the slope.
  - `audience_matching(...)` (method 3) and `error_correction(...)` (method 4), same return shape.
- At origin index 0 every method returns the plain panel's `diff` and `correct` unchanged, and method 1's `p_variant` is NaN there.

Exact definitions. `x` is a centred reader score divided by 10. Training rows at an origin are `visible_before` rows.

1. Direction map: `sklearn.linear_model.LogisticRegression(C=1.0, max_iter=500)` of `y > 0` on the plain panel difference divided by 10, with an intercept, fitted on training contrasts whose difference is not NaN. `p_variant` is its probability on a scored contrast; `correct` is 1 when `p_variant > 0.5` and `y > 0` or `p_variant < 0.5` and `y < 0`, and 0.5 at exactly 0.5. Brier skill is `1 - sum((p_variant - e)^2) / sum((base - e)^2)` over origin indexes 1 to 6, `e` being `y > 0`.
2. Reader weights: parameters `u` (ten), `a`, `beta`; `w = softmax(u)`, `b = exp(beta)`, `eta_j = a + b * sum_r w_r x_jr`, `p_j = sigmoid(eta_j)`. Objective: `-(1/N) * sum_j [k_j log p_j + (n_j - k_j) log(1 - p_j)] / n_j + 1.0 * sum_r (w_r - 0.1)^2`, with `k_j` clicks and `n_j` impressions of training arm `j` and `N` the count of training arms that all ten readers scored. `scipy.optimize.minimize(method="L-BFGS-B")` from `u = 0`, `a = logit(sum k / sum n)`, `beta = log(0.1)`. An arm that lost a reader is scored with the weights renormalised over the readers present.
3. Audience matching: with `L_r` the mean of reader `r`'s `raw` score divided by 100 over training arms, and `T = sum k / sum n` over training arms, choose `w = softmax(u)` minimising `(sum_r w_r L_r - T)^2 + 0.01 * sum_r (w_r - 0.1)^2` by L-BFGS-B from `u = 0`. No outcome direction enters. The scored difference is the weighted centred panel difference.
4. Error correction: step one, `LogisticRegression(C=1e6, max_iter=1000)` fitted on two rows per training arm (clicked, not clicked) with sample weights `k_j` and `n_j - k_j`, on the plain panel score divided by 10; `m_j` is its probability. Step two, weighted least squares, weights `n_j`, of `k_j / n_j - m_j` on an intercept and the four traits. An arm's corrected value is `m_j` plus the fitted correction, and the difference of corrected values gives the direction.

- [ ] **Step 1: Write the failing tests** on a synthetic set with three origins (index 0, 1, 2), in which reader 7's centred score equals the planted effect and the other readers are noise:

```python
def test_every_method_equals_the_plain_panel_at_the_first_origin(world):
    plain = directions(world.contrasts, panel_scores(world.rs))
    for fit in (direction_map, reader_weights, audience_matching, error_correction):
        out = fit(world.arms, world.contrasts, world.rs)
        out = out[0] if isinstance(out, tuple) else out
        first = world.contrasts.origin_index == 0
        assert np.array_equal(out.correct[first.values], plain.correct[first.values])

def test_reader_weights_find_the_informative_reader_and_help(world):
    out, fits = reader_weights(world.arms, world.contrasts, world.rs)
    assert np.argmax(fits[2]["weights"]) == 6 and fits[2]["slope"] > 0
    later = (world.contrasts.origin_index > 0).values
    assert out.correct[later].mean() > directions(world.contrasts, panel_scores(world.rs)).correct[later].mean()

def test_a_unit_not_yet_usable_changes_no_fit(world):
    # the added unit starts at origin 0 with a decisive planted signal, and its usable_after is later than origin 1
    late = world.with_unit_usable_only_after(origin_index=1)
    at1 = world.contrasts.row_id[world.contrasts.origin_index == 1]
    for fit, column in ((direction_map, "p_variant"), (reader_weights, "diff"), (audience_matching, "diff"), (error_correction, "diff")):
        a, b = fit(world.arms, world.contrasts, world.rs), fit(late.arms, late.contrasts, late.rs)
        a, b = (a[0] if isinstance(a, tuple) else a), (b[0] if isinstance(b, tuple) else b)
        assert np.allclose(a.set_index("row_id")[column][at1], b.set_index("row_id")[column][at1], equal_nan=True)

def test_audience_matching_ignores_which_arm_won(world):
    flipped = world.contrasts.assign(y=-world.contrasts.y)
    a, fa = audience_matching(world.arms, world.contrasts, world.rs)
    b, fb = audience_matching(world.arms, flipped, world.rs)
    assert np.allclose(fa[2]["weights"], fb[2]["weights"]) and np.allclose(a["diff"], b["diff"], equal_nan=True)

def test_traits_are_the_four_fixed_ones():
    assert list(traits("Why would YOU read 9 things?")) == [6.0, 1.0, 1.0, 1.0]
    assert list(traits("Your youth")) == [2.0, 0.0, 0.0, 0.0]

def test_direction_map_returns_probabilities_and_a_base(world):
    out = direction_map(world.arms, world.contrasts, world.rs)
    later = (world.contrasts.origin_index > 0).values
    assert out.p_variant[later].between(0, 1).all() and out.p_variant[~later].isna().all()

def test_error_correction_uses_a_planted_trait(world_with_question_mark_effect):
    w = world_with_question_mark_effect
    out, _ = error_correction(w.arms, w.contrasts, w.rs)
    later = (w.contrasts.origin_index > 0).values
    assert out.correct[later].mean() > directions(w.contrasts, panel_scores(w.rs)).correct[later].mean()
```

- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_readers_align.py`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit**: "Add four alignment methods that read stored panel answers".

### Task 7: Method 5, the panel as a feature of the text classifier

**Files:**
- Create: `src/mootcourt/simulators/readers/textfeature.py`
- Test: `tests/test_readers_textfeature.py`

**Interfaces:**
- Consumes: `mootcourt.harness.TextLR`, `mootcourt.ledger.visible_rows`, `ADMITTED`, `contrasts`, a plain panel difference per `row_id`.
- Produces: `text_with_panel(ledger: pd.DataFrame, contrasts: pd.DataFrame, panel_diff: pd.Series) -> pd.DataFrame` with `row_id`, `correct_without`, `correct_with`, `p_without`, `p_with`.

Definition. At each origin, the training rows are `visible_rows` of the admitted rows of the source, every cell, exactly as run 9's `text_lr` was fitted. "Without" is `TextLR(rows)`; its direction on a scored row is the sign of `p_gt0 - 0.5` from `score_block`. "With" is a subclass that adds one column to the design: the panel difference divided by 10 for a row that has one (a headline-only row of an earlier scored unit in training, every scored row at scoring), and zero otherwise. `harness.py` is not edited. The same seed, vectorizer settings and `C` apply.

- [ ] **Step 1: Write the failing tests** on a synthetic ledger (use `mootcourt.sources.synthetic` as the existing text tests do):

```python
def test_without_the_feature_it_is_the_package_s_text_classifier(synth):
    out = text_with_panel(synth.ledger, synth.contrasts, synth.zero_diff)
    assert np.allclose(out.p_without, synth.package_text_lr_p_gt0)

def test_a_feature_of_zeros_changes_nothing(synth):
    out = text_with_panel(synth.ledger, synth.contrasts, synth.zero_diff)
    assert np.allclose(out.p_with, out.p_without, atol=1e-9)

def test_an_informative_feature_raises_accuracy_after_the_first_origin(synth):
    out = text_with_panel(synth.ledger, synth.contrasts, synth.diff_equal_to_planted_effect)
    later = (synth.contrasts.origin_index > 0).values
    assert out.correct_with[later].mean() > out.correct_without[later].mean()

def test_the_first_origin_is_unchanged_by_any_feature(synth):
    out = text_with_panel(synth.ledger, synth.contrasts, synth.diff_equal_to_planted_effect)
    first = (synth.contrasts.origin_index == 0).values
    assert np.allclose(out.p_with[first], out.p_without[first], atol=1e-9)
```

- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_readers_textfeature.py`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit**: "Add the panel difference as a feature of the text classifier".

The check on real data (that `correct_without` equals run 9's saved `text_lr` direction on all 5,966 rows) is in Task 13, because it reads the archive.

### Task 8: Methods 6 and 7, earlier results in front of the reader

**Files:**
- Create: `src/mootcourt/simulators/readers/incontext.py`
- Modify: `src/mootcourt/simulators/readers/protocol.py`
- Test: `tests/test_readers_incontext.py`

**Interfaces:**
- Consumes: `arms`, `visible_before`, `rng`.
- Produces: `example_units(arms, origin_index: int, n: int = 10) -> list[str]` (stream `examples`); `examples_preface(arms, unit_ids: list[str]) -> str`; `brief_units(arms, origin_index: int, n: int = 200) -> list[str]` (stream `brief_draw`; every visible unit when fewer than `n` exist); `brief_prompt(arms, unit_ids) -> str`; `brief_preface(note: str) -> str`; `clip_note(note: str, max_words: int = 150) -> str`; `BRIEF_SCHEMA = {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"], "additionalProperties": False}`.
- Both draw functions raise `ValueError` at origin index 0.

Exact copy for `protocol.py`.

`EXAMPLES_HEADER`: `Results of earlier tests on this site. Each line is a headline and the share of visitors who clicked it. Headlines under one number were shown for the same story.`
A unit is rendered as its number, then one line per arm in `arm_id` order: `   <headline> (<rate>% clicked)`, the rate being `100 * clicks / impressions` to two decimals.

`BRIEF_SYSTEM`: `You study the audience of a news and entertainment site from the results of its headline tests. Reply with one JSON object and nothing else.`

`BRIEF_TEMPLATE`:

```
Below are results of earlier headline tests on this site. Headlines under one number were shown for the same story, and each has the share of visitors who clicked it.

{rendered units}

Write a note of at most 150 words on what this audience clicked and what it passed over. Describe patterns only. Do not quote a headline. Reply as {"note": "..."}.
```

`BRIEF_PREFACE`: `What is known about this site's audience from earlier tests: {note}`

- [ ] **Step 1: Write the failing tests:**

```python
def test_examples_come_only_from_units_visible_at_the_origin(world):
    ids = example_units(world.arms, 2)
    seen = set(visible_before(world.arms, world.origin(2)).unit_id)
    assert len(ids) == 10 == len(set(ids)) and set(ids) <= seen

def test_no_draw_exists_at_the_first_origin(world):
    for draw in (example_units, brief_units):
        with pytest.raises(ValueError):
            draw(world.arms, 0)

def test_the_preface_shows_rates_and_no_identifier(world):
    text = examples_preface(world.arms, example_units(world.arms, 2))
    assert text.startswith(EXAMPLES_HEADER) and re.search(r"\(\d+\.\d\d% clicked\)", text)
    assert not re.search(r"@|#\d", text)

def test_the_brief_draw_takes_every_unit_when_fewer_than_200_exist(world):
    assert set(brief_units(world.arms, 1)) == set(visible_before(world.arms, world.origin(1)).unit_id)

def test_a_long_note_is_cut_at_150_words():
    assert len(clip_note("w " * 400).split()) == 150 and clip_note("short note") == "short note"

def test_draws_repeat(world):
    assert example_units(world.arms, 2) == example_units(world.arms, 2)
```

- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_readers_incontext.py`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit**: "Add the two alignment methods that show earlier results to the reader".

### Task 9: The recall probes

**Files:**
- Create: `src/mootcourt/simulators/readers/probes.py`
- Modify: `src/mootcourt/simulators/readers/protocol.py`
- Test: `tests/test_readers_probes.py`

**Interfaces:**
- Produces: `probe_units(arms, n: int = 300) -> list[str]` (stream `probe_set`, drawn from all units sorted by `unit_id`); `completion_items(arms, unit_ids) -> pd.DataFrame` (`arm_id`, `role` `"winner"` or `"other"`, `stem`, `rest`, `skipped`); `familiarity_items(arms, unit_ids) -> pd.DataFrame`; `pair_items(contrasts, arms, unit_ids) -> pd.DataFrame` (`row_id`, `a_arm_id`, `b_arm_id`, the order drawn with stream `probe_items`); `batches(frame, size) -> list[pd.DataFrame]`; the three prompt builders and parsers; `token_f1(completion: str, truth: str) -> float`; `probe_measures(...) -> dict`.

Rules:
- Completion: the winner is the arm of the unit with the highest `clicks / impressions` (the lowest `arm_id` on a tie). The other arm is one draw from the rest (stream `probe_items`). The stem is the first four whitespace-separated words. An arm with fewer than eight words is skipped and counted. Ten items to a call.
- `token_f1`: lower-case both texts, replace every character that is not a letter, a digit or a space with a space, split on spaces, and compute F1 over the two multisets of tokens. Two empty texts score 0.
- Familiarity: every arm of the 300 units, shuffled (stream `probe_items`), 30 to a call.
- Pairs: every scored contrast of the 300 units, shuffled, 10 to a call.

Exact copy:

`COMPLETION_SYSTEM`: `Reply with one JSON object and nothing else.`
`COMPLETION_TEMPLATE`: `Below are the first four words of headlines published on a news and entertainment site between 2013 and 2015. For each, write the rest of the headline as you believe it was published.` then the numbered stems, then `Reply as {"completions": [...]} with exactly {n} strings, one for each line in order.`

`FAMILIARITY_SYSTEM`: the same as `COMPLETION_SYSTEM`.
`FAMILIARITY_TEMPLATE`: `Below are headlines. For each, give a number from 0 to 100 for how sure you are that you have seen this exact headline before.` then the numbered headlines, then `Reply as {"seen": [...]} with exactly {n} numbers, one for each headline in order.`

`PAIR_SYSTEM`: the same.
`PAIR_TEMPLATE`: `Upworthy tested pairs of headlines for the same story between 2013 and 2015. For each pair below, say which headline had the higher click rate.` then per pair `{i}. A: <headline>` and `   B: <headline>`, then `Reply as {"winners": [...]} with exactly {n} entries, each "A" or "B".`

Measures: `completion.f1_winner`, `completion.f1_other`, `completion.f1_difference` (paired within unit, units with both arms kept), `completion.n_pairs`, `completion.n_skipped`; `familiarity.direction_accuracy` of "the higher rating wins" on the probe units' contrasts (ties half), `familiarity.agreement_with_panel`; `pairs.direction_accuracy`; each with `n`.

- [ ] **Step 1: Write the failing tests:**

```python
def test_token_f1():
    assert token_f1("the cat sat", "The cat, sat!") == 1.0
    assert token_f1("a b", "c d") == 0.0 and token_f1("", "") == 0.0
    assert token_f1("a b c d", "a b") == pytest.approx(2 * 0.5 * 1.0 / 1.5)

def test_the_winner_is_the_arm_with_the_highest_click_rate(world):
    items = completion_items(world.arms, probe_units(world.arms, 20))
    w = items[items.role == "winner"].merge(world.arms, on="arm_id")
    best = world.arms.assign(rate=lambda d: d.clicks / d.impressions).sort_values(["rate", "arm_id"], ascending=[False, True]).groupby("unit_id").arm_id.first()
    assert (w.arm_id.values == best[w.unit_id].values).all()

def test_short_headlines_are_skipped_and_counted(world):
    items = completion_items(world.arms, list(world.units_with_a_short_headline))
    assert items.skipped.any() and (items[~items.skipped].stem.str.split().str.len() == 4).all()

def test_the_stem_and_the_rest_rebuild_the_headline(world):
    items = completion_items(world.arms, probe_units(world.arms, 20)).merge(world.arms, on="arm_id")
    ok = items[~items.skipped]
    assert ((ok.stem + " " + ok.rest).str.split().str.join(" ") == ok.headline.str.split().str.join(" ")).all()

def test_only_the_pair_prompt_names_the_publisher():
    assert "Upworthy" in PAIR_TEMPLATE
    assert "upworthy" not in (COMPLETION_TEMPLATE + FAMILIARITY_TEMPLATE).lower()

def test_the_probe_set_repeats_and_holds_300(world_large):
    a = probe_units(world_large.arms)
    assert a == probe_units(world_large.arms) and len(a) == 300 == len(set(a))

def test_a_model_that_knows_the_winner_scores_one_on_pairs(world):
    assert probe_measures_for_oracle_pairs(world)["pairs"]["direction_accuracy"] == 1.0
```

- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_readers_probes.py`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit**: "Add three probes that describe what the model may recall".

### Task 10: Measures and the report

**Files:**
- Create: `src/mootcourt/simulators/readers/measures.py`
- Test: `tests/test_readers_measures.py`

**Interfaces:**
- Consumes: `contrasts`, `feeds`, the per-row `correct` columns of every method, `mootcourt.decision_value` (`budget_k`, `_top_k_value`, `_matched_value`).
- Produces:
  - `paired_difference(contrasts, a: np.ndarray, b: np.ndarray, block_of_row: pd.Series, *, family: int | None, B: int = 500) -> dict` with `estimate` (mean of `a` minus mean of `b`), `n`, `lo`, `hi` (the 5th and 95th percentiles over resamples of whole blocks, `rng("bootstrap", 0)`), `se`, `adjusted_lo`, `adjusted_hi` (`estimate` minus and plus `se * scipy.special.ndtri(1 - 0.05 / family)`, absent when `family` is None), `family_size`, `test_lo`, `test_hi` (resampling tests, `rng("bootstrap", 1)`), `verdict` (`"above"`, `"contains_zero"` or `"below"` from the adjusted interval; absent when `family` is None).
  - `accuracy(contrasts, correct, mask=None) -> dict` with `accuracy`, `n`, `ties`, `no_reader`.
  - `ranking(contrasts, diff: pd.Series, frac: float = 0.25) -> dict`: per origin, a test's score is the largest `diff` among its contrasts (NaN as minus infinity), its value is the largest `max(y, 0)`, and its arm count is its number of scored contrasts; returns the captured share pooled over origins for the panel, the arm-count rule and the matched random order, the two differences, and intervals that resample tests within each origin (`rng("bootstrap", 2)`).
  - `model_report(...) -> dict` and `agreement_report(per_model: dict[str, pd.DataFrame]) -> dict`.

Report keys of `simulated-readers-<model>-20261106-2dc461f52ea4.json` (names are fixed here because tables and `% src:` lines will cite them):

```
model, primary (true for claude-opus-5-5), seed, commit, counts.{units, tests, contrasts, blocks, feeds, calls_planned, calls_ok, calls_invalid, calls_refusal},
tool_versions.{<version>: count}, reported_models.{<id>: count},
baselines.{always_reference, text_lr, ceiling}.accuracy, baselines.text_lr_minus_always_reference (paired_difference, family None),
plain.{accuracy, n, ties, no_reader, accuracy_minus_half, decisive.accuracy, decisive.n, split_half.agree_share},
readings.plain_minus_always_reference, readings.weights_minus_plain, readings.text_with_panel_minus_text (each a paired_difference; family 3),
methods.<name>.{accuracy, decisive_accuracy, minus_plain, minus_always_reference} for name in
    direction_map, reader_weights, audience_matching, error_correction, text_with_panel, examples_in_prompt, audience_brief,
methods.direction_map.brier_skill, methods.reader_weights.fits.<origin>, methods.audience_brief.notes.<origin> (word count and SHA-256, not the text),
by_origin.<origin>.{plain, always_reference, reader_weights}.accuracy, ranking.{panel, arm_count, matched_random, panel_minus_arm_count, panel_minus_matched_random},
probes.{completion, familiarity, pairs}
```

For Sonnet and Haiku the three readings carry `family_size` 3 and the adjusted bounds as well, and no `verdict` key: the paper gives them no verdict word.

`simulated-readers-agreement-20261106-2dc461f52ea4.json`: for each pair of models, the share of contrasts on which the plain panels agree in direction (ties left out, with their count).

- [ ] **Step 1: Write the failing tests:**

```python
def test_block_resampling_is_wider_than_row_noise_when_a_block_moves_together(clustered):
    d = paired_difference(clustered.contrasts, clustered.a, clustered.b, clustered.block, family=3)
    assert d["hi"] - d["lo"] > 3 * clustered.iid_width and d["family_size"] == 3

def test_adjusted_bounds_use_the_family_of_three():
    d = paired_difference(simple.contrasts, simple.a, simple.b, simple.block, family=3)
    z = scipy.special.ndtri(1 - 0.05 / 3)
    assert d["adjusted_hi"] == pytest.approx(d["estimate"] + z * d["se"]) and z == pytest.approx(2.128, abs=1e-3)

@pytest.mark.parametrize("shift, verdict", [(0.3, "above"), (0.0, "contains_zero"), (-0.3, "below")])
def test_verdict_reads_the_adjusted_interval(shift, verdict):
    w = planted(shift)
    assert paired_difference(w.contrasts, w.a, w.b, w.block, family=3)["verdict"] == verdict

def test_no_family_means_no_verdict_and_no_adjusted_bounds():
    d = paired_difference(simple.contrasts, simple.a, simple.b, simple.block, family=None)
    assert "verdict" not in d and "adjusted_lo" not in d

def test_intervals_repeat():
    assert paired_difference(simple.contrasts, simple.a, simple.b, simple.block, family=3) == paired_difference(simple.contrasts, simple.a, simple.b, simple.block, family=3)

def test_ranking_by_the_planted_effect_beats_the_arm_count_rule(planted_ranking):
    r = ranking(planted_ranking.contrasts, planted_ranking.diff)
    assert r["panel"]["estimate"] > r["arm_count"]["estimate"] and 0 <= r["matched_random"]["estimate"] <= 1

def test_ties_and_missing_readers_are_counted(simple):
    a = accuracy(simple.contrasts, simple.correct_with_two_ties_one_missing)
    assert (a["ties"], a["no_reader"]) == (2, 1)

def test_only_the_primary_model_gets_a_verdict(tiny_run):
    assert "verdict" in model_report(tiny_run, "claude-opus-5-5")["readings"]["plain_minus_always_reference"]
    assert "verdict" not in model_report(tiny_run, "claude-haiku-5-5")["readings"]["plain_minus_always_reference"]
```

- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_readers_measures.py`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Commit**: "Add the measures and the report of the simulated readers".

### Task 11: The script and the end-to-end test

**Files:**
- Create: `scripts/simulated_readers.py`
- Create: `docs/simulated-readers.md`; modify `docs/method.md` (one new numbered decision that points to the spec and this plan) and the documentation index if `tests/test_docs_site.py` requires an entry
- Test: `tests/test_simulated_readers_script.py`

**Interfaces:**
- Consumes: everything above.
- Produces the command line:
  - `plan --ledger L --scores S --out DIR`: writes `arms.parquet`, `contrasts.parquet`, `feeds.parquet`, `probes.json`, and `plan.json` with the counts per origin, the exact count of calls per model and per kind (`plain`, `examples`, `brief_note`, `brief`, `probe_completion`, `probe_familiarity`, `probe_pairs`) and the SHA-256 of each file. With `--expect-archive-counts` it stops with exit code 2 unless the counts equal the table of this plan (1,771 units, 1,770 tests, 5,966 contrasts, 63 blocks, 308 feeds, and each row).
  - `run --model NAME --plan DIR --transcripts DIR --allow-model-calls [--kinds ...] [--workers 4] [--program claude]`: makes the calls not yet stored, in the order `plain`, `brief_note`, `examples`, `brief`, the probes. Without `--allow-model-calls` it exits with code 2 before anything else. It stops with exit code 3 after five transport failures in a row and prints the count outstanding. `NAME` must be one of the three models unless `--program` is given.
  - `canary --model NAME --transcripts DIR --allow-model-calls`: one call on a synthetic feed of five invented headlines with the tool's start record captured (Task 13 fixes how); writes `canary-<model>.json`; exits with code 4 if the record lists any tool or any server.
  - `score --plan DIR --transcripts DIR --ledger L --out DIR --commit HASH`: refuses with exit code 5, naming the count outstanding, unless every planned call of all three models is stored; then writes the three model reports and the agreement report. It never calls a model.
- The file names a ledger or scores path may not contain are checked first: a path whose name holds `holdout`, `confirmatory` or `undeployed` is refused, as the other scripts do.

- [ ] **Step 1: Write the failing tests** (the fake tool of Task 4 plays the model; a synthetic ledger with a planted text effect plays the archive):

```python
def test_run_refuses_without_the_flag(tmp_path, planned):
    r = run_script("run", "--model", "claude-opus-5-5", "--plan", planned, "--transcripts", tmp_path)
    assert r.returncode == 2 and not any(tmp_path.iterdir())

def test_score_refuses_while_calls_are_outstanding(tmp_path, planned, one_model_done):
    r = run_script("score", "--plan", planned, "--transcripts", one_model_done, "--ledger", LEDGER, "--out", tmp_path, "--commit", "x")
    assert r.returncode == 5 and "outstanding" in r.stderr and not list(tmp_path.glob("*.json"))

def test_planted_effect_is_recovered_end_to_end(tmp_path, planned, fake_that_reads_the_planted_word):
    for m in MODELS:
        assert run_script("run", "--model", m, "--plan", planned, "--transcripts", tmp_path / "t", "--allow-model-calls", "--program", fake_that_reads_the_planted_word).returncode == 0
    assert run_script("score", "--plan", planned, "--transcripts", tmp_path / "t", "--ledger", LEDGER, "--out", tmp_path / "o", "--commit", "x").returncode == 0
    rep = json.loads(next((tmp_path / "o").glob("simulated-readers-claude-opus-5-5-*.json")).read_text())
    assert rep["plain"]["accuracy"] > 0.8 and rep["readings"]["plain_minus_always_reference"]["verdict"] == "above"
    assert rep["counts"]["calls_ok"] == rep["counts"]["calls_planned"]

def test_a_reader_that_answers_at_random_is_not_shown_to_beat_the_baseline(tmp_path, planned, fake_random):
    rep = full_run(tmp_path, planned, fake_random)["claude-opus-5-5"]
    assert rep["readings"]["plain_minus_always_reference"]["verdict"] in {"contains_zero", "below"}

def test_a_second_run_makes_no_call(tmp_path, planned, fake_counting):
    full_run(tmp_path, planned, fake_counting)
    n = fake_counting.calls()
    full_run(tmp_path, planned, fake_counting)
    assert fake_counting.calls() == n

def test_run_stops_after_five_transport_failures(tmp_path, planned, fake_always_limit):
    r = run_script("run", "--model", "claude-opus-5-5", "--plan", planned, "--transcripts", tmp_path, "--allow-model-calls", "--program", fake_always_limit, "--workers", "1")
    assert r.returncode == 3 and fake_always_limit.calls() == 5

def test_plan_is_repeatable_and_makes_no_call(tmp_path):
    a, b = plan_into(tmp_path / "a"), plan_into(tmp_path / "b")
    assert a["sha256"] == b["sha256"] and a["calls"]["per_model"] == sum(a["calls"]["by_kind"].values())

def test_forbidden_file_names_are_refused(tmp_path):
    assert run_script("plan", "--ledger", tmp_path / "upworthy-confirmatory.parquet", "--scores", "s", "--out", tmp_path).returncode != 0
```

- [ ] **Step 2: Run** `uv run pytest -p no:cacheprovider tests/test_simulated_readers_script.py`. Expected: FAIL.
- [ ] **Step 3: Implement** the script. The `brief_note` call of an origin must be stored before any `brief` reader call of that origin is built, since the note is part of that prompt; a note whose status is not `"ok"` stops the run with a message, because 2,860 calls depend on it.
- [ ] **Step 4: Run** again. Expected: PASS.
- [ ] **Step 5: Write** `docs/simulated-readers.md` (what the module does, the three stages, the flag, what the result may and may not be called, a pointer to the spec) and the decision in `docs/method.md`.
- [ ] **Step 6: Run the whole suite**: `nice -n 19 uv run pytest -p no:cacheprovider > "$MOOTCOURT_DATA_ROOT/full-suite-run11.log" 2>&1; tail -5 "$MOOTCOURT_DATA_ROOT/full-suite-run11.log"` (about 50 minutes), then `uv run ruff check src scripts tests`. Expected: no failure. Report any failure by name, including one this work did not cause.
- [ ] **Step 7: Commit**: "Add the script of the simulated readers with its three stages and its manual page".

### Task 12: Review of the branch before any call

- [ ] **Step 1:** Dispatch one fresh reviewer on the most capable model with the spec, this plan and the diff from `main`. It may not read `paper/reviews/`, `.claude/` or `.superpowers/`. Ask it in particular for any path by which an outcome reaches a prompt, a feed or a fit before the visibility rule allows, and for the five lines of Review Focus.
- [ ] **Step 2:** Fix each confirmed finding with a failing test first. Rerun the suite. Commit.

### Task 13: The record before the first call on the archive

Model calls begin in this task, on synthetic headlines only. No `src/` or `scripts/` file changes after its last commit.

- [ ] **Step 1: Settle the flags on synthetic headlines.** With five invented headlines and `--allow-model-calls`, find the flags for which the tool's own start record (from `--output-format stream-json --verbose`) lists no tool and no server, the reply satisfies the schema, and the login works with the smallest `LOGIN_ENV`. Fix `build_command`, `LOGIN_ENV`, `ENVELOPE` and `USAGE_LIMIT_PATTERN`, update the tests of Task 4 to the real envelope, run the suite, and commit. If no set of flags gives an empty tool list and an empty server list, stop and tell the user: the spec's requirement cannot be met.
- [ ] **Step 2: Record the models' knowledge cutoffs.** Open the vendor's public page for each of the three model identifiers and copy each published cutoff, with the page's address and the date read. If a cutoff is not published, write that.
- [ ] **Step 3: Run `plan` on the archive** with `--expect-archive-counts`, writing to `$MOOTCOURT_DATA_ROOT/experiments/run11-simulated-readers/plan`. Expected: exit code 0 and the counts of this plan's table.
- [ ] **Step 4: Check method 5's baseline on the archive.** Run `text_with_panel` with a panel difference of zero and compare `correct_without` with `contrasts.text_lr_correct`. Expected: equal on all 5,966 rows. If it is not, stop: reading 3 has no valid comparison until it is.
- [ ] **Step 5: Run the canary** for each model. Expected: exit code 0 three times.
- [ ] **Step 6: Append a section "Record before the first call" to this plan** holding: the commit of the code, the exact flags, the tool version, the three cutoffs, the counts and the SHA-256 values that `plan` printed, the exact number of calls per model and in all, and the three start records. Commit and push the branch. This commit is the record that everything in the spec's "Fixed before the first call" was fixed.

### Task 14: The run

- [ ] **Step 1:** `git status --short src scripts` must print nothing. Record the commit.
- [ ] **Step 2:** For each model, `nice -n 19 uv run python scripts/simulated_readers.py run --model <id> --plan ... --transcripts ... --allow-model-calls`, in the background, with the log on the data root. On exit code 3 wait for the limit to reset and start it again; it resumes. Do not read any reply for its content while the run is going.
- [ ] **Step 3:** When all three exit with code 0, run `score` into `$MOOTCOURT_DATA_ROOT/reports/`.
- [ ] **Step 4:** Assemble `paper/data/run11-simulated-readers/`: the four reports, `plan.json`, the three canary files, and a `README.md` that says this is a side run and run 9 remains the current main run, gives the commit, the dates, the tool versions, the count of replies per version, the flags, the start records, the checksums of the transcript archive, and every deviation. `CLAUDE.md` says the highest numbered run is current; add one sentence there naming run 11 as a side run.
- [ ] **Step 5:** Report the numbers to the user as they are. No method changes because of them. Commit.

### Task 15: Prior work

- [ ] **Step 1:** Open and read the journal article on weights over prompts and profiles fitted to aggregate benchmarks (DOI 10.1287/mksc.2024.0983). Searches and fetches carry no paper title, name, repository name or email address. If it cannot be opened, tell the user, and write none of the three "to our knowledge" points until it has been read.
- [ ] **Step 2:** For each work the new section will cite, open the source, check authors, title, venue and year, and only then add its entry to the bibliography.
- [ ] **Step 3:** Decide which of the three points survive the reading, and note the reason for each in the pull request.

### Task 16: The paper

**Files:**
- Create: `paper/sections/simulated-readers.tex`, a group module under `paper/summary_tables/` for three tables (the three readings by model; the seven methods by model; the probes), with tests beside the existing table tests
- Modify: `paper/main.tex`, `paper/sections/abstract-tmlr.tex`, `paper/dist/metadata.md`, `paper/sections/related-work.tex`, `paper/sections/limitations.tex`, `paper/sections/analysis-history.tex`, `paper/sections/conclusion.tex`, `paper/sections/appendix.tex`, `paper/sections/reproducibility.tex`, `paper/reviews/claims.md`, `paper/build_tables.py` if a run folder must be named

Fixed wording (from the spec; the three choices are read from Opus's `verdict` keys in the order above, contains, below):

> On the headline-only tests of the exploratory split, with nothing hidden from the model's training and contamination not excluded, a panel of ten simulated readers {matched the observed direction more often than always choosing the earliest arm | is not shown to match the observed direction more often than always choosing the earliest arm | matched the observed direction less often than always choosing the earliest arm}. Aligning the readers with earlier results {raised | is not shown to raise | lowered} that share, and adding the simulated readers to a classifier fitted on earlier tests {raised | is not shown to raise | lowered} its share of directions matched.

Contribution item: "A time-ordered test of simulated readers, plain and aligned with earlier tests by seven methods, under a fixed rule for what an alignment may see."

- [ ] **Step 1:** Write the table builders with tests first (a fixture report with known values; the test asserts each printed cell against its key). Build with `make tables`; `git status --short paper/tables` shows only the three new tables.
- [ ] **Step 2:** Write the section: the design in brief, the two body tables, the limits. Every line with a number has its `% src:` block naming the run 11 report and key. At most two numbers to a sentence.
- [ ] **Step 3:** Make the other edits the spec lists under "In the paper": the fifth contribution and "five contributions"; the abstract finding in both builds and in `metadata.md`, which must stay under 1,920 characters and now has five to spare, so other wording there is trimmed; related work with the sentence "The simulated readers of Section N are scored on direction only and are not that forecast."; the limitations paragraph; the item in the appendix on which readings were fixed before their results, under "Added after results of this work had been seen, with the reading written down before the analysis's own result"; the conclusion; the appendix with prompts, profiles, probes and remaining measures; how the calls were made, in reproducibility.
- [ ] **Step 4:** Add a row to `paper/reviews/claims.md` for every new claim and update its footer.
- [ ] **Step 5:** Run the `paper-check` skill in full. Expected: both builds compile, 0 unmatched and 0 unresolved numbers, the claims audit exits 0, the paper tests pass.
- [ ] **Step 6:** Dispatch one fresh reader with the `paper-review` brief on the new section and the changed passages. Apply confirmed findings.
- [ ] **Step 7:** Commit. Open a pull request. Do not merge without green CI and the user's word.

## Self-review notes

- Spec coverage: reader and feed (Tasks 2, 3); card (3); rows and arms (1); blocks (2); panel, ties, missing (5); seven methods (6, 7, 8); baselines and measures (1, 10); wording (16); probes (9); the call (4, 13); code layout and flag (4, 11); run order (12 to 14); paper (16); prior work (15); "Fixed before the first call" (this plan plus the record of Task 13).
- Two items of "Fixed before the first call" cannot be exact until code exists: the checksums and the tool's exact flags. Task 13 fixes both in a commit that precedes the first call on an archive headline.
