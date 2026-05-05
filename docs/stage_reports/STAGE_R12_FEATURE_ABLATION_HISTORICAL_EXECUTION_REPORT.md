# Stage R12 Feature Ablation Historical Execution Report

Status: closed - supplied specs and feature-ablation specs execute as research backtests
Owner: Codex Research Agent
Date: 2026-05-04

## Scope

This packet completed the WPR12-15 research execution slice:

- Valid supplied generic `ExperimentSpec` payloads now control the generic runner instead of being replaced by the default canned spec.
- Supplied dataset paths take precedence over pipeline/evidence dataset paths and are reflected in dataset identity metadata.
- Search candidates are expanded into actual executable candidates with candidate IDs, search parameters, effective strategy config, feature identity, cost settings, holding window, and cache keys.
- Generic and generated feature-ablation specs run through `BacktestEngine` when a dataset exists.
- No-dataset runs are explicit non-run artifacts, not placeholder empirical metrics.
- Supplied validation methods drive split backtests for supported split methods and fail closed when unsupported or not actually executed.
- Malformed, generic, or stale pre-existing pipeline evidence specs are not injected into the HMM/KNN matrix evidence stage before generic-runner fallback.

## Path Audit

WPR12-15-specific edits were confined to the packet's allowed paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR12-15-feature-ablation-historical-execution.md`
- `docs/stage_reports/STAGE_R12_FEATURE_ABLATION_HISTORICAL_EXECUTION_REPORT.md`
- `src/tradingbotsuite/research/experiment_runner.py`
- `src/tradingbotsuite/research/feature_ablation.py`
- `tests/tradingbotsuite/test_experiment_runner.py`
- `tests/tradingbotsuite/test_feature_ablation.py`

`docs/KNOWN_ISSUES.md` and `tests/live/test_preflight.py` remained allowed but did not need edits. The working tree still contains earlier uncommitted WPR files and modifications already represented in the ledger; those were not reverted or normalized.

## Research Boundary

All artifacts remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `candidate_acceptance_allowed: false`
- no live signal, sizing, operator, execution, runtime, live-fetch, order-placement, paper, shadow, testnet, canary, promotion, or capital-allocation behavior

Feature-ablation and generic-runner real backtests are evidence inputs only. They do not promote hypotheses, candidates, or runtime behavior.

## Review Resolution

Read-only reviewers identified and rechecked these issues:

- Supplied datasets could be silently replaced by pipeline/evidence datasets. Resolved by giving valid supplied `ExperimentSpec.dataset.dataset_path` precedence and testing with conflicting pipeline/supplied datasets.
- Search candidates were reported but not executed. Resolved by materializing search expansion into executable candidate rows and testing two search candidates against actual backtest manifests/configs.
- Malformed supplied specs could bypass safe fallback. Resolved by guarded supplied-spec loading and by withholding malformed/generic specs from the HMM/KNN matrix evidence stage.
- Pre-existing pipeline evidence specs could preserve stale generic or malformed specs. Resolved by removing existing `evidence_stage.experiment_spec` before adding only vetted HMM/KNN matrix specs to the effective pipeline spec.
- Candidate manifests omitted executed config. Resolved by recording effective strategy config, feature manifest hash, search parameters, and strategy config hash per execution candidate.
- Dataset identity mislabeled parquet hashes as dataset manifest hashes. Resolved by separating dataset artifact SHA-256, dataset manifest SHA-256, supplied manifest hash, and dataset identity hash.
- Failed backtest rows used successful metrics-source labels. Resolved by using `backtest_engine_failed` for failed candidate rows and top-level failed scopes.
- Supplied validation was only reported. Resolved by executing supplied supported split methods and adding fail-closed validation statuses and failure reasons for unsupported or not-run validation methods.
- No-dataset and no-split artifacts could report validation methods as executed. Resolved by tying validation execution status to empirical scope and actual split output, with regression coverage for both missing dataset and too-short dataset cases.
- Failed split validation rows could be counted as executed validation. Resolved by counting only successful `real_backtest` split rows and adding regression coverage for failed split validation.
- Only one generated ablation spec had real execution coverage. Resolved by testing all eight generated feature-ablation specs across `lc_reference_v1`, `funding_basis_v1`, and baseline fallback branches.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_experiment_runner.py -q` passed: 11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_feature_ablation.py -q` passed: 4 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` passed: 24 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 59 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q` passed: 273 passed.
- `git diff --check` passed with only existing LF-to-CRLF warnings.

## Remaining Limitations

- Generated feature-ablation real backtests remain rejected/not-promotable until later empirical acceptance criteria produce complete OOS/stress/stability evidence.
- The packet does not ingest large real datasets, implement vectorized execution, or run paper/shadow/testnet/live stages.
- Stage 13 execution remains blocked until real OOS/stress/stability evidence, paper/shadow/testnet archives, rollback evidence, and explicit approval artifacts exist.
