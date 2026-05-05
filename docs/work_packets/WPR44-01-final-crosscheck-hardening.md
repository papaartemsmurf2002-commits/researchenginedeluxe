# WPR44-01 Final Crosscheck Hardening

Status: closed
Owner: Codex Research Agent
Stage: Stage R44 final crosscheck hardening
Opened: 2026-05-05
Closed: 2026-05-05

## Objective

Resolve final crosscheck blockers before committing and pushing the research branch. The scope is limited to evidence hygiene, reproducibility, path safety, and regression coverage. This packet does not add live, paper, shadow, testnet, promotion, order-placement, runtime-control, or capital-allocation behavior.

## Allowed paths

- `.gitignore`
- `configs/research/full_cycle_btc_v1.json`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR44-01-final-crosscheck-hardening.md`
- `docs/stage_reports/STAGE_R44_FINAL_CROSSCHECK_HARDENING_REPORT.md`
- `src/tradingbotsuite/backtesting/splits.py`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/optimization/stability.py`
- `src/tradingbotsuite/research/feature_ablation.py`
- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_cycle/spec.py`
- `tests/backtesting/test_splits.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_research_cycle_benchmark.py`
- `tests/optimization/test_region_of_stability.py`
- `tests/research_artifacts/test_candidate_pack.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `data/research/fixtures/btcusdt_context_provider_latest_month_v1/**`

## Inputs

- Final code review findings from independent agents.
- Full-suite failures from the first final validation run.
- WPR41 latest-month provider fixture.
- WPR42 provider benchmark command.

## Exit criteria

- Full pytest failure set is resolved.
- Provider latest-month fixture is durable in the branch.
- Benchmark output paths are absolute and do not trigger Windows filename-length warnings.
- Holdout splits preserve exact held-out rows for non-contiguous regimes and stress periods.
- Stability and feature-ablation evidence grouping includes exit-policy identity.
- Fixed-interval context collectors report and reject gaps in strict mode.
- Research/live boundaries remain unchanged and fail closed.
- Focused validation and full-suite validation pass.

## Completion evidence

- `provider_latest_month` benchmark rerun completed with passed/evidence-complete gate.
- WPR42 report SHA-256 after rerun: `01c0bc350237682fa5c74335fc0fbce54c32fb1cad9314cda69297a1897a7136`.
- Provider fixture manifest SHA-256 remains `3f6264f446217fc0a81964ddff71f2f07f35c862665687bca27abe58136d46ac`.
- `git status --ignored --short data\research\benchmarks\wpr42_latest_month_provider_benchmark` reports the ignored benchmark directory without filename-length warnings.
- `docs/KNOWN_ISSUES.md` records the discovered P1 as resolved.

## Validation

Focused validation passed before closure:

- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py::test_research_cycle_benchmark_report_contains_research_only_gate_metrics tests\historical\test_research_cycle_benchmark.py::test_research_cycle_benchmark_resolves_relative_output_paths -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\test_removed_source_boundaries.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_feature_ablation.py::test_stage12_feature_ablation_spec_executes_as_real_backtest -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_splits.py tests\optimization\test_region_of_stability.py tests\tradingbotsuite\test_market_data_collection.py::test_collect_binance_usdm_context_detects_fixed_interval_gaps -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\contracts\test_research_cycle_contract.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py tests\historical\test_full_cycle_synthetic.py tests\historical\test_full_cycle_local_fixture_pack.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\optimization tests\backtesting\test_splits.py tests\tradingbotsuite\test_market_data_collection.py tests\tradingbotsuite\test_feature_ablation.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\test_removed_source_boundaries.py tests\research_artifacts\test_candidate_pack.py -q`

Full validation is recorded in the stage report.

Final validation passed:

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest -q` passed: 724 tests.
