# WPR106-20 Performance Speedups And UI Wiring

Status: closed

## Scope

Implement the safe speed improvements identified by WPR106-19 and verify that
the operator UI/API exposes the relevant performance controls and evidence.

This packet prioritizes:

- exact-discovery timing and child/process visibility;
- lower finalization/artifact-accounting overhead without weakening durable
  trial records or atomic state writes;
- operator/UI wiring for worker-cap/performance evidence;
- focused validation around discovery telemetry, operator UI summaries, and
  research-only boundaries.

## Allowed paths

- `docs/work_packets/WPR106-20-performance-speedups-and-ui-wiring.md`
- `docs/stage_reports/STAGE_R106_PERFORMANCE_SPEEDUPS_AND_UI_WIRING_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/research_discovery/**`
- `tests/research_cycle/**`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/contracts/**`

## Constraints

- Preserve `research_only`, `observe_only`, and `promotion_ready: false`.
- Do not place orders, change live runtime mode, write live configuration, or
  import live order-placement adapters into research code.
- Do not weaken exact-discovery resume durability, per-trial JSON persistence,
  run-state atomic writes, or final ledger integrity.
- Do not make candidate-ready performance or profit claims from benchmark
  artifacts.
- Keep concurrency defaults conservative unless focused tests and benchmark
  evidence prove the change is safe.

## Acceptance

- Exact-discovery manifests expose finer execution/finalization timing and make
  child/process CPU accounting limitations clear.
- Discovery finalization avoids unnecessary broad artifact rescans where
  already-observed artifact counters are available.
- Operator API/UI surfaces performance worker plan, cache/ETA, artifact write
  pressure, and performance-study artifacts without requiring raw JSON.
- Focused tests cover telemetry/manifest shape and UI wiring.
- Baseline validation passes:
  `python -m compileall -q src\tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`.

## Closeout

- Added observed artifact accounting for discovery runner writes so telemetry
  can avoid recursive artifact scans when observed counters are available.
- Added finalization timing buckets and process chunk timing summaries to
  discovery manifests.
- Avoided unnecessary real-discovery context initialization for placeholder
  process-executor runs.
- Surfaced discovery worker plan, cache hit rates, artifact pressure, process
  timing, active-progress telemetry, and WPR106-19 performance-study artifacts
  through the operator API/UI.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
