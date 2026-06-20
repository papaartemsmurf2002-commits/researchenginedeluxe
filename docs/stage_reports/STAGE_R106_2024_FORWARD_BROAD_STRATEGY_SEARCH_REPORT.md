# Stage R106 2024-Forward Broad Strategy Search Report

Date: 2026-06-10

Work packet:
`docs/work_packets/WPR106-85-2024-forward-broad-strategy-search.md`

## Scope

WPR106-85 moved the next research step away from defending the rejected
BTCUSDT sparse side-veto lead. It first replayed the existing no-RSI four-bar
Lorentzian/KNN archive mapper, then built exact-window archive-backed durable
fixture packs for the historical-cycle runner and screened broader transparent
strategy families over BTCUSDT and ETHUSDT.

The tuning/search window was restricted to:

- start: 2024-01-01 00:00:00 UTC;
- cutoff: 2026-04-30 23:59:59 UTC;
- May 2026: not used.

## Data And Artifacts

Generated research-only output root:

- `data/research/wpr106_85_2024_forward_pre_may_archive_map/`

Archive mapper command:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main map-binance-archive-four-bar-datasets --output-dir wpr106_85_2024_forward_pre_may_archive_map --start-month 2024-01 --end-month 2026-04 --sample-rows-per-interval 8000 --matrix-workers 2 --force
```

The mapper used existing local Binance Vision monthly ZIPs only. It did not
download provider data. Runtime was 2426.860491 seconds.

Generated datasets:

- BTCUSDT:
  `data/research/wpr106_85_2024_forward_pre_may_archive_map/datasets/btcusdt_no_rsi_four_bar_binance_archive_2024-01_to_2026-04_8000_dataset.parquet`
- ETHUSDT:
  `data/research/wpr106_85_2024_forward_pre_may_archive_map/datasets/ethusdt_no_rsi_four_bar_binance_archive_2024-01_to_2026-04_8000_dataset.parquet`

Each symbol has:

- 16,000 selected rows;
- 8,000 15m-to-1h rows;
- 8,000 1h-to-4h rows;
- 8,000 long rows and 8,000 short rows;
- timestamp range from 2024-01-01 00:00:00 UTC through
  2026-04-30 22:45:00 UTC;
- zero 2026-05 rows.

The generated mapping manifest records `research_only: true`,
`observe_only: true`, `promotion_ready: false`, and a passing research boundary
report.

Additional exact-window durable fixture roots:

- BTCUSDT:
  `data/research/wpr106_85_2024_forward_durable_public_archive/fixture_packs/btcusdt_public_archive_candidate_depth_v1/fixture_pack_manifest.json`
- ETHUSDT:
  `data/research/wpr106_85_2024_forward_durable_public_archive_ethusdt/fixture_packs/ethusdt_public_archive_candidate_depth_v1/fixture_pack_manifest.json`

The fixture packs use the same 2024-01 through 2026-04 tuning window and do
not include May 2026. Each symbol has 28 monthly periods, 81,696 15m primary
bars, 1,225,440 1m lower-timeframe bars, and 1,225,406 selected aggTrade proxy
rows. The manifests validate with the historical fixture-pack contracts and
record research-only, observe-only, promotion-ready-false metadata.

The first combined BTC/ETH durable collection run timed out after BTCUSDT had
completed, leaving a stale `running` progress file in
`data/research/wpr106_85_2024_forward_durable_public_archive/`. ETHUSDT was
therefore collected in a separate root and only that completed ETHUSDT
manifest is used as evidence.

## KNN Matrix

Matrix replay command:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main run-hmm-knn-experiments --spec 'C:\Users\papaa\Music\researchenginedeluxe\data\research\wpr106_85_2024_forward_pre_may_archive_map\specs\btcusdt_four_bar_knn_larger_validation_spec.json' --dataset 'C:\Users\papaa\Music\researchenginedeluxe\data\research\wpr106_85_2024_forward_pre_may_archive_map\datasets\btcusdt_no_rsi_four_bar_binance_archive_2024-01_to_2026-04_8000_dataset.parquet' --output-dir 'C:\Users\papaa\Music\researchenginedeluxe\data\research\wpr106_85_2024_forward_pre_may_archive_map\matrices\btcusdt' --cache-dir 'C:\Users\papaa\Music\researchenginedeluxe\data\research\wpr106_85_2024_forward_pre_may_archive_map\cache\btcusdt' --workers 2 --skip-monitor
python -m tradingbotsuite.main run-hmm-knn-experiments --spec 'C:\Users\papaa\Music\researchenginedeluxe\data\research\wpr106_85_2024_forward_pre_may_archive_map\specs\ethusdt_four_bar_knn_larger_validation_spec.json' --dataset 'C:\Users\papaa\Music\researchenginedeluxe\data\research\wpr106_85_2024_forward_pre_may_archive_map\datasets\ethusdt_no_rsi_four_bar_binance_archive_2024-01_to_2026-04_8000_dataset.parquet' --output-dir 'C:\Users\papaa\Music\researchenginedeluxe\data\research\wpr106_85_2024_forward_pre_may_archive_map\matrices\ethusdt' --cache-dir 'C:\Users\papaa\Music\researchenginedeluxe\data\research\wpr106_85_2024_forward_pre_may_archive_map\cache\ethusdt' --workers 2 --skip-monitor
```

The replay completed four experiment rows. It emitted repeated HMM convergence
warnings and an XGBoost device fallback warning. Those warnings were treated as
diagnostic only; no CUDA speedup or GPU acceleration claim is made.

Summary:

| Symbol | Row | KNN trades | KNN expectancy | KNN profit factor | Meta trades | Meta expectancy | Meta profit factor | Decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BTCUSDT | 15m price/vol/flow Lorentzian inverse compatible | 602 | -0.000912 | 0.560923 | 18 | -0.001479 | 0.430281 | rejected |
| BTCUSDT | 1h price/vol/flow Lorentzian inverse compatible | 697 | -0.000462 | 0.871652 | 11 | +0.003944 | 3.944240 | rejected |
| ETHUSDT | 15m price/vol/flow Lorentzian inverse compatible | 816 | -0.000737 | 0.738044 | 72 | -0.000462 | 0.848209 | rejected |
| ETHUSDT | 1h price-path Lorentzian uniform same | 904 | -0.000535 | 0.896262 | 122 | -0.000543 | 0.891863 | rejected |

The BTCUSDT 1h/4h meta-filter row is the only aggregate-positive cell, but it
has only 11 trades, only four active months, and all meta-model PnL is
concentrated in 2025-08 through 2025-11. It remains blocked by
`meta_insufficient_trade_count`, `meta_single_split_dominates_pnl`, and
`research_only_not_live_promotable`. It is not a promising lead for May 2026
holdout.

## Stability Summary

Generated stability outputs:

- `data/research/wpr106_85_2024_forward_pre_may_archive_map/wpr106_85_pre_may_knn_stability_summary.json`
- `data/research/wpr106_85_2024_forward_pre_may_archive_map/wpr106_85_pre_may_knn_stability_summary.csv`
- `data/research/wpr106_85_2024_forward_pre_may_archive_map/wpr106_85_pre_may_knn_monthly_summary.csv`

Stability summary by accepted row set:

| Symbol | Row | Filter | Trades | Net return after costs | Active months | Losing active months | Avg trades/active day | Worst month |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 15m price/vol/flow | KNN | 602 | -0.548755 | 12 | 11 | 2.104895 | -0.132033 |
| BTCUSDT | 15m price/vol/flow | Meta | 18 | -0.026613 | 6 | 5 | 1.058824 | -0.011526 |
| BTCUSDT | 1h price/vol/flow | KNN | 697 | -0.322010 | 12 | 9 | 2.300330 | -0.135835 |
| BTCUSDT | 1h price/vol/flow | Meta | 11 | +0.043389 | 4 | 0 | 1.100000 | +0.004289 |
| ETHUSDT | 15m price/vol/flow | KNN | 816 | -0.601077 | 12 | 9 | 2.542056 | -0.129458 |
| ETHUSDT | 15m price/vol/flow | Meta | 72 | -0.033236 | 11 | 7 | 1.142857 | -0.038029 |
| ETHUSDT | 1h price-path | KNN | 904 | -0.483370 | 12 | 7 | 2.798762 | -0.328190 |
| ETHUSDT | 1h price-path | Meta | 122 | -0.066242 | 10 | 5 | 1.284211 | -0.110721 |

The active-entry policy was respected: rows with roughly 1 to 3 accepted
entries per active day were evaluated rather than rejected for activity alone.
They failed on expectancy, active-month sparsity, or split/month stability.

## Broad Historical-Cycle Screen

Broad-screen configs:

- BTCUSDT:
  `configs/research/wpr106_85_2024_forward_broad_screen_btcusdt_v1.json`
- ETHUSDT:
  `configs/research/wpr106_85_2024_forward_broad_screen_ethusdt_v1.json`

Cycle commands:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main run-historical-research-cycle --spec configs\research\wpr106_85_2024_forward_broad_screen_btcusdt_v1.json
python -m tradingbotsuite.main run-historical-research-cycle --spec configs\research\wpr106_85_2024_forward_broad_screen_ethusdt_v1.json
```

The broad screen covered `baseline_no_trade`, `trend_following_v1`,
`volatility_breakout_v1`, and `range_reversion_v1` across
`features_price_trend_vol`, `features_price_trend_vol_wt3d`, and 1h/4h/12h/24h
fixed holding windows. The configs explicitly set the 2024-01-01 through
2026-04-30 tuning window, keep May 2026 out of tuning, allow active 1 to 5
trades/day rows when cost and overlap evidence is available, and require May
2026 holdout only for promising pre-May leads.

Cycle outputs:

- BTCUSDT:
  `data/research/historical_cycles/wpr106_85_2024_forward_broad_screen_btcusdt_v1/`
- ETHUSDT:
  `data/research/historical_cycles/wpr106_85_2024_forward_broad_screen_ethusdt_v1/`

Each cycle materialized 63 candidates, 63 aggregate vector fixed-holding
backtests, 8 split backtests, and 22 cost-stress backtests. No candidate pack
was written. The backend summary records CPU vector aggregate screening and
reference validation/stress checks; CUDA was not selected by the
`fastest_exact` profile, so no GPU speedup claim is made.

Broad-screen stability outputs:

- `data/research/wpr106_85_2024_forward_broad_screen_summary/wpr106_85_broad_screen_stability_summary.json`
- `data/research/wpr106_85_2024_forward_broad_screen_summary/wpr106_85_broad_screen_candidate_stability_summary.csv`
- `data/research/wpr106_85_2024_forward_broad_screen_summary/wpr106_85_broad_screen_monthly_returns.csv`
- `data/research/wpr106_85_2024_forward_broad_screen_summary/wpr106_85_broad_screen_top_rows.csv`

Summary across non-baseline aggregate candidates:

| Symbol | Candidates | Positive net | Positive expectancy | Promising pre-May leads | Best net return | Best expectancy | Fewest losing months among top-net 10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 55 | 0 | 0 | 0 | -0.638379 | -0.001002 | 17 |
| ETHUSDT | 55 | 0 | 1 | 0 | -0.236801 | +0.000246 | 12 |

Best broad-screen rows by symbol:

| Symbol | Rank | Strategy | Features | Holding | Trades | Avg trades/active day | Active months | Losing active months | Expectancy | Net return | Profit factor | Worst month |
| --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 9 | trend_following_v1 | features_price_trend_vol | 24h | 778 | 1.000 | 28 | 19 | -0.001002 | -0.638379 | 0.892827 | -0.370583 |
| BTCUSDT | 11 | volatility_breakout_v1 | features_price_trend_vol | 24h | 740 | 1.000 | 28 | 18 | -0.001173 | -0.667204 | 0.880168 | -0.277847 |
| ETHUSDT | 9 | range_reversion_v1 | features_price_trend_vol | 24h | 681 | 1.000 | 28 | 13 | +0.000246 | -0.236801 | 1.019674 | -0.282171 |
| ETHUSDT | 10 | volatility_breakout_v1 | features_price_trend_vol | 12h | 1223 | 1.449 | 28 | 15 | -0.000157 | -0.471743 | 0.983725 | -0.382219 |

The ETHUSDT range-reversion row is the only positive-expectancy broad-screen
cell, but it is still negative after total costs, has 13 losing active months,
and remains rejected by incomplete split/cost/stability-region evidence. It is
not a promising pre-May lead and was not sent to May 2026 holdout.

## May 2026 Holdout

May 2026 was not used for tuning or selection. No May 2026 benchmark was run,
because no pre-May lead qualified as promising after either the KNN matrix or
the broad historical-cycle screen.

The current local archive cache has BTCUSDT/ETHUSDT monthly 15m, 1m, and
aggTrade ZIPs through 2026-04 only. `ISSUE-R106-025` records that May 2026
local holdout archive material must be added before a later promising lead can
receive the required May benchmark.

## Broad Family Status

The broader non-KNN families were fairly screened for the first time on
archive-backed 2024-01 through 2026-04 historical-cycle fixture packs. The
transparent trend, range, volatility breakout, and no-trade families did not
produce a promising pre-May lead.

The result should not be read as a proof that all broad families are dead. It
only closes this first archive-backed screen over the currently registered
transparent strategy contracts and two price/trend/vol feature sets. Families
still worth future research include:

- sparse event filters with alternate spacing, side gates, shock/ATR filters,
  flow confirmation, and post-selection logic;
- perp-context strategies where funding/OI/premium/basis data has truthful
  full-window coverage;
- fixed-hold, primary-bar exit, and lower-timeframe exit variants beyond the
  first 1h/4h/12h/24h grid;
- replay-overlay families that are representable by the current strategy
  contract;
- simple ensembles/vetoes with transparent economic logic and negative
  controls;
- scoped Lorentzian/KNN feature, filter, and parameter variants that can be
  tested without defending the rejected sparse BTC meta-filter lead.

The next engineering step is no longer the basic archive-backed fixture mapper
for pre-May BTCUSDT/ETHUSDT; that evidence now exists. The remaining data
blocker is May 2026 holdout ingestion, plus broader feature/context coverage
for strategy families that require funding, open interest, premium, basis, or
other perp context over the full window.

## Decision

WPR106-85 found no KNN or broad transparent-strategy lead worth sending to May
2026 holdout. The tested no-RSI four-bar Lorentzian/KNN rows remain
research-only rejected evidence, and the first archive-backed broad
historical-cycle screen over trend/range/volatility breakout/no-trade families
also rejected all non-baseline aggregate candidates.

The research direction stays broad. Future packets should prioritize novel
families, scoped Lorentzian/KNN feature/filter/parameter changes, truthful
full-window perp context where available, and month-to-month stability over one
large profitable window. May 2026 remains reserved as a benchmark holdout and
should only be used after a pre-May lead survives the documented gates.

No candidate pack, paper/live artifact, order placement, position sizing,
runtime-mode change, live configuration write, or promotion claim was produced.

## Validation

Passed:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

The contracts suite passed with 451 tests.
