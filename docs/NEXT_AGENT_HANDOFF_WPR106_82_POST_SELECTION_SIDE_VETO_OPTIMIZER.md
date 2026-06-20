# WPR106-82 Next Agent Handoff - Side-Veto Gate Evidence Closure

Date: 2026-06-10

## State

WPR106-80 rejected the archive-backed KNN rows, conservative fixed TP/SL rows,
and x1.5 Martingale overlays under the user fee model. Taker commission was
0.0432% per side and funding was ignored. The useful finding was narrower: BTC
sparse rows had a long-only side decomposition worth testing as a true
strategy contract.

WPR106-81 added explicit `allowed_sides` and `side_filter_stage` controls to
`sparse_event_filter_v1`. Pre-selection one-sided rows failed, but
post-selection long-only rows survived the first real validation pass. The
aggTrade-contrarian post-selection long row ranked first with 346 long trades,
+9.420343 net return after cycle costs, split trade-count minimum 116, and
11/11 cost-stress scenarios passed.

WPR106-82 ran the bounded optimizer follow-up. A 194-candidate attempt was
stopped after roughly 89 CPU minutes without aggregate artifacts, then a
50-candidate random sample completed with 54 candidate rows, 54 aggregate
backtests, 8 split backtests, and 22 cost-stress backtests.

## Current Lead

The current research lead is the optimized BTCUSDT aggTrade-contrarian
post-selection long-only sparse row:

`941c7d1a1a3b8669c66e816ee465dc30cf18b1fba56c54b95555a027cdf046d6`

Key parameters:

- `atr_percentile_threshold: 0.65`
- `shock_threshold: 1.3`
- `min_score: 0.5`
- `score_window_bars: 288`
- `top_n_per_window: 2`
- `cooldown_bars: 48`
- `max_side_share: 0.65`
- `side_balance_min_trades: 8`
- `flow_abs_threshold: 0.1`
- `flow_count_z_min: 0.5`
- `allowed_sides: long`
- `side_filter_stage: post_selection`

Observed evidence:

- 319 long trades.
- +20.174216 net return after cycle costs.
- +0.010652 expectancy.
- 0.551724 hit rate.
- -0.321446 max drawdown.
- Weakest split net return +0.039327.
- 11/11 cost-stress scenarios passed.
- Monte Carlo under 0.0432% taker fee per side and funding ignored: observed
  terminal return +29.322120, 5th percentile terminal return +7.143444, and
  0/10000 negative terminal paths.
- Observed max loss streak 7; Monte Carlo p95 max loss streak 9.

This is a research lead only. It is not candidate-ready.

## Active Blockers

`ISSUE-R106-024` remains open. The current candidate gate cannot yet represent
explicit one-sided side-veto evidence without treating it like missing
long/short side evidence.

The optimized row also still needs:

- a gate rule that distinguishes explicit one-sided contracts from missing
  side evidence;
- paired opposite-side controls;
- no-trade and transparent baselines;
- feature-ablation evidence for aggTrade flow value versus price-only sparse
  comparators;
- stability-region acceptance around the optimized parameter neighborhood;
- research-only provenance in every artifact that could feed eligibility.

Fixed TP/SL and Martingale remain blocked. Do not use x1.5 Martingale unless a
later packet proves a sequence-aware 1:2 fixed TP/SL exit with acceptable
loss-streak, drawdown, and ruin-risk evidence after costs. WPR106-82 is still a
fixed-hold result.

## Broad Next Task

Open WPR106-83 as a research-only gate and evidence closure packet. The
objective is to make explicit one-sided side-veto strategies evaluable by the
candidate gate without weakening safety gates:

- Do not require both long and short trades inside the same candidate when the
  strategy contract explicitly sets `allowed_sides` and the opposite side is
  intentionally vetoed.
- Require stronger external evidence instead: paired opposite-side controls,
  transparent/no-trade baselines, feature ablation, split survival, cost-stress
  survival, stability-region evidence, and research-only provenance.
- Keep the gate fail-closed if any one of those conditions is absent.

The first target should be the WPR106-82 optimized lead above. If the lead
fails ablation or stability, document the rejection and stop. Only if every
gate passes should the next agent evaluate whether a candidate-pack attempt is
allowed by existing contracts. Do not create a candidate pack merely because
the PnL, split, cost-stress, and Monte Carlo numbers look good.

## Suggested Starting Points

- `docs/stage_reports/STAGE_R106_POST_SELECTION_SIDE_VETO_OPTIMIZER_REPORT.md`
- `docs/stage_reports/STAGE_R106_SPARSE_SIDE_VETO_VALIDATION_REPORT.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/sparse_side_veto_optimizer_btcusdt_r106_v1.json`
- `configs/research/sparse_side_veto_btcusdt_r106_v1.json`
- `data/research/historical_cycles/sparse_side_veto_optimizer_btcusdt_r106_v1/`
- `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/`
- `data/research/monte_carlo_exit_sizing/wpr106_82/`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_artifacts/`
- `tests/contracts/test_strategy_contracts.py`
- `tests/research_artifacts/`
- `tests/historical/`

## Boundary

All current outputs remain research-only and observe-only. The intended
metadata stance is:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `candidate_pack_written: false`
- `paper_artifact_written: false`
- `live_artifact_written: false`
- `order_placement_used: false`
- `position_sizing_used: false`
- `runtime_mode_changed: false`

Do not place orders, change runtime mode, write live configuration, introduce
live adapter imports into research modules, claim promotion readiness, or treat
this handoff as trading advice.

## Next Goal Prompt

```text
/goal WPR106-83: Continue after WPR106-82. Use AGENTS.md, docs/ORCHESTRATOR_STAGE_LEDGER.md, docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md, docs/stage_reports/STAGE_R106_POST_SELECTION_SIDE_VETO_OPTIMIZER_REPORT.md, and docs/KNOWN_ISSUES.md ISSUE-R106-024. The optimized BTCUSDT aggTrade-contrarian sparse post-selection long-only candidate 941c7d1a1a3b8669c66e816ee465dc30cf18b1fba56c54b95555a027cdf046d6 is the current research lead, but it is not candidate-ready. Formulate and implement a research-only gate/evidence closure packet that lets explicit one-sided side-veto strategies be evaluated without weakening safety gates: require paired opposite-side controls, no-trade/transparent baselines, feature ablation, split/cost/stability evidence, and research-only provenance, but do not require both long and short trades inside a candidate whose contract explicitly vetoes one side. Add feature-ablation evidence for the aggTrade sparse lead, add stability-region acceptance around the optimized parameter neighborhood, rerun eligibility/gate checks, and stop fail-closed unless every gate passes. Keep all outputs research_only, observe_only, promotion_ready false; do not create paper/live artifacts, place orders, change sizing/runtime/live config, or claim promotion readiness.
```
