# Backtest Contract

Every backtest run must be reproducible from its manifest and resolved config.

## Required outputs

- `backtest_manifest.json`
- `trades.parquet`
- `signals.parquet`
- `equity_curve.parquet`
- `metrics.json`
- `config_resolved.json`
- optional `debug_trace.parquet`

## Required metrics

- net return after fees, slippage, and funding
- trade count
- long count and short count
- hit rate
- expectancy per trade
- average and median holding time
- max drawdown
- profit factor
- exposure
- turnover
- slippage sensitivity
- funding contribution
- split-by-regime metrics
- split-by-month metrics
- split-by-volatility bucket metrics
- capacity/liquidity flags where available

## Invalid backtests

A backtest is invalid if it uses future features, fits preprocessing on validation rows, omits fees/slippage/funding, reports only in-sample metrics, or makes a WT3D claim without a no-WT baseline.
