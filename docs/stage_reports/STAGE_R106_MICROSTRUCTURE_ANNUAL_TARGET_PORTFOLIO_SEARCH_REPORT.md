# Stage R106 Microstructure Annual-Target Portfolio Search Report

Date: 2026-06-12
Packet: WPR106-135
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of source-pool membership, source de-duplication,
portfolio construction, daily-cap choice, ranking, and selection. May was
replayed only after fixed strict pre-May portfolio selection.

## Method

The runner
`data/research/wpr106_135_microstructure_annual_target_portfolio_search/scripts/run_wpr106_135_microstructure_annual_target_portfolio_search.py`
loads the WPR106-134 pre-May ranking and uses only rows with
`positive_annual_target: true` as source candidates.

It replays all source candidates through the WPR106-134 completed-bar
microstructure runner, de-duplicates by exact pre-May symbol/entry/exit/side
trade behavior, and keeps a diversified 128-row source pool. Portfolio search
then generates fixed equal-sleeve combinations from that source pool, with
member counts of 2, 3, 4, 5, 6, 8, 10, and 12 and portfolio daily caps of 3 and
5 accepted trades. Portfolio execution skips overlapping accepted trades on
the same symbol and applies the daily cap before equal-sleeve return
accounting.

Costs use the inherited WPR106-134/WPR106-126 taker plus slippage/spread model:
0.0432% taker fee per side plus 0.0150% slippage/spread per side, for a
0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers.

## Results

Source and portfolio search:

- Positive annual-target source rows replayed: 797.
- Deduped source-pool rows: 128.
- Generated member sets: 4,300.
- Evaluated unique portfolio rows: 8,542.
- Positive pre-May portfolios: 8,542.
- Annual-target portfolios: 3,538.
- Loose pre-May portfolios: 4,635.
- Strict pre-May portfolios: 279.
- Fixed selected portfolios: top 100 strict rows.

The top selected strict pre-May portfolio is:

- Portfolio ID: `microportfolio-6ecc88f99a825fe6`.
- Member count: 5 equal-sleeve sources.
- Daily cap: 3 accepted trades.
- Source symbols: BTCUSDT, BTCUSDT, ETHUSDT, ETHUSDT, BTCUSDT.
- Source families: volatility-burst follow, return-streak, volatility-burst
  follow, flow-agreement, volatility-burst follow.
- Trades: 125.
- Active days: 115.
- Trades per active day: 1.086957.
- Active months: 28.
- Losing months: 4.
- Annual losses: 2024: 2, 2025: 2, 2026 Jan-Apr: 0.
- Pre-May net return: +0.133239.
- Max drawdown: -0.011290.
- Sortino daily: 0.716224.
- Best-month share: 0.173208.
- Cost-stress survival: 4/4.

May 2026 benchmark after fixed top-100 strict pre-May selection:

- May-positive selected portfolios: 43.
- May-negative selected portfolios: 55.
- May-flat selected portfolios: 2.
- Best May net return: +0.002333.
- Worst May net return: -0.003529.
- Median May net return: -0.000509.
- Selected portfolios fired only 3 to 8 May trades each.

## Decision

The microstructure annual-target portfolio construction is rejected as a
candidate lead. It successfully converts sparse annual-target diagnostics into
strict-looking pre-May portfolios with low drawdown, full cost-stress survival,
and active rates around 1 trade/day. The fixed strict selection does not carry
into May 2026: the selected benchmark has more negative than positive rows,
a negative median, and very sparse May firing.

This is useful negative evidence. It suggests that combining sparse
annual-target microstructure rows can manufacture pre-May monthly stability,
but the selected behavior is not robust enough for May 2026.

## Artifacts

- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/wpr106_135_microstructure_annual_target_portfolio_summary.json`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/source_replay_all_positive_annual_target.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/source_pool.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/source_pool_pre_may_trades.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/portfolio_ranking.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/portfolio_top2000.csv`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/portfolio_monthly_returns.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_135_microstructure_annual_target_portfolio_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_135_microstructure_annual_target_portfolio_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
