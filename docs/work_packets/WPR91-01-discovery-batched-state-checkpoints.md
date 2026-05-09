# WPR91-01 Discovery Batched State Checkpoints

## Objective

Reduce discovery-run IO overhead by writing `run_state.json` at checkpoints
instead of after every trial, while preserving crash recovery through immutable
trial records.

## Fit Check

This fits the current discovery architecture because trial records are already
written atomically before a trial is considered complete, resume already loads
all trial records, and `_merge_state_records` can rebuild state from durable
records. The change stays research-only and does not alter trial evaluation,
ledgers, snapshots, artifacts, candidate gates, promotion readiness, or live
behavior.

## Allowed paths

- `src/tradingbotsuite/research_discovery/runner.py`
- `tests/research_discovery/test_discovery_runner.py`
- `docs/work_packets/WPR91-01-discovery-batched-state-checkpoints.md`
- `docs/stage_reports/STAGE_R91_DISCOVERY_BATCHED_STATE_CHECKPOINTS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Planned changes

- Stop rewriting `run_state.json` after every individual trial.
- Keep trial record writes per trial as the durable source of completion truth.
- Continue writing state at initial setup, resume merge, snapshots, pause,
  completion, and final manifest checkpoint.
- Add manifest telemetry for the state checkpoint policy.
- Add a resume regression where `run_state.json` is deliberately stale but
  trial records are intact.

## Exit criteria

- Focused discovery runner tests pass.
- Full discovery tests pass.
- Compile and contract baseline pass.
- Stage report records implementation and validation.
