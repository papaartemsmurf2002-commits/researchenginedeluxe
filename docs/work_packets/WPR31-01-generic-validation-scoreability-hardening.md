# WPR31-01 Generic Validation Scoreability Hardening

Status: closed
Owner: Codex Research Agent
Stage: Stage R31 generic validation scoreability hardening
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Make generic experiment scoreability fail closed when any configured validation method is unsupported or not executed. A row must not remain scoreable while the experiment manifest records `validation_method_not_executed:<method>` for a configured method such as `nested_validation`.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR31-01-generic-validation-scoreability-hardening.md`
- `docs/stage_reports/STAGE_R31_GENERIC_VALIDATION_SCOREABILITY_REPORT.md`
- `src/tradingbotsuite/research/experiment_runner.py`
- `tests/tradingbotsuite/test_experiment_runner.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No new validation engine implementation for `nested_validation`.
- No unrelated generic experiment output refactor.
- No changes to historical research-cycle runner or candidate-pack gates.

## Implementation plan

1. Broaden generic row scoreability checks from executable-only missing validation methods to all configured `validation_method_not_executed:<method>` reasons.
2. Preserve existing fail-closed behavior for missing datasets, failed backtests, and missing executable split validation.
3. Update tests so default `nested_validation` support gap makes rows non-scoreable/non-rankable until implemented or removed from the configured validation methods.
4. Add a focused supplied-spec regression for aggregate backtest evidence plus unsupported validation.
5. Record validation evidence and close the packet.

## Exit criteria

- Unsupported configured validation methods make `validation_evidence_complete` false and `scoreable_candidate` false.
- Rows with incomplete validation have empirical metric fields cleared and receive no rank.
- Existing missing-dataset, failed-backtest, and executable-validation-incomplete fail-closed paths remain covered.
- Focused experiment tests, live preflight, compile, contracts, and diff check pass.

## Completion evidence

- `src/tradingbotsuite/research/experiment_runner.py` now derives row-level `validation_method_not_executed:<method>` blockers from `validation_method_execution`, so unsupported, executable-not-executed, and report-output-not-executed configured validation methods all block scoreability.
- Generic rows with aggregate backtest evidence but incomplete configured validation are marked `real_backtest_validation_incomplete`, `validation_evidence_complete: false`, `scoreable_candidate: false`, and have empirical metric fields cleared.
- `tests/tradingbotsuite/test_experiment_runner.py` now covers default unsupported `nested_validation`, a supplied-spec unsupported validation method, existing executable split validation incompleteness, and report-output validation not executed.
- Validation:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_experiment_runner.py -q` -> 14 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` -> 24 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 76 passed
  - `git diff --check` -> CRLF warnings only
