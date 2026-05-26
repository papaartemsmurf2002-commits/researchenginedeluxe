# Stage R106 Exact Discovery Process Worker Guard And Runtime Probe Report

Date: 2026-05-23

## Scope

WPR106-08 investigated the failed BTC candidate-depth exact-discovery run
`run-discovery-8067b58ead8249099e361cf189e4f8b4`, fixed the process-pool and
resume hazards, and measured whether the 570240-trial exact sweep can run below
the 30-hour target on the active R106 candidate-depth data.

All changes remain research-only, observe-only, and promotion-ready false. No
live execution, order placement, runtime-mode change, sizing behavior, or live
configuration write was introduced.

## Failure Diagnosis

The active BTC run at
`data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-candidate-depth-v1`
had a valid resolved spec, run state, snapshots, feature matrices, and trial
records. The failed job error was:

`A process in the process pool was terminated abruptly while the future was running or pending`

The active spec requested 48 process workers over 570240 exact trials on the
candidate-depth BTC fixture. On Windows, each child process loaded the large
real-discovery context; the original tiny process chunks also caused repeated
exact KNN base recomputation and made progress fragile when a child failed.

## Fixes

- Added a real-discovery process worker plan: configured workers, requested
  workers, active workers, cap source, and cap reason are recorded in manifests
  and compute telemetry.
- Capped real-discovery process workers to 8 by default via
  `TBS_DISCOVERY_REAL_PROCESS_MAX_WORKERS`, while preserving the configured
  48-worker request.
- Released the parent real-discovery context before starting the process pool
  to reduce duplicated memory pressure.
- Persisted completed process chunks through `as_completed()` so later failures
  do not discard already-returned records.
- Wrapped broken process-pool failures with the active/requested/configured
  worker plan for diagnosis.
- Added cache-affinity ordering and full cache-group chunks for no-stop
  production discovery runs.
- Added exact batched nearest-neighbor materialization, KNN base-result reuse,
  threshold metric-array reuse, no-regime baseline caching, and screening
  artifact deferral for `interesting_only` sweeps.
- Added compute telemetry fields for completed, total, remaining, and estimated
  remaining seconds.

## Recovery Evidence

The active BTC exact-discovery state was recovered in place. Bounded resume
probes advanced the run from 128 persisted trial records to 512 persisted trial
records without deleting the output directory or restarting from zero.

Final bounded probe:

- Completed additional trials: 64
- Wall time: 610.7 seconds
- Active workers: 8
- Process chunk size under bounded probe: 8
- Final manifest completed trials: 512
- State completed trials: 512
- Base KNN miss average: 365.2 seconds
- Base-hit, non-artifact threshold average: 0.379 seconds
- Inline heavy artifacts written in final probe: 0

The active full BTC sweep has 108 exact KNN cache groups. With full cache-group
chunks on unbounded UI/operator runs, the measured base cost plus cache-hit
threshold cost estimates roughly 9 to 12 wall-clock hours on this machine,
comfortably below the prior 30-hour blocker. The bounded probe remains
conservative because its `stop_after_trials` path intentionally keeps small
chunks to sample multiple groups.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - 188 passed
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - 427 passed
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\tradingbotsuite\test_data_pipeline.py tests\tradingbotsuite\test_market_data_collection.py -q`
  - 95 passed
  - Existing CUDA/XGBoost environment warnings were observed; no test failed.

## Current Status

The BTC exact-discovery run is still in progress, not candidate-ready evidence:
512 of 570240 trials are completed. The next operator action can safely resume
the same BTC exact-discovery run. It should not start over; completed trial
records are recovered from `trials/*.json` and merged into `run_state.json`.

