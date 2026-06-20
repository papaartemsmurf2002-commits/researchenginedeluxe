# Repo Structure And Dependency Fuse

Date: 2026-06-04
Branch: `main` local mirror of `research/v3-experimental-engine`
Scope: modular strategy research, historical evidence, iteration speed, and
research/live separation

This document is a fuse for future agents. Read it before changing shared
research infrastructure. The branch is powerful because its contracts are
connected; casual rewrites in one package can silently invalidate data
provenance, feature identity, backtest evidence, candidate gates, or the
ability to compare strategy experiments cleanly.

## Current Status

The research development goals are complete for the documented branch scope:
the repo is ready to compute new strategy iterations and refine existing
families through reproducible evidence, not through live execution.

- Provider/archive intake exists for Binance REST, Binance Vision, Crypto Lake
  free-sample fallback, Hyperliquid archive surfaces, and local manifest inputs.
- Historical fixture packs validate provenance, hashes, row counts, optional
  context families, lower-timeframe bars, and research-only metadata.
- Registered feature sets materialize point-in-time completed-bar features,
  optional context, liquidation context, and deterministic feature caches.
- The historical research cycle loads fixtures, builds features, creates splits,
  generates strategy candidates, runs backtests, ranks candidates, writes gate
  evidence, and refuses weak candidates.
- Strategy plugins cover transparent baselines, perp context strategies,
  funding/OI/timing strategies, HMM/KNN filters, and liquidation absorption.
- Backtesting supports reference execution, vector fixed-holding execution,
  fixed holds, lower-timeframe triple-barrier policies, primary-bar research
  exits, cost/funding/stress evidence, and artifact manifests.
- Optimizer, stability, trial-budget, overfit diagnostics, feature ablation,
  benchmark evidence, candidate-pack gates, and research UI/CLI surfaces exist.
- The active strategy surface is structurally complete for research iteration:
  transparent baselines, trend/range/volatility, perp-context v2,
  funding/OI-flow, GMM/regime-assisted, HMM/KNN local analog, liquidation
  diagnostic, and LC reference plugins are registered and contract-covered.
- Research/live separation remains intact. This branch is not a live trading
  branch; the boundary exists so research outputs stay analyzable and do not
  get confused with execution instructions.

Current practical next work is optional and separate: checked local liquidation
cycle artifacts/configs or durable BTCUSDT/ETHUSDT liquidation context wiring.
WPR64 Crypto Lake free-sample liquidation evidence remains diagnostic only.

## Research Dataflow

```text
provider/archive data
  -> data manifest or fixture pack
  -> validated provenance, hashes, row counts, context metadata
  -> completed-bar and as-of feature materialization
  -> feature-cache identity
  -> historical-cycle validation splits
  -> strategy candidate space
  -> reference/vector backtests
  -> split, regime, side, cost-stress, ablation, stability evidence
  -> candidate rankings and gate report
  -> candidate pack only if all research gates pass
```

Every stage writes evidence. Most failures are intentional rejection outcomes,
not engine failures: a blocker, zero eligible row, failed ablation, or
validation-floor miss is data for the next iteration.

## Top-Level Repo Map

| Path | Role | Rewrite risk |
| --- | --- | --- |
| `AGENTS.md` | Branch rules for agents and validation baseline. | High: governs all work packets. |
| `START_HERE.md` | Human/agent onboarding entrypoint. | Medium: keep current stage guidance accurate. |
| `README.md` | Install, validation, and command summary. | Medium: public-facing orientation. |
| `docs/ORCHESTRATOR_STAGE_LEDGER.md` | Stage ledger and packet registry. | High: stage control source. |
| `docs/KNOWN_ISSUES.md` | Blocking issue registry. | High: stage advancement gate. |
| `docs/contracts/` | Data, feature, strategy, backtest, artifact, promotion, boundary contracts. | High: tests enforce these. |
| `docs/work_packets/` | Scoped work packets. | High: defines allowed paths. |
| `docs/stage_reports/` | Stage close evidence and validation. | Medium: audit trail. |
| `configs/research/` | Historical-cycle specs. | High: checked evidence wiring. |
| `configs/features/` | Feature preset manifests. | High: feature identity and cache hashes. |
| `configs/strategies/` | Strategy configs. | High: plugin contract and default behavior. |
| `data/research/fixtures/` | Checked fixture packs and diagnostic fixtures. | High: evidence provenance. |
| `data/research/historical_cycles/` | Checked local cycle evidence where committed. | High: do not overwrite casually. |
| `src/tradingbotsuite/` | Active research/runtime package. | High: main branch implementation. |
| `src/tradingbot/` | Legacy package still present for older surfaces/tests. | Medium: do not mix into new research work unless scoped. |
| `tests/` | Contract, historical, live-boundary, feature, optimization, artifact tests. | High: branch safety net. |

## Active Package Map

| Package | Purpose | Critical dependencies |
| --- | --- | --- |
| `tradingbotsuite.data` | Data contracts, provider manifests, fixture-pack validation/building, storage. | Feeds research cycle, feature joins, candidate-pack provenance. |
| `tradingbotsuite.features` | Feature registry, completed-bar alignment, optional context materialization, cache identity. | Feeds strategies and backtests; cache identity must match data/context/interval. |
| `tradingbotsuite.strategies` | Plugin contract, registry, configs, bounded metadata, signal validation. | Feeds candidate generation, optimizer, backtest engine. |
| `tradingbotsuite.backtesting` | Reference/vector engines, splits, exits, execution simulator, metrics. | Feeds research-cycle rankings, gates, candidate packs. |
| `tradingbotsuite.optimization` | Search spaces, candidate configs/results, cache, scorer, stability. | Feeds rankings, stability evidence, gate decisions. |
| `tradingbotsuite.research_cycle` | Spec, runner, benchmark; main orchestration layer. | Connects every research subsystem. |
| `tradingbotsuite.research_artifacts` | Candidate-pack gate and pack writing/validation. | Enforces evidence and live-adjacent rejection. |
| `tradingbotsuite.research` | HMM/KNN, data pipeline, feature ablation, stage planning, market data tooling. | Produces research artifacts and provider inputs. |
| `tradingbotsuite.live` | Live preflight and shadow loader guards. | Must reject research commands/artifacts from live execution. |
| `tradingbotsuite.promotion` | Promotion validators and readiness templates. | Must keep research artifacts non-live unless later approved. |
| `tradingbotsuite.web`, `tradingbotsuite.ui` | Research/job diagnostics and read-only operator surfaces. | Must remain thin visibility/control surfaces. |
| `tradingbotsuite.core`, `tradingbotsuite.adapters`, `tradingbotsuite.runtime` | Runtime/live-adjacent legacy and operator surfaces. | Do not import into research/data/features/backtesting/strategies. |

## Framework And Dependency Map

The branch is a Python 3.11 package installed from `pyproject.toml` with
`setuptools`. It is not a monolith: provider intake, research computation,
operator UI, and live-adjacent guards share typed contracts and manifests.

| Dependency family | Used for | Rewrite caution |
| --- | --- | --- |
| `pandas`, `numpy`, `pyarrow` | Dataframes, Parquet fixtures, feature frames, backtest/evidence tables. | Preserve schemas, dtypes, timestamps, and sorted completed-bar semantics. |
| `pydantic` | Runtime and research config models. | Keep defaults fail-closed and compatible with CLI/env loading. |
| `fastapi`, `uvicorn`, `jinja2`, `itsdangerous`, `python-multipart` | Operator and research UI surfaces. | UI must remain thin; command/live guards belong below the route layer too. |
| `httpx`, `websockets` | Provider/runtime connectivity. | Provider failures must produce truthful metadata, not silent synthetic data. |
| `aiosqlite` | Local operator/runtime persistence surfaces. | Do not mix with generated research evidence storage. |
| `PyYAML` | Legacy and helper config loading. | Prefer JSON contracts for current research specs unless existing surface requires YAML. |
| `scikit-learn`, `scipy` | Research modeling, KNN/diagnostics, feature transforms, stability helpers. | Fit only on training splits; never leak validation/OOS rows into fitted transforms. |
| `hyperliquid-python-sdk` | Live-adjacent adapter surfaces. | Research modules must not import order-placement adapters. |
| Optional `lakeapi` | Crypto Lake free-sample fallback. | Treat free sample data as diagnostic/latest-window only unless broader evidence is added. |
| Optional `hmmlearn`, `xgboost`, GPU extras | Research-only modeling experiments. | Keep model fitting split-safe and artifact-labeled as research-only. |

## Extension Checklist

Use this when adding new capability:

| New capability | Required touchpoints |
| --- | --- |
| Provider/source | Data contract, manifest metadata, provenance labels, gap/duplicate/hash tests, runbook if operator setup is needed. |
| Feature pack | Registry entry, preset config, completed-bar/context behavior, cache identity coverage, contract and feature-builder tests. |
| Strategy plugin | Strategy module, registry/config/metadata, required features, bounded defaults, signal validation, comparator status decision, contract and backtest tests. |
| Exit policy | Exit registry/engine/vector behavior, lower-timeframe requirements, cost/funding semantics, backtest contract tests. |
| Research-cycle spec | Config, fixture/source wiring, split and comparator coverage, evidence outputs, historical tests. |
| Optimizer/gate rule | Candidate identity, stability/gate report fields, artifact validation, optimization and candidate-pack tests. |
| UI/command surface | Route/API plus service-layer guard, live-mode rejection, path/output allowlists, integration tests. |

## Unsafe To Rewrite Casually

These areas have cross-module contracts. Change them only inside a work packet
with focused tests and usually full contracts.

### Data And Fixture Provenance

Critical files:

- `src/tradingbotsuite/data/contracts.py`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/research/market_data.py`
- `tests/contracts/test_data_contracts.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`

Do not remove or weaken:

- `research_only`, `observe_only`, `promotion_ready: false`
- content hashes and row-count checks
- unsafe-source rejection
- fixed-interval gap/duplicate evidence
- optional context metadata such as `coverage_scope`, `latest_window_only`,
  `source_access_mode`, `diagnostic_only`, `free_sample_data`
- fixture `base_interval` and family interval semantics

Fixture manifests feed feature identity, data-quality reports, candidate-pack
source validation, and live-boundary rejection. A small provenance shortcut can
turn diagnostic evidence into misleading acceptance evidence.

### Feature Registry, Builders, And Cache

Critical files:

- `src/tradingbotsuite/features/registry.py`
- `src/tradingbotsuite/features/alignment.py`
- `src/tradingbotsuite/features/builders.py`
- `src/tradingbotsuite/features/cache.py`
- `src/tradingbotsuite/features/packs.py`
- `tests/contracts/test_feature_contracts.py`
- `tests/features/test_feature_builders.py`

Do not remove or weaken:

- completed-bar validation
- as-of and windowed context joins
- explicit missingness columns
- interval-aware rolling windows
- `FeatureCacheIdentity` fields
- feature manifest hashes
- train-only preprocessing boundaries

Feature frames are consumed by every strategy and backtest. Cache keys must
change when data, feature definitions, context, interval, or builder identity
changes.

### Historical Research Cycle

Critical files:

- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_cycle/benchmark.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/`

Do not remove or weaken:

- manifest writing and required outputs
- data-source provenance propagation
- feature-build identity checks
- split namespaces and validation evidence
- baseline comparator injection/coverage
- candidate, feature, backtest, and stability identity columns
- trial-budget, overfit, ablation, and gate reports
- live/research boundary flags

The runner is the main orchestration seam. Most shared package contracts meet
here, so refactors need broad validation.

### Strategy Contract And Metadata

Critical files:

- `src/tradingbotsuite/strategies/contracts.py`
- `src/tradingbotsuite/strategies/registry.py`
- `src/tradingbotsuite/strategies/parameters.py`
- strategy modules under `src/tradingbotsuite/strategies/`
- `configs/strategies/`
- `tests/contracts/test_strategy_contracts.py`

Do not remove or weaken:

- required feature-set and holding-window validation
- empty `skip_reason` for accepted trade signals
- non-empty `skip_reason` only for skipped/no-trade rows
- bounded metadata spaces
- strategy config validation
- fail-closed missing-context behavior
- research-only signal fields

Strategies are normal research candidates unless explicitly declared as
comparators. Do not add advanced strategies to transparent comparator lists by
accident.

### Backtesting And Exit Semantics

Critical files:

- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `src/tradingbotsuite/backtesting/exits.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/splits.py`
- `src/tradingbotsuite/backtesting/metrics.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/backtesting/`

Do not remove or weaken:

- same-bar entry/exit assumptions
- fees, slippage, spread, and funding costs
- lower-timeframe sequencing requirements for triple-barrier exits
- fixed-holding vector support checks
- cache-key components
- split/purge/embargo logic
- non-finite context fail-closed behavior

Backtest artifacts become ranking and gate evidence. Optimistic execution
assumptions corrupt the whole research pipeline.

### Optimizer, Stability, And Candidate Gates

Critical files:

- `src/tradingbotsuite/optimization/`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `tests/optimization/`
- `tests/research_artifacts/test_candidate_pack.py`

Do not remove or weaken:

- duplicate candidate handling
- deterministic candidate/result identity
- costed scoring
- spike rejection and stability-region requirements
- split/trade-floor/gate evidence
- fixture provenance checks
- candidate-pack required outputs
- live-adjacent artifact rejection

A candidate pack is not a performance claim. It is still research-only unless a
later promotion process changes it.

### Research/Live Separation

Critical files:

- `src/tradingbotsuite/live/preflight.py`
- `src/tradingbotsuite/live/shadow_loader.py`
- `src/tradingbotsuite/promotion/artifact_validator.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/contracts/test_import_boundaries.py`
- `tests/live/`

Do not remove or weaken:

- research-command rejection in live mode
- research-artifact rejection as live order inputs
- promotion/shadow validation checks
- import-boundary tests preventing research modules from importing order paths

This branch can contain live-adjacent code, but research modules must not place
orders or mutate live runtime state. The point is not to build a strong live
guardrail system here; it is to keep research artifacts separate enough that
strategy evidence can be trusted, compared, and iterated.

## Generated Data And Artifacts

Treat checked fixture and cycle outputs as evidence, not scratch space.

Do not overwrite or regenerate these casually:

- `data/research/fixtures/btcusdt_v1/`
- `data/research/fixtures/btcusdt_context_provider_latest_month_v1/`
- `data/research/fixtures/ethusdt_context_provider_latest_month_v1/`
- `data/research/fixtures/btcusdt_liquidation_free_sample_v1/`
- committed `data/research/historical_cycles/**` evidence

Temporary cycle tests should write under `tmp_path`. Large provider caches,
local downloads, credentials, `.env`, SQLite databases, and unreviewed generated
artifacts should stay out of git.

## Research Evidence Controls

Future agents must preserve these evidence-quality controls. They are not the
project mission by themselves; they keep the mission honest while the platform
tests and refines strategies quickly.

- Research outputs are not live signals.
- Local cycle evidence is not a profit claim.
- Diagnostic free-sample data is not broad OOS/stress evidence.
- Synthetic data is for tests and benchmark tiers, not provider-backed
  candidate-pack eligibility.
- Context with unknown windows is missing, not zero.
- Latest-window endpoint evidence must be labeled and cannot support multi-year
  claims.
- Advanced features such as WT3D, HMM/KNN, and liquidation context require
  comparator and provenance evidence before any claim.
- Candidate-pack absence can be correct when gates reject weak candidates.
- Rejection reports, blocker codes, ablations, multiple-testing evidence, and
  validation-floor misses are first-class research outputs.

## Safe Change Pattern

1. Read `AGENTS.md`, this document, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, and
   `docs/KNOWN_ISSUES.md`.
2. Open a work packet before editing.
3. Keep edits inside the packet paths.
4. Preserve manifest and hash identity when touching artifacts.
5. Add focused tests for changed behavior.
6. Run at least:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

7. Broaden tests when touching shared packages:

| Touched area | Add validation |
| --- | --- |
| `data`, fixture packs | `tests/contracts/test_data_contracts.py`, `tests/contracts/test_historical_fixture_pack_contract.py` |
| `features` | `tests/contracts/test_feature_contracts.py`, `tests/features/test_feature_builders.py` |
| `strategies` | `tests/contracts/test_strategy_contracts.py`, integration backtest fixture tests |
| `backtesting` | `tests/contracts/test_backtest_contracts.py`, `tests/backtesting/` |
| `research_cycle` | `tests/contracts/test_research_cycle_contract.py`, `tests/historical/` |
| `optimization` | `tests/optimization/` |
| `research_artifacts` | `tests/research_artifacts/test_candidate_pack.py` |
| live/promotion boundary | `tests/live/`, `tests/contracts/test_import_boundaries.py` |

## Red Flags

Stop and open/record an issue if a change:

- makes a research artifact `promotion_ready: true`
- imports live execution adapters into research/data/features/backtesting or
  strategies
- removes hashes, manifests, or row-count checks
- silently fills unknown context as zero
- changes cache identity without test coverage
- loosens backtest execution assumptions
- bypasses baseline comparator or candidate-gate evidence
- rewrites checked fixture/cycle evidence without a stage report
- adds live command execution to research workflows

## Quick Start For Future Agents

Read in this order:

1. `AGENTS.md`
2. `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
3. `docs/ORCHESTRATOR_STAGE_LEDGER.md`
4. `docs/KNOWN_ISSUES.md`
5. `docs/contracts/README.md`
6. `docs/RESEARCH_BRANCH_DISTILLATION.md`
7. The package root you plan to edit
8. The relevant tests under `tests/contracts/` and focused area tests

If a proposed change cuts across more than one critical package, assume it is a
shared-contract change and broaden validation accordingly.
