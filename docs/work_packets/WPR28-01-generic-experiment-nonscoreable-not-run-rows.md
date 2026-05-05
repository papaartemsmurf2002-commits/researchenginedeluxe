# WPR28-01 Generic Experiment Non-Scoreable Not-Run Rows

Status: closed
Owner: Codex Research Agent
Stage: Stage R28 generic experiment output truthfulness
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Generic experiment outputs must not present missing-dataset, failed-backtest, or unexecuted-validation rows as scoreable empirical candidates. Prior hardening marks `metric_scope` and some failure reasons correctly, but several artifact paths can still produce metric-shaped zero values, aggregate-only empirical scope, report-only validation statuses, or derived `final_score` rankings for rows that were never backed by complete real empirical evidence.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR28-01-generic-experiment-nonscoreable-not-run-rows.md`
- `docs/stage_reports/STAGE_R28_GENERIC_EXPERIMENT_TRUTHFULNESS_REPORT.md`
- `src/tradingbotsuite/research/experiment_runner.py`
- `tests/tradingbotsuite/test_experiment_runner.py`
- `tests/tradingbotsuite/test_feature_ablation.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No changes to research-cycle backtest scoring or candidate-pack gates.
- No optimizer or benchmark implementation changes in this packet.
- No acceptance of generic experiment candidates as promotion-ready or live-ready.

## Implementation plan

1. Add explicit generic experiment scoreability fields so rows distinguish real scoreable backtests from not-run/failed/unvalidated rows.
2. Ensure not-run and failed rows carry null/blank empirical metric fields instead of zero-valued performance claims.
3. Ensure aggregate-only rows with missing executable validation splits are not scoped as complete empirical evidence.
4. Make report-only validation statuses depend on real output rows and candidate coverage, not method type alone.
5. Ensure candidate ranking artifacts do not derive `final_score` for rows without empirical evidence and executed validation.
6. Remove dead placeholder metric-table helpers that can recreate synthetic-looking metrics.
7. Add tests for missing-dataset, failed-backtest, no-validation-split, and report-output status paths.
8. Record validation evidence and close the packet.

## Exit criteria

- Missing-dataset generic outputs have `empirical_evidence=false`, `scoreable_candidate=false`, blank/null metric fields, and no numeric `final_score`.
- Failed backtest or unexecuted-validation rows are non-scoreable and cannot rank as empirical candidates.
- Generic manifests distinguish aggregate real backtests from complete validation evidence.
- Report-only validation methods require non-empty real report rows.
- Real backtest rows remain scoreable only when real backtest metrics exist and required executable validation methods ran.
- Focused experiment-runner, feature-ablation, live preflight, compile, contracts, and diff check pass.

## Completion evidence

- Generic summary and ranking rows now include `aggregate_backtest_evidence`, `validation_evidence_complete`, `scoreable_candidate`, and `scoreability_status`.
- Missing-dataset, failed-backtest, and validation-incomplete rows clear empirical metric fields and cannot receive a numeric `final_score` or rank.
- Generic manifests now report `aggregate_backtest_evidence`, `scoreable_candidate_count`, and `non_scoreable_candidate_count`, and downgrade aggregate-only/no-validation outputs to validation-incomplete scope.
- Report-only validation methods now require non-empty `real_backtest` rows in their report artifacts.
- Dead placeholder metric-table helper functions were removed from the generic runner.
- Validation:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_experiment_runner.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_feature_ablation.py tests\live\test_preflight.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `git diff --check` completed with line-ending warnings only.
