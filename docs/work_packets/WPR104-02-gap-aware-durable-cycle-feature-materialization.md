# WPR104-02 Gap-Aware Durable Cycle Feature Materialization

Owner: Codex Research Agent
Stage: R104 candidate validation on durable evidence
Status: closed
Created: 2026-05-17

## Goal

Fix the failed R104 durable historical-cycle run caused by compact
multi-window public-archive fixtures being treated as one continuous bar
series. Feature materialization must remain point-in-time safe and avoid
rolling/return leakage across intentional fixture window gaps.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `src/tradingbotsuite/features/builders.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/features/**`
- `tests/historical/**`
- `tests/contracts/**`

## Constraints

- Do not weaken completed-bar validation for normal continuous datasets.
- Do not compute rolling, return, or momentum features across multi-window
  fixture gaps.
- Keep outputs `research_only`, `observe_only`, and `promotion_ready: false`.
- Do not add live execution, runtime-mode changes, order placement, sizing, or
  promotion behavior.

## Planned implementation

1. Detect intentional multi-window fixture evidence in historical-cycle data
   source metadata and set feature materialization to gap-aware mode.
2. Materialize non-contiguous feature sets by continuous segment so rolling and
   lagged features reset at each fixture window.
3. Preserve cache identity and manifest evidence that continuity was not
   required because the input is a compact multi-window screening fixture.
4. Add focused tests and rerun the failed R104 durable cycle.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\features tests\historical -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Exit evidence

- Reproduced the failed operator-copied BTC R104 cycle:
  `ValueError: bar_time_gaps:1704894300000,1709660700000,1715780700000`.
- Added gap-aware segmented materialization when a historical-cycle data source
  is an intentional `multi_window_public_archive_selection` fixture.
- Segmenting is only used for intentional multi-window fixture gaps; normal
  historical-cycle datasets still require continuous completed bars.
- Gap-aware segmentation splits only on true forward gaps larger than the
  expected interval. Duplicate bars and short-cadence anomalies fail closed
  instead of being treated as fixture window boundaries.
- Bumped the feature-builder cache identity to
  `research-feature-builder-v2` so old relaxed-continuity cache artifacts are
  not reused after the materialization semantic change.
- Reran the failed copied operator spec successfully and wrote
  `research_cycle_manifest.json`, `candidate_rankings.parquet`,
  `backtest_index.parquet`, and `rejection_report.md`.
- Validation:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/features/test_feature_builders.py::test_materialized_feature_set_segments_intentional_bar_gaps_without_cross_gap_returns tests/features/test_feature_builders.py::test_materialized_feature_set_rejects_duplicate_bars_inside_intentional_gap_segments tests/features/test_feature_builders.py::test_materialized_feature_set_rejects_short_intervals_when_continuity_is_relaxed tests/historical/test_full_cycle_local_fixture_pack.py::test_r104_public_archive_multi_window_cycle_materializes_features_gap_aware -q`
  - `$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-historical-research-cycle --spec data\research\operator_runs\cycle_specs\run-historical-research-cycle-27f50be6d16241c4a665a937b342f222\cycle_spec.json`
  - `$env:PYTHONPATH='src'; python -m pytest tests -q`
