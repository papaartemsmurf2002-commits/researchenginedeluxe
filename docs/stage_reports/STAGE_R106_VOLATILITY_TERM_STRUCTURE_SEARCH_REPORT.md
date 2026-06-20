# Stage R106 Volatility Term-Structure Search Report

Date: 2026-06-11
Packet: WPR106-131
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all feature, threshold, filter, hold, ranking, and
selection decisions. May was replayed only after fixed loose pre-May selection,
because no strict pre-May rows existed.

## Method

The runner
`data/research/wpr106_131_volatility_term_structure_search/scripts/run_wpr106_131_volatility_term_structure_search.py`
uses WPR106-126 source-context loading over WPR106-96 public-archive BTCUSDT
and ETHUSDT bars plus 15m aggTrade-flow aggregation.

Each symbol has 84,672 15m bars from 2024-01-01 through 2026-05-31. Signals
use completed 15m bars and enter on the next 15m open. Pre-May trades are
required to exit before 2026-05-01.

The grid covers:

- Realized-volatility windows: 96, 384, and 1,536 bars.
- Fixed holds: 4, 8, 16, and 32 bars.
- Sessions: all, Asia, EU, and US.
- Volatility regimes: all, compressed, expanding, and high-volatility.
- Flow filters: all, flow-confirmed, flow-contrarian, and flow-neutral.
- Target raw signals: 1, 3, and 5 per day.
- Families: compression breakout follow, volatility-expansion follow,
  volatility-shock fade, term-structure reversal, quiet-trend pullback, and
  compression mean reversion.

Costs use 0.0432% taker fee per side plus 0.0150% slippage/spread per side,
for 0.001164 round-trip cost. Cost stress tests 1.00x, 1.25x, 1.50x, and 2.00x
cost multipliers.

## Results

Full pre-May grid:

- Evaluated rows: 27,648.
- Positive pre-May rows: 3,267.
- Positive annual-target rows: 249.
- Loose rows: 96.
- Strict rows: 0.
- Selected rows: 96 loose rows.

The top selected loose pre-May row is:

- Symbol: ETHUSDT.
- Family: volatility quiet-trend pullback.
- Template: quiet trend pullback.
- Volatility window: 1,536 bars.
- Hold: 8 bars.
- Session: US.
- Volatility regime: expanding.
- Flow filter: flow-confirmed.
- Target signals per day: 1.
- Trades: 62.
- Active months: 23.
- Losing months: 4.
- Annual losses: 2024: 2, 2025: 1, 2026 Jan-Apr: 1.
- Pre-May net return: +0.314313.
- Max drawdown: -0.068759.
- Best-month share: 0.186075.
- Cost-stress survival: 4/4.

This row passes the annual losing-month target, but remains loose rather than
strict because it has only 62 trades and 23 active months. The rest of the
selected loose set is dominated by ETHUSDT volatility-expansion follow and
quiet-trend pullback variants; those rows are active, but generally fail the
annual loss caps or drawdown/stability requirements.

May 2026 benchmark after fixed loose pre-May selection:

- May-positive selected rows: 30.
- May-negative selected rows: 65.
- May-flat selected rows: 1.
- Best May net return: +0.023473.
- Worst May net return: -0.053216.
- Median May net return: -0.007760.

## Decision

The realized-volatility term-structure family is rejected as currently
configured. It finds many positive and annual-target diagnostics, but no strict
pre-May row. The fixed loose selection fails May 2026 as a benchmark group,
with more than twice as many negative rows as positive rows and a negative
median May return.

Useful follow-up context: the most promising diagnostics are ETHUSDT
quiet-trend pullback and volatility-expansion follow variants. Future work
should not promote them directly; any new packet would need a separate
pre-May-only way to raise active-month/trade-count coverage without degrading
annual stability, followed by a fresh fixed May benchmark.

## Artifacts

- `data/research/wpr106_131_volatility_term_structure_search/wpr106_131_volatility_term_structure_summary.json`
- `data/research/wpr106_131_volatility_term_structure_search/pre_may/volatility_term_structure_ranking.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/pre_may/volatility_term_structure_top2000.csv`
- `data/research/wpr106_131_volatility_term_structure_search/pre_may/volatility_term_structure_monthly_returns.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/pre_may/family_summary.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_131_volatility_term_structure_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_131_volatility_term_structure_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
