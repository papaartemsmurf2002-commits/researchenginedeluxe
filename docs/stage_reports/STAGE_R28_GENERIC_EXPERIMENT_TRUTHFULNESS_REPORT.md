# Stage R28 Generic Experiment Truthfulness Report

Date: 2026-05-04

## Scope

WPR28 hardened generic research experiment outputs so missing-dataset, failed-backtest, and validation-incomplete rows cannot be interpreted as scoreable empirical candidates.

This work remains research-only, observe-only, and not promotion-ready. It does not touch live execution, provider downloading, paper/shadow/testnet/canary paths, order placement, or candidate promotion.

## Changes

- `src/tradingbotsuite/research/experiment_runner.py`
  - Adds row-level `aggregate_backtest_evidence`, `validation_evidence_complete`, `scoreable_candidate`, and `scoreability_status`.
  - Clears empirical performance fields for non-scoreable rows, including missing-dataset, failed-backtest, and aggregate-only validation-incomplete rows.
  - Prevents candidate ranking artifacts from assigning numeric `final_score` or rank to non-scoreable rows.
  - Distinguishes aggregate backtest evidence from complete validated empirical evidence in generic experiment manifests.
  - Requires report-only validation methods to have non-empty `real_backtest` report rows before reporting `executed_by_required_output`.
  - Removes dead placeholder metric table helpers that could reintroduce synthetic-looking generic metrics.

- `tests/tradingbotsuite/test_experiment_runner.py`
  - Covers missing-dataset non-scoreable rows.
  - Covers aggregate real backtests without executable validation splits.
  - Covers failed backtest rows and failed report-output validation status.
  - Asserts real validated runs remain scoreable.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_experiment_runner.py -q` passed: 12 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_feature_ablation.py tests\live\test_preflight.py -q` passed: 28 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 76 tests.
- `git diff --check` completed with line-ending warnings only.

## Result

WPR28 is complete. Generic experiment outputs now separate aggregate diagnostic backtests from complete scoreable validation evidence, and non-executed or failed paths no longer carry metric-shaped performance claims.
