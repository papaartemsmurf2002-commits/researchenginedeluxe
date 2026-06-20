# WPR106-176 Causal Side-Policy Switch Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search after WPR106-175 showed that
June 1-11 2026 favored both direct and inverse same-threshold
volatility-breakout controls. Test whether causal completed-bar regime rules
can switch between direct, inverse, and skip behavior using only pre-May data,
then benchmark fixed promising rows on May 2026 and the fresh June 1-11 2026
holdout.

This packet is not a defense of the WPR106-173 strict anti-signal rows. It
uses the WPR106-175 control result as a prompt to test a broader side-policy
switch family.

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
- transparent completed-bar score templates from WPR106-173;
- direct, inverse, and causal switch/skip rules based on volatility, flow, and
  trend state computed from completed bars only;
- fixed-hold and ATR-barrier exits;
- accepted-trade daily caps supporting active 1-5 trades/day behavior.

May and June must not be used for rule choice, row inclusion, ranking, or
selection. June can only be replayed after fixed pre-May rows are selected.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-176-causal-side-policy-switch-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_SIDE_POLICY_SWITCH_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_176_causal_side_policy_switch_search/**`

## Plan

1. Import WPR106-173 score, feature, exit, cost, overlap, and metric helpers.
2. Build WPR106-96 plus WPR106-168 June contexts as in WPR106-174/175.
3. Define causal side-policy rules that map each fixed-threshold signal to
   direct, inverse, or skip using only completed-bar volatility, flow, trend,
   and range state.
4. Evaluate the search grid on pre-May only, using WPR106-173 strict/loose
   monthly stability metrics.
5. Select fixed promising pre-May rows and replay those rows on May 2026 and
   June 1-11 2026.
6. Write metrics, monthly/daily/trade artifacts, selected descriptors, report,
   ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_176_causal_side_policy_switch_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Completed as an artifact-only causal side-policy switch search. The runner
evaluated 14,880 pre-May rows across BTCUSDT/ETHUSDT completed-bar score
templates, direct/inverse/switch/skip rules, side modes, sessions, fixed and
ATR-barrier exits, and 1/3/5 daily caps. All thresholds, rules, ranking, and
selection used only 2024-01-01 through 2026-04-30.

The search found 5,945 positive pre-May rows, 1,273 annual-target rows, 299
loose rows, and 10 strict rows. The fixed selected set contains 10 strict and
90 loose rows. All strict rows are ETHUSDT `vol_breakout_follow` variants with
`barrier_h32_tp2_sl1` exits; strict policy rules are `inverse_high_vol_skip`,
`inverse_all`, `inverse_high_vol_direct_else`, and
`inverse_flow_confirm_direct_contra_skip`.

May 2026 rejects the fixed selected set: 19 selected rows are May-positive, 58
are May-negative, 23 are flat/no-trade, median return is -0.002036, and active
mean return is -0.010022. The strict subset has zero May-positive rows, six
May-negative rows, and four May-flat rows. June 1-11 2026 is broadly positive
again with 81 selected rows positive, 19 negative, median +0.026792, and active
mean +0.025377.

Decision: reject the causal side-policy switch search as candidate-ready,
portfolio-ready, or promotion-ready evidence. Loose direct/flow/trend switch
rows are useful diagnostics because some are May-positive, but no strict row
confirms in May and flat high-volatility skip rows do not prove robustness.

Validation passed: scoped script compile, `src/tradingbotsuite` compile, and
contracts. Contracts reported 460 passed. No candidate pack, paper/live
artifact, order/sizing/runtime change, live config write, CUDA speedup claim,
or promotion claim exists.
