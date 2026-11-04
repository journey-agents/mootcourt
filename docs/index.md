# Moot Court

Moot Court argues the next experiment from precedent before the trial. A ledger of concluded tests is the case law. A
ladder of predictors weighs the precedents. A card states an opinion in numbers, or declines to rule, and every opinion is
scored against what the live test later showed.

The card prioritizes and sizes the test. The live test decides. Moot Court never touches a ship, allocation or stopping rule.

**Who it is for.** A data scientist or experimentation team with an archive of concluded A/B tests, planning the next ones. You do not need user-level data: for each experiment, variant and metric, the effect, its standard error, the units per arm and the dates are enough.

## Where to start

| If you want to | Read |
|---|---|
| Get a first card in about ten minutes, install included | [Tutorial 1: your first card](tutorials/01-first-card.md) |
| Use your own archive | [Tutorial 2: your own archive](tutorials/02-your-own-archive.md) |
| Learn the vocabulary | [Concepts](concepts.md) and its glossary |
| Reproduce the published study | [Tutorial 3](tutorials/03-reproduce-upworthy.md) and the [Results](results.md) |
| Keep it current every week | [Tutorial 4](tutorials/04-weekly-loop.md) and [Operations](operations.md) |
| Serve cards to other tools or an assistant | [Tutorial 5](tutorials/05-serve-http-and-mcp.md) |
| Attach an outside agent as a second opinion | [Tutorial 6](tutorials/06-simulation-agent.md) and [Simulators](simulators.md) |
| Score your program on a standard protocol | [Run the benchmark](benchmark.md) |
| Look up a command, a setting or a file format | [Command guide](commands.md), [Command line](reference/cli.md), [Configuration](reference/config.md), [Ledger format](ledger-format.md), [Python API](reference/api.md) |
| Fix a problem | [Troubleshooting](troubleshooting.md) and the [FAQ](faq.md) |
| Understand what was decided and why | [Method](method.md), [Limitations](limitations.md), [Landscape](landscape.md) |

## What the manual contains

- **Tutorials** take you through one task each, with every command, its real output and what to look at in it. A test runs every command in them.
- **Concepts** explains the flow with a diagram and defines every term before the pages use it.
- **Reference** lists every command, option and configuration key. The command guide adds, for each command, what it reads and writes, an example and the errors you are likely to meet.
- **Method, Limitations and Results** say what was built, what the numbers show and what they do not.

## Install

```
pip install -e .
moot --version
```

Python 3.11 or newer. Install from a clone on your internal disk; an external exFAT volume breaks the environment (see [troubleshooting](troubleshooting.md#working-from-a-clone-on-an-exfat-volume)). The package makes no network call and no model call in any default code path.
