# WPR12-15 Feature Ablation Historical Execution

Status: closed
Owner: Codex Research Agent
Stage: Stage R12/R15 feature ablation historical execution
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Make generated feature-ablation and caller-supplied generic `ExperimentSpec` payloads executable through real research backtests when a dataset is available. The generic experiment runner must stop substituting a canned strategy/feature spec when a valid supplied spec exists, and it must not emit placeholder empirical metrics when no dataset can be resolved.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR12-15-feature-ablation-historical-execution.md`
- `docs/stage_reports/STAGE_R12_FEATURE_ABLATION_HISTORICAL_EXECUTION_REPORT.md`
- `src/tradingbotsuite/research/experiment_runner.py`
- `src/tradingbotsuite/research/feature_ablation.py`
- `tests/tradingbotsuite/test_experiment_runner.py`
- `tests/tradingbotsuite/test_feature_ablation.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No claim that feature-ablation hypotheses are accepted without generated OOS/stress evidence floors.
- No broad rewrite of Stage 12 planning or historical-cycle runner.
- No large real dataset ingestion.
- No vectorized engine or full-cycle parallel benchmark work in this packet.

## Implementation plan

1. Add a generic-runner loader for valid supplied `ExperimentSpec` JSON payloads.
2. Preserve the existing default generic spec only when no valid supplied spec exists.
3. Override resolved dataset identity into the executable spec when a parquet dataset is available.
4. Replace no-dataset placeholder/contract-only metric rows with explicit non-run rows that cannot be mistaken for empirical metrics.
5. Add tests proving a supplied feature/strategy spec is what gets executed.
6. Add tests proving generated feature-ablation specs can run as real backtests through `run_research_experiment`.
7. Keep live preflight coverage intact for research commands.

## Exit criteria

- Supplied `ExperimentSpec` payloads control feature set, strategies, search method, validation, and backtest config in the generic runner.
- Generated feature-ablation spec files can produce real backtest manifests and real metric scopes when run with a dataset.
- No-dataset runs are explicitly blocked/not-run, not placeholder empirical outputs.
- All artifacts remain `research_only`, `observe_only`, and `promotion_ready: false`.
- Focused tests, live preflight, contracts, compileall, and diff checks pass.

## Risk controls

- Keep acceptance blocked; real backtests are evidence inputs, not promotion approval.
- Do not fabricate metrics when datasets are unavailable.
- Keep dirty-tree edits confined to WPR12-15 allowed paths.
- Treat earlier uncommitted WPR files in the dirty tree as out of scope.

## Completion evidence

- Supplied generic `ExperimentSpec` payloads are loaded by the generic runner when valid; the default generic spec is used only when no valid supplied generic spec exists.
- Supplied dataset paths take precedence over pipeline/evidence dataset paths. Missing supplied dataset paths fail closed as `not_run_missing_dataset`.
- Generic search candidates are materialized into executable candidates with candidate IDs, effective strategy config, search parameters, feature identity, backtest cost/holding settings, and cache identity.
- Supplied validation methods now control split execution for supported split methods; unsupported validation methods are reported as `unsupported_fail_closed` and copied into candidate failure reasons.
- Malformed, generic, or stale pre-existing pipeline evidence specs are not injected into the HMM/KNN matrix evidence stage before generic-runner fallback; HMM/KNN matrix specs remain eligible for pipeline evidence execution.
- No-dataset runs emit explicit non-run summary rows and empty split/regime/side/cost-stress metric outputs rather than placeholder empirical metrics.
- No-split and failed-split validation cases fail closed; validation methods are reported as executed only when successful split outputs exist.
- All generated Stage 12.1 feature-ablation specs execute through `run_research_experiment` against a dataset and produce real backtest metric scopes while remaining rejected/not promotable.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_experiment_runner.py -q` passed: 11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_feature_ablation.py -q` passed: 4 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q` passed: 24 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed: 59 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q` passed: 273 passed.
- `git diff --check` passed with only LF-to-CRLF warnings.
