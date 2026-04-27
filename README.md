# Tradingbot Workspace

This repository now contains two related Python codebases:

- `tradingbot`: the current Lorentzian Classification / signal-generation parity project.
- `tradingbotsuite`: the BTC runtime, operator console, market-data reliability, execution-safety, and testnet-validation stack migrated from local development.

The current priority is correctness: Pine-compatible feature helpers, Lorentzian ANN voting, kernel gates, TradingView export parity, and a local UI for manual marker validation.

The runtime stack is preserved beside the parity project so agents can work in parallel without losing the production-hardening work. TradingView chart-export importing, dataset-building, and training experiments are retained as legacy/reference code only; they are not the active next workstream unless explicitly reactivated.

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

Runtime operator console:

```powershell
$env:TBS_OPERATOR_UI_ENABLED="true"
$env:TBS_OPERATOR_UI_SECRET="change-this-local-secret"
python tools\tradingbotsuite\run_server.py
```

Then open `http://127.0.0.1:8000/ui`.

Runtime manual shell:

```powershell
python tools\tradingbotsuite\run_manual.py
```

Hyperliquid testnet credentials should be provided through `TBS_HL_*` environment variables. A local repo-root `hyperliquidtestnet.txt` fallback is supported for operator testing, but it is intentionally gitignored. Use `configs/tradingbotsuite/hyperliquidtestnet.example.txt` as the placeholder format only.

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
- `src/tradingbotsuite/`: BTC runtime engine, Binance microstructure, Hyperliquid execution adapter, operator UI, and legacy research helpers.
- `tests/tradingbotsuite/`: migrated runtime regression tests.
- `docs/tradingbotsuite_runtime/`: runtime handoff, reliability, operator, and preservation docs.
- `tools/tradingbotsuite/`: runtime launch helpers kept out of the main package namespace.
- `configs/tradingbotsuite/`: runtime config examples and non-secret placeholders.

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/PARITY_WORKFLOW.md`
- `docs/UI_VALIDATION.md`
- `docs/AGENT_WORKSTREAMS.md`
- `docs/lc_diagnostic_export_usage.md`
- `docs/tradingbotsuite_runtime/README.md`
- `docs/tradingbotsuite_runtime/AGENT_GUIDE.md`
- `docs/tradingbotsuite_runtime/PROJECT_PRESERVATION_HANDOFF.md`
- `docs/tradingbotsuite_runtime/MICROSTRUCTURE_RELIABILITY.md`
- `docs/tradingbotsuite_runtime/BTC_RUNTIME_RELIABILITY_GUIDE.md`

## Rules

- Do not commit TradingView CSV exports, cache files, logs, or generated reports.
- Do not commit `hyperliquidtestnet.txt`, `.env`, SQLite databases, `data/`, or generated research artifacts.
- Keep `pine_exact` source-faithful.
- Add research modes only when they are explicitly labeled as research.
- Prefer diagnostic exports over marker-only fitting when parity diverges.
- Keep runtime trading logic in `src/tradingbotsuite`; the operator UI must stay a thin command/visibility layer.
