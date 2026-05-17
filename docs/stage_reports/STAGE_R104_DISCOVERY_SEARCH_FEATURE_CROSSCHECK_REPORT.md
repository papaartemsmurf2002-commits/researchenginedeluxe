# Stage R104 Discovery Search Feature Crosscheck Report

Date: 2026-05-17
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR104-05-discovery-search-feature-crosscheck.md`

## Scope

This pass crosschecked the durable R104 discovery search path: exact sweep
combination math, generated trial identity, KNN threshold payload wiring,
feature-column-set materialization, compact durable fixture behavior, and
focused test coverage.

No live execution, promotion, runtime-mode mutation, order placement, sizing
behavior, or candidate-pack writing was added.

## Changes

- Exact discovery search specs now reject duplicate feature-column-set IDs and
  duplicate search-dimension values before trial generation.
- Generated real-discovery candidate IDs are now parameter-identity based
  rather than shuffled-order based, so the same payload keeps the same candidate
  ID across RNG seeds for a fixed run.
- Real-trial execution failures now preserve the original KNN/search payload
  plus regime-mode truthfulness fields in the failed trial record.
- The runner now derives an effective finite-variant feature column list before
  HMM/KNN evaluation. Compact durable runs no longer present all-NaN long-window
  columns as active KNN dimensions.
- Trial records now expose configured feature columns, effective feature
  columns, and pruned feature-column count.
- The real-discovery score policy version was bumped so incomplete runs with
  older feature-column semantics cannot be resumed into mixed evidence.
- Focused regression coverage now proves exact R104 dimensions, miniature
  exhaustive generation uniqueness, sparse sample uniqueness, KNN threshold
  rejection reasons, runner payload propagation, durable feature preflight, and
  failed-trial audit payload preservation.
- The removed-source boundary test no longer trips over a literal legacy token
  embedded in the operator UI test fixture.

## Crosscheck Results

BTC and ETH exact durable configs each cover 570240 planned combinations:

- `feature_column_set_id`: 2
- `hmm_state_count`: 1
- `hmm_posterior_threshold`: 1
- `hmm_entropy_threshold`: 1
- `label_horizon`: 3
- valid `k` / `min_neighbor_count` pairs: 22
- `distance_metric`: 3
- `probability_threshold`: 6
- `expected_value_threshold`: 4
- `min_neighbor_agreement`: 5
- `min_distance_quality`: 3
- `vote_margin_threshold`: 4
- `regime_mode`: 1

The selected compact durable feature sets materialize on both BTCUSDT and
ETHUSDT public-archive fixtures:

- `price_trend_vol` effective columns:
  `log_return_1`, `log_return_4`
- `compact_wt3d_base` effective columns:
  `log_return_1`, `log_return_4`, `wt3d_normal`, `wt3d_slope`

Long-window configured columns remain recorded as configured columns but are
pruned from compact-fixture KNN/HMM evaluation when they have no finite variant
values.

## Residual Limits

The branch is wired for durable exact discovery, but candidate-ready empirical
completion is still blocked by `ISSUE-R104-001`: the checked durable fixtures
have only 32 primary 15m bars per symbol. They are valid for screening and
plumbing evidence, not for brute-force candidate-ready claims. Expanded durable
primary-bar fixtures remain the next empirical requirement.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\features -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
```

Results:

- Compile passed.
- `tests/research_discovery`: 174 passed.
- `tests/features`: 29 passed.
- `tests/contracts`: 425 passed.
- `tests/tradingbotsuite/test_operator_ui.py`: 43 passed.
- Full suite: 1366 passed, 1 skipped.
- `git diff --check` passed with line-ending warnings only.
