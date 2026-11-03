# FAQ

**Does it replace running the experiment?** No. The card helps you choose which tests to run and how large to make them, and the
result of the live test is what counts.

**Why does the card often abstain?** Because declining is the right answer when the ledger holds little support for the
proposal, when the proposal is unlike every precedent, or when the recent forecasts have been unreliable. The abstention rate
is reported next to every score.

**Why is P2 sometimes no better than P1?** Weighing precedents helps only if similar tests had similar effects. When they did
not, the admission guard sets the weight on precedents to zero for that cell and P2 equals P1. The reports say how often.

**How many tests do I need?** The gates in the report give the number of scored tests at which a Brier skill difference of 0.20
or 0.10 can be told from zero, at two power targets. Below them, comparisons are reported as undecidable.

**Does anything leave my machine?** No. No default code path calls the network or a model. A response simulator is an outside
program that you configure, and it receives aggregate inputs only.

**Can I use my own agent for a second opinion?** Yes. See [Attach a simulation agent](simulators.md). It starts with a weight of
zero and earns a weight only by beating the model on later origins.

**Where do the numbers in the README come from?** From the reports in the data root, refreshed by a script that also checks they
are current.
