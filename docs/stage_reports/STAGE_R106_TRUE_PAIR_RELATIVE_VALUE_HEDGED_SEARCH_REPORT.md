# Stage R106 True Pair Relative-Value Hedged Search Report

Date: 2026-06-11
Packet: WPR106-125
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all hedge-ratio choice, feature choice, threshold
choice, filter choice, exit choice, ranking, and selection. May was replayed
only after fixed pre-May loose rows were selected.

## Method

The runner
`data/research/wpr106_125_true_pair_relative_value_hedged_search/scripts/run_wpr106_125_true_pair_relative_value_hedged_search.py`
tests true two-leg BTCUSDT/ETHUSDT pair trades over the existing WPR106-96
public-archive context:

- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/btcusdt_2024_01_to_2026_05_cycle_dataset.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/ethusdt_2024_01_to_2026_05_cycle_dataset.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/btcusdt_2024_01_to_2026_05_agg_trade_1m.parquet`
- `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/source_context/ethusdt_2024_01_to_2026_05_agg_trade_1m.parquet`

The aligned pair context has 84,672 15m bars from 2024-01-01 through
2026-05-31. The pre-May OLS ETH/BTC beta is 1.130693. Candidate trades enter
on the next 15m open after a completed signal bar, use one pair position at a
time, and apply normalized two-leg round-trip cost of 0.001164 per unit pair
capital. Cost stress uses 1.00x, 1.25x, 1.50x, and 2.00x cost multipliers.

The first broader attempt was stopped after it remained on the first feature
set without artifacts. The closed run uses a narrowed diagnostic grid with
unit, pre-May OLS, and rolling-1536 hedge ratios; 384/1536-bar score windows;
16/32/64-bar holds; fixed, spread-reversion, and score-flip exits; all/US
sessions; wide/extreme spread filters; all/high-correlation filters; all or
flow-confirmed filters; and 1, 3, or 5 target raw signals per day.

The tested families are spread mean reversion, spread momentum,
spread-acceleration fade, spread-acceleration momentum, relative-return
reversion, relative-return momentum, flow-supported reversion, and
flow-dislocation momentum. All rows are true pair trades; unlike WPR106-108,
this packet does not include single-leg lead-lag diagnostics.

## Results

Full pre-May grid:

- Evaluated rows: 17,280.
- Positive pre-May rows: 1,974.
- Positive annual-target rows: 10.
- Loose rows: 8.
- Strict rows: 0.
- Selected rows: 8 loose rows.

The selected rows are all unit-beta, US-session, extreme-spread,
flow-confirmed spread-acceleration momentum variants:

- Pre-May net return: +0.137747 to +0.252520.
- Trades: 101 to 158.
- Active months: 27.
- Losing months: 8.
- Annual loss counts: selected rows miss at least one annual cap, usually 2025.
- Max drawdown: -0.035342 to -0.058080.
- Cost-stress survival: 4/4 scenarios.

The annual-target positives are not active enough to become loose or strict
leads. They are rolling-1536 spread-momentum or spread-acceleration rows with
only 21 to 22 trades and 12 active months.

May 2026 benchmark after fixed pre-May selection:

- May-positive selected rows: 0.
- May-negative selected rows: 8.
- May-flat selected rows: 0.
- Best May return: -0.005138.
- Worst May return: -0.023808.
- Median May return: -0.020340.
- Selected May trades: 2 to 7 per row.
- May cost-stress survival: 0/4 for every selected row.

## Decision

The true-pair relative-value family is rejected as currently configured. The
new two-leg construction improves interpretability versus prior single-leg
relative-value diagnostics and finds some low-drawdown, cost-positive pre-May
pockets, but the active loose rows miss the year-by-year loss caps and every
fixed selected row loses in May. The rows that meet the annual loss target are
too sparse to support the requested active profile.

Useful follow-up context: true pair spread-acceleration momentum is the only
positive active pocket in this packet. A future packet should not treat this
specific selected set as a lead unless it introduces new pre-May-only evidence,
such as a different pair universe, better pair exit model, or causal regime
filter that is justified without May feedback.

## Artifacts

- `data/research/wpr106_125_true_pair_relative_value_hedged_search/wpr106_125_true_pair_relative_value_summary.json`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/pre_may/true_pair_ranking.parquet`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/pre_may/true_pair_top2000.csv`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/pre_may/true_pair_monthly_returns.parquet`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/pre_may/family_summary.parquet`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/pre_may/selected_pre_may.csv`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_125_true_pair_relative_value_hedged_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_125_true_pair_relative_value_hedged_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.

