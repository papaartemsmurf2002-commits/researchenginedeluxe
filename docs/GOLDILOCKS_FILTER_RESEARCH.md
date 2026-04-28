# Goldilocks Filter Research

This document defines the BTC-only, research-only `goldilocks` entry-gate family. It exists beside the current `acf_hvr_dsp` gate family and does not change live entry behavior.

## Objective
- Test whether a practical OHLCV-only filter stack can reject corridor/chop TradingView signals without removing the high-energy trend signals that the TradingView KNN model handles best.
- Keep the implementation closed-bar only on 15m data.
- Use TradingView chart-export `Buy` and `Sell` markers as candidate signals.
- Use Binance 15m OHLCV only for historical volume enrichment required by VWAP.
- Keep OI, CVD, and L2 microstructure out of this historical optimizer unless future coverage manifests prove aligned historical data exists.

## Corrected Claims
- ER is useful, but it is not magic zero-lag. It is causal and lookback-based: the value at a signal uses only bars at or before that signal bar.
- Daily VWAP is source-backed as a volume-weighted average with a reset anchor, but the claim that it is an institutional boundary is an interpretation that must be tested.
- HVP is a valid percentile-ranked realized-volatility context feature, but thresholds like `20-80` are search defaults, not truths.
- OI and CVD are valuable for crypto perps, but official Binance historical OI and taker-volume endpoints are limited relative to the current multi-month TradingView export.
- L2 microstructure remains useful for safety, diagnostics, and prospective capture. It is not a hard 15m historical gate in this stack.

## Source Basis
- TradingView VWAP support documentation establishes the VWAP formula using `Typical Price * Volume / Volume` and anchor-period reset behavior.
- QuantConnect Kaufman Efficiency Ratio documentation establishes ER as absolute net change divided by cumulative absolute price movement.
- Binance USD-M `klines` provide the historical 15m OHLCV enrichment source used by this implementation.
- Binance OI/taker-flow historical endpoints are intentionally excluded from this backtest stack because their official historical availability is not enough for the current full export window.
- Time-ordered validation stays aligned with walk-forward principles. No randomized train/test shuffling is used for replay evaluation.

## Components
- `ER`: `abs(close_t - close_t-n) / sum(abs(close_i - close_i-1))`.
- `daily_vwap`: UTC-day anchored VWAP using `hlc3 * volume / volume`.
- `HVP`: percentile rank of rolling log-return historical volatility.

## Defaults
- `er_window=14`
- `er_min=0.20`
- `vwap_anchor=utc_day`
- `vwap_source=hlc3`
- `vwap_margin_bps=0`
- `hv_window_bars=672`
- `hvp_lookback_bars=2880`
- `hvp_min=20`
- `hvp_max=80`

## Optimizer Ranges
- ER window: `[10, 14, 20, 24]`
- ER minimum: `[0.12, 0.16, 0.20, 0.24, 0.30]`
- VWAP margin bps: `[0, 5, 10, 20, 30]`
- HV window bars: `[96, 288, 672]`
- HVP lookback bars: `[1344, 2880]`
- HVP minimum: `[10, 15, 20, 25, 30]`
- HVP maximum: `[70, 80, 90, 100]`

## Decision Rule
- All enabled Goldilocks components must pass.
- Long signal passes VWAP only when `close >= daily_vwap * (1 + margin_bps / 10000)`.
- Short signal passes VWAP only when `close <= daily_vwap * (1 - margin_bps / 10000)`.
- Missing selected components reject as `insufficient_goldilocks_history`.
- Metrics report missing-component rejections separately from strategic rejections. This prevents warmup or missing volume from being mistaken for useful filter behavior.

## OHLCV Enrichment
- Current TradingView chart exports do not contain usable volume, so VWAP needs Binance 15m OHLCV.
- The cache is stored under `data/research/chart_ohlcv_cache/`.
- Cache identity includes symbol, timeframe, requested start timestamp, and requested end timestamp.
- The enrichment layer requires timestamp alignment.
- If Binance OHLC differs from the chart-export OHLC by more than `5 bps`, the bar keeps the TradingView chart price but marks VWAP volume unavailable for that bar.
- Cache manifests include row count, first/last bar, source, requested window, and hash.

## CLI Examples
```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main research-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1_goldilocks --gate-family goldilocks --allowed-components er,vwap,hvp --ohlcv-cache-policy use-or-fetch
```

```powershell
$env:PYTHONPATH="src"
python -m tradingbotsuite.main optimize-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1_goldilocks_opt --gate-family goldilocks --allowed-components er,vwap,hvp --ohlcv-cache-policy use-or-fetch --exit-profile runner --workers 15 --max-gate-candidates 10000
```

For an offline repeat using an existing cache:
```powershell
python -m tradingbotsuite.main optimize-entry-gates --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1_goldilocks_cache_only --gate-family goldilocks --allowed-components er,vwap,hvp --ohlcv-cache-policy cache-only --exit-profile runner --workers 15
```

## UI Workflow
- Open `/ui/analysis`.
- Select `Goldilocks ER / VWAP / HVP` in `Filter Stack`.
- Keep `OHLCV Cache Policy` on `Use cache or fetch Binance OHLCV` for the first run.
- Check only the components you want the optimizer to search.
- Run `Analyze Current Setup` for a visual replay.
- Queue optimizer only after the cache coverage panel shows usable VWAP and HVP coverage.
- Use `Load Latest Optimizer Best` to restore the winning family, selected components, and parameter values.

## Promotion Boundary
- This stack is observe-only.
- Passing optimizer metrics does not enable live gating.
- Live promotion requires repeated walk-forward evidence, stable out-of-sample behavior, and a separate runtime wiring decision.
- OI/CVD and microstructure can be added later as prospective context, but they should not be mixed into the historical chart-export backtest without source coverage proof.
