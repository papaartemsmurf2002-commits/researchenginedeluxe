# WPR106-202 Motif Risk-Throttle Stability Repair

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Test whether the WPR106-192 causal state/motif lookup family can be repaired
with accepted-trade risk and activity throttles instead of exit changes.
WPR106-192 found active May transfer, especially ETHUSDT
`trend_pullback_clock`, but excessive pre-May losing months and drawdown.
WPR106-193 showed simple stop/target path exits do not repair that pocket.

This packet keeps the WPR106-192 source entries fixed and tests causal
pre-May-only accepted-trade overlays that may drop trades based on prior
monthly/daily/source health, side, symbol, motif, and trade density.

## Data And Selection Policy

- Source rows are WPR106-192 selected motif rows, which were selected without
  May 2026.
- Overlay construction, ranking, source inclusion, and selection use only
  2024-01-01 through 2026-04-30 UTC.
- May 2026 is benchmark-only after the fixed selected overlay set exists.
- Overlays may allow active behavior in the 1 to 5 trades/day range when
  costs, overlap, and monthly stability remain explicit.
- All outputs are `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-202-motif-risk-throttle-stability-repair.md`
- `docs/stage_reports/STAGE_R106_MOTIF_RISK_THROTTLE_STABILITY_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_202_motif_risk_throttle_stability_repair/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that reads WPR106-192 selected pre-May and May
   trade artifacts plus selected source metrics.
2. Generate deterministic accepted-trade overlay variants over each fixed
   WPR106-192 source row using only pre-May trade history for selection.
3. Test causal throttles such as prior-month health, rolling monthly loss
   count, rolling daily loss pause, side-only controls, one-to-five daily
   trade caps, and recent active-month requirements.
4. Rank overlays on pre-May monthly stability, active months, loss-month caps,
   drawdown, cost-stress survival, best-month concentration, trade count, and
   total return.
5. Replay the fixed selected overlay set on pre-May and May 2026, then write
   metrics, monthly/daily/trade artifacts, comparison tables, controls, and a
   summary manifest.
6. Document whether motif risk throttles repair the active May clue or whether
   the motif family remains unstable after realistic accepted-trade controls.
7. Update the stage report and ledger, then run validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; if the runner is CPU/vectorized
only, the manifest must say so truthfully.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_202_motif_risk_throttle_stability_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Exit Evidence

WPR106-202 completed the fixed-source accepted-trade risk/throttle repair over
WPR106-192 selected motif rows. It evaluated 17,766 overlay rows using only
2024-01-01 through 2026-04-30 for ranking and selection, then used May 2026
only as a benchmark for the fixed selected overlay set.

The pre-May overlay screen found 10,089 positive rows, 4,812 annual-target
rows, 32 loose rows, and zero strict rows. No positive row reached at least 20
active months with five or fewer losing months, and no positive annual-target
row reached at least 20 active months.

The fixed selected set contains 100 ETHUSDT `trend_pullback_clock`
`positive_recent_throttle` rows. Selected pre-May replay is 100/100 positive,
with median return +0.766617, median active months 28, median losing months
10, median inactive months 0, zero strict rows, and zero annual-target rows.
May benchmark improves versus WPR106-192 with 100 active rows, 98 positive,
two negative, median May +0.027644, active mean +0.018009, best +0.039212,
and worst -0.008458.

The best stability and May row, `motif202-00860ffdbf2eb058`, records
+0.720677 pre-May over 103 trades, 23 active months, seven losing months,
max drawdown -0.067553, 100% cost-stress survival, and +0.039212 in May over
five trades. It remains diagnostic-only because it misses the requested
annual loss-month stability profile.

WPR106-202 rejects motif risk throttles as candidate-ready, portfolio-ready,
or promotion-ready. The accepted-trade overlays improve May transfer and some
drawdowns, but the family still cannot produce the requested month-to-month
stability over 2024-forward pre-May evidence. No candidate pack, paper/live
artifact, order/sizing/runtime change, live config write, CUDA speedup claim,
or promotion claim exists.

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_202_motif_risk_throttle_stability_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
