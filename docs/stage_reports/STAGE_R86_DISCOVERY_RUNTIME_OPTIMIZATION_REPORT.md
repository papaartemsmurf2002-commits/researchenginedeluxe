# Stage R86 Discovery Runtime Optimization Report

Date: 2026-05-09
Branch: `research/v3-experimental-engine`

## Summary

Stage R86 implements the optimization subset that fits the existing discovery
architecture without weakening state, resume, artifact, or live-boundary
contracts.

Implemented now:

- Configurable `execution.max_workers` for bounded thread-based trial
  evaluation.
- Configurable `execution.persist_trial_artifacts`.
- Parent-only trial-record and run-state writes; worker threads only evaluate
  trial records and write their own unique trial artifact directories.
- In-run HMM materialization cache keyed by feature set, label horizon, split
  settings, and HMM settings.
- Compact blocked-trial artifact mode for standard/deep presets:
  `interesting_only` keeps full HMM/KNN/accounting artifacts for interesting
  candidates and keeps compact metrics/blocker evidence for rejected trials.
- Feature-set preflight blocks empty/all-NaN/constant feature sets before HMM/KNN
  compute.
- HMM/KNN train-only scalers now handle all-NaN split-local columns without
  warning spam while preserving existing finite-value behavior.

Deferred intentionally:

- Process-pool execution, because Windows process spawning needs a separate
  parent/worker artifact merge design and careful dataframe sharing.
- GPU KNN, because it requires a dependency/runtime decision such as FAISS,
  CuPy, PyTorch, or RAPIDS/cuML, ideally with a WSL2/Linux path.
- Full threshold-grid neighbor-basis caching, because it should be introduced
  with explicit result-equivalence tests across KNN thresholds.

## Config Changes

- `standard_entry_discovery_btcusdt_v4.json`
  - `execution.max_workers: 4`
  - `execution.persist_trial_artifacts: interesting_only`
- `deep_candidate_harvest_btcusdt_v4.json`
  - `execution.max_workers: 8`
  - `execution.persist_trial_artifacts: interesting_only`

Old specs default to serial execution and full artifacts:

- `execution.max_workers: 1`
- `execution.persist_trial_artifacts: all`

## Measured Local Impact

Deep-mode 10-trial probe on the local BTCUSDT latest-month fixture:

- Before R86: 67.4 seconds, 20.2 MB artifacts.
- After R86: 34.4 seconds, 13.0 MB artifacts.

Current full 5,000-trial deep estimate on the same fixture:

- Approximate runtime: 4.8 hours from the 10-trial probe.
- Practical range: 4-7 hours depending on candidate mix, disk pressure, and
  HMM/KNN cache hit rate.
- Artifact estimate: lower than R85 because blocked trials no longer write full
  HMM/KNN/accounting artifacts.

## Validation

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/research_discovery -q`

Validation status: passed.

## Research Boundary

- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- No live order-placement adapters are imported.
- No live runtime mode or live configuration is changed.
