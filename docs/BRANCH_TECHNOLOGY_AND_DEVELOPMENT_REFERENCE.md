# Branch Technology And Development Reference

Date: 2026-05-13
Branch: `research/v3-experimental-engine`
Scope: research infrastructure, historical evidence, discovery experiments, and
live-boundary safety

## Purpose

This document is the compact reference for what this branch is built from, what
has been implemented, how the main research logic works, and which boundaries
must not be crossed.

Use it together with:

- `AGENTS.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/contracts/`
- `docs/stage_reports/`

## One Sentence Summary

This branch is a research-only evidence factory: it turns provider/archive data
into validated fixtures, point-in-time features, strategy candidates,
backtests, discovery evidence, gates, and research-only artifacts while
refusing to produce live signals or promotion-ready outputs.

## Current Branch State

- Active package: `src/tradingbotsuite/`
- Legacy compatibility package: `src/tradingbot/`
- Build metadata: `pyproject.toml`
- Distribution name: `tradingbotsuite`
- Canonical console script: `tradingbotsuite`
- Legacy console script: `tradingbot`
- Current invariant: research outputs stay `research_only`, `observe_only`,
  and `promotion_ready: false`
- Stage 13 paper, shadow, testnet, canary, live, and promotion execution remain
  blocked unless a later promotion process explicitly changes scope.

## Technology Stack

| Area | Technology | Used For |
| --- | --- | --- |
| Language/runtime | Python `>=3.11` | Main package, CLI, research jobs, tests. |
| Build system | `setuptools`, `wheel` | Source-layout package build from `src/`. |
| Table/data compute | `pandas`, `numpy` | Feature frames, metrics tables, backtest rows, research ledgers. |
| Columnar storage | `pyarrow`, Parquet | Fixture data, feature caches, backtest indices, evidence tables. |
| Config/validation | `pydantic`, JSON, YAML | App config, research specs, manifests, legacy config loading. |
| Web/operator UI | `fastapi`, `uvicorn`, `jinja2`, `itsdangerous`, `python-multipart` | Local operator surfaces, research status, form/API handling. |
| Provider/API IO | `httpx`, `websockets` | REST/WebSocket connectivity for provider and runtime-adjacent surfaces. |
| Local persistence | `aiosqlite`, SQLite | Runtime/operator persistence surfaces. |
| ML/research | `scikit-learn`, `scipy` | Research transforms, KNN, diagnostics, stability helpers. |
| Optional research models | `hmmlearn`, `xgboost` | HMM/GMM/KNN-style diagnostics and model experiments. |
| Optional data provider | `lakeapi` | Crypto Lake free-sample fallback, diagnostic unless broader evidence exists. |
| Optional GPU | `cupy-cuda12x`, NVIDIA CUDA runtime/NVRTC/cuBLAS wheels | Diagnostic CUDA KNN/backtest screening paths. |
| Live-adjacent SDK | `hyperliquid-python-sdk` | Adapter/runtime surfaces guarded away from research modules. |
| Test tooling | `pytest`, `pytest-asyncio`, `hypothesis` | Contract, integration, property, async, and regression tests. |

Primary artifact formats:

- JSON for manifests, configs, reports, and resolved specs.
- Parquet for fixtures, feature caches, backtest indices, rankings, and gate
  tables.
- Markdown for stage reports, work packets, runbooks, and rejection reports.
- SQLite for local runtime/operator persistence, not for research evidence
  tables.

## Package Map

| Package | Role |
| --- | --- |
| `tradingbotsuite.data` | Provider manifests, data contracts, fixture-pack validation/building, Parquet storage. |
| `tradingbotsuite.features` | Feature registry, completed-bar alignment, context joins, feature packs, deterministic feature cache. |
| `tradingbotsuite.strategies` | Strategy plugin contract, registry, bounded metadata, research signal validation. |
| `tradingbotsuite.backtesting` | Reference engine, vector fixed-holding engine, CUDA diagnostic engines, exits, splits, costs, metrics. |
| `tradingbotsuite.optimization` | Candidate identity, search spaces, optimizer, scoring, stability regions, GPU screening. |
| `tradingbotsuite.research_cycle` | Main historical-cycle spec, runner, benchmark, candidate ranking, gate orchestration. |
| `tradingbotsuite.research_discovery` | V4 discovery specs, run manager, ledgers, snapshots, telemetry, validation floors, bridge checks. |
| `tradingbotsuite.research_artifacts` | Research candidate-pack gate validation and pack writing. |
| `tradingbotsuite.research` | Dataset/model/evaluation tools, HMM/KNN research, feature ablation, market data collection. |
| `tradingbotsuite.live` | Live preflight and shadow loader guards. |
| `tradingbotsuite.promotion` | Promotion/shadow artifact validators and readiness planning templates. |
| `tradingbotsuite.web` | FastAPI/Jinja operator UI. |
| `tradingbotsuite.ui` | Earlier research UI app and job/status surfaces. |
| `tradingbotsuite.core`, `tradingbotsuite.adapters`, `tradingbotsuite.runtime`, `tradingbotsuite.persistence` | Runtime-adjacent and legacy/operator foundations. Research packages must not import order-placement paths from here. |

## Development Logic

The branch follows a work-packet and evidence-led development model:

1. Check the ledger and issue registry.
2. Open a scoped work packet before edits.
3. Keep edits inside allowed paths.
4. Preserve research-only and live-boundary invariants.
5. Add or update focused tests for changed behavior.
6. Run baseline validation and broaden validation for shared contracts.
7. Close with a stage report and ledger update.

The research dataflow is:

```text
provider/archive/local manifest data
  -> validated fixture pack or dataset manifest
  -> provenance, hashes, row counts, gap/duplicate evidence
  -> completed-bar/as-of feature materialization
  -> deterministic feature-cache identity
  -> validation splits and holdout definitions
  -> strategy candidate space
  -> reference/vector/CUDA-diagnostic backtests
  -> split, regime, side, cost-stress, ablation, and stability evidence
  -> candidate rankings and gate reports
  -> research-only candidate pack only if all gates pass
```

Most rejected rows are expected fail-closed outcomes. Candidate-pack absence is
valid evidence when gates reject weak, incomplete, synthetic, latest-window-only,
or non-durable results.

## Implemented Subsystems

### Governance And Contracts

Implemented:

- Orchestrator stage ledger.
- Work-packet model.
- Stage report audit trail.
- Known-issues blocking registry.
- Contract docs for data, features, strategies, backtesting, artifacts,
  boundaries, and promotion.
- Import-boundary tests that prevent research modules from depending on live
  order-placement adapters.

Key files:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/`
- `docs/stage_reports/`
- `docs/contracts/`
- `tests/contracts/`

### Data Intake And Fixture Packs

Implemented:

- Provider manifest contract with source, family, symbol, interval, timestamp,
  hash, row-count, and research-boundary metadata.
- Binance REST and Binance Vision intake surfaces.
- Crypto Lake free-sample fallback, explicitly diagnostic unless stronger
  evidence exists.
- Hyperliquid/archive surfaces where supported by manifests.
- Local fixture-pack builder and validator.
- Unsafe-source rejection for synthetic/TradingView-style provenance when
  provider-backed evidence is required.
- Optional context families for funding, premium, open interest, aggregate
  trade flow, liquidation, lower-timeframe bars, and cross-symbol context.
- Checked BTCUSDT fixtures and generated context fixtures with provenance.
- Durable BTC/ETH public archive readiness contracts.

Key files:

- `src/tradingbotsuite/data/contracts.py`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/data/storage/parquet_store.py`
- `src/tradingbotsuite/research/market_data.py`
- `data/research/fixtures/`
- `tests/contracts/test_data_contracts.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`

### Feature Construction

Implemented:

- Registered, versioned feature packs.
- Completed-bar validation and point-in-time alignment.
- Backward as-of context joins.
- Explicit missingness/quality flags.
- Deterministic feature-cache identity.
- Interval-aware rolling windows.
- Train-only preprocessing boundaries.
- Perp context v2/v3 source/version checks.
- AggTrade orderflow proxy feature pack.
- Liquidation context feature pack.
- BTC/ETH cross-asset residual features.
- WT3D feature variants with mandatory comparator context for claims.

Important feature families:

- Price path, returns, trend, volatility, chop.
- Perp funding, premium, basis, and open-interest context.
- AggTrade orderflow proxy context.
- Liquidation/free-sample diagnostic context.
- Cross-asset BTC/ETH residual context.
- WT3D oscillator family.

Key files:

- `src/tradingbotsuite/features/registry.py`
- `src/tradingbotsuite/features/alignment.py`
- `src/tradingbotsuite/features/builders.py`
- `src/tradingbotsuite/features/cache.py`
- `configs/features/`
- `tests/contracts/test_feature_contracts.py`
- `tests/features/test_feature_builders.py`

### Strategy Framework

Implemented:

- Strategy plugin protocol with `prepare`, `predict`, and `explain`.
- Strategy registry and config validation.
- Bounded parameter metadata.
- Required-feature and holding-window validation.
- Signal-frame validation including side, timestamp, score, holding window,
  and `skip_reason` semantics.
- Transparent no-trade/comparator coverage.

Implemented strategy families include:

- No-trade baseline.
- Trend following.
- Volatility breakout.
- Range reversion.
- Funding/basis convergence.
- Funding crowding fade.
- Open-interest flow breakout.
- Funding-window timing.
- Regime-adaptive research variants.
- HMM/KNN diagnostic and local-analog filters.
- Liquidation absorption classifier.
- LC reference/legacy comparison surfaces.

Key files:

- `src/tradingbotsuite/strategies/contracts.py`
- `src/tradingbotsuite/strategies/registry.py`
- `src/tradingbotsuite/strategies/parameters.py`
- `configs/strategies/`
- `configs/research/strategy_family_matrix_existing_plugins_v1.json`
- `tests/contracts/test_strategy_contracts.py`

### Backtesting And Exits

Implemented:

- Artifact-rich reference backtest engine.
- Vector fixed-holding primary-bar engine with parity tests.
- Optional CUDA fixed-holding and CUDA batched engines, diagnostic only.
- Execution simulator with fees, slippage, spread, and funding costs.
- Split definitions including purged, rolling, shifted, month holdout,
  stress-period holdout, and regime holdout.
- Fixed-holding exits.
- Lower-timeframe triple-barrier sequencing with fail-closed lower-timeframe
  requirements.
- Research exit policies for volatility, regime, funding, remaining edge,
  adverse selection, trailing after profit, and maximum MAE.
- Backtest identity/cache evidence and deterministic artifact outputs.

Key files:

- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `src/tradingbotsuite/backtesting/cuda_engine.py`
- `src/tradingbotsuite/backtesting/cuda_batched_engine.py`
- `src/tradingbotsuite/backtesting/exits.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/splits.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/backtesting/`

### Optimization, Stability, And Candidate Gates

Implemented:

- Candidate config and result identity.
- Search-space expansion from specs and strategy metadata.
- Deterministic candidate/result cache.
- Parallel evaluator parity checks.
- Spike rejection.
- Stability-region search and local-neighborhood evidence.
- Bootstrap and overfit diagnostics.
- Trial-budget accounting.
- Candidate ranking with costed scoring.
- Evidence floors for trade counts, splits, cost stress, side concentration,
  regime evidence, ablations, stability, and comparator dominance.
- Durable candidate-pack gates.

Key files:

- `src/tradingbotsuite/optimization/`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `tests/optimization/`
- `tests/research_artifacts/test_candidate_pack.py`

### Historical Research Cycle

Implemented:

- Historical-cycle spec model.
- Fixture/source loading and validation.
- Feature materialization and cache reuse.
- Validation split generation.
- Strategy candidate generation.
- Aggregate, split, stress, ablation, and stability backtests.
- Candidate rankings.
- Gate reports and rejection reports.
- Candidate-pack attempt only when all evidence gates pass.
- Benchmark tiers and evidence-completeness gates.
- Compute policy with fastest parity-safe default.

Default compute posture after R97:

- `gpu_execution_profile: fastest_exact`
- `cpu_threads: 48`
- aggregate fixed-holding screening prefers `vector_fixed_holding` where
  supported
- validation remains reference-backed when required
- CUDA and Tensor Core routes remain opt-in diagnostic evidence paths
- no production speedup claim is made

Key files:

- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `configs/research/`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/`

### V4 Discovery Engine

Implemented:

- Discovery run manager.
- Flexible feature-column sets.
- Split-safe GMM/regime materialization and naming truthfulness.
- Regime-local KNN study engine.
- WT/KNN strategy candidate integration.
- Perp context filter ablation matrix.
- Exit lab.
- Deep discovery benchmarks.
- Candidate-pack bridge eligibility checks.
- Runtime optimization, vectorized KNN prediction, deterministic top-k, GMM
  vectorized assignment, HMM label cache, and batched state checkpoints.
- Independent-event accounting and score v2.
- Mandatory exit-lab gate.
- Matched filter ablation v2.
- Multiple-testing and stability gates.
- Validation floors and blocker registry.
- Compute telemetry and cached KNN sweeps.
- Operator discovery UI and truthfulness modernization.

Important truthfulness corrections:

- GMM/current-regime evidence is not mislabeled as true HMM transition
  evidence.
- Dense overlapping 72h events are not treated as independent evidence without
  explicit independent-event accounting.
- Latest-window provider evidence remains diagnostic unless durable
  multi-window contracts are met.
- Exit, filter, feature, and multiple-testing evidence must pass explicit
  gates before candidate-ready claims.

Key files:

- `src/tradingbotsuite/research_discovery/spec.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/validation_floors.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `configs/discovery/`
- `tests/research_discovery/`

### Research Dataset, Model, And Evaluation Tools

Implemented:

- Dataset building and manifests.
- Base model training and calibrated artifact manifests.
- Replay evaluation metrics.
- Shared fail-closed research artifact boundary metadata.
- HMM/KNN research preparation, sweeps, replay, monitoring, and experiments.
- Feature ablation planning and execution through real research backtests when
  dataset evidence exists.

After R98, legacy research dataset/model/evaluation outputs now carry:

```text
research_only: true
observe_only: true
promotion_ready: false
live_signal_input: false
position_sizing_input: false
operator_control_input: false
live_execution_input: false
runtime_control_input: false
```

Key files:

- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/modeling.py`
- `src/tradingbotsuite/research/evaluation.py`
- `src/tradingbotsuite/research/live_readiness.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/experiment_runner.py`
- `src/tradingbotsuite/research/feature_ablation.py`
- `tests/tradingbotsuite/test_research.py`

### Candidate Packs And Promotion Boundary

Implemented:

- Research candidate-pack validator.
- Required evidence table checks.
- Fixture provenance and row/hash validation.
- Split, cost, ablation, stability, and gate evidence checks.
- Live-adjacent rejection fields.
- Discovery candidate-pack bridge eligibility checks.
- Blocker-registry hash and payload validation.
- Explicit exit-lab gate status checks.

Candidate packs are still research artifacts. They are not live signals and not
promotion-ready outputs.

Key files:

- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `src/tradingbotsuite/research_discovery/validation_floors.py`
- `tests/research_artifacts/test_candidate_pack.py`
- `tests/research_discovery/test_candidate_pack_bridge.py`

### Operator And Research UI

Implemented:

- FastAPI/Jinja operator UI.
- Research tab with artifact summaries, historical-cycle status, blockers,
  candidate gates, discovery snapshots, compute profile, and backend evidence.
- Research job actions with live-mode and output-path guards.
- Older Stage 9 research UI for manifest-linked pages and job API.
- Stage 13 readiness/shadow review surfaces remain planning/read-only.

Key files:

- `src/tradingbotsuite/web/app.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/ui/research_app.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/integration/test_research_ui.py`

## CLI And Command Surface

Canonical installed command:

```powershell
tradingbotsuite --help
```

Module form:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main --help
```

Legacy compatibility command:

```powershell
tradingbot --help
```

Research commands registered for live-mode rejection include:

- `benchmark-discovery-run`
- `benchmark-historical-research-cycle`
- `benchmark-research-experiment`
- `build-dataset`
- `build-historical-fixture-pack`
- `calibrate-model`
- `collect-binance-bars`
- `collect-binance-context`
- `evaluate-discovery-candidate-pack-eligibility`
- `fetch-binance-vision`
- `fetch-crypto-lake`
- `monitor-hmm-knn`
- `plan-feature-ablation`
- `plan-stage12-research`
- `plan-stage13-readiness`
- `prepare-hmm-knn-research-data`
- `replay-eval`
- `replay-hmm-knn`
- `research`
- `research-hmm-knn`
- `run-discovery`
- `run-hmm-knn-experiments`
- `run-historical-research-cycle`
- `run-research-experiment`
- `train-model`
- `write-hmm-knn-sweep-datasets`

Command registry source:

- `src/tradingbotsuite/research/command_registry.py`

## Stage History Summary

### Stage 0-13: Branch Foundation

Built governance, repo inventory, contract docs, data manifests, feature
registry, backtest engine, strategy plugins, HMM/KNN diagnostics, generic
experiment runner, research UI, live preflight rejection, promotion/shadow
validators, feature ablation planning, and Stage 13 readiness planning. Stage
13 execution remained blocked.

### R0-R24: Historical Research Engine Hardening

Moved from placeholder research to real historical research cycles: fixture
backtests, split/exit/feature foundations, materialized feature cache,
optimizer stability, candidate-pack provenance gates, vector fixed-holding
parity, expanded exit policies, validation split modes, and evidence floors.

### R25-R44: Provider Context Evidence And First Completion Point

Added lower-timeframe triple-barrier evidence, context-family materialization,
benchmark gates, checked BTCUSDT fixtures, Binance USD-M context collection,
latest-month provider context cycles, provider-backed benchmark evidence,
WT3D/full-context ablation, and final crosscheck hardening. R44 was the first
documented research-engine completion point.

### R45-R66: Perp Strategy And Data Expansion

Added branch distillation, perp strategy roadmap alignment, Crypto Lake
free-sample fallback, perp context manifests/features, perp basis/funding/OI
strategies, ETH mirror fixture cycles, funding/OI exits, trial-budget
diagnostics, split-safe HMM/KNN surfaces, liquidation fixture/features, and
interval-aware feature building.

### R67-R92: Operator UX And V4 Discovery Engine

Added the dependency fuse, operator quickstart and research UI expansion,
discovery run manager, flexible feature columns, split-safe regime
materialization, regime-local KNN, KNN strategy candidates, filter ablation,
exit lab, candidate-pack bridge, deep discovery benchmarks, vectorized
prediction/assignment, deterministic top-k, batched checkpoints, and final
branch crosscheck.

### R93-R94: Truthfulness And BTC/ETH Roadmap Execution

Converted planning findings into branch hardening: regime naming truthfulness,
independent-event score v2, mandatory exit-lab gates, matched filter ablation
v2, multiple-testing/stability gates, validation floors, durable BTC/ETH public
archive readiness contracts, perp context source/version audit, AggTrade
orderflow features, cached KNN sweeps, exit model upgrades, strategy-family
matrix, BTC/ETH blueprints, cross-asset residual features, and research UI
truthfulness.

### R95-R98: Compute And Boundary Hardening

Added candidate-selection performance accounting, optional diagnostic CUDA
fixed-holding parity, opt-in CUDA/Tensor Core screening, fastest parity-safe
default compute behavior, 48-worker default, research UI compute summaries, and
R98 research-boundary hardening for legacy research artifacts, validation-floor
exit-lab gate checks, blocker-registry integrity, and CLI naming.

### R99: This Reference Document

Adds this single durable technology/development reference. It does not change
code, artifacts, live behavior, promotion, candidate-pack writing, or sizing.

### R100-R103: Capability Gates And Durable Data Foundation

Added provider capability metadata, source capability revalidation, direct CLI
research output-root allowlisting, expanded live-adjacent import-boundary
coverage, capability-aware research/candidate/discovery gates, the
`tradingbotsuite` distribution identity, and compact checksum-verified
BTCUSDT/ETHUSDT Binance Vision multi-window fixture packs. These fixtures are
research-only data-foundation artifacts, not candidate-ready performance or
promotion evidence.

## Live And Promotion Boundary

Hard rules:

- Research outputs are not live signals.
- Research outputs are not position sizing inputs.
- Research outputs are not live config.
- Research jobs must not place orders.
- Research jobs must not change runtime mode.
- Research jobs must not write live configuration.
- Research modules must not import live order-placement adapters.
- Research artifacts must remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Promotion/shadow/testnet/live execution is outside this branch scope unless a
  later governed promotion process changes that explicitly.

Boundary files:

- `docs/contracts/boundary_contract.md`
- `src/tradingbotsuite/live/preflight.py`
- `src/tradingbotsuite/live/shadow_loader.py`
- `src/tradingbotsuite/promotion/artifact_validator.py`
- `tests/live/`
- `tests/contracts/test_import_boundaries.py`

## Validation Strategy

Minimum branch baseline:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Broaden tests by touched area:

| Area changed | Add validation |
| --- | --- |
| Data/fixtures | `tests/contracts/test_data_contracts.py`, `tests/contracts/test_historical_fixture_pack_contract.py` |
| Features | `tests/contracts/test_feature_contracts.py`, `tests/features/test_feature_builders.py` |
| Strategies | `tests/contracts/test_strategy_contracts.py`, integration backtest fixture tests |
| Backtesting/exits | `tests/contracts/test_backtest_contracts.py`, `tests/backtesting/`, `tests/unit/test_execution_simulator.py` |
| Research cycle | `tests/contracts/test_research_cycle_contract.py`, `tests/historical/` |
| Optimization | `tests/optimization/` |
| Research artifacts | `tests/research_artifacts/test_candidate_pack.py` |
| Discovery | `tests/research_discovery/` |
| Live/promotion boundary | `tests/live/`, `tests/contracts/test_import_boundaries.py` |
| UI/operator | `tests/tradingbotsuite/test_operator_ui.py`, `tests/integration/test_research_ui.py` |

For docs-only changes, `git diff --check` plus the branch baseline is enough
unless the docs describe changed contracts or commands.

## Known Deferred Work

Deferred items recorded by recent closeout context:

- Stage 13 paper/shadow/testnet/canary/live execution.
- Any promotion authorization workflow.
- Live signal generation and position sizing.
- Legacy `tradingbot` package and console compatibility remain; new packaging
  and docs should orient around the `tradingbotsuite` distribution and console
  command.
- Rerunning historical cycles and discovery validation on the durable public
  archive BTC/ETH fixture packs.
- Production no-regime-baseline ladder reporting.
- True HMM transition evidence distinct from current GMM/regime labels.
- True L2/order-book/depth OFI features.
- Liquidation evidence becoming candidate-pack eligible.
- Any claim that optional CUDA/Tensor Core paths are production speedups.

## High-Risk Rewrite Areas

Treat these as shared-contract areas:

- `src/tradingbotsuite/data/`
- `src/tradingbotsuite/features/`
- `src/tradingbotsuite/strategies/`
- `src/tradingbotsuite/backtesting/`
- `src/tradingbotsuite/optimization/`
- `src/tradingbotsuite/research_cycle/`
- `src/tradingbotsuite/research_discovery/`
- `src/tradingbotsuite/research_artifacts/`
- `src/tradingbotsuite/live/`
- `src/tradingbotsuite/promotion/`
- `docs/contracts/`
- checked `data/research/fixtures/`
- committed `data/research/historical_cycles/`

Common failure modes to avoid:

- Marking research artifacts `promotion_ready: true`.
- Treating synthetic/latest-window/free-sample data as durable evidence.
- Dropping provenance hashes or row-count checks.
- Filling unknown context as zero.
- Weakening completed-bar or as-of feature alignment.
- Adding feature/cache identity changes without tests.
- Optimizing backtest execution assumptions.
- Letting CUDA/GPU diagnostic paths bypass reference validation.
- Allowing discovery artifacts through candidate-pack bridge without validation
  floors, exit-lab evidence, and blocker-registry integrity.
- Importing live order-placement paths into research modules.

## Quick Orientation For Future Work

Read these first:

1. `AGENTS.md`
2. `docs/ORCHESTRATOR_STAGE_LEDGER.md`
3. `docs/KNOWN_ISSUES.md`
4. `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
5. `docs/contracts/README.md`
6. This document
7. The package and tests for the area you plan to edit

Then open a work packet and keep the validation scope proportional to the
contract surface touched.
