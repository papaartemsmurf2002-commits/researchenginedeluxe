# Stage R78 Perp Context Filter Ablation Matrix Report

Date: 2026-05-08
Owner: Codex Research Agent
Packet: `docs/work_packets/WPR78-01-perp-context-filter-ablation-matrix.md`

## Summary

WPR78 is complete. The discovery package now has a research-only ablation matrix
foundation for comparing no-perp, perp-feature, perp-filter, perp-strategy,
perp-exit, and feature-combination variants. The implementation records
pass/fail/pending evidence and blocks default-filter claims unless treatment
rows beat configured comparators after costs and evidence floors.

## Implemented

- Added `tradingbotsuite.research_discovery.ablation_matrix`.
- Added `configs/discovery/perp_filter_ablation_matrix_v4.json`.
- Added ablation comparison specs with selectors, score delta floors,
  trade-count floors, missingness floors, and explicit default-filter guard
  flags.
- Added matrix generation from existing ranking/evidence tables.
- Added feature-combination stability diagnostics using discovery feature-column
  set manifests and optional evidence rows.
- Added artifact writer for:
  - `perp_filter_ablation_manifest.json`
  - `perp_filter_ablation_matrix.parquet`
  - `feature_combination_stability.parquet`
- Exported the new API from `tradingbotsuite.research_discovery`.
- Added focused discovery tests.

## Boundary Evidence

- Checked BTCUSDT and ETHUSDT historical-cycle configs were not changed.
- No optimizer gates, candidate-pack gates, promotion validators, operator UI,
  live execution, sizing, or order placement behavior was changed.
- Outputs remain `research_only`, `observe_only`, and `promotion_ready: false`.
- Feature-combination stability diagnostics are explicitly separate from the
  existing optimizer region-of-stability gate.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Results:

- Compile passed.
- `tests\research_discovery`: 40 passed.
