# Stage R106 Cross-Family Daily Risk Throttle Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-113-cross-family-daily-risk-throttle-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for source filtering, behavior deduplication,
portfolio member choice, weight choice, daily risk policy choice, ranking, and
selection. May 2026 is excluded from all tuning and selection. May is joined
only after fixed pre-May rows are selected, and only as a benchmark holdout. No
candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or promotion
claim is made.

## Method

The runner loads selected trade-level artifacts from WPR106-106, WPR106-107,
WPR106-108, WPR106-109, WPR106-111, and WPR106-112. These are already
research-only rows selected without May tuning by their source packets. WPR106
-113 does not inspect May source trades until fixed pre-May portfolio rows are
selected.

The pre-May source stage starts from 758 raw source rows and applies positive
return, minimum trade count, active-month, active-rate, and behavior-fingerprint
deduplication. WPR106-113 keeps 140 deduped source rows, then builds deterministic
monthly-complement portfolio beams with packet/family diversity caps. The trade
replay stage evaluates equal and stability-weighted portfolios under 48 daily
risk policies covering max concurrent positions, max trades per day, daily loss
stops, and daily profit locks.

Unlike the WPR106-110 monthly meta-selector, this packet replays actual selected
trade streams. The replay enforces cross-source overlap, optional same-symbol
overlap blocking, max trades/day, and daily stop/profit-lock skipping before
computing pre-May monthly stability.

## Results

The screen evaluated 40,320 trade-level portfolio rows after the monthly beam.
Every evaluated row was positive pre-May, 16,896 rows were loose, and 4,182 rows
were strict by the packet's pre-May monthly-stability/risk controls.

| Scope | Rows |
| --- | ---: |
| Raw source rows | 758 |
| Deduped source rows | 140 |
| Monthly screen rows | 2,750 |
| Trade-level portfolio rows | 40,320 |
| Positive pre-May rows | 40,320 |
| Loose pre-May rows | 16,896 |
| Strict pre-May rows | 4,182 |
| Selected strict rows | 100 |
| Selected unique member sets | 44 |
| May-positive selected rows | 0 |
| May-negative selected rows | 100 |
| May-flat selected rows | 0 |

The selected pre-May rows were active and stable on the optimization window.
The rank 1 row, `riskcombo-910a9cff55b9e469`, combines WPR106-106 dense wick
fade, WPR106-108 ETH-follow-BTC lead-lag, and WPR106-109 ETH session-anchor
rows. It records +0.605807 pre-May return, 548 trades, 514 active days, 1.066
trades per active day, 28 active months, two losing pre-May months, annual
losses of 2024: 0, 2025: 1, and 2026 Jan-Apr: 1, max drawdown -0.058369, and
full cost-stress survival.

Representative selected rows:

| Rank | Portfolio | Members | Weight | Policy | Pre-May Return | Loss Months | Annual Losses | Max DD | May Return | May Trades |
| ---: | --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| 1 | `riskcombo-910a9cff55b9e469` | 5 | equal | conc1/day2/no stop | +0.605807 | 2 | 2024: 0, 2025: 1, 2026: 1 | -0.058369 | -0.009206 | 20 |
| 2 | `riskcombo-f801ebafd9b72b67` | 5 | stability | conc1/day2/no stop | +0.594014 | 2 | 2024: 0, 2025: 2, 2026: 0 | -0.054083 | -0.009098 | 20 |
| 5 | `riskcombo-3023847d256caca0` | 4 | stability | conc1/day1/no stop | +0.740160 | 4 | 2024: 1, 2025: 2, 2026: 1 | -0.058792 | -0.001124 | 20 |
| 17 | `riskcombo-0a9209b9d2890799` | 4 | stability | conc1/day3/loss stop | +0.621385 | 3 | 2024: 1, 2025: 2, 2026: 0 | -0.051116 | -0.003897 | 19 |

May rejected the selected set. The best May row was still negative:
`riskcombo-3023847d256caca0` at -0.001124 with 20 trades and -0.015772 max
drawdown. The worst selected May row was `riskcombo-65ef61c1f667f036` at
-0.028437. All selected May rows had zero cost-stress survival.

## Interpretation

The cross-family daily risk throttle can manufacture excellent-looking pre-May
month stability from existing rejected sleeves. That is useful diagnostic
evidence because it handles actual trade timing and overlap instead of relying
only on monthly recombination. It also shows that the active-rate target is not
the blocker: selected rows sit near 1.0 to 1.24 trades per active day after
overlap and daily throttles.

The problem is out-of-sample transfer. The selected set is still dominated by
ETHUSDT prior-day/session-anchor, ETH-follow-BTC lead-lag, and dense ETH wick or
volatility rows. Those streams complement each other in pre-May months but lose
as a group in May 2026. Because every selected strict row benchmarks negative,
this is not candidate-ready evidence.

WPR106-113 rejects the current cross-family daily risk-throttle portfolio
construction. The next useful direction should avoid selecting from the same
ETH-heavy WPR106-106/108/109 sleeve cluster unless a new pre-May-only
out-of-sample split or source-level regime test can explain why May should not
repeat the cluster failure.

## Artifacts

- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/scripts/run_wpr106_113_cross_family_daily_risk_throttle_search.py`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/wpr106_113_cross_family_daily_risk_throttle_summary.json`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/wpr106_113_runner.log`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/pre_may/deduped_source_pool.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/pre_may/monthly_screen_combos.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/pre_may/combined_ranking.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/pre_may/combined_monthly_returns.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_113_cross_family_daily_risk_throttle_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_113_cross_family_daily_risk_throttle_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
