# Stage R77 WT/KNN Strategy Candidate Integration Report

Date: 2026-05-07
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR77-01-wt-knn-strategy-candidate-integration.md`

## Summary

WPR77 is complete. Discovery KNN predictions can now be attached to a
historical-cycle `features_perp_context_v2` frame through an explicit
materialized prediction overlay, and the updated frame identity is used by
candidate backtests. The existing `hmm_knn_local_analog_filter_v2` strategy now
emits executable active signals through the standard strategy/backtest contract.

## Implemented

- Added `features.materialized_prediction_overlays` to historical-cycle specs.
- Added historical-cycle overlay loading after registered feature
  materialization and before candidate backtests.
- Validated overlay paths, research-only manifest flags, approved HMM/KNN
  columns, row-count alignment, one-to-one join keys, and accepted-neighbor
  split safety.
- Updated feature-build manifest records with overlay evidence,
  post-overlay feature-frame hashes, and materialized prediction columns.
- Added discovery-side strategy accounting for raw accepted KNN rows, plugin
  signals, backtest-executable signals, filter blocks, and optional executed
  trade counts.
- Added research-only accounting artifacts:
  `strategy_accounting_manifest.json` and `strategy_signals.parquet`.
- Corrected `hmm_knn_local_analog_filter_v2` active signals to leave
  `skip_reason` empty so they are executable by the existing backtest filter.

## Boundary Evidence

- No live adapters, order-placement paths, runtime mode changes, promotion
  behavior, candidate-pack bridge behavior, sizing, or operator UI behavior were
  added.
- Overlay artifacts remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Checked BTCUSDT/ETHUSDT cycle configs were not changed.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- Compile passed.
- `tests\research_discovery`: 35 passed.
- `tests\contracts\test_strategy_contracts.py`: 267 passed.
- `tests\contracts\test_research_cycle_contract.py`: 30 passed.
- `tests\contracts`: 372 passed.
- Temp historical-cycle overlay smoke produced HMM/KNN aggregate trade counts
  and wrote a feature build manifest with
  `materialized_registered_feature_sets_with_prediction_overlays`.

