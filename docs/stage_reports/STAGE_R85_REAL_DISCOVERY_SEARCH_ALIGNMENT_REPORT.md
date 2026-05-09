# Stage R85 Real Discovery Search Alignment Report

Date: 2026-05-09
Branch: `research/v3-experimental-engine`

## Summary

The fast no-result operator runs were caused by quick-smoke discovery specs and
placeholder discovery generation. Stage R85 changes standard/deep discovery from
placeholder ledger generation into real, research-only HMM/KNN trial execution
when data is configured.

## Changes

- Added checked operator presets:
  - `configs/discovery/standard_entry_discovery_btcusdt_v4.json`
  - `configs/discovery/deep_candidate_harvest_btcusdt_v4.json`
- Standard discovery now samples 360 real trials from 1,990,656 bounded
  combinations.
- Deep discovery now samples 5,000 real trials from 887,040,000 bounded
  combinations without materializing the full Cartesian product.
- Real discovery trials now materialize registered feature sets, build
  directional labels, create purged walk-forward splits, fit split-safe HMM
  regimes, run regime-local KNN predictions, write HMM/KNN/accounting artifacts,
  and record trial metrics in candidate ledgers.
- Search dimensions now include HMM state count, HMM posterior/entropy gates,
  label horizon, KNN `k`, minimum neighbor count, distance metric, probability
  and EV thresholds, agreement/distance/vote gates, same-regime filtering, and
  discovery acceptance floors.
- Optional feature-set materialization failures are isolated to the affected
  feature set and become blocked trial evidence instead of crashing the whole
  run.
- Operator discovery launches now avoid completed-run collisions by writing new
  completed runs to job-specific directories, while paused runs keep a stable
  run directory for resume.
- The operator Research tab now defaults to standard real entry discovery,
  exposes deep harvest and quick smoke separately, and queues selected real
  discovery from Full Research Review.
- Discovery benchmarks remain bounded run-manager regression checks with
  explicit benchmark placeholders, so they do not pretend to perform deep
  research or block routine validation.

## Research Boundary

- All outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Discovery artifacts do not write candidate packs.
- No live order-placement adapters are imported.
- No live runtime mode or live configuration is mutated.

## Validation

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/research_discovery -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only tests/tradingbotsuite/test_operator_ui.py::test_operator_discovery_job_writes_research_only_artifacts tests/tradingbotsuite/test_operator_ui.py::test_operator_discovery_job_can_pause_and_resume -q`

Validation status: passed.

## Operator Note

Use quick smoke only for UI/plumbing verification. Use standard real discovery
for normal candidate search. Use deep candidate harvest for long unattended
research with snapshots and resume.
