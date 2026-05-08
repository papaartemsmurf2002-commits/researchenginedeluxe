# Stage R80 Operator Discovery UI Report

Date: 2026-05-08
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR80-01-operator-discovery-ui.md`

## Summary

WPR80 exposes V4 discovery runs in the operator Research tab without changing discovery math, historical-cycle semantics, candidate-pack gates, promotion behavior, or live execution. Discovery launches now use the existing guarded operator research job queue, rewrite checked specs into the configured research output root, and surface run state, snapshots, candidate ledgers, and blocker tables as observe-only artifacts.

## Changes

- Added `/api/operator/research/jobs/run-discovery` with session, same-origin, CSRF, spec allowlist, discovery-spec validation, and positive `stop_after_trials` validation.
- Added `run-discovery` service dispatch through the existing operator research-job guard that blocks live mode, ambiguous safety states, and open live positions.
- Rewrote queued discovery specs to `research_output_dir/operator_runs/discovery_runs/<run_id>` and stored isolated job specs under `research_output_dir/operator_runs/discovery_specs/<run_id>/<job_id>`.
- Added stop/resume support for paused discovery runs while preserving discovery runner spec immutability.
- Added `discovery_run` artifact summaries with manifest fields, state, counts, latest snapshot, interesting candidates, blocked candidates, and filter blockers.
- Added Research-tab controls for launch/resume and a Discovery Ledger chart/card using existing operator UI conventions.

## Research Boundary

- Discovery artifacts remain `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- No live order-placement adapter imports were added.
- No live runtime mode, live configuration, promotion readiness, candidate-pack gate, optimizer, backtest, or checked BTCUSDT/ETHUSDT cycle behavior was changed.

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Results:

- `compileall`: passed
- `tests/tradingbotsuite/test_operator_ui.py`: 32 passed
- `tests/contracts`: 372 passed

## Stage Decision

R80 is closed. The next V4 implementation stage is WPR81 deep discovery benchmarks.
