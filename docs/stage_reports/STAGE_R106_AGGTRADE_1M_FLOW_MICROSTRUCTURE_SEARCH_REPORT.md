# Stage R106 AggTrade 1m Flow Microstructure Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-111-aggtrade-1m-flow-microstructure-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for family choice, score construction, threshold
calibration, hold choice, session/filter choice, ranking, and selection. May
2026 is excluded from all tuning and selection. May is joined only after
pre-May loose/strict rows are selected, and only as a benchmark holdout. No
candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or promotion
claim is made.

## Method

The artifact runner uses WPR106-96 verified Binance Vision 1m aggTrade
aggregates for BTCUSDT and ETHUSDT from 2024-01-01 through 2026-05-31. Each
symbol contributes 1,270,046 completed 1m aggregate rows. The aggregate `price`
field is used as a next-minute entry and fixed-horizon exit price; this packet
does not claim complete 1m OHLC path/high-low exit evidence.

Signals are computed from completed 1m aggregate rows and enter on the next 1m
aggregate price. Pre-May trades must exit before 2026-05-01. One-position
overlap handling is enforced before active-rate metrics are measured. Costs are
0.0432% taker fee per side plus a 0.0150% slippage/spread allowance per side.

Families:

- flow-burst follow and fade;
- flow-persistence follow and exhaustion fade;
- price/flow divergence follow variants;
- volume-shock follow and fade.

The search covers BTCUSDT and ETHUSDT, long/short/both side modes, 15/30/60/120
/240-minute fixed holds, all/Asia/Europe/US sessions, all/calm/wide/flow-active
filters, and pre-May-only thresholds targeting 1, 2, 3, or 5 signals per active
day.

## Results

The screen evaluated 15,360 rows. It found 442 positive pre-May rows, 42 loose
pre-May rows, and zero strict month-stability rows.

| Scope | Rows |
| --- | ---: |
| Evaluated rows | 15,360 |
| Positive pre-May rows | 442 |
| Loose pre-May rows | 42 |
| Strict pre-May rows | 0 |
| Selected May benchmark rows | 42 |
| May-positive selected rows | 18 |
| May-negative selected rows | 24 |
| May-flat selected rows | 0 |

The active-rate hypothesis was not the blocker: all 442 positive rows landed
inside 1 to 5 trades per active day after overlap handling. Of the positive
rows, 403 were active in at least 24 months and 210 had cost-stress survival of
at least 0.75. The blocker was annual stability. Only seven positive rows met
the full-year plus partial-2026 losing-month target, and none had at least 60
trades or 24 active months; they were sparse flow-burst fade shorts with 5 to
15 trades.

Top selected rows by pre-May return:

| Rank | Candidate | Family | Pre-May Return | Trades | Active Months | Annual Losses | May Return | May Trades | Note |
| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 1 | `flow1m-58682c5dd5e1679d` | ETH price/flow divergence | +0.700716 | 358 | 28 | 2024: 6, 2025: 2, 2026 Jan-Apr: 1 | -0.007368 | 21 | High pre-May return, 2024 instability, May negative. |
| 3 | `flow1m-97de4c7e28fc7979` | ETH volume-shock follow | +0.635439 | 186 | 28 | 2024: 5, 2025: 4, 2026 Jan-Apr: 1 | -0.039361 | 9 | Low drawdown but annual target fail, May negative. |
| 6 | `flow1m-db360562a6a340e2` | ETH volume-shock follow | +0.576991 | 421 | 28 | 2024: 4, 2025: 4, 2026 Jan-Apr: 0 | -0.045154 | 19 | Best active-row stability among high-return rows, still fails both full years. |
| 7 | `flow1m-99503eb48c3459f6` | ETH flow-persistence follow | +0.406836 | 323 | 28 | 2024: 2, 2025: 5, 2026 Jan-Apr: 1 | -0.014530 | 11 | 2024 acceptable, 2025 unstable, May negative. |
| 14 | `flow1m-fa3e6d2009132db3` | BTC price/flow divergence | +0.175070 | 113 | 28 | 2024: 4, 2025: 3, 2026 Jan-Apr: 1 | +0.001844 | 3 | May positive but pre-May annual target fail. |

Best May benchmark rows among selected rows:

| Candidate | Family | Pre-May Return | Pre-May Annual Losses | May Return | May Trades | Note |
| --- | --- | ---: | --- | ---: | ---: | --- |
| `flow1m-bcca91654aeec288` | ETH price/flow divergence short | +0.173806 | 2024: 6, 2025: 3, 2026 Jan-Apr: 1 | +0.013959 | 7 | May-positive, but 2024 fails badly and active months are only 24. |
| `flow1m-c53cdb04068495dd` | ETH price/flow divergence long | +0.379975 | 2024: 2, 2025: 5, 2026 Jan-Apr: 1 | +0.010422 | 2 | May-positive, but 2025 fails. |
| `flow1m-1535ffde0926fd0e` | BTC price/flow divergence long | +0.098576 | 2024: 3, 2025: 5, 2026 Jan-Apr: 2 | +0.007678 | 2 | May-positive, but 2025 and partial-2026 fail. |

The full-year-target positives were not viable leads:

| Candidate | Symbol | Family | Trades | Active Months | Annual Losses | Pre-May Return | Reason Not Selected |
| --- | --- | --- | ---: | ---: | --- | ---: | --- |
| `flow1m-54845263e4b947c7` | BTCUSDT | flow-burst fade short | 7 | 5 | 2024: 0, 2025: 2, 2026 Jan-Apr: 0 | +0.022958 | Too sparse for active strategy evidence. |
| `flow1m-85d3469e6df62ae5` | ETHUSDT | flow-burst fade short | 13 | 9 | 2024: 1, 2025: 2, 2026 Jan-Apr: 0 | +0.017708 | Too sparse for active strategy evidence. |
| `flow1m-53d8c33392034204` | ETHUSDT | flow-burst fade short | 15 | 7 | 2024: 2, 2025: 2, 2026 Jan-Apr: 0 | +0.013516 | Too sparse for active strategy evidence. |

## Interpretation

WPR106-111 gives the 1m aggTrade order-flow family a serious pre-May sweep with
active 1 to 5 trades/day allowed. It finds some active, cost-positive rows, but
not the requested month-stable profile. The most profitable rows are
ETHUSDT-heavy, 240-minute holds around price/flow divergence or volume-shock
follow behavior; they fail annual month stability, especially 2024 or 2025.

May does not rescue the family. Some selected rows are May-positive, but every
May-positive selected row was already rejected by pre-May annual stability. The
only rows satisfying the annual loss-count target are too sparse to support an
active lead. This is diagnostic evidence, not candidate-ready evidence.

## Artifacts

- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/scripts/run_wpr106_111_aggtrade_1m_flow_microstructure_search.py`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/wpr106_111_aggtrade_1m_flow_summary.json`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/wpr106_111_runner.log`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/pre_may/combined_ranking.parquet`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/pre_may/combined_monthly_returns.parquet`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/pre_may/family_summary.parquet`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_111_aggtrade_1m_flow_microstructure_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
