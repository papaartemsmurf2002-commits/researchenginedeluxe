# Research Branch Distillation

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Scope: trusted historical research only

## Executive Summary

`research/v3-experimental-engine` is the research and experimentation branch for TradingBotSuite. Its job is to turn historical market data into reproducible, auditable research artifacts:

```text
provider data
  -> validated manifests and fixture packs
  -> point-in-time feature frames
  -> validation splits
  -> strategy candidates
  -> reference or vector backtests
  -> cost stress, stability, and ablation evidence
  -> ranked research candidates
  -> candidate pack only if all research gates pass
```

The branch is not a live trading branch. Research outputs are not signals, not live configuration, not capital-allocation inputs, and not promotion evidence. The branch deliberately keeps artifacts `research_only`, `observe_only`, and `promotion_ready: false` unless a later promotion process explicitly changes that outside this research scope.

As of Stage R44, the development plan's research-engine implementation stop point has been reached and final crosscheck hardening has passed. The branch contains the historical research cycle, provider fixture intake, feature construction and caching, strategy plugins, backtesting engines, optimizer and stability analysis, candidate gates, candidate-pack validation, benchmark gates, and research UI surfaces. Stage 13 paper, shadow, testnet, live, canary, and promotion execution remain blocked.

## What The Branch Does

The branch provides a complete local framework for historical strategy research:

- Collects and ingests historical provider data for research use.
- Builds durable local fixture packs with primary bars and optional context families.
- Validates manifests, hashes, row counts, provenance, and point-in-time compatibility.
- Builds registered feature sets using completed-bar and as-of semantics.
- Caches materialized feature frames with deterministic identity.
- Generates strategy candidates from registered plugin metadata and configured search spaces.
- Runs aggregate, split, cost-stress, and ablation backtests.
- Supports fixed-holding and expanded research exit policies.
- Supports reference backtesting and a vector path for fixed-holding primary-bar cycles.
- Ranks candidates using costed metrics, split evidence, stability evidence, ablation evidence, and research gates.
- Writes reproducible manifests, Parquet evidence tables, JSON reports, and rejection reports.
- Writes a research candidate pack only when durable evidence and all gates pass.
- Blocks research commands in live runtime mode.

## What It Does Not Do

The branch does not:

- Place orders.
- Produce live trading signals.
- Change live runtime mode.
- Write live configuration.
- Promote candidates into paper, shadow, testnet, canary, or live execution.
- Claim profit, production speedup, or live readiness from local research results.
- Treat legacy chart-export data as an acceptable provider source.

Synthetic data still exists for contract tests and small benchmark tiers, but synthetic evidence is not acceptable for provider-backed candidate packs or empirical acceptance.

## Governance Framework

The branch is controlled by the orchestrator ledger and work-packet model:

- `AGENTS.md` defines branch rules and validation baseline.
- `docs/ORCHESTRATOR_STAGE_LEDGER.md` records current stage, packet status, and stage decisions.
- `docs/work_packets/` scopes each work item before edits begin.
- `docs/stage_reports/` records close evidence and validation.
- `docs/KNOWN_ISSUES.md` is the blocking issue registry.
- `docs/contracts/` defines artifact, data, feature, backtest, strategy, boundary, and promotion contracts.

The working rule is simple: before changing code or docs, open a packet, keep changes inside its allowed paths, validate, then close the packet and ledger.

## Package Map

| Area | Main paths | Role |
| --- | --- | --- |
| Research cycle | `src/tradingbotsuite/research_cycle/` | Main historical-cycle spec, runner, benchmark gate, and artifact orchestration. |
| Data contracts and fixtures | `src/tradingbotsuite/data/`, `src/tradingbotsuite/research/market_data.py` | Provider manifests, local fixture packs, archive ingestion, REST collection, and provenance validation. |
| Features | `src/tradingbotsuite/features/`, `configs/features/` | Feature registry, presets, builders, as-of context joins, materialization, split transforms, and feature cache. |
| Strategies | `src/tradingbotsuite/strategies/`, `configs/strategies/` | Plugin contract, transparent baselines, funding/regime/HMM-KNN diagnostics, parameter metadata, and search defaults. |
| Backtesting | `src/tradingbotsuite/backtesting/` | Reference engine, vector fixed-holding engine, execution simulator, exit policies, splits, and metrics artifacts. |
| Optimization | `src/tradingbotsuite/optimization/` | Candidate configs, search spaces, deterministic cache, multi-stage optimizer, scoring, and stability regions. |
| Research artifacts | `src/tradingbotsuite/research_artifacts/` | Candidate-pack gate evaluation, pack writing, evidence validation, and live-adjacent artifact rejection. |
| Research experiments | `src/tradingbotsuite/research/` | HMM/KNN research, generic experiment runner, feature ablation, stage planning, provider data tooling, and monitoring reports. |
| UI and web | `src/tradingbotsuite/ui/`, `src/tradingbotsuite/web/` | Research job/status surfaces and read-only operator diagnostics. |
| Live boundary | `src/tradingbotsuite/live/`, `src/tradingbotsuite/promotion/` | Preflight and validators that reject research artifacts or research commands from live execution paths. |
| Tests | `tests/` | Contract, historical-cycle, optimization, backtesting, feature, artifact, and live-boundary tests. |

The primary active framework is `src/tradingbotsuite/`. A legacy `src/tradingbot/` package still exists with older backtest, indicator, optimization, data, and live-adjacent surfaces. Treat it as legacy/reference material unless a work packet explicitly scopes it. Current research execution, gates, and documentation should orient around `tradingbotsuite` and the ledger state, not older orientation files that predate the R40-R44 completion wave.

## Research Cycle Framework

The central research entry point is:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main run-historical-research-cycle --spec configs\research\full_cycle_btc_v1.json
```

The spec model lives in `src/tradingbotsuite/research_cycle/spec.py`. It supports:

- Symbols: currently BTCUSDT-oriented configs and fixtures, with ETHUSDT accepted in provider collectors.
- Holding windows: `1h`, `4h`, `12h`, `24h`, `72h`, `7d`.
- Data sources: dataset manifests, local fixture packs, direct dataset paths, lower-timeframe datasets, and explicit synthetic fixtures for tests.
- Feature sets: price/trend/vol, price/trend/vol plus WT3D, full context with and without WT3D, perp context only, microstructure filter only, and related registered presets.
- Strategies: no-trade baseline, trend following, volatility breakout, range reversion, funding basis, regime adaptive, HMM/KNN diagnostic, and reference strategies.
- Validation modes: purged/embargoed, anchored, rolling, shifted purged, month holdout, stress-period holdout, and regime holdout.
- Exit policies: fixed holding, triple-barrier variants, volatility-scaled barriers, regime/funding/alpha/adverse-selection exits, trailing-after-profit, and max-MAE stop.
- Backtest backends: `reference`, `vector_fixed_holding`, and `auto`.

The runner writes the core artifact family:

- `research_cycle_manifest.json`
- `cycle_spec_resolved.json`
- `data_quality_report.json`
- `feature_build_manifest.json`
- `split_manifest.json`
- `candidate_space_manifest.json`
- `backtest_index.parquet`
- `candidate_rankings.parquet`
- `stability_regions.parquet`
- `metrics_by_split.parquet`
- `metrics_by_regime.parquet`
- `metrics_by_side.parquet`
- `metrics_by_holding_window.parquet`
- `metrics_by_cost_stress.parquet`
- `ablation_report.json`
- `candidate_gate_report.parquet`
- `rejection_report.md`
- `research_candidate_pack/` only when gates pass

## Data And Provenance

The data framework is manifest-first. Historical data is not trusted just because it exists on disk. Manifests carry source identity, symbol, family, time bounds, row counts, content hashes, quality flags, and research-only status.

Primary data surfaces:

- `src/tradingbotsuite/data/contracts.py`: normalized data-manifest contract and validation.
- `src/tradingbotsuite/data/historical_fixture_pack.py`: provider kline fixture-pack builder, context-family slicing, unsafe-source rejection, and fixture validation.
- `src/tradingbotsuite/research/market_data.py`: research-only Binance USD-M bar and context collectors plus archive ingestion.
- `data/research/fixtures/btcusdt_v1/`: durable compact BTCUSDT fixture.
- `data/research/fixtures/btcusdt_context_provider_latest_month_v1/`: durable provider-backed latest-month BTCUSDT fixture with funding, premium, and open-interest context.

Provider fixture packs reject unsafe or synthetic provenance for provider-backed research evidence. Context families are joined into cycle rows using backward as-of semantics so a bar can only see context available at or before the bar's effective research time.

## Feature Framework

Features are registered, versioned, and built from explicit feature packs:

- Price path.
- Trend and chop.
- Volatility.
- Perpetual-market context.
- Microstructure context.
- WT3D oscillator family.
- Cross-asset context.
- Calendar and funding-window context.

`src/tradingbotsuite/features/registry.py` owns feature metadata and preset definitions. `src/tradingbotsuite/features/builders.py` builds registered feature sets, materializes context families, and preserves completed-bar alignment. `src/tradingbotsuite/features/cache.py` writes and validates deterministic feature-cache artifacts keyed by dataset, feature manifest, context hash, and builder identity.

WT3D is treated as optional. Any WT3D-positive claim must be compared against no-WT and price/trend/vol baselines, and the branch currently records this as research evidence rather than promotion readiness.

## Strategy Framework

Strategies are plugins with a common contract:

- `prepare(train_context)`
- `predict(feature_frame)`
- `explain(prediction_frame)`

Signal frames must satisfy required columns, allowed sides, holding windows, timestamps, research-only behavior, and parameter validation. Strategy metadata supplies per-holding-window defaults and bounded parameter spaces used by the historical cycle.

Current strategy families include:

- `baseline_no_trade`
- `trend_following_v1`
- `volatility_breakout_v1`
- `range_reversion_v1`
- `funding_basis_v1`
- `regime_adaptive_v1`
- `hmm_knn_diagnostic_v1`
- `lc_reference_v1`

HMM/KNN is diagnostic-first. It is intended as a regime-local similarity tool, optional filter, and explainability layer, not as a default live alpha engine.

## Backtesting Framework

The backtesting package has two engine paths:

- Reference engine: artifact-rich pandas path used for correctness and general policy coverage.
- Vector fixed-holding engine: array-oriented path for fixed-holding primary-bar cycles, with explicit fallback/rejection evidence for unsupported scopes.

Backtest outputs include manifests, trades, signals, equity curves, metrics, resolved configs, hashes, cache identity components, backend evidence, and runtime summaries.

Execution and exit handling includes:

- Fixed-holding exits.
- Lower-timeframe triple-barrier sequencing when lower-timeframe bars are supplied.
- Primary-bar research exits for volatility, regime, funding, alpha decay, adverse selection, trailing, and MAE policies.
- Directional fee, slippage, spread, and funding cost accounting.
- No optimistic same-bar stop/target ordering without lower-timeframe proof.

## Optimization And Stability

The optimizer is intentionally stability-oriented. It does not accept a candidate because one point scores well.

Main components:

- `CandidateConfig` and `CandidateResult`.
- `SearchSpace` expansion from explicit specs and strategy metadata.
- `CandidateCache` for deterministic candidate-result identity.
- `OptimizationRun` for staged evaluation.
- `rank_by_stability` and `stability_region_for` for local-neighborhood evidence.
- Composite scoring in `src/tradingbotsuite/optimization/scorer.py`.

Candidate ranking and pack eligibility consider:

- No-trade and transparent baseline comparison.
- Costed expectancy after fees, slippage, spread, and funding.
- Split coverage and dominance limits.
- Regime and side evidence.
- Cost-stress survival.
- Stability-region quality and spike rejection.
- Feature-ablation evidence.
- Fixture provenance and durable evidence-table agreement.
- Minimum trade floors.

## Candidate Packs And Gates

Candidate packs are fail-closed. `src/tradingbotsuite/research_artifacts/candidate_pack.py` validates the cycle manifest, candidate ranking row, candidate gate report, required evidence outputs, fixture provenance, split/stress evidence, backtest manifests, ablation evidence, and live-adjacent flags before writing a pack.

A candidate pack must remain:

```text
research_only: true
observe_only: true
promotion_ready: false
```

Current provider-backed cycles have produced local research evidence and blocked all candidates at the research gates. That is a valid outcome: it means the branch is refusing to package weak or incomplete candidates.

## Benchmark Framework

The benchmark entry point is:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main benchmark-historical-research-cycle --tier provider_latest_month --repeat 2
```

Benchmark tiers currently include:

- `small`: synthetic contract benchmark.
- `medium`: larger synthetic local benchmark.
- `provider_latest_month`: local provider-fixture benchmark using the latest-month BTCUSDT context fixture.

Benchmark reports record rows per second, candidate backtests per minute, feature rows per second, feature-cache reuse, memory peak, artifact overhead, deterministic repeat identity, optimizer parallel equivalence, and reference-versus-vector behavioral parity. These are regression guardrails and local observations, not production speed or profit claims.

## CLI Surface

Primary research commands are exposed through `python -m tradingbotsuite.main`:

- `collect-binance-bars`
- `collect-binance-context`
- `fetch-binance-vision`
- `fetch-crypto-lake`
- `build-historical-fixture-pack`
- `prepare-hmm-knn-research-data`
- `research-hmm-knn`
- `run-hmm-knn-experiments`
- `replay-hmm-knn`
- `monitor-hmm-knn`
- `run-research-experiment`
- `benchmark-research-experiment`
- `run-historical-research-cycle`
- `benchmark-historical-research-cycle`
- `plan-feature-ablation`
- `plan-stage12-research`
- `plan-stage13-readiness`

The same entry module also contains live/operator commands, but live preflight rejects research commands in live mode. Research modules must not import live order-placement adapters.

## UI Surface

The web/UI layer provides research status and diagnostics, not live control over research artifacts:

- Research pages show manifest-linked metrics and queued research jobs.
- Operator diagnostics expose read-only shadow/readiness information.
- Stage 13 planning surfaces produce templates and checklists only.
- Research artifacts are rejected as live order inputs.

## Python Stack

Project metadata is in `pyproject.toml`.

Runtime:

- Python `>=3.11`
- `pandas`, `numpy`, `pyarrow` for tables, arrays, and Parquet artifacts
- `pydantic` for typed validation surfaces
- `scikit-learn`, `scipy` for research/modeling utilities
- `fastapi`, `uvicorn`, `jinja2`, `itsdangerous`, `python-multipart` for the local web surface
- `httpx`, `websockets` for provider/API connectivity
- `aiosqlite` for local persistence
- `PyYAML` for config support
- `hyperliquid-python-sdk` remains present for live-adjacent project surfaces, guarded away from research execution

Development:

- `pytest`
- `pytest-asyncio`
- `hypothesis`

Optional research:

- `hmmlearn==0.3.3`
- `xgboost>=3.2,<4`

Optional research GPU:

- `cupy-cuda12x`
- Nvidia CUDA runtime and NVRTC packages

Artifact formats are mostly JSON, JSONL, Markdown, and Parquet.

## Current Evidence State

The research plan implementation reached its stop point at Stage R43, and Stage R44 completed final hardening.

Notable current evidence:

- Latest-month BTCUSDT provider context fixture is durable in `data/research/fixtures/btcusdt_context_provider_latest_month_v1/`.
- Provider-backed benchmark gate passed for `provider_latest_month`.
- The WPR43 full-context WT3D/no-WT ablation cycle ran against provider fixture data.
- Candidate gates remained blocked and no promotion-ready candidate pack was produced.
- Stage R44 fixed final evidence hygiene, Windows path hygiene, holdout exactness, context gap detection, exit-policy grouping, and validation issues.
- Full validation after R44 passed: `724` pytest tests.

Current status is best described as: historical research framework complete for the documented objective, empirical candidate acceptance still blocked by gates, and Stage 13 execution still not started.

## Validation Baseline

Before closing scoped work, use at least the branch baseline:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Broaden validation when shared behavior changes. R44 full validation used:

```powershell
$env:PYTHONPATH='src'; python -m pytest -q
```

## How To Continue Work Safely

1. Read `AGENTS.md` and `docs/ORCHESTRATOR_STAGE_LEDGER.md`.
2. Confirm no open P0 issue and fewer than four unresolved P1 issues in `docs/KNOWN_ISSUES.md`.
3. Write a work packet before editing.
4. Keep edits inside the packet's allowed paths.
5. Preserve research-only boundaries and live preflight behavior.
6. Prefer provider-backed fixture evidence over synthetic evidence for empirical claims.
7. Keep WT3D, KNN, and any advanced model feature-agnostic and comparator-backed.
8. Treat candidate-pack absence as valid evidence when gates block weak candidates.
9. Record close evidence in a stage report and update the ledger.

## Quick Orientation For Future Agents

Start with these files:

- `AGENTS.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/full_cycle_btc_v1.json`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `docs/stage_reports/STAGE_R44_FINAL_CROSSCHECK_HARDENING_REPORT.md`

The safest mental model is: this branch is a research evidence factory. It can collect, replay, compare, reject, and package historical evidence. It must not trade, promote, or imply that local research evidence is live-ready.
