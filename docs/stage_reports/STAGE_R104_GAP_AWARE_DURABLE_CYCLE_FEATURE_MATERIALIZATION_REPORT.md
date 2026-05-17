# Stage R104 Gap-Aware Durable Cycle Feature Materialization Report

Date: 2026-05-17
Work packet: `docs/work_packets/WPR104-02-gap-aware-durable-cycle-feature-materialization.md`
Stage status: fix complete

## Problem

The R104 durable BTC historical cycle failed after data-quality output with:

```text
ValueError: bar_time_gaps:1704894300000,1709660700000,1715780700000
```

The durable public-archive fixture is intentionally compact and multi-window:
it selects several market-regime windows from checksum-verified Binance Vision
archives. The historical-cycle feature path still required one continuous bar
series, so the run failed before candidate ranking artifacts were written.

## Fix

- Historical-cycle feature building now detects intentional
  `multi_window_public_archive_selection` fixture metadata and disables the
  continuous-series requirement only for that source shape.
- `materialize_registered_feature_set(..., require_continuous=False)` now
  segments non-contiguous bars into continuous windows and builds features per
  segment, preventing returns, momentum, and rolling features from crossing
  fixture gaps.
- The segmenter splits only true forward gaps larger than the expected bar
  interval. Duplicate bars and short-cadence anomalies remain hard validation
  failures and are covered by regression tests.
- The feature-builder identity was bumped to `research-feature-builder-v2` so
  relaxed-continuity cache artifacts are not reused across the semantic change.
- Feature-build manifests record:
  - `feature_continuity_required: false`
  - `feature_gap_policy: segment_on_intentional_multi_window_fixture_gaps`
  - segmented materialization scope on the affected feature set.

Normal continuous datasets remain fail-closed on bar gaps.

## Evidence

The failed copied operator spec was rerun successfully:

```text
data/research/operator_runs/historical_cycles/r104-btcusdt-durable-public-archive-v1/run-historical-research-cycle-27f50be6d16241c4a665a937b342f222/research_cycle_manifest.json
data/research/operator_runs/historical_cycles/r104-btcusdt-durable-public-archive-v1/run-historical-research-cycle-27f50be6d16241c4a665a937b342f222/candidate_rankings.parquet
data/research/operator_runs/historical_cycles/r104-btcusdt-durable-public-archive-v1/run-historical-research-cycle-27f50be6d16241c4a665a937b342f222/backtest_index.parquet
data/research/operator_runs/historical_cycles/r104-btcusdt-durable-public-archive-v1/run-historical-research-cycle-27f50be6d16241c4a665a937b342f222/rejection_report.md
```

## Validation

- `python -m compileall -q src/tradingbotsuite`
- Focused gap-aware feature/cycle regression:
  - `4 passed`
- Failed operator-copied historical cycle spec rerun:
  - wrote `research_cycle_manifest.json`, `candidate_rankings.parquet`,
    `backtest_index.parquet`, and `rejection_report.md`
- `$env:PYTHONPATH='src'; python -m pytest tests -q`
  - `1345 passed, 1 skipped`
