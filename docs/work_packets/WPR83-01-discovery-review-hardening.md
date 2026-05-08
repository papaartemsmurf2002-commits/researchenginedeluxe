# WPR83-01 Discovery Review Hardening

## Status

Closed.

## Owner

Codex Research Agent.

## Scope

Fix review findings discovered during the R82 crosscheck without changing the
research-only discovery branch boundary or candidate-pack ownership.

## Allowed Paths

- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/web/operator.py`
- `tests/research_discovery/**`
- `tests/live/test_preflight.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR83-01-discovery-review-hardening.md`
- `docs/stage_reports/STAGE_R83_DISCOVERY_REVIEW_HARDENING_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Non-Goals

- Do not add live, paper, shadow, testnet, promotion, sizing, or order inputs.
- Do not weaken historical-cycle candidate-pack gates.
- Do not write candidate packs from discovery code.
- Do not redesign the discovery search engine beyond targeted correctness fixes.

## Exit Criteria

- KNN training labels cannot leak across the validation boundary.
- Selected WT3D feature-column sets require selected enabled comparators.
- Discovery resume fails closed if state references missing or changed trial
  records.
- `run-discovery` is covered by the central live-rejection registry.
- Operator model-artifact jobs validate paths against the research output root.
- Discovery candidate-pack bridge CLI uses an isolated default output path.
- Snapshot interval is honored between completed trials.
- HMM/KNN artifact writers avoid non-atomic overwrite of existing artifacts.
- Focused discovery tests, compile, and contract validation pass.

## Exit Evidence

- Added discovery bridge ledger/state/trial integrity checks so tampered ledger
  rows, edited incomplete state, and live-adjacent trial records fail closed.
- Added KNN label-horizon training-tail exclusion to prevent forward-label
  leakage across the validation boundary.
- Added selected WT3D comparator enforcement, resume missing-trial checks,
  snapshot-interval snapshots, and artifact overwrite refusal for HMM/KNN/bridge
  outputs.
- Added `run-discovery` to the central research-command live rejection registry.
- Added operator artifact-path allowlisting for train/calibrate/replay jobs.
- Validation passed:
  - `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q`
