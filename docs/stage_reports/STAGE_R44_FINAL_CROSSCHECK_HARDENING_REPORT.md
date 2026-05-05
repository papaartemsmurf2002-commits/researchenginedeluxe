# Stage R44 Final Crosscheck Hardening Report

Date: 2026-05-05
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR44-01-final-crosscheck-hardening.md`
Status: closed

## Scope

R44 is the final crosscheck remediation stage requested before commit and push. It fixes review and validation blockers found after the documented research plan reached its stop point at R43. It does not reopen empirical acceptance, promotion, Stage 13 execution, live testing, or order-placement work.

## Findings Resolved

- Benchmark report final-report byte accounting now converges before the report is returned.
- Benchmark output directories and generated cycle `output_dir` values are resolved to absolute paths.
- Generated historical-cycle backtest run directory names are shortened, avoiding Windows filename-length warnings in WPR42 benchmark outputs.
- The WPR41 latest-month provider fixture is unignored so provider benchmark evidence is durable after push.
- Non-synthetic data specs omit synthetic row-count and synthetic-variant fields in serialized payloads.
- Regime and stress holdout splits preserve exact non-contiguous validation row membership.
- Stability-region grouping and feature-ablation comparator keys include exit-policy identity and params.
- Fixed-interval Binance USD-M premium/open-interest context manifests now report gaps and strict mode rejects them.
- Stage 12 feature-ablation execution specs use executable validation evidence methods, so real backtest runs are not mislabeled as validation-incomplete.
- Removed-source boundary tests pass without active tree literals for removed chart-export sources.

## Provider Benchmark Rerun

Command:

```powershell
$env:PYTHONPATH='src'
$env:TBS_RUNTIME_MODE='paper'
python -m tradingbotsuite.main benchmark-historical-research-cycle --tier provider_latest_month --output-dir data\research\benchmarks\wpr42_latest_month_provider_benchmark --repeat 2
```

Evidence:

- Report: `data/research/benchmarks/wpr42_latest_month_provider_benchmark/research_cycle_benchmark_report.json`
- Report SHA-256: `01c0bc350237682fa5c74335fc0fbce54c32fb1cad9314cda69297a1897a7136`
- Benchmark gate: passed
- Evidence complete: true
- Dataset manifest SHA-256: `3f6264f446217fc0a81964ddff71f2f07f35c862665687bca27abe58136d46ac`
- Rows per second mean: 2,691.891211
- Candidate backtests per minute mean: 66.980241
- Feature rows per second mean: 3,426.62383
- Python tracemalloc repeat peak bytes: 19,037,694
- Artifact bytes per candidate backtest: 439,076.9

`git status --ignored --short data\research\benchmarks\wpr42_latest_month_provider_benchmark` reports the ignored benchmark directory without filename-length warnings.

## Boundary Notes

- Research outputs remain `research_only`, `observe_only`, and `promotion_ready: false`.
- The provider fixture is local historical research evidence, not OOS acceptance evidence.
- No live fetch, order placement, runtime-control write, promotion acceptance, paper/shadow/testnet/canary flow, or capital-allocation behavior was added.
- Candidate gates remain fail-closed; this stage does not produce or promote a live candidate.

## Validation

Focused validation passed:

- Benchmark targeted tests: 2 passed.
- Removed-source boundary test: 1 passed.
- Feature-ablation execution target: 1 passed.
- Splits, stability, and context-gap target: 13 passed.
- Fixture-pack and research-cycle contract focus: 51 passed.
- Historical cycle and benchmark focus: 32 passed.
- Optimization, splits, market-data, and feature-ablation focus: 45 passed.
- Removed-source and candidate-pack focus: 35 passed.

Full validation after documentation updates:

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest -q` passed: 724 tests.

## Close Decision

Stage R44 is closed. The documented research-plan implementation remains complete at the R43 stop point, with R44 limited to final crosscheck hardening before commit and push.
