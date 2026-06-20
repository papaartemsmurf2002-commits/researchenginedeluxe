# WPR106-191 Directional KNN Accepted-Trade Stability Repair

Status: closed
Owner: Codex Research Agent
Date: 2026-06-13

## Objective

Continue the broad 2024-forward search after WPR106-190 rejected directional
KNN confidence entries as candidate-ready, while preserving the useful
diagnostic that ETHUSDT short directional-KNN rows were mostly positive when
active in May. This packet tests whether May-blind accepted-trade overlays can
repair WPR106-190's weak pre-May month stability without creating new entries.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May overlay selection.

Inputs:

- WPR106-190 selected pre-May trade ledgers, May benchmark trade ledgers, and
  selected source metrics.

Overlay family:

- accepted-trade-only filters over fixed WPR106-190 source rows;
- pre-May calibrated KNN confidence and good-spread quantile filters;
- entry-hour/session filters;
- additional accepted-trade daily caps;
- causal prior-month health gates using only previously completed pre-May
  accepted-trade history;
- pre-May-only overlay ranking by monthly stability, annual losing-month
  limits, active trade behavior, cost-stress survival, drawdown, and
  concentration;
- May replay of the fixed selected overlays only.

May must not be used for overlay thresholds, health gate settings, source
inclusion, row ranking, cap choice, or tie-breaking. May is benchmark-only
after fixed pre-May selection.

## Allowed Paths

- `docs/work_packets/WPR106-191-directional-knn-accepted-trade-stability-repair.md`
- `docs/stage_reports/STAGE_R106_DIRECTIONAL_KNN_ACCEPTED_TRADE_STABILITY_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_191_directional_knn_accepted_trade_stability_repair/**`

## Plan

1. Load WPR106-190 selected pre-May and May accepted-trade ledgers.
2. Build source-level pre-May calibration tables for absolute KNN confidence,
   absolute good-rate spread, entry-hour/session, and monthly accepted-trade
   history.
3. Generate May-blind overlay candidates across confidence quantiles,
   good-spread quantiles, session filters, daily caps, and causal monthly
   health gates.
4. Evaluate overlays on pre-May with no new entries, preserving source costs
   and accepted-trade overlap assumptions.
5. Select fixed overlays from pre-May diagnostics only.
6. Replay the fixed selected overlays on May 2026.
7. Write ranking, selected pre-May, May benchmark, monthly/daily/trade
   artifacts, summary, report, ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_191_directional_knn_accepted_trade_stability_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.

## Exit Evidence

WPR106-191 evaluated 19,200 accepted-trade-only overlays over the fixed
WPR106-190 selected source rows. All overlay thresholds, session filters,
daily caps, causal monthly gates, ranking, and selected-row inclusion used
only 2024-01-01 through 2026-04-30 UTC. May 2026 remained benchmark-only after
the fixed pre-May selection.

The run found 9,110 positive pre-May rows, 4,320 annual-target rows, 156 loose
rows, and zero strict rows. The fixed selected set contained 100 ETHUSDT rows:
70 loose rows and 30 positive-stability fallback rows. Selected pre-May replay
was 100 positive rows, zero negative rows, median +0.343498, active mean
+0.365477, best +0.770810, and worst +0.124099.

May rejected the repair by inactivity rather than losses: all 100 selected
overlays were flat/no-trade in May, with zero active rows and zero total
return. The best ranked selected overlay was active in all four latest pre-May
months with 40 latest-four-month trades, but still had no May trades after the
fixed overlay was applied.

WPR106-191 is therefore a negative diagnostic. Accepted-trade overlays improved
pre-May stability but destroyed the useful WPR106-190 May activity, so this
does not produce candidate-ready, portfolio-ready, or promotion-ready evidence.
All outputs remain research-only, observe-only, and promotion-ready false.
