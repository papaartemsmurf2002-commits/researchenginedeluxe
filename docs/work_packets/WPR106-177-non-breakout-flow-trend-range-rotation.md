# WPR106-177 Non-Breakout Flow/Trend/Range Rotation Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search after WPR106-175 and WPR106-176
rejected the repeated ETHUSDT volatility-breakout cluster. Move away from that
cluster and test non-breakout completed-bar families with causal side-policy
rules, active trade rates, overlap handling, and May/June fixed benchmarks.

This packet is not allowed to select `vol_breakout_follow` rows. It should
revisit discarded flow, trend, range, wick, compression, and cross-symbol ideas
with new score variants and policy rules.

## Scope

Selection/tuning source:

- 2024-01-01 00:00:00 UTC through 2026-04-30 23:59:59 UTC.

Benchmark-only windows:

- May 2026 from WPR106-96 context.
- June 1-11 2026 from WPR106-168 packet-local verified Binance Vision daily
  archives, with WPR106-96 context through May used only as rolling-feature
  warmup.

Search surface:

- BTCUSDT and ETHUSDT completed 15m bars plus 1m aggTrade flow context;
- non-breakout score variants only;
- direct, inverse, flow/trend switch, and regime skip rules based on
  completed-bar state;
- fixed-hold and ATR-barrier exits;
- accepted-trade daily caps supporting active 1-5 trades/day behavior.

May and June must not be used for score definition, threshold choice, rule
choice, row inclusion, ranking, or selection. June can only be replayed after
fixed pre-May rows are selected.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-177-non-breakout-flow-trend-range-rotation.md`
- `docs/stage_reports/STAGE_R106_NON_BREAKOUT_FLOW_TREND_RANGE_ROTATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_177_non_breakout_flow_trend_range_rotation/**`

## Plan

1. Import WPR106-173 helper code for context loading, completed-bar features,
   exits, costs, overlap handling, daily caps, and metrics.
2. Build May-warmup plus June contexts as in WPR106-174 through WPR106-176.
3. Define non-breakout score variants for flow absorption, trend pullback,
   range z-score reversion, wick absorption, compression release, and
   cross-symbol relative reversion.
4. Evaluate the search grid on pre-May only, selecting fixed strict/loose rows
   with the existing monthly stability criteria.
5. Replay fixed selected rows on May 2026 and June 1-11 2026.
6. Write ranking, selected descriptor, metrics, monthly/daily/trade, and
   benchmark comparison artifacts.
7. Write the report, ledger update, and validation notes.

## Research Boundary

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_177_non_breakout_flow_trend_range_rotation\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Completed as an artifact-only non-breakout screen. The runner evaluated 60,480
pre-May rows across BTCUSDT/ETHUSDT non-breakout completed-bar score variants,
causal direct/inverse/switch/skip policy rules, side modes, fixed and ATR exits,
and 1/3/5 daily caps. `vol_breakout_follow` was excluded.

The search found 10,930 positive pre-May rows, 287 annual-target rows, 235
loose rows, and zero strict rows. The fixed selected set contains 100 loose rows
and no strict rows. The best selected pre-May row was ETHUSDT
`flow_absorption_fade` with `inverse_high_vol_skip`, `fixed_64`, and daily cap
1, recording 221 trades, +1.496901 pre-May return, seven losing months, and
full cost-stress survival.

May and June reject the selected set. May has 14 positive rows, 33 negative
rows, 53 flat/no-trade rows, median 0.000000, and active mean -0.016519. June
1-11 has 32 positive rows, 48 negative rows, 20 flat/no-trade rows, median
0.000000, and active mean -0.006525.

Decision: reject the non-breakout flow/trend/range rotation search as
candidate-ready, portfolio-ready, or promotion-ready evidence. Useful
diagnostics are BTCUSDT `wick_absorption_reversal` under high-volatility
inverse policy and ETHUSDT `flow_burst_nonbreakout_follow` short with trend
switch, but both remain loose-only and do not support a candidate claim.

Validation passed: scoped script compile, `src/tradingbotsuite` compile, and
contracts. Contracts reported 460 passed. No candidate pack, paper/live
artifact, order/sizing/runtime change, live config write, CUDA speedup claim,
or promotion claim exists.
