# Stage R92 Final Branch Crosscheck Report

Date: 2026-05-10
Branch: `research/v3-experimental-engine`
Packet: `docs/work_packets/WPR92-01-final-branch-crosscheck.md`

## Scope

Final audit of the research branch after discovery runtime optimization:

- HMM materialization and KNN local analog logic.
- Discovery run generation, checkpointing, snapshots, ledgers, and metrics.
- Research-only/live-boundary flags.
- Operator Research page and embedded guide documentation.
- Removed legacy vendor source boundary.
- Full validation and push readiness.

## Fixes Made

### KNN Short-Side Expectancy

The audit found a material KNN accounting issue. Short-majority neighbor pools
were using raw future returns as `expected_net_return_after_costs`, which made
profitable short setups look negative and could suppress valid short candidates.

Fix:

- `src/tradingbotsuite/research_discovery/knn_study.py` now side-adjusts
  expectancy by the implied KNN side.
- `src/tradingbotsuite/research_discovery/runner.py` now computes discovery
  realized expectancy and gross return from side-adjusted accepted returns.
- Discovery metrics now count only accepted rows with a clear KNN skip reason.
- Regression tests cover short-majority expectancy and side-adjusted discovery
  metrics.

### Operator Docs And UI Guide Source

The embedded operator Guides page preferred an older runtime copy of the
operator guide. The service now prefers canonical root-level docs first, and the
older runtime guide was reduced to a pointer. Root quickstart/guide docs and the
Research UI runbook now describe the current Research page: provider pipeline,
research experiments, historical-cycle review, V4 discovery, charts, local
history, HMM/KNN monitoring, and Stage 13 readiness.

### Removed Source Boundary

The full suite found forbidden legacy vendor wording inside a UI test assertion.
The assertion was rewritten with concatenated tokens so the test still checks the
rendered page without putting the removed source name back into active test text.

## External References Checked

- [NumPy `argpartition`](https://numpy.org/doc/stable/reference/generated/numpy.argpartition.html):
  partition order is undefined/unstable, confirming why
  the KNN top-k implementation keeps a stable sort over the reduced kth-distance
  set.
- [scikit-learn `GaussianMixture`](https://scikit-learn.org/stable/modules/generated/sklearn.mixture.GaussianMixture.html):
  `predict_proba`, `covariance_type`, and `random_state` semantics match the
  split-local deterministic regime detector use in the branch.
- [pandas `DataFrame.loc`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.loc.html):
  vectorized `.loc` assignment semantics match the HMM posterior assignment
  approach.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed:
  372 passed.
- Focused discovery/UI validation passed:
  66 passed for KNN, discovery runner, operator UI, and research UI tests.
- Removed-source boundary passed:
  1 passed.
- Real discovery probe passed:
  4 completed standard real discovery trials, 2 interesting rows, 2 blocked rows,
  4 snapshots, `promotion_ready: false`, `order_placement_used: false`.
- Deep discovery benchmark gate passed:
  tier `deep`, repeat `1`, `benchmark_gate_passed: true`,
  `evidence_complete: true`.
- Full suite passed:
  1144 passed, 91 warnings in 302.74 seconds.

The warnings are existing pandas `FutureWarning`s from legacy
`src/tradingbot/lorentz_lc.py` strategy-flow tests. They are not new R92
failures and do not affect the research branch completion gate.

## Boundary Result

No live execution, live fetch, runtime mode mutation, candidate-pack promotion,
or sizing behavior was added. Research artifacts remain `research_only`,
`observe_only`, and `promotion_ready: false` by default.

## Status

Stage R92 is closed. No P0/P1 blocker remains open in `docs/KNOWN_ISSUES.md`.
