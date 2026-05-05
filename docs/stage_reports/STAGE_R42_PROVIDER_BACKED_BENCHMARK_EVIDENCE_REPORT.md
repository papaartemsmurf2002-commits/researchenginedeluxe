# Stage R42 Provider-Backed Benchmark Evidence Report

Date: 2026-05-05
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR42-01-provider-backed-benchmark-evidence.md`
Status: closed

## Scope

WPR42 extended the historical research-cycle benchmark command with a provider-backed tier while preserving the existing synthetic `small` and `medium` regression tiers. The new tier uses the WPR41 latest-month BTCUSDT context fixture and writes non-synthetic historical-cycle specs.

No legacy TradingView exports, Pine files, parity files, live execution, paper/shadow/testnet/canary flows, order placement, promotion, or candidate acceptance were added.

## Implementation

`src/tradingbotsuite/research_cycle/benchmark.py` now includes:

- `provider_latest_month` in `BENCHMARK_TIERS`.
- Provider tier data payloads with `dataset_manifest_paths` and `synthetic_fixture: false`.
- Provider-scope report metadata through `benchmark_data_scope: local_provider_fixture_pack`.
- Dataset manifest evidence with path, existence, and SHA-256.
- Provider-specific benchmark gate profile and scope strings.
- Provider-specific reference/vector backend comparison claim scope with `speed_claimed: false`.

`tests/historical/test_research_cycle_benchmark.py` now verifies:

- The provider tier is registered and CLI-selectable.
- Provider specs omit synthetic row-count/variant fields and use fixture manifest paths.
- Provider benchmark gates use provider-fixture scope.
- Existing synthetic tier behavior remains intact.

## Benchmark Run

Command:

```powershell
$env:PYTHONPATH='src'
$env:TBS_RUNTIME_MODE='paper'
python -m tradingbotsuite.main benchmark-historical-research-cycle --tier provider_latest_month --output-dir data/research/benchmarks/wpr42_latest_month_provider_benchmark --repeat 2
```

Output:

- Report: `data/research/benchmarks/wpr42_latest_month_provider_benchmark/research_cycle_benchmark_report.json`
- Report SHA-256: `01c0bc350237682fa5c74335fc0fbce54c32fb1cad9314cda69297a1897a7136`
- Benchmark data scope: `local_provider_fixture_pack`
- Dataset manifest: `data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json`
- Dataset manifest SHA-256: `3f6264f446217fc0a81964ddff71f2f07f35c862665687bca27abe58136d46ac`
- Repeat count: 2
- Benchmark gate: passed
- Evidence complete: true

Summary metrics:

- Rows per second mean: 2,691.891211
- Candidate backtests per minute mean: 66.980241
- Feature rows per second mean: 3,426.62383
- Python tracemalloc repeat peak bytes: 19,037,694
- Artifact bytes per candidate backtest: 439,076.9
- Candidate backtests per repeat: 25
- Processed rows per repeat: 60,284

Evidence sections:

- Feature cache reuse: measured; cold misses 2, warm hits 2, output hashes matched.
- Backtest identity repeat consistency: measured; cache keys, result hashes, and ranking identity consistent.
- Optimizer parallel evidence: measured; speedup factor 3.586032 with result and stability-region hashes equal.
- Reference/vector comparison: measured; provider-fixture runtime observation only, `speed_claimed: false`.
- Artifact overhead: measured after backend comparison and final report write; final-report byte accounting matches the written report.
- Benchmark paths are absolute in generated specs and use short backtest run directory names to avoid Windows filename-length warnings.

## Boundary Notes

- The report is `research_only`, `observe_only`, and `promotion_ready: false`.
- `live_fetch_used` and `order_placement_used` are `false`.
- Backtest cache lookup, cache hit, and execution-cache reuse are all `false`.
- This is local provider-fixture benchmark evidence only. It is not OOS acceptance evidence, promotion evidence, or a production performance claim.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py -q` passed: 11 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py tests\contracts\test_historical_fixture_pack_contract.py -q` passed: 38 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.

## Close Decision

Stage R42 is closed. The benchmark gate now has real provider-fixture evidence using the WPR41 context fixture while preserving synthetic benchmark guardrails.
