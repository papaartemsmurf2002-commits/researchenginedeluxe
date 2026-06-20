# WPR106-180 Volatility-Term Quiet-Trend Adaptive Exit Repair

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search by revisiting the discarded
WPR106-131 realized-volatility term-structure family. WPR106-131 found one
annual-loss-compliant ETHUSDT quiet-trend pullback diagnostic but rejected the
family because selected loose rows had insufficient strict coverage and failed
May 2026 as a group.

This packet tests whether a May-blind repair can raise active coverage and
monthly stability by focusing on the WPR106-131 quiet-trend pullback,
volatility-expansion follow, and compression-breakout neighborhoods, adding
causal adaptive exits and stricter pre-May stability scoring.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only windows:

- May 2026, replayed only after fixed pre-May selection.
- WPR106-168 June 1-11 2026 if the packet can replay the fixed rows without
  introducing May or June tuning.

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m bar context through May 2026 and 15m
  aggTrade-flow aggregation used by WPR106-131.
- WPR106-168 BTCUSDT/ETHUSDT June 1-11 2026 packet-local bars and aggTrade
  flow context if compatible with the replay helper.
- WPR106-131 implementation patterns and artifacts as source evidence, not as
  candidate claims.

Variant families:

- quiet-trend pullback;
- volatility-expansion follow;
- compression-breakout follow;
- selected controls from volatility-shock fade and term-structure reversal.

Repair dimensions:

- adaptive exits with score decay, volatility expansion stop, and fixed-hold
  fallbacks;
- target active rates at 1, 3, and 5 raw signals per day;
- daily accepted-trade caps at 1, 3, and 5;
- session, flow, and realized-volatility regime filters;
- annual loss caps and active-month/trade-rate constraints weighted before
  aggregate return.

May and June must not be used for feature definitions, threshold choices,
filter choices, exit choices, row inclusion, ranking, or selection.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-180-volterm-quiet-trend-adaptive-exit-repair.md`
- `docs/stage_reports/STAGE_R106_VOLTERM_QUIET_TREND_ADAPTIVE_EXIT_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_180_volterm_quiet_trend_adaptive_exit_repair/**`

## Plan

1. Reuse WPR106-131 source-context loading and completed-bar alignment.
2. Build a scoped grid around volatility-term quiet-trend, expansion, and
   compression variants with adaptive and fixed exits.
3. Evaluate all thresholds, filters, exits, and row selection using only the
   pre-May window.
4. Select fixed rows by monthly stability, annual loss caps, active 1-5
   trades/day behavior, cost stress, drawdown, and best-month concentration.
5. Replay selected fixed rows on May 2026, and June 1-11 2026 if compatible.
6. Write metrics, monthly/daily/trade artifacts, summary, report, ledger
   update, and validation notes.

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
python -m compileall -q data\research\wpr106_180_volterm_quiet_trend_adaptive_exit_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12. The runner evaluated 129,600 WPR106-131 volatility-term
repair rows across BTCUSDT/ETHUSDT, realized-volatility windows, quiet-trend,
vol-expansion, compression-breakout, shock-fade, and term-structure templates,
daily caps, and adaptive/fixed exits.

Pre-May results improved the diagnostic surface but did not produce a
candidate-ready lead: 18,762 rows were positive, 1,270 rows met annual losing
month caps, 391 rows were loose, and zero rows were strict. The annual-target
rows were usually too sparse; the only annual-target loose rows were ETHUSDT
quiet-trend pullback variants with 62 to 64 trades.

The fixed selected set contained 100 pre-May-positive rows with median
+0.601534 and active mean +0.599311. May 2026 rejected the fixed set with 12
positive rows, 88 negative rows, median -0.009113, active mean -0.014822, best
+0.077562, and worst -0.108927. Every `dropout_repair` selected row lost in
May.

Decision: WPR106-180 rejects the volatility-term adaptive-exit repair as
candidate-ready, portfolio-ready, or promotion-ready. All outputs remain
research-only, observe-only, and `promotion_ready: false`; no candidate pack,
paper/live artifact, order path, sizing change, runtime-mode change, live
configuration write, CUDA speedup claim, or promotion claim was produced.

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_180_volterm_quiet_trend_adaptive_exit_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contract result: 460 passed.
