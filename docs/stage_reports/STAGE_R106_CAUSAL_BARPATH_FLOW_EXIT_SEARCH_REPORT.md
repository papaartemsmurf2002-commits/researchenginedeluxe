# Stage R106 Causal Bar-Path Flow Exit Search Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-105-causal-barpath-flow-exit-search.md`
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It uses
2024-01-01 through 2026-04-30 for optimization, scoring, ranking, filtering,
and selection. May 2026 is joined only after fixed pre-May rows are selected,
and only as a benchmark holdout. No candidate pack, paper/live artifact, order
placement, sizing change, runtime-mode change, live configuration write, CUDA
speedup claim, or promotion claim is made.

## Method

The runner uses the WPR106-96 verified BTCUSDT/ETHUSDT public-archive context
from 2024-01-01 through 2026-05-31. Both symbols have 84,672 15m bars, May
2026 checksum-verified 15m/1m/aggTrade archives, and 1-minute aggTrade rows
aggregated to a trade-flow proxy. Signals are generated from completed 15m bars
and enter on the next bar. Pre-May trades are required to exit before
2026-05-01, so late-April signals cannot borrow May price path during tuning.

The artifact runner evaluates 5,832 deterministic candidates: 2,916 per
symbol. Families include:

- channel breakout with same-direction, opposite-flow, or no flow confirmation;
- flush/fade reversal using return shock, wick, session, and flow;
- range reversion using channel location, choppiness, and flow reversal;
- compression continuation after low-range regimes.

Each candidate uses one-position-at-a-time overlap handling, fixed-hold or
ATR-barrier exits, and explicit round-trip cost of 0.0432% taker fee per side
plus 0.0150% slippage/spread allowance per side. Active 1-to-5 trades per
active day are accepted when monthly, cost, concentration, and drawdown
evidence are measured.

## Results

The staged screen found 270 positive pre-May rows, but zero strict
month-stability rows. Three ETHUSDT rows passed the loose holdout-candidate
filter; all three failed the May benchmark.

| Scope | Rows | Positive Pre-May | Loose Rows | Strict Rows | Best Pre-May Return |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 2,916 | 97 | 0 | 0 | +0.122212 |
| ETHUSDT | 2,916 | 173 | 3 | 0 | +0.288412 |
| Total | 5,832 | 270 | 3 | 0 | +0.288412 |

By family:

| Symbol | Family | Rows | Positive Rows | Loose Rows | Strict Rows | Best Return | Fewest Losing Months |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | channel_breakout | 972 | 27 | 0 | 0 | +0.030263 | 0 |
| BTCUSDT | compression_continuation | 432 | 18 | 0 | 0 | +0.122212 | 2 |
| BTCUSDT | flush_fade | 648 | 52 | 0 | 0 | +0.063104 | 0 |
| BTCUSDT | range_reversion | 864 | 0 | 0 | 0 | -0.052580 | 13 |
| ETHUSDT | channel_breakout | 972 | 55 | 1 | 0 | +0.288412 | 0 |
| ETHUSDT | compression_continuation | 432 | 53 | 0 | 0 | +0.132603 | 0 |
| ETHUSDT | flush_fade | 648 | 63 | 2 | 0 | +0.063250 | 0 |
| ETHUSDT | range_reversion | 864 | 2 | 0 | 0 | +0.080391 | 11 |

The selected pre-May rows:

| Selected Rank | Candidate | Family | Pre-May Return | Trades | Active Months | Losing Months | Annual Losses | May Return | May Trades | Note |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| 1 | `barflow-4af57c2235dc425e` | ETHUSDT channel breakout | +0.093710 | 54 | 23 | 10 | 2024: 5, 2025: 4, 2026 Jan-Apr: 1 | -0.010393 | 5 | Loose only; May rejects. |
| 2 | `barflow-5adcceacbae60ef7` | ETHUSDT flush/fade | +0.063250 | 56 | 24 | 10 | 2024: 5, 2025: 5, 2026 Jan-Apr: 0 | -0.036940 | 3 | Loose only; May rejects. |
| 3 | `barflow-1f575771dfa9ff18` | ETHUSDT flush/fade | +0.015509 | 54 | 25 | 10 | 2024: 4, 2025: 5, 2026 Jan-Apr: 1 | -0.002629 | 1 | Loose only; May rejects. |

Several rows have appealing annual loss counts, but they are too sparse to be
credible leads. For example, the top compression-continuation diagnostics have
only 9 to 15 active months and 13 to 19 inactive months. They are useful
directional evidence, not stable strategies.

## Interpretation

This packet gives the bar-path/flow family a fair staged test without reusing
the rejected sleeve portfolio logic. It finds profitable pockets, especially
ETHUSDT compression and channel-breakout variants, but the stable-looking rows
are too inactive and the active rows lose in too many months. The only three
fixed pre-May rows that met the loose holdout rule all lose in May.

The family is therefore rejected as currently configured. The useful signal is
negative: simple completed-bar price path plus aggTrade-flow filters do not
solve the requested month-to-month stability target when costs, overlap, active
coverage, and May holdout are handled.

## Artifacts

- `data/research/wpr106_105_causal_barpath_flow_exit_search/scripts/run_wpr106_105_barpath_flow_search.py`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/wpr106_105_barpath_flow_summary.json`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/wpr106_105_runner.log`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/pre_may/wpr106_105_barpath_flow_candidate_ranking.parquet`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/pre_may/wpr106_105_barpath_flow_top2000.csv`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/pre_may/wpr106_105_monthly_returns_all_ranked.csv`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/pre_may/wpr106_105_daily_returns_all_ranked.csv`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/pre_may/wpr106_105_selected_pre_may_leads.csv`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/pre_may/wpr106_105_selected_monthly_returns.csv`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/pre_may/wpr106_105_selected_pre_may_trades.parquet`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/may_benchmark/wpr106_105_selected_may_benchmark.csv`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/may_benchmark/wpr106_105_selected_may_monthly_returns.csv`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/may_benchmark/wpr106_105_selected_may_daily_returns.csv`
- `data/research/wpr106_105_causal_barpath_flow_exit_search/may_benchmark/wpr106_105_selected_may_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_105_causal_barpath_flow_exit_search/scripts`: passed.
- `python -m compileall -q src/tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`: 460 passed.
