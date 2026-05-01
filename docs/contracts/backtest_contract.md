# Backtest Contract

Every backtest run must be reproducible from its manifest and resolved config.

Implementation:

- Engine: `src/tradingbotsuite/backtesting/engine.py`
- Execution simulator: `src/tradingbotsuite/backtesting/execution_sim.py`
- Cost model: `src/tradingbotsuite/backtesting/costs.py`
- Portfolio layer: `src/tradingbotsuite/backtesting/portfolio.py`
- Metrics: `src/tradingbotsuite/backtesting/metrics.py`
- Benchmarks: `src/tradingbotsuite/backtesting/benchmark.py`

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

## Stage 5 baseline assumptions

- Research outputs must set `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- Same-bar entry/exit is forbidden unless a lower-timeframe execution path proves event sequence.
- Supported primary holding windows are `1h`, `24h`, `72h`, and `7d`.
- Benchmark baselines live under `data/research/benchmarks/`.
