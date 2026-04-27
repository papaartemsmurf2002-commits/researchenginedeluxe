# Tradingbot Parity Project

Python research and validation stack for the TradingView Lorentzian Classification indicator.

The current priority is correctness: Pine-compatible feature helpers, Lorentzian ANN voting, kernel gates, TradingView export parity, and a local UI for manual marker validation.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Validate

```powershell
python -m pytest -q
python -m compileall -q src\tradingbot
```

## Current LC Validation Profile

Use `examples/btc_lc_close_10_6000.yaml` for the full-history marker export:

- source `close`
- neighbors `10`
- max bars back `6000`
- features `RSI 14/1`, `WT 10/11`, `CCI 20/1`, `ADX 20/2`, `RSI 9/1`
- kernel `8 / 8 / 25`, lag `2`
- kernel trade filter on
- all other filters off

Full-history export result with `C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv`:

- kernel parity: passed after warmup
- marker parity exact: `406/407`
- marker parity within one bar: `407/407`
- remaining exact offset is at the max-bars-back boundary

## Commands

Kernel parity:

```powershell
python -m tradingbot.cli parity-check --config examples\btc_lc_close_10_6000.yaml --symbol BTC --base-csv "C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv" --tv-export "C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv" --columns kernel --skip-rows 26 --tolerance 0.01 --kernel-preflight --exclude-last-bar
```

Entry parity:

```powershell
python -m tradingbot.cli entry-parity --config examples\btc_lc_close_10_6000.yaml --symbol BTC --base-csv "C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv" --tv-export "C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv" --mode full --tolerance-bars 1 --no-hypotheses
```

UI validation:

```powershell
python -m tradingbot.cli serve-ui --config examples\btc_lc_close_10_6000.yaml --symbol BTC --csv "C:\Users\papaa\Downloads\BINANCE_BTCUSDT.P, 15 (21).csv"
```

Then open the printed local URL.

## Repository Map

- `src/tradingbot/features_tv.py`: Pine-compatible feature helpers.
- `src/tradingbot/kernels_tv.py`: rational quadratic and Gaussian kernel helpers.
- `src/tradingbot/lorentz_tv.py`: source-faithful LC classifier.
- `src/tradingbot/parity.py`: TradingView export normalization and parity reports.
- `src/tradingbot/ui.py`: local browser UI for marker validation.
- `src/tradingbot/backtest.py`: backtest and execution simulation.
- `src/tradingbot/data/`: data providers and cache resolution.
- `docs/`: parity workflow and diagnostic Pine export scripts.
- `examples/`: reproducible YAML profiles.
- `references/`: original Pine source and minimal source libraries used for parity reasoning.
- `tests/`: unit and regression tests.

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/PARITY_WORKFLOW.md`
- `docs/UI_VALIDATION.md`
- `docs/AGENT_WORKSTREAMS.md`
- `docs/lc_diagnostic_export_usage.md`

## Rules

- Do not commit TradingView CSV exports, cache files, logs, or generated reports.
- Keep `pine_exact` source-faithful.
- Add research modes only when they are explicitly labeled as research.
- Prefer diagnostic exports over marker-only fitting when parity diverges.
