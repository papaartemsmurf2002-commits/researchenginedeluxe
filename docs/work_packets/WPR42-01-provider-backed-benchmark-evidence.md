# WPR42-01 Provider-Backed Benchmark Evidence

Status: closed
Owner: Codex Research Agent
Stage: Stage R42 provider-backed benchmark evidence
Opened: 2026-05-05
Closed: 2026-05-05

## Objective

Extend the historical research-cycle benchmark command so it can benchmark a non-synthetic provider fixture tier, then run that tier against the WPR41 latest-month BTCUSDT context fixture to record speed, memory, feature-cache reuse, parallel optimizer evidence, artifact overhead, and backend comparison evidence without changing live behavior.

## Allowed paths

- `src/tradingbotsuite/research_cycle/benchmark.py`
- `tests/historical/test_research_cycle_benchmark.py`
- `data/research/benchmarks/wpr42_latest_month_provider_benchmark/**`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR42-01-provider-backed-benchmark-evidence.md`
- `docs/stage_reports/STAGE_R42_PROVIDER_BACKED_BENCHMARK_EVIDENCE_REPORT.md`

## Inputs

- WPR41 fixture manifest: `data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json`.
- Benchmark command: `benchmark-historical-research-cycle`.
- Existing synthetic benchmark tiers and gate semantics.

## Non-goals

- No legacy chart export, TradingView, Pine, parity, or synthetic input use for the provider-backed tier.
- No removal of synthetic benchmark guardrails; they remain useful as contract/regression checks.
- No live, paper, shadow, testnet, canary, promotion, order-placement, runtime-control, or capital-allocation work.
- No OOS acceptance, performance claim, candidate promotion, or Stage 13 execution.

## Implementation plan

1. Add a provider-backed benchmark tier that writes a historical-cycle spec with `dataset_manifest_paths` and `synthetic_fixture: false`.
2. Keep existing synthetic tiers and tests intact.
3. Label provider benchmark reports and gates so they do not claim local synthetic scope.
4. Add tests that prove provider tiers write non-synthetic specs and remain CLI-selectable.
5. Run the provider-backed benchmark tier with repeat evidence.
6. Audit gate status, benchmark metrics, live flags, cache evidence, and generated report hashes.

## Exit criteria

- Provider-backed tier is registered and writes a non-synthetic fixture manifest spec.
- Synthetic tiers retain their previous behavior.
- Benchmark report includes provider fixture scope, deterministic repeat evidence, memory, feature-cache reuse, optimizer parallel timing/equivalence, artifact overhead, and reference/vector comparison.
- Generated benchmark report remains `research_only`, `observe_only`, and `promotion_ready: false`.
- Validation evidence is recorded in the stage report.

## Completion evidence

- Added benchmark tier `provider_latest_month`.
- Provider tier writes `dataset_manifest_paths` to the WPR41 fixture manifest and `synthetic_fixture: false`.
- Existing `small` and `medium` tiers retain synthetic fixture payloads and `local_synthetic` report/gate scope.
- Provider benchmark report: `data/research/benchmarks/wpr42_latest_month_provider_benchmark/research_cycle_benchmark_report.json`.
- Report SHA-256: `01c0bc350237682fa5c74335fc0fbce54c32fb1cad9314cda69297a1897a7136`.
- Benchmark data scope: `local_provider_fixture_pack`.
- Dataset manifest SHA-256: `3f6264f446217fc0a81964ddff71f2f07f35c862665687bca27abe58136d46ac`.
- Repeat count: 2.
- Benchmark gate: passed and evidence-complete.
- Summary metrics:
  - Rows per second mean: 2,691.891211.
  - Candidate backtests per minute mean: 66.980241.
  - Feature rows per second mean: 3,426.62383.
  - Python tracemalloc repeat peak bytes: 19,037,694.
  - Artifact bytes per candidate backtest: 439,076.9.
- Feature-cache reuse measured: cold misses 2, warm hits 2, output hashes matched.
- Optimizer parallel evidence measured: speedup factor 3.586032, result and stability hashes equal.
- Reference/vector backend comparison measured with `speed_claimed: false`.
- Final crosscheck rerun uses absolute benchmark spec paths and short backtest run directory names; `git status --ignored` no longer emits filename-length warnings for the WPR42 output.
- Live/order flags: `live_fetch_used: false`, `order_placement_used: false`.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py -q` passed: 11 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_research_cycle_benchmark.py tests\contracts\test_historical_fixture_pack_contract.py -q` passed: 38 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
