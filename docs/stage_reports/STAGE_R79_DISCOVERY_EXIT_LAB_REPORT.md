# Stage R79 Discovery Exit Lab Report

Date: 2026-05-08
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR79-01-discovery-exit-lab.md`

## Summary

WPR79 is complete. The discovery package now has a research-only exit lab that
compares exit-policy families only after a fixed-holding entry candidate meets
configured trade-density floors. The lab consumes existing ranking/evidence rows
and does not add or change backtest execution policies.

## Implemented

- Added `tradingbotsuite.research_discovery.exit_lab`.
- Added `configs/discovery/discovery_exit_lab_v4.json`.
- Added exit family comparisons for:
  - fixed holding reference
  - barrier exits
  - funding/OI exits
  - HMM/KNN-adjacent exits
  - trailing/risk-control exits
- Added explicit decisions:
  - `passed`
  - `failed`
  - `pending_evidence`
  - `skipped_low_trade_density`
- Added family summaries with winner candidate IDs.
- Added artifact writer for:
  - `discovery_exit_lab_manifest.json`
  - `discovery_exit_lab_matrix.parquet`
  - `discovery_exit_family_summary.parquet`
- Exported the new API from `tradingbotsuite.research_discovery`.
- Added focused discovery tests.

## Boundary Evidence

- No checked BTCUSDT/ETHUSDT historical-cycle configs or artifacts were changed.
- No new exit policy math or backtest execution policy was added.
- No optimizer gates, candidate-pack gates, promotion validators, operator UI,
  live execution, sizing, or order placement behavior was changed.
- Outputs remain `research_only`, `observe_only`, and `promotion_ready: false`.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Results:

- Compile passed.
- `tests\research_discovery`: 46 passed.
