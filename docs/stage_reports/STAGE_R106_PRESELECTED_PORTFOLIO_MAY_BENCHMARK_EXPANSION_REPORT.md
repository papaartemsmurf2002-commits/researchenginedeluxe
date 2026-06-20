# Stage R106 Preselected Portfolio May Benchmark Expansion Report

Date: 2026-06-11
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-97-preselected-portfolio-may-benchmark-expansion.md`

## Scope

WPR106-97 expands the May 2026 benchmark from the WPR106-96 rank-1 portfolio
check to all 40 WPR106-95 combinations that were already marked
`may_holdout_candidate: true` before May data was evaluated. The packet uses
frozen WPR106-95 sleeve definitions and the WPR106-96 verified BTCUSDT/ETHUSDT
May source context.

May 2026 was not used for strategy choice, feature choice, filter choice,
threshold choice, parameter changes, optimizer feedback, or selection changes.

## Method

The runner extracted 36 unique packet-qualified sleeves from the WPR106-95
top-40 May-holdout combinations and copied each sleeve's original
`config_resolved.json` into the WPR106-97 input inventory. It materialized
four full-context feature frames for:

- BTCUSDT `features_price_trend_vol`
- BTCUSDT `features_price_perp_aggflow_no_wt`
- ETHUSDT `features_price_trend_vol`
- ETHUSDT `features_price_perp_aggflow_no_wt`

Each sleeve was replayed over the full 2024-01-01 through 2026-05-31 context
with its frozen parameters, costs, holding window, and exit policy. Trades
were then filtered to May-entry trades. This preserves single-sleeve spacing,
cooldown, and no-overlap state across the April-to-May boundary. Portfolio
accounting matches WPR106-95: sum member trade `net_return / sleeve_count`.

Primary artifacts:

- Summary:
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/wpr106_97_may_benchmark_summary.json`
- Feature manifest:
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/features/wpr106_97_feature_context_manifest.json`
- Selected combinations:
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/input/wpr106_97_selected_top40_combinations.csv`
- Unique sleeve inventory:
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/input/wpr106_97_unique_sleeves.csv`
- Combo benchmark table:
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/may_only/wpr106_97_top40_combo_may_benchmarks.csv`
- Combo daily returns:
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/may_only/wpr106_97_top40_combo_daily_returns.csv`
- Unique sleeve May summary:
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/may_only/wpr106_97_unique_sleeve_may_summary.csv`

## Results

All 36 sleeve replays completed successfully. Across the 40 preselected
combinations:

- Positive May combinations: 24
- Negative May combinations: 16
- Combinations in the 1 to 5 trades-per-active-day range: 40
- May return range: -0.018153 to +0.044274
- Median May return: +0.023551
- Trades per active day range: 1.053 to 1.667

Top May benchmark rows:

| WPR106-95 rank | Combo | May return | Trades | Active days | Trades/active day | Overlap-day share | Positive days | Losing days |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 13 | `combo-f4f5b5aa62ffd476` | +0.044274 | 30 | 24 | 1.250 | 0.250 | 13 | 11 |
| 2 | `combo-d1ccbd91dc5325e5` | +0.031402 | 20 | 19 | 1.053 | 0.053 | 8 | 11 |
| 20 | `combo-476ca02fe3f276af` | +0.027199 | 28 | 23 | 1.217 | 0.130 | 12 | 11 |
| 21 | `combo-0c182c4a75e6a25d` | +0.027199 | 28 | 23 | 1.217 | 0.130 | 12 | 11 |
| 30 | `combo-8308c2da2c699773` | +0.026623 | 21 | 19 | 1.105 | 0.105 | 9 | 10 |
| 1 | `combo-d9edcc252c323b03` | +0.026603 | 25 | 20 | 1.250 | 0.250 | 8 | 12 |

The WPR106-96 rank-1 result is reproduced exactly:
`combo-d9edcc252c323b03` records +0.026603 equal-sleeve May return, 25
member trades, 20 active days, and 1.250 trades per active day.

Worst May benchmark rows:

| WPR106-95 rank | Combo | May return | Trades | Active days | Trades/active day | Overlap-day share | Positive days | Losing days |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 22 | `combo-356a713b5dd426b2` | -0.018153 | 24 | 18 | 1.333 | 0.333 | 6 | 12 |
| 23 | `combo-d27a1775c7b30df7` | -0.018153 | 24 | 18 | 1.333 | 0.333 | 6 | 12 |
| 17 | `combo-94d050e0ea08ac32` | -0.017340 | 25 | 19 | 1.316 | 0.316 | 7 | 12 |
| 18 | `combo-f79fd777c18f4031` | -0.017340 | 25 | 19 | 1.316 | 0.316 | 7 | 12 |
| 3 | `combo-40bfb3546b9707ac` | -0.014460 | 29 | 20 | 1.450 | 0.450 | 7 | 13 |

Ranks 3 through 12 all lose -0.014460 in May because they share a repeated
BTCUSDT volatility-breakout sleeve variant (`fbbe/6e79`) that records
-0.104401 May net return on 10 trades. That sleeve contradicted its pre-May
portfolio role and should be treated as rejected by this benchmark evidence.

Best and worst sleeve-level May evidence:

- Best sleeve: WPR106-91 BTCUSDT `0aa0ffe36b5f...`, transparent
  volatility breakout, +0.082892 May net return on 10 trades.
- Next best sleeves: WPR106-94 BTCUSDT `c66b21e80bf...` at +0.057419 and
  WPR106-91 BTCUSDT `ea9b0ade9515...` at +0.057029.
- Worst repeated sleeve: BTCUSDT `fbbe4e1c284...` / WPR106-94
  `6e79fc83ab5...`, transparent volatility breakout, -0.104401 May net
  return on 10 trades.
- Worst ETH sleeve: WPR106-88 ETHUSDT `56790eb061f...`, transparent
  volatility breakout, -0.031131 May net return on 13 trades.

## Interpretation

May 2026 does not reject the entire WPR106-95 portfolio-combination idea, but
it does reject several highly ranked combinations and exposes sleeve fragility.
The best May row is rank 13, not rank 1, and rank 2 also beats rank 1 on the
holdout. That is useful benchmark evidence, not permission to retune the old
selection with May.

The more defensible next research direction is to build a new pre-May-only
search that emphasizes the May-validated pattern as a diagnostic: avoid the
repeated BTC `fbbe/6e79` variant, investigate why the BTC `0aa0`, `c66b`, and
`ea9b` volatility-breakout sleeves held up, and require broader split,
monthly, cost-stress, ablation, no-trade, transparent baseline, and gate
evidence before any candidate claim.

No WPR106-97 row is candidate-ready. Daily behavior remains uneven even for
positive May rows: the best row has 11 losing active days, rank 2 has 11
losing active days, and rank 1 has 12 losing active days. These are
research-only diagnostics.

## Boundary

All outputs are research-only, observe-only, and promotion-ready false. No
candidate pack, paper/live artifact, order placement, position sizing,
runtime-mode change, live-configuration write, CUDA speedup claim, or
promotion claim was created. No May 2026 tuning or selection feedback was
applied to the benchmarked WPR106-95 definitions.

## Validation

Passed:

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed
