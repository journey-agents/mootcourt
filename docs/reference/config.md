# Configuration

Settings live in `mootcourt.toml` in the working directory. Every key is optional. `moot init` writes the file with its
defaults. A malformed file stops the command with an error that names the file. A test checks that this page lists every key
the code reads, with the defaults the code uses.

## Keys

| Table | Key | Type | Default | Meaning |
|---|---|---|---|---|
| `[project]` | `name` | text | empty (`moot init` writes the folder name) | Project name shown by `moot doctor`. |
| `[storage]` | `data_root` | path | none: folders in the working directory | Folder that holds data, models, reports, cards and caches. `~` is expanded. The environment variable `MOOTCOURT_DATA_ROOT` wins over it. |
| `[cells]` | `names` | list of text | empty | Cells the program forecasts. `moot doctor` checks that each has at least 20 admitted rows. Informational: no command refuses a cell that is not listed. |
| `[decision]` | `action_threshold` | number in (0, 1) | 0.35 | Probability of a significant positive result above which the team would act. The card's robustness check and the instability trigger ask whether the forecast stays on one side of it. Read by `moot card`, the service and the MCP server. |
| `[gate]` | `target_power` | number in [0.5, 1) | 0.90 | Power of the release gate. `moot simulate power` uses it; the reports read the gate sizes at this target. |
| `[service]` | `url` | URL | none | Address of a running service. `moot doctor` checks it when set. Only a loopback address is contacted. |
| `[simulators.NAME]` | `adapter` | text | none, required | `stdio`, `http`, `recorded` or `builtin`. |
| `[simulators.NAME]` | `command` | list of text | none | The program of a `stdio` provider, run without a shell in the folder of the config file. Required for `stdio`. |
| `[simulators.NAME]` | `url` | URL | none | The address of an `http` provider. Required for `http`. A host that is not loopback needs `--allow-remote` on the command line. |
| `[simulators.NAME]` | `path` | path | none | The records file of a `recorded` provider. Required for `recorded`. |
| `[simulators.NAME]` | `name` | text | the table name | For `builtin`: which built-in provider (`null` or `heuristic`). |
| `[simulators.NAME]` | `version` | text | `0` | Version of the agent. A weight belongs to one version. |
| `[simulators.NAME]` | `knowledge_cutoff` | date | none, required for `stdio` and `http` | The date the agent's knowledge ends. Origins before it are flagged as possibly contaminated. |
| `[simulators.NAME]` | `cost_model` | text | `free` | `free`, `per_call` or `per_token`. |
| `[simulators.NAME]` | `description` | text | the adapter and the name | Shown by `moot simulators list`. |
| `[simulators.NAME]` | `provider_id` | text | the table name | Identifier written into every record. |
| `[simulators.NAME]` | `time_cap_s` | number | 30 | Wall-clock cap in seconds for one call. |
| `[simulators.NAME]` | `env` | list of text | empty | Names of environment variables the agent may see. Every variable that looks like a credential is removed unless listed here. |
| `[simulators.NAME]` | `enabled` | true or false | true | Set to false to leave the provider out without deleting its table. |

A table may not reuse the name of a built-in provider (`null`, `heuristic`) unless its adapter is `builtin`. The agent's
rules (what it receives, what it may run, how its environment is cleaned) are in [Simulators](../simulators.md).

A minimal file:

```toml
[project]
name = "checkout-program"

[storage]
data_root = "/Volumes/big/mootcourt-data"

[cells]
names = ["checkout_conversion", "revenue_per_user"]

[decision]
action_threshold = 0.35

[gate]
target_power = 0.90
```

## Environment

| Variable | Meaning |
|---|---|
| `MOOTCOURT_DATA_ROOT` | The data root. It wins over `data_root` in the file. In `make`, it wins over an untracked `.env` file. |

## Layout under the data root

| Folder | Holds |
|---|---|
| `data/raw` | Downloaded archives, checked against pinned checksums. |
| `data/ledger` | The ledger and its immutable snapshots. |
| `models` | Fitted bundles and the registry. |
| `reports` | Backtests, gates, reliability reports, benchmark cards and scale runs. |
| `cards` | Frozen cards and their outcomes. |
| `cache` | Simulator results. |
| `experiments` | Ablations, challengers and scale runs. |

`moot storage` prints each folder, its size and the free space of its volume. Large files belong under the data root, never
inside the repository. A data root on a volume formatted as exFAT works: no symlinks, hard links or permission changes are
needed.
