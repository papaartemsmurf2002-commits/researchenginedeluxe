# ResearchEngineDeluxe

ResearchEngineDeluxe v2 is a research-only, data-first, multi-instrument
perpetual-futures research platform. Its active direction is Hyperliquid-first:
discover and archive perpetual instruments above USD 5,000,000 daily notional
volume, enforce 2024+ data, 6+ usable months, 0.98 coverage, dynamic lockbox,
and as-of universe rules, then evaluate agent-safe strategy ideas through
strict non-promotable research evidence.

BTC and ETH remain useful fixture, smoke-test, reference, and legacy evidence
symbols. They are not the full v2 product scope.

The project is not a live trading system, paper trading system, execution
system, sizing system, order-placement system, or promotion system. The
research boundary exists to keep evidence clean: outputs are manifests,
metrics, rejections, ablations, validation floors, multiple-testing reports,
lead diagnostics, and audit records, not paper/live signals, sizing
instructions, order-placement behavior, or promotion authorization.

The active Python package is still named `tradingbotsuite` for compatibility.
This repository contains two related Python codebases:

- `tradingbot`: the legacy Lorentzian Classification signal-generation, backtest, optimization, and data-cache package.
- `tradingbotsuite`: the active research platform, operator console,
  market-data reliability, execution-safety, and experiment stack.

Legacy vendor-specific import, chart replay, parity diagnostics, source-script references, and gate-research paths have been removed. Research signal rows are now generic SQLite research events, while Binance, Binance Vision, Crypto Lake, and Hyperliquid sources are market-data/context providers only.

## Current V2 Readiness

The existing `tradingbotsuite` strategy and sandbox surfaces are useful legacy
and transition assets. The registry and checked configs cover transparent
baselines, trend/range/volatility strategies, perp-context strategies, funding
and OI flow strategies, GMM/regime-assisted strategies, HMM/KNN local analog
filters, liquidation diagnostics, rapid sandbox tooling, and LC reference
material.

The v2 foundation is implemented and self-checked as a research-only platform:
package skeleton, contracts, archive layout, Hyperliquid universe manager,
coverage service, durable workers, public collectors, lockbox-aware backtest
data service, declarative strategy specs, vectorized backtest artifacts, cost
models, append-only ledger, Lead Book, validation gates, bounded autopilot,
read-only UI rendering, scheduler tick, and autonomous-readiness blocker audit.

The latest archive-ref bounded cycle can run end-to-end through durable
universe, archive-ref, coverage, strategy queue, backtest-data, vectorized
backtest, validation, ledger, Lead Book, and audit workers when supplied
passing local archive evidence. This state is ready for independent final
audit, but not for agentic strategy testing yet: accepted historical as-of
archive coverage, independent audit acceptance, and a separate readiness report
with real evidence paths are still required before agent iteration can be
called fully operational.
No output is candidate-ready, paper-ready, live-ready, order-ready,
sizing-ready, runtime-ready, or promotion-ready.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Validate

```powershell
python -m compileall -q src\tradingbot src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
python -m pytest -q
```

The checked-in GitHub Actions baseline is
`.github/workflows/research-validation.yml`. It installs `.[dev]` in Python
3.11, runs `pip check`, compiles `src/tradingbotsuite`, runs contracts, runs
the v2 foundation suite, and runs focused sandbox plus live/artifact boundary
tests. Optional research, Crypto Lake, and GPU extras are intentionally
excluded from that baseline.

## Core Commands

Fetch and cache backtest data:

```powershell
python -m tradingbot.cli fetch-data --symbol BTC --days 60 --base-timeframe 15m --confirm-timeframe 5m
```

Run a backtest:

```powershell
python -m tradingbot.cli backtest --config examples\default.yaml --symbol BTC
```

Run a legacy BTC research experiment bundle:

```powershell
tradingbotsuite run-research-experiment --spec configs\experiments\v2_btc_phase1_research_experiment.json
```

Provider and archive intake:

```powershell
tradingbotsuite collect-binance-bars --help
tradingbotsuite fetch-binance-vision --help
tradingbotsuite fetch-crypto-lake --help
tradingbotsuite prepare-hmm-knn-research-data --help
```

Crypto Lake is optional local fallback data. Install it with
`python -m pip install -e ".[crypto-lake]"`; direct fetches use Crypto Lake free
sample data without paid credentials. Free sample access has been smoke-tested
locally; follow `docs/runbooks/crypto_lake_free_data_runbook.md`.

Runtime operator console:

```powershell
$env:TBS_OPERATOR_UI_ENABLED="true"
$env:TBS_OPERATOR_UI_SECRET="change-this-local-secret"
tradingbotsuite serve
```

Then open `http://127.0.0.1:8000/ui`.

Research Autopilot on the Research page has explicit compute-scope semantics:

- `reused_existing_evidence`: all required artifacts were already complete.
- `refreshed_downstream_evidence`: only downstream review artifacts such as
  analysis, exit-lab, or candidate eligibility were refreshed on reused
  upstream cycle/discovery evidence.
- `executed_upstream_compute`: catalog, historical-cycle, or exact-discovery
  compute executed.
- `blocked` or `failed`: the manifest records the blocking reason or failure
  text; these states are not candidate evidence.

Use `Run New Compute Iteration` when you intentionally want a new isolated
cycle/discovery iteration even though current artifacts are complete. Use
`Review Existing Evidence` only for the fast cache/reuse audit. Forced compute
does not rewrite stable completed discovery artifacts, does not write candidate
packs by itself, and does not change live or paper runtime behavior.

For compact operator instructions, use `docs/OPERATOR_QUICKSTART.md`. The same
quickstart is also embedded in the operator UI `Guides` page.

## Repository Map

For the active product scope, read `docs/PRODUCT_SCOPE.md`. For the current
research branch architecture, package responsibilities, dependency map, and
unsafe-to-rewrite areas, read `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
before changing shared infrastructure.

- `src/tradingbot/features_lc.py`: Lorentzian Classification feature helpers.
- `src/tradingbot/kernels_lc.py`: rational quadratic and Gaussian kernel helpers.
- `src/tradingbot/lorentz_lc.py`: LC classifier.
- `src/tradingbot/backtest.py`: backtest and execution simulation.
- `src/tradingbot/data/`: data providers and cache resolution.
- `examples/`: reproducible YAML profiles.
- `src/tradingbotsuite/`: active research suite, legacy runtime-adjacent
  guarded surfaces, operator UI, and research pipeline.
- `tests/`: unit and regression tests.
- `configs/tradingbotsuite/`: runtime config examples and non-secret placeholders.

## Rules

- Read `docs/ACTIVE_INDEX.md` before starting work.
- Read `docs/PRODUCT_SCOPE.md` and `docs/V2_NO_TOUCH_PATHS.md` before v2 work.
- Do not treat research outputs as live signals.
- Do not weaken evidence controls; zero eligible candidates is useful rejection
  evidence.
- Do not commit credentials, `.env`, SQLite databases, `data/`, or generated research artifacts.
- Keep research outputs explicitly `research_only`, `observe_only`, and non-promotable unless a separate promotion plan changes that.
- Keep runtime trading logic in `src/tradingbotsuite`; the operator UI must stay a thin command/visibility layer.
- Before broad rewrites, read `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md` and
  preserve the branch contract tests.
