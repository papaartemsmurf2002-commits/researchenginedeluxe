# WPR106-171 Market-State Regime-Gated Intrabar Flow Repair

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search after WPR106-170 rejected the
path-quality KNN event-veto formulation. Test whether independent completed-bar
market-state gates can repair pre-May stability for prior intrabar order-flow
leads without using May 2026 for tuning.

This packet intentionally shifts away from defending the rejected BTC sparse
side-veto path. It revisits a prior loose but discarded family, adds a novel
exogenous regime-gate layer, allows active accepted rates up to five trades per
day, and ranks for month-to-month stability rather than one concentrated
profitable window.

## Scope

Default tuning/search window:

- 2024-01-01 00:00:00 UTC through 2026-04-30 23:59:59 UTC.

Benchmark holdout:

- 2026-05-01 through 2026-05-31 UTC.

May 2026 must not be used for feature choice, market-state threshold choice,
gate choice, daily-cap choice, ranking, filtering, or selection. It may only be
replayed after fixed pre-May rows are selected.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-171-market-state-regime-gated-intrabar-flow-repair.md`
- `docs/stage_reports/STAGE_R106_MARKET_STATE_REGIME_GATED_INTRABAR_FLOW_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_171_market_state_regime_gated_intrabar_flow_repair/**`

## Plan

1. Load WPR106-153 selected intrabar order-flow trade ledgers and WPR106-96
   verified BTCUSDT/ETHUSDT completed-bar source context.
2. Build causal completed-bar market-state features for each symbol and
   cross-symbol context using pre-May quantiles only.
3. Apply fixed regime gates to pre-May trade ledgers, preserving existing
   trade costs and one-position overlap behavior from the source replay.
4. Evaluate daily accepted-trade caps of 1, 3, and 5 where the filtered source
   allows more than one accepted trade per day.
5. Rank only on pre-May monthly stability, annual losing-month profile,
   drawdown, cost stress, trade count, overlap, and concentration.
6. Replay only fixed promising/loose pre-May rows on May 2026 as a benchmark.
7. Write research-only artifacts, report, ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_171_market_state_regime_gated_intrabar_flow_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Completed as an artifact-only research packet. The runner evaluated 6,600
pre-May rows by applying 22 fixed completed-bar market-state gates and 1/3/5
accepted-trade daily caps to 100 WPR106-153 selected intrabar order-flow source
rows. All state thresholds, gates, caps, ranking, and selection used only
2024-01-01 through 2026-04-30. May 2026 was benchmark-only after fixed pre-May
selection.

The grid found 5,115 positive pre-May rows, 219 annual-target rows, 1,615 loose
rows, and zero strict rows. The selected set contains 100 loose rows with
median +0.781872 pre-May net return and no negative pre-May selected rows, but
selection is duplicate-heavy because source caps and new daily caps often leave
the same already overlap-filtered trade set unchanged.

May 2026 rejected the selected set as candidate-ready evidence: 46 rows were
May-positive, 51 May-negative, 3 May-flat, with best +0.069661, worst
-0.057689, and median -0.001737. The best diagnostic pocket is ETHUSDT
late-delta-flip fade under `shock_q80` or `volume_high_q70` gates, but May
support is small and duplicate-heavy. No candidate pack, paper/live artifact,
order/sizing/runtime change, live config write, CUDA speedup claim, or
promotion claim exists.

Validation passed: scoped script compile, `src/tradingbotsuite` compile, and
contracts. Contracts reported 460 passed.
