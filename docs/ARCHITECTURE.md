# Architecture

The project is organized around independently testable subsystems.

## Core LC Parity

- `features_tv.py` implements Pine-compatible RSI, WT, CCI, ADX, smoothing, and filters.
- `kernels_tv.py` implements rational quadratic and Gaussian kernels.
- `lorentz_tv.py` implements the TradingView Lorentzian Classification state machine.
- `tv_backtest.py` reproduces the TradingView-style trade statistics used by parity checks.

This layer should not depend on data providers, live trading, or UI code.

## Parity Tooling

- `parity.py` normalizes TradingView exports, merges split diagnostic exports, compares subsystems, and writes reports.
- `lc_marker_research.py` runs marker-only research probes and can create escalation casefiles.
- `docs/lc_lorentzian_diagnostic_*_export.pine` are Pine-side export scripts.

This layer may depend on the LC core, but the LC core should not depend on it.

## UI

- `ui.py` starts a local HTTP server and renders a browser chart.
- It uses exported OHLC candles as the market data source.
- Python entries are shown as blue triangles.
- TradingView exported markers are shown as yellow diamonds.
- The max-bars-back boundary is shown as a purple dashed line.

The UI is diagnostic only. It does not write config, place orders, or mutate live state.

## Data And Backtest

- `data/` resolves cached datasets and provider fallbacks.
- `backtest.py` runs strategy simulation.
- `optimization.py` runs walk-forward candidate search.
- `risk.py`, `market_structure.py`, `order_blocks.py`, and `execution_rules.py` support non-parity strategy research.

These modules may use LC output, but parity checks should remain possible without live provider access.

## Live Shell

- `live.py` and `data/hyperliquid.py` contain execution-facing adapters.
- Live trading is disabled by default in example configs.

Keep live execution changes isolated from parity and research changes.

## TradingBotSuite Runtime

- `src/tradingbotsuite/core/engine.py` is the canonical BTC runtime decision, supervision, reconciliation, and system-snapshot path.
- `src/tradingbotsuite/adapters/binance.py` owns Binance USD-M bars, aggTrade flow, bookTicker, and local diff-depth book reliability.
- `src/tradingbotsuite/adapters/execution.py` owns Hyperliquid order placement, testnet support, protection cleanup, and execution reports.
- `src/tradingbotsuite/persistence.py` owns SQLite-backed state, events, operator jobs, health events, and runtime attribution.
- `src/tradingbotsuite/web/` and `src/tradingbotsuite/operator_console.py` expose the localhost operator console as a thin layer over the engine.

This package is preserved as a sibling runtime stack. It should not be merged into `tradingbot` parity code unless there is a deliberate interface design for signal handoff.

## Archived Runtime Research

- `src/tradingbotsuite/research/` contains preserved chart-export import, dataset, filter, optimizer, and artifact tooling from previous V2 work.
- That code is not the active workstream. TradingView data importing, dataset training, and live model promotion are frozen until explicitly reactivated.
- Runtime reliability and signal-generation parity should be stabilized independently before reopening this layer.
