# TradingBotSuite Workspace

This repository contains two related Python codebases:

- `tradingbot`: the Lorentzian Classification signal-generation, backtest, optimization, and data-cache package.
- `tradingbotsuite`: the BTC runtime, operator console, market-data reliability, execution-safety, and research experiment stack.

Legacy vendor-specific import, chart replay, parity diagnostics, source-script references, and gate-research paths have been removed. Research signal rows are now generic SQLite research events, while Binance, Binance Vision, Crypto Lake, and Hyperliquid sources are market-data/context providers only.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Validate

```powershell
python -m pytest -q
python -m compileall -q src\tradingbot src\tradingbotsuite
```

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
python -m tradingbotsuite.main run-research-experiment --spec configs\experiments\v2_btc_phase1_research_experiment.json
```

Runtime operator console:

```powershell
$env:TBS_OPERATOR_UI_ENABLED="true"
$env:TBS_OPERATOR_UI_SECRET="change-this-local-secret"
python tools\tradingbotsuite\run_server.py
```

Then open `http://127.0.0.1:8000/ui`.

## Repository Map

- `src/tradingbot/features_lc.py`: Lorentzian Classification feature helpers.
- `src/tradingbot/kernels_lc.py`: rational quadratic and Gaussian kernel helpers.
- `src/tradingbot/lorentz_lc.py`: LC classifier.
- `src/tradingbot/backtest.py`: backtest and execution simulation.
- `src/tradingbot/data/`: data providers and cache resolution.
- `examples/`: reproducible YAML profiles.
- `src/tradingbotsuite/`: BTC runtime engine, Binance microstructure, Hyperliquid execution adapter, operator UI, and research pipeline.
- `tests/`: unit and regression tests.
- `tools/tradingbotsuite/`: runtime launch helpers kept out of the main package namespace.
- `configs/tradingbotsuite/`: runtime config examples and non-secret placeholders.

## Rules

- Do not commit credentials, `.env`, SQLite databases, `data/`, or generated research artifacts.
- Keep research outputs explicitly `research_only`, `observe_only`, and non-promotable unless a separate promotion plan changes that.
- Keep runtime trading logic in `src/tradingbotsuite`; the operator UI must stay a thin command/visibility layer.
