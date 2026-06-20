# WPR106-194 Intrabar Flow Burst Profile Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-13

## Objective

Continue the 2024-forward broad search after WPR106-193 rejected path-managed
exits over WPR106-192 motif entries. This packet tests a fresh order-flow style
source family using 1m aggTrade-flow profiles inside completed 15m bars.

The family is meant to give order-flow style logic a fair but bounded test:
late-flow bursts, flow acceleration, absorption, exhaustion, and
follow-through are evaluated as direct entries with normal active rates allowed
when costs, overlap, and monthly stability are handled.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May row selection.

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m OHLCV and 1m aggTrade-flow proxy context.
- WPR106-170 helper cost model, labels, period masks, and metric accounting.

Search family:

- completed 15m bar profiles built from the fifteen prior 1m aggTrade buckets;
- late-flow imbalance, first-vs-last flow acceleration, volume concentration,
  quote-volume burst, wick/close-location, trend, volatility, and cross-symbol
  residual states;
- direct follow/fade templates with long, short, and both-sided variants;
- session filters, active daily caps, and fixed holding windows;
- same-symbol overlap blocking and WPR106 embedded costs;
- pre-May-only ranking by monthly stability, annual losing-month limits,
  drawdown, downside risk, best-month concentration, cost-stress survival, and
  recent activity;
- May replay of fixed selected rows only.

May must not be used for feature choice, threshold choice, side choice, session
choice, hold choice, cap choice, row ranking, or tie-breaking. May is
benchmark-only after fixed pre-May selection.

## Allowed Paths

- `docs/work_packets/WPR106-194-intrabar-flow-burst-profile-search.md`
- `docs/stage_reports/STAGE_R106_INTRABAR_FLOW_BURST_PROFILE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_194_intrabar_flow_burst_profile_search/**`

## Plan

1. Load WPR106-96 15m bar and 1m aggTrade-flow source context.
2. Build completed 15m intrabar flow profile features from prior 1m buckets.
3. Generate flow-follow, flow-fade, absorption, exhaustion, and continuation
   scores.
4. Calibrate thresholds on pre-May only for target active rates.
5. Evaluate fixed-hold entries with same-symbol overlap and embedded costs.
6. Select fixed rows from pre-May diagnostics only.
7. Replay selected rows on May 2026.
8. Write ranking, monthly/daily/trade artifacts, summary, report, ledger
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

Passed:

```powershell
python -m compileall -q data\research\wpr106_194_intrabar_flow_burst_profile_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.

## Exit Evidence

WPR106-194 evaluated 4,320 intrabar 1m aggTrade-flow profile rows over BTCUSDT
and ETHUSDT. All thresholds and selection used 2024-01-01 through
2026-04-30; May 2026 was benchmark-only after fixed pre-May selection.

The pre-May screen found 280 positive rows, zero annual-target rows, zero
loose rows, and zero strict rows. The fixed selected set contained 100
fallback `positive_recent_stability` rows: 89 ETHUSDT and 11 BTCUSDT.
Selected pre-May replay was 100 positive rows, zero negative rows, median
+0.184677, active mean +0.233582, best +0.821519, and worst +0.050271.

May rejected the selected set: all 100 selected rows were active, but only 22
were positive and 78 were negative, with median -0.010404, active mean
-0.008656, best +0.078131, and worst -0.049117. The best May row was ETHUSDT
`late_flow_exhaustion_fade`, EU session, 32-bar hold, both-sided, daily cap 1;
it returned +0.249145 pre-May and +0.078131 in May, but had 14 pre-May losing
months, seven losing months in 2024, five in 2025, two in 2026 Jan-Apr, and
max drawdown -0.465964.

WPR106-194 therefore rejects the intrabar flow burst profile family as
candidate-ready, portfolio-ready, or promotion-ready. It preserves ETHUSDT
EU-session `late_flow_exhaustion_fade` as a research-only diagnostic pocket,
but the family does not meet the requested month-to-month stability standard.
