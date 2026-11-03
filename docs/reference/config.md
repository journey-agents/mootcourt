# Configuration

Settings live in `mootcourt.toml` in the working directory. Every key is optional. `moot init` writes the file with its
defaults.

| Table | Key | Meaning | Default |
|---|---|---|---|
| `[project]` | `name` | Project name shown by `moot doctor`. | the folder name |
| `[storage]` | `data_root` | Folder that holds data, models, reports, cards and caches. | none: folders in the working directory |
| `[cells]` | `names` | Cells the program forecasts; `moot doctor` checks them. | none |
| `[decision]` | `action_threshold` | Probability above which the team would act; used by the card's robustness check. | 0.35 |
| `[gate]` | `target_power` | Power at which gate sizes are read. | 0.90 |
| `[service]` | `url` | Address of a running service; `moot doctor` checks it. | none |
| `[simulators.NAME]` | see [Attach a simulation agent](../simulators.md) | One outside agent. | none |

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
inside the repository.
