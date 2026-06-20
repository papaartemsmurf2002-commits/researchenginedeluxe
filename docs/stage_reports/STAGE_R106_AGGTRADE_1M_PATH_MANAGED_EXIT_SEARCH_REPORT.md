# Stage R106 AggTrade 1m Path-Managed Exit Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-112-aggtrade-1m-path-managed-exit-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for source-row pool choice, TP/SL/time-stop
choice, ranking, and selection. May 2026 is excluded from all tuning and
selection. May is joined only after fixed pre-May rows are selected, and only as
a benchmark holdout. No candidate pack, paper/live artifact, order placement,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim is made.

The replay uses completed 1m aggTrade aggregate prices as a diagnostic point
path. It does not claim complete 1m OHLC coverage or intraminute high/low
barrier precision.

## Method

The runner starts from WPR106-111 positive pre-May 1m aggTrade flow rows for
BTCUSDT and ETHUSDT. The source pool is filtered before May on trade count,
active months, active 1 to 5 trades per day, and cost-stress survival, producing
271 source rows: 63 BTCUSDT and 208 ETHUSDT.

Each source row is replayed with fixed path-managed exit overlays:

- max hold: 30, 60, 120, or 240 minutes;
- take profit: 0.3%, 0.6%, 1.0%, or 1.5%;
- stop loss: 0.3%, 0.6%, 1.0%, or 1.5%.

Signals enter on the next completed 1m aggregate price. The first reached TP,
SL, or time stop exits the trade using that aggregate price. One-position
overlap is enforced against the actual path-managed exit timestamp, and pre-May
trades must exit before 2026-05-01. Costs remain the WPR106-111 explicit taker
commission plus conservative slippage/spread allowance.

## Results

The screen evaluated 17,344 exit-overlay rows. It found 2,316 positive pre-May
rows, 89 loose pre-May rows, and zero strict month-stability rows.

| Scope | Rows |
| --- | ---: |
| Source pool rows | 271 |
| Evaluated exit-overlay rows | 17,344 |
| Positive pre-May rows | 2,316 |
| Loose pre-May rows | 89 |
| Strict pre-May rows | 0 |
| Selected May benchmark rows | 89 |
| May-positive selected rows | 58 |
| May-negative selected rows | 31 |
| May-flat selected rows | 0 |

The active-rate hypothesis was not the blocker: all 2,316 positive rows landed
inside 1 to 5 trades per active day after overlap handling. Of the positive
rows, 2,057 were active in at least 24 months, 557 had cost-stress survival of
at least 0.75, and 123 had full cost-stress survival. The blocker remained
annual month stability: zero positive rows met the full-year target of no more
than two losing active months in both 2024 and 2025.

Top selected rows by pre-May return:

| Rank | Candidate | Family | Exit | Pre-May Return | Trades | Active Months | Annual Losses | May Return | May Trades | Note |
| ---: | --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 1 | `exit1m-d17af0cdc1689d55` | ETH flow leads price follow short | TP 1.0%, SL 1.5%, 240m | +0.193259 | 152 | 28 | 2024: 4, 2025: 5, 2026 Jan-Apr: 0 | -0.009363 | 4 | Highest selected pre-May return, annual target fail, May negative. |
| 2 | `exit1m-1ab1bd9643b8bbc5` | ETH price leads flow follow short | TP 1.5%, SL 1.5%, 240m | +0.191279 | 76 | 24 | 2024: 5, 2025: 3, 2026 Jan-Apr: 1 | +0.015629 | 7 | Best May-positive cluster, but pre-May annual target fail. |
| 8 | `exit1m-1c37852392f71dfc` | ETH price leads flow follow short | TP 1.5%, SL 1.0%, 240m | +0.161480 | 78 | 24 | 2024: 3, 2025: 3, 2026 Jan-Apr: 1 | +0.015629 | 7 | Lower losing-month count than ranks 2-7, still fails both full years. |
| 21 | `exit1m-c2ce6b6362f5430b` | BTC price leads flow follow long | TP 1.0%, SL 1.5%, 240m | +0.073721 | 99 | 26 | 2024: 3, 2025: 6, 2026 Jan-Apr: 1 | -0.011147 | 3 | Best selected BTC cluster by rank, unstable 2025, May negative. |

Best stability diagnostics among positive active rows were too weak to select
as leads. The closest rows had five losing pre-May months but were only barely
positive and cost-stress fragile. Example:

| Candidate | Symbol | Family | Trades | Active Months | Annual Losses | Pre-May Return | Cost-Stress Survival | Reason Not Selected |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| `exit1m-1171e35f9299e0e3` | BTCUSDT | flow leads price follow short | 69 | 23 | 2024: 1, 2025: 3, 2026 Jan-Apr: 1 | +0.013981 | 0.25 | Fails 2025 annual cap, insufficient active months, weak cost stress. |

Family summary:

| Symbol | Family | Template | Rows | Positive | Loose | Strict | Best Return | Best Losing Months |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | flow_price_divergence | price_leads_flow_follow | 2,496 | 347 | 41 | 0 | +0.188334 | 8 |
| BTCUSDT | flow_price_divergence | flow_leads_price_follow | 512 | 66 | 9 | 0 | +0.037121 | 5 |
| ETHUSDT | flow_persistence | flow_exhaustion_fade | 512 | 48 | 6 | 0 | +0.358010 | 9 |
| ETHUSDT | flow_price_divergence | price_leads_flow_follow | 8,640 | 1,477 | 30 | 0 | +0.332812 | 7 |
| ETHUSDT | flow_price_divergence | flow_leads_price_follow | 320 | 20 | 2 | 0 | +0.193259 | 9 |

## Interpretation

Path-managed exits improve the 1m aggTrade flow family as a diagnostic screen:
positive rows increase from 442 to 2,316, loose rows increase from 42 to 89, and
selected May positives improve from 18/42 to 58/89 compared with WPR106-111.
That is useful evidence that exit timing matters for this family.

It still does not produce a candidate-quality lead. Every selected May-positive
row was already rejected by pre-May annual stability, and the closest pre-May
stability rows are low-return, cost-stress fragile diagnostics. The strongest
cluster is ETHUSDT short price/flow divergence with 240-minute path exits; it
can benchmark positive in May, but it fails the requested month-to-month
stability target before May is ever inspected.

Several rows share identical trade behavior through different WPR106-111 source
hold or filter settings, so duplicate-looking selected rows should be treated
as repeated diagnostics of the same underlying signal behavior rather than
independent leads.

## Artifacts

- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/scripts/run_wpr106_112_aggtrade_1m_path_managed_exit_search.py`
- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/wpr106_112_aggtrade_1m_path_exit_summary.json`
- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/wpr106_112_runner.log`
- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/pre_may/source_pool.parquet`
- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/pre_may/combined_ranking.parquet`
- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/pre_may/combined_monthly_returns.parquet`
- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/pre_may/family_summary.parquet`
- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_112_aggtrade_1m_path_managed_exit_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
