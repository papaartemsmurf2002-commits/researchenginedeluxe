# WPR106-179 Causal Accepted-Trade Throttle Overlay

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search after WPR106-178 showed that a
monthly stability selector improved June but still failed May. Test whether
causal accepted-trade throttle overlays can reduce pre-May adverse months and
transfer to May/June without using May or June for rule selection.

This packet does not create new entry signals. It conservatively overlays
pre-May-selected WPR106-178 accepted trade ledgers, so skipped trades do not
open later skipped raw signals.

## Scope

Selection/tuning source:

- WPR106-178 selected pre-May accepted trade ledger and descriptors.
- Overlay parameter choice uses only 2024-01-01 through 2026-04-30 accepted
  trade chronology.

Benchmark-only windows:

- WPR106-178 selected May 2026 accepted trade ledger.
- WPR106-178 selected June 1-11 2026 accepted trade ledger.

Overlay families:

- score tightening by pre-May score quantile;
- side filtering from pre-May side evidence;
- causal cooldown after accepted losing trades;
- causal daily loss-stop and monthly loss-stop overlays;
- combined score plus loss-stop overlays.

May and June must not be used for overlay choice, row inclusion, ranking, or
selection.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-179-causal-accepted-trade-throttle-overlay.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_ACCEPTED_TRADE_THROTTLE_OVERLAY_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_179_causal_accepted_trade_throttle_overlay/**`

## Plan

1. Load WPR106-178 selected descriptors and pre-May/May/June accepted trade
   ledgers.
2. Build causal overlay variants from pre-May trade history only.
3. Evaluate overlays on pre-May, selecting fixed overlays by monthly stability,
   active trade rate, cost stress, drawdown, and annual loss caps.
4. Replay fixed overlays on May 2026 and June 1-11 2026 trade ledgers.
5. Write overlay descriptors, metrics, monthly/daily/trade artifacts, and
   comparison tables.
6. Decide whether any overlay becomes candidate-ready or remains diagnostic.
7. Write report, ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_179_causal_accepted_trade_throttle_overlay\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12. The runner evaluated 28,800 causal accepted-trade
overlay descriptors over the WPR106-178 selected accepted trade ledgers. The
overlay search found 25,178 positive pre-May overlays, 1,863 annual-target
overlays, 4,798 loose overlays, and 231 strict overlays, then selected 100
fixed overlays using only 2024-01-01 through 2026-04-30 evidence.

The selected overlays were very clean in pre-May replay: 100 positive rows, 0
negative rows, median +1.106529, and active mean +1.121298. May 2026 rejected
the fixed selected set with 7 positive rows, 46 negative rows, 47 flat/no-trade
rows, median 0.000000, and active mean -0.025601. June 1-11 2026 improved to
72 positive rows, 24 negative rows, 4 flat/no-trade rows, median +0.024723, and
active mean +0.015573, but that does not rescue the failed May benchmark.

Decision: WPR106-179 rejects the throttle overlay as candidate-ready,
portfolio-ready, or promotion-ready. All outputs remain research-only,
observe-only, and `promotion_ready: false`; no candidate pack, paper/live
artifact, order path, sizing change, runtime-mode change, live configuration
write, CUDA speedup claim, or promotion claim was produced.

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_179_causal_accepted_trade_throttle_overlay\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contract result: 460 passed.
