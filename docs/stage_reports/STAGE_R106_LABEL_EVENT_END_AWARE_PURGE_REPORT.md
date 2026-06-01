# Stage R106 Label Event-End-Aware Purge Report

Date: 2026-05-31

## Scope

WPR106-35 closed `ISSUE-R106-011` without adding strategies, filters, models,
live/paper behavior, order placement, promotion logic, or candidate-ready
claims.

## Changes

- Added `LabelSpec` to `src/tradingbotsuite/backtesting/splits.py`.
- Updated walk-forward split builders to support event-end-aware purge using
  label/event end time plus embargo milliseconds.
- Kept fixed-bar purge as an explicitly identified fallback when no event-end
  metadata is available.
- Added explicit safe `train_indices` for event-end-aware splits and compact
  SHA-backed train-index summaries in split payloads.
- Updated train-only feature transforms, HMM materialization, and KNN
  materialization to honor explicit event-safe train indices.
- Stamped discovery directional labels with `label_event_end_time_ms` and wired
  discovery split building through `LabelSpec`.
- Updated historical-cycle split manifests with purge-method counts,
  event-end columns, embargo millisecond values, and compact train-index
  evidence.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_splits.py tests\features\test_feature_builders.py::test_train_only_split_transform_honors_event_safe_train_indices -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_hmm_materialization.py::test_hmm_materialization_honors_event_safe_train_indices tests\research_discovery\test_hmm_materialization.py tests\research_discovery\test_knn_study.py tests\research_discovery\test_discovery_runner.py::test_discovery_label_splits_stamp_event_end_and_use_label_aware_purge -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py::test_full_cycle_synthetic_writes_required_research_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Results:

- Compile passed.
- Backtesting plus focused feature transform: 10 passed.
- Focused research discovery: 35 passed.
- Historical-cycle reference: 1 passed.
- Contracts: 430 passed.
- Diff check passed with line-ending warnings only.

## Evidence

- Event-end-aware purge excludes overlapping and missing event-end train rows.
- Positive embargo is converted from bars to milliseconds before purge.
- Missing required event-end columns fail closed.
- Discovery labels carry event-end timestamps and produce
  `purge_method: label_event_end_time` splits.
- Historical-cycle split manifests identify event-end purge and compact
  train-index evidence.

## Research Status

No candidate-ready evidence was created. Research outputs remain
`research_only`, `observe_only`, and `promotion_ready: false`. Zero eligible
candidates remains valid evidence.

## Remaining Blockers

- `ISSUE-R106-012`: lower-timeframe entry pricing is labeled but not used.
- `ISSUE-R106-013`: local credential files can imply Hyperliquid live/testnet
  enablement.
- `ISSUE-R106-014`: runtime artifact validation is not mode-aware and not
  fail-closed for unknown manifests.
