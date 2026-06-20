# Stage R106 Post-Selection Side Veto Optimizer Report

Date: 2026-06-10

Work packet: `docs/work_packets/WPR106-82-post-selection-side-veto-optimizer.md`

## Scope

WPR106-82 ran the expensive follow-up requested by the WPR106-81 decision: a
bounded optimizer sweep around BTCUSDT post-selection long-only
`sparse_event_filter_v1` rows. It kept the fixed-hold exit, durable public
archive data source, research-only boundary, and no candidate-pack policy.

The first 194-candidate sample was stopped after roughly 89 CPU minutes without
aggregate artifacts. The packet was downshifted to a tractable 50-candidate
random sample with top-two split and cost-stress refinement. That run
completed and wrote final manifests.

## Artifacts

Generated cycle outputs:

- `data/research/historical_cycles/sparse_side_veto_optimizer_btcusdt_r106_v1/research_cycle_manifest.json`
- `data/research/historical_cycles/sparse_side_veto_optimizer_btcusdt_r106_v1/candidate_rankings.parquet`
- `data/research/historical_cycles/sparse_side_veto_optimizer_btcusdt_r106_v1/candidate_gate_report.parquet`
- `data/research/historical_cycles/sparse_side_veto_optimizer_btcusdt_r106_v1/backtest_index.parquet`
- `data/research/historical_cycles/sparse_side_veto_optimizer_btcusdt_r106_v1/wpr106_82_candidate_summary.csv`

Generated Monte Carlo outputs:

- `data/research/monte_carlo_exit_sizing/wpr106_82/wpr106_82_monte_carlo_optimizer_summary.json`
- `data/research/monte_carlo_exit_sizing/wpr106_82/wpr106_82_monte_carlo_optimizer_candidates.csv`
- `data/research/monte_carlo_exit_sizing/wpr106_82/wpr106_82_monte_carlo_optimizer_paths.csv`

Cycle counts:

- candidates: 54;
- aggregate backtests: 54;
- split backtests: 8;
- cost-stress backtests: 22;
- candidate packs written: 0.

## Optimizer Results

The optimizer improved the WPR106-81 lead. The top two refined rows were both
aggTrade-contrarian post-selection long-only sparse rows.

Rank 1 optimized row:

- candidate: `941c7d1a1a3b8669c66e816ee465dc30cf18b1fba56c54b95555a027cdf046d6`;
- parameters:
  - `atr_percentile_threshold: 0.65`;
  - `shock_threshold: 1.3`;
  - `min_score: 0.5`;
  - `score_window_bars: 288`;
  - `top_n_per_window: 2`;
  - `cooldown_bars: 48`;
  - `max_side_share: 0.65`;
  - `side_balance_min_trades: 8`;
  - `flow_abs_threshold: 0.1`;
  - `flow_count_z_min: 0.5`;
  - `allowed_sides: long`;
  - `side_filter_stage: post_selection`.
- aggregate: 319 long trades, net return after cycle costs +20.174216,
  expectancy +0.010652, hit rate 0.551724, max drawdown -0.321446.
- split evidence: minimum split trade count 109; weakest split net return
  +0.039327 after cycle costs.
- cost stress: 11/11 scenarios passed; worst listed stress was
  shock-transition-only with +1.109521 net return.

Rank 2 optimized row:

- candidate: `427561d82c4ff4a65959d8283ff69e38331b3f1eeb6cd9c21f8ad6501575c423`;
- parameters:
  - `atr_percentile_threshold: 0.25`;
  - `shock_threshold: 0.7`;
  - `min_score: 0.25`;
  - `score_window_bars: 288`;
  - `top_n_per_window: 2`;
  - `cooldown_bars: 24`;
  - `max_side_share: 0.75`;
  - `side_balance_min_trades: 8`;
  - `flow_abs_threshold: 0.05`;
  - `flow_count_z_min: 0.5`;
  - `allowed_sides: long`;
  - `side_filter_stage: post_selection`.
- aggregate: 342 long trades, net return after cycle costs +14.714547,
  expectancy +0.009147, hit rate 0.538012, max drawdown -0.274609.
- split evidence: minimum split trade count 121; weakest split net return
  +0.128974 after cycle costs.
- cost stress: 11/11 scenarios passed; worst listed stress was
  shock-transition-only with +0.370998 net return.

Both rows improved the WPR106-81 aggregate lead, whose cycle net return was
+9.420343.

## Monte Carlo

The follow-up Monte Carlo used:

- taker commission: 0.0432% per side;
- round-trip commission: 0.0864%;
- funding ignored;
- slippage ignored for this offline analysis;
- 10,000 bootstrap paths.

Rank 1 optimized row:

- observed terminal return after user fee: +29.322120;
- MC 5th percentile terminal return: +7.143444;
- terminal-negative probability: 0.0000;
- observed max loss streak: 7;
- MC p95 max loss streak: 9.

Rank 2 optimized row:

- observed terminal return after user fee: +22.107677;
- MC 5th percentile terminal return: +4.704648;
- terminal-negative probability: 0.0001;
- observed max loss streak: 7;
- MC p95 max loss streak: 10.

Martingale x1.5 remains not applicable because the optimized rows are
fixed-hold exits, not sequence-proven 1:2 fixed TP/SL exits. WPR106-80 still
blocks current fixed TP/SL and Martingale evidence.

## Gate Outcome

Every optimized candidate remains rejected by the current gate. The top two
rows fail closed on the same non-PnL blockers as WPR106-81:

- explicit one-sided side-veto evidence is not yet represented by the gate;
- the aggTrade row requires feature-ablation comparator evidence;
- stability-region acceptance is required before candidate-pack use.

No candidate pack, paper/live artifact, order, sizing behavior, runtime-mode
change, or promotion claim was produced.

## Decision

The optimizer found a better research lead than WPR106-81. The next work should
resolve the fail-closed gate blockers rather than broadening the optimizer:

1. teach the candidate gate to accept explicit one-sided side-veto rows only
   when paired opposite-side controls and all other evidence pass;
2. add feature-ablation evidence for aggTrade-contrarian sparse rows;
3. add stability-region acceptance around the optimized parameter neighborhood;
4. only after those pass, revisit lower-timeframe sequence-proven exits.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-historical-research-cycle --spec configs/research/sparse_side_veto_optimizer_btcusdt_r106_v1.json
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

The contracts suite passed with 451 tests.
