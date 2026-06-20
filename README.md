# ResearchEngineDeluxe

ResearchEngineDeluxe is a modular strategy-research workbench for BTC/ETH
perpetual futures. Its purpose is to test new strategy theories, refine
existing strategy families, and produce reproducible evidence patterns that can
be compared, rejected, ablated, and iterated quickly.

The project is not a live trading system. The no-live boundary exists to keep
research evidence clean: outputs are manifests, metrics, rejections, ablations,
validation floors, multiple-testing reports, and candidate diagnostics, not
paper/live signals, sizing instructions, order-placement behavior, or promotion
authorization.

The active Python package is still named `tradingbotsuite` for compatibility.
This repository contains two related Python codebases:

- `tradingbot`: the legacy Lorentzian Classification signal-generation, backtest, optimization, and data-cache package.
- `tradingbotsuite`: the active BTC runtime, operator console, market-data reliability, execution-safety, and research experiment stack.

Legacy vendor-specific import, chart replay, parity diagnostics, source-script references, and gate-research paths have been removed. Research signal rows are now generic SQLite research events, while Binance, Binance Vision, Crypto Lake, and Hyperliquid sources are market-data/context providers only.

## Current Strategy Readiness

The active `tradingbotsuite` strategy surface is structurally complete for the
next research iteration. The registry and checked configs cover transparent
baselines, trend/range/volatility strategies, perp-context v2 strategies,
funding and OI flow strategies, GMM/regime-assisted strategies, HMM/KNN local
analog filters, liquidation diagnostics, and LC reference material.

That means the next work is empirical: compute new iterations, inspect the
evidence patterns, refine strategy hypotheses, and rerun focused experiments.
Current completed evidence still has zero eligible candidate-pack rows, so the
platform is ready to test and learn, not to claim a working tradable strategy.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Validate

```powershell
python -m compileall -q src\tradingbot src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
python -m pytest -q
```

The checked-in GitHub Actions baseline is
`.github/workflows/research-validation.yml`. It installs `.[dev]` in Python
3.11, runs `pip check`, compiles `src/tradingbotsuite`, runs contracts, and runs
focused live/artifact boundary tests. Optional research, Crypto Lake, and GPU
extras are intentionally excluded from that baseline.

## Core Commands

Fetch and cache backtest data:

```powershell
python -m tradingbot.cli fetch-data --symbol BTC --days 60 --base-timeframe 15m --confirm-timeframe 5m
```

Run a backtest:

```powershell
python -m tradingbot.cli backtest --config examples\default.yaml --symbol BTC
```

Run the BTC research experiment bundle:

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

For the current research branch architecture, package responsibilities,
dependency map, and unsafe-to-rewrite areas, read
`docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md` before changing shared
infrastructure.

- `src/tradingbot/features_lc.py`: Lorentzian Classification feature helpers.
- `src/tradingbot/kernels_lc.py`: rational quadratic and Gaussian kernel helpers.
- `src/tradingbot/lorentz_lc.py`: LC classifier.
- `src/tradingbot/backtest.py`: backtest and execution simulation.
- `src/tradingbot/data/`: data providers and cache resolution.
- `examples/`: reproducible YAML profiles.
- `src/tradingbotsuite/`: BTC runtime engine, Binance microstructure, Hyperliquid execution adapter, operator UI, and research pipeline.
- `tests/`: unit and regression tests.
- `configs/tradingbotsuite/`: runtime config examples and non-secret placeholders.

## Rules

- Read `docs/ACTIVE_INDEX.md` before starting work.
- Do not treat research outputs as live signals.
- Do not weaken evidence controls; zero eligible candidates is useful rejection
  evidence.
- Do not commit credentials, `.env`, SQLite databases, `data/`, or generated research artifacts.
- Keep research outputs explicitly `research_only`, `observe_only`, and non-promotable unless a separate promotion plan changes that.
- Keep runtime trading logic in `src/tradingbotsuite`; the operator UI must stay a thin command/visibility layer.
- Before broad rewrites, read `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md` and
  preserve the branch contract tests.
