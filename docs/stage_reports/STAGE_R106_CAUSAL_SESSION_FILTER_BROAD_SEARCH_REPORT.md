# Stage R106 Causal Session Filter Broad Search Report

Date: 2026-06-11
Work packet: WPR106-94-causal-session-filter-broad-search
Status: closed

## Scope

WPR106-94 continued the 2024-forward broad search after the rejected ETHUSDT
May holdout from WPR106-93. The packet tested causal UTC hour and weekday
entry filters on transparent trend, volatility-breakout, range-reversion, and
sparse/event families.

The tuning window remained 2024-01-01 through 2026-04-30. May 2026 was not
used for tuning, ranking, selection, or benchmark feedback.

## Implementation

- Added default-off `allowed_hours_utc` and `allowed_weekdays_utc` entry
  filters through a shared strategy helper.
- Wired the causal session filter into:
  - `trend_following_v1`
  - `volatility_breakout_v1`
  - `range_reversion_v1`
  - `sparse_event_filter_v1`
- Extended the touched metadata domains to accept session parameters and
  scoped 4-bar spacing for transparent active-rate variants.
- Added focused strategy-contract tests for default-off behavior, explicit
  hour/weekday filtering, and invalid-value fail-closed behavior.

## Runs

An initial BTCUSDT v1 grid materialized 584 candidate rows and 2,184 backtest
files but was stopped after more than 50 minutes without a final cycle
manifest. It is retained only as an aborted oversized compute attempt under:

`data/research/historical_cycles/wpr106_94_causal_session_filter_broad_search_btcusdt_v1/`

The v2 grid fixed core strategy parameters and used UTC session filters as the
primary search variables. Both symbols completed:

- `configs/research/wpr106_94_causal_session_filter_broad_search_btcusdt_v2.json`
- `configs/research/wpr106_94_causal_session_filter_broad_search_ethusdt_v2.json`
- `data/research/historical_cycles/wpr106_94_causal_session_filter_broad_search_btcusdt_v2/`
- `data/research/historical_cycles/wpr106_94_causal_session_filter_broad_search_ethusdt_v2/`

Summary artifacts:

- `data/research/wpr106_94_causal_session_filter_broad_search/summary/wpr106_94_causal_session_filter_summary.json`
- `data/research/wpr106_94_causal_session_filter_broad_search/summary/wpr106_94_symbol_summary.csv`
- `data/research/wpr106_94_causal_session_filter_broad_search/summary/wpr106_94_candidate_summary.csv`
- `data/research/wpr106_94_causal_session_filter_broad_search/summary/wpr106_94_candidate_summary.parquet`
- `data/research/wpr106_94_causal_session_filter_broad_search/summary/wpr106_94_monthly_returns.csv`

## Results

BTCUSDT v2 produced 119 total rows, including 115 research candidates and 4
injected no-trade comparators. Eleven research rows were positive net and
positive expectancy after costs. All 115 research rows were inside the 1 to 5
trades-per-active-day band. Zero rows passed loose monthly stability, zero
passed strict monthly stability, and zero qualified for May 2026 holdout.

The best BTCUSDT row was a 72h `volatility_breakout_v1` session variant using
UTC hours 16-23. It recorded 264 trades, 264 active days, 1.0 trades per active
day, +1.996558 net return after costs, +0.004918 expectancy, profit factor
1.392614, 28 active months, 20 positive months, and 8 losing months. It was
rejected because month-to-month stability is still outside the target and cost
stress survival is 0.636364, below the 0.70 floor.

ETHUSDT v2 produced 119 total rows, including 115 research candidates and 4
injected no-trade comparators. Eleven research rows were positive net and
positive expectancy after costs. All 115 research rows were inside the 1 to 5
trades-per-active-day band. Zero rows passed loose monthly stability, zero
passed strict monthly stability, and zero qualified for May 2026 holdout.

The best ETHUSDT row was a 72h `sparse_event_filter_v1` volatility-breakout
variant with contrarian aggTrade-flow confirmation, UTC hours 0-7, and UTC
weekdays 0-4. It recorded 131 trades, 131 active days, 1.0 trades per active
day, +1.273124 net return after costs, +0.008575 expectancy, profit factor
1.408041, 28 active months, 16 positive months, and 12 losing months. It passed
cost stress in the shortlist evidence but was rejected because monthly
stability is too weak.

## Decision

The causal session-filter slice is rejected as a source of May-holdout
candidates. It can produce profitable pre-May rows, but the rows are still too
unstable month to month. May 2026 remains fully unused in WPR106-94.

No candidate pack, paper/live artifact, order-placement path, position sizing,
runtime-mode change, live configuration write, CUDA speedup claim, or
promotion-ready claim was created.

## Validation

Focused validation passed before cycle execution:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py -q
```

Result: 295 passed.

Final baseline validation passed:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Result: compileall passed; contracts reported 460 passed.
