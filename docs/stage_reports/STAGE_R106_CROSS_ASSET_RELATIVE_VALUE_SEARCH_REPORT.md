# Stage R106 Cross-Asset Relative Value Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-108-cross-asset-relative-value-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for family choice, beta choice, spread window,
score-threshold calibration, hold choice, session/filter choice, ranking, and
selection. May 2026 is excluded from all tuning and selection. May is joined
only after pre-May loose/strict rows are selected, and only as a benchmark
holdout. No candidate pack, paper/live artifact, order placement, sizing
change, runtime-mode change, live configuration write, CUDA speedup claim, or
promotion claim is made.

## Method

The artifact runner uses the WPR106-96 verified BTCUSDT/ETHUSDT public-archive
context from 2024-01-01 through 2026-05-31. BTC and ETH 15m bars are aligned on
timestamp, with matching aggTrade quote-flow imbalance. Both symbols contribute
84,672 aligned rows. The pre-May OLS ETH/BTC beta is fixed at 1.130693 and is
computed only from pre-May 4-bar returns.

The runner tests cross-asset signals built from completed 15m bars and enters
on the next bar. Pair-return rows are normalized BTC/ETH spread trades with
both legs represented inside the return and cost accounting. Single-leg
diagnostic rows use the cross-asset signal but trade only BTCUSDT or ETHUSDT;
they are reported separately from true pair rows.

Families:

- ETH/BTC spread mean reversion;
- ETH/BTC spread momentum and spread-delta momentum;
- ETH/BTC relative-return momentum and reversion;
- BTC-leading-ETH and ETH-leading-BTC pair catch-up;
- flow-divergence relative-value;
- single-leg BTC/ETH lead-lag diagnostics.

The search covers unit beta and pre-May OLS beta, 96/384/1,536-bar windows,
4/8/16/32/64-bar holds, all/Asia/Europe/US sessions, all/calm/wide/flow
filters, and pre-May-only quantile thresholds for 1, 2, 3, or 5 target signals
per active day. Costs are 0.0432% taker fee per side plus 0.0150%
slippage/spread allowance per normalized trade.

## Results

The screen evaluated 19,200 rows. It found 986 positive pre-May rows, 81 loose
pre-May rows, and zero strict month-stability rows.

| Scope | Rows |
| --- | ---: |
| Evaluated rows | 19,200 |
| Positive pre-May rows | 986 |
| Loose pre-May rows | 81 |
| Strict pre-May rows | 0 |
| Selected May benchmark rows | 81 |
| May-positive selected rows | 11 |
| May-negative selected rows | 69 |
| May-flat selected rows | 1 |

The positive rows split by trade type:

| Trade Type | Positive Rows | Loose Rows |
| --- | ---: | ---: |
| Pair BTC/ETH relative value | 301 | 7 |
| Single ETH follow-BTC diagnostic | 526 | 71 |
| Single BTC follow-ETH diagnostic | 159 | 3 |

The active-rate hypothesis was not the blocker: all 986 positive rows landed
inside 1 to 5 trades per active day after overlap handling. Of the positive
rows, 953 were active in at least 24 months and 475 had cost-stress survival of
at least 0.75. The blocker was annual stability: zero positive rows met the
full-year constraint of two or fewer losing active months in both 2024 and
2025, and zero met the combined full-year plus partial-2026 target.

Top selected rows were dominated by ETH single-leg follow-BTC diagnostics:

| Rank | Candidate | Trade Type | Pre-May Return | Trades | Trades/Active Day | Active Months | Losing Months | Annual Losses | May Return | May Trades | Note |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 1 | `xasset-de4ac045c28d3b9c` | ETH single-leg | +1.652138 | 299 | 1.000 | 28 | 9 | 2024: 5, 2025: 3, 2026 Jan-Apr: 1 | -0.038135 | 12 | High pre-May return, annual target fail, May negative. |
| 3 | `xasset-ff42f59deceb29fd` | ETH single-leg | +1.524334 | 277 | 1.018 | 28 | 8 | 2024: 2, 2025: 4, 2026 Jan-Apr: 2 | -0.093322 | 9 | Annual target fail, May negative. |
| 8 | `xasset-d44e3799b6d3061e` | ETH single-leg | +1.417152 | 744 | 1.000 | 28 | 7 | 2024: 2, 2025: 3, 2026 Jan-Apr: 2 | +0.043278 | 27 | May positive, pre-May annual target fail. |
| 12 | `xasset-264398ad33c1ce89` | ETH single-leg | +1.384788 | 281 | 1.052 | 28 | 5 | 2024: 2, 2025: 3, 2026 Jan-Apr: 0 | -0.016162 | 5 | Closest stability row, still fails 2025 by one month and May negative. |

True pair-return rows were weaker. The best selected pair rows:

| Rank | Candidate | Family | Pre-May Return | Trades | Active Months | Losing Months | Annual Losses | May Return | May Trades | Note |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 75 | `xasset-bdc76b3e1b897357` | spread-delta momentum | +0.191125 | 179 | 28 | 10 | 2024: 5, 2025: 2, 2026 Jan-Apr: 3 | -0.042232 | 9 | Pair row, unstable, May negative. |
| 76 | `xasset-cea2dbfbcf58865c` | spread-delta momentum | +0.177596 | 58 | 26 | 8 | 2024: 3, 2025: 5, 2026 Jan-Apr: 0 | -0.010221 | 2 | Pair row, too weak, May negative. |
| 78 | `xasset-5811c24a7dfe96e3` | relative momentum | +0.149425 | 268 | 28 | 10 | 2024: 6, 2025: 2, 2026 Jan-Apr: 2 | -0.025013 | 8 | Pair row, unstable, May negative. |

The best May-positive rows among all selected rows were not eligible because
they already failed pre-May annual stability. For example
`xasset-a1968ab22fed56bd` benchmarks +0.061293 in May, but its pre-May losses
are 2024: 3, 2025: 4, and 2026 Jan-Apr: 2.

## Interpretation

WPR106-108 adds a materially different family to the broad search. It shows
that cross-asset lead-lag diagnostics can produce active and cost-positive
ETHUSDT rows, but the strongest rows are single-leg ETH follow-BTC effects, not
robust BTC/ETH pair trades. True pair-return strategies are much weaker and
May rejects every selected pair row that traded in May.

The family fails the requested objective as currently configured. There is no
strict row, no positive row meets the full-year annual stability target, and
May mostly contradicts the selected loose rows. The closest row has only five
pre-May losing months but still fails the 2025 annual cap and loses in May.
This is diagnostic evidence, not a candidate-ready lead.

## Artifacts

- `data/research/wpr106_108_cross_asset_relative_value_search/scripts/run_wpr106_108_cross_asset_relative_value_search.py`
- `data/research/wpr106_108_cross_asset_relative_value_search/wpr106_108_cross_asset_summary.json`
- `data/research/wpr106_108_cross_asset_relative_value_search/wpr106_108_runner.log`
- `data/research/wpr106_108_cross_asset_relative_value_search/pre_may/combined_ranking.parquet`
- `data/research/wpr106_108_cross_asset_relative_value_search/pre_may/combined_ranking.csv`
- `data/research/wpr106_108_cross_asset_relative_value_search/pre_may/family_summary.parquet`
- `data/research/wpr106_108_cross_asset_relative_value_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_108_cross_asset_relative_value_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_108_cross_asset_relative_value_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_108_cross_asset_relative_value_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_108_cross_asset_relative_value_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
