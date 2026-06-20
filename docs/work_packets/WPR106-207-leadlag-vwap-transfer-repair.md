# WPR106-207 Lead-Lag VWAP Transfer Repair

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Follow up WPR106-206 by testing whether the only noncanonical families with
useful May-transfer hints, WPR106-133 cross-symbol lead-lag and WPR106-128
anchored VWAP, can be repaired into a more stable 2024-forward research lead.

This packet is a pre-May-only transfer repair and portfolio/composition audit,
not a promotion attempt. It reuses the completed source-family trade artifacts
from WPR106-128 and WPR106-133, ranks and composes only on 2024-01-01 through
2026-04-30 evidence, then benchmarks fixed promising rows and portfolios on
May 2026.

## Data And Selection Policy

- Source candidates come from WPR106-128 and WPR106-133 ranking, selected
  metric, monthly, daily, and accepted-trade artifacts.
- Optimization, ranking, behavior deduplication, portfolio construction, and
  repair thresholds use only pre-May evidence ending before 2026-05-01 UTC.
- May 2026 is benchmark-only after the fixed pre-May rows/portfolios are
  selected.
- Active rows around 1 to 5 trades per active day remain allowed when costs,
  overlap, drawdown, loss-month counts, and source concentration are explicit.
- All outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-207-leadlag-vwap-transfer-repair.md`
- `docs/stage_reports/STAGE_R106_LEADLAG_VWAP_TRANSFER_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope unless this packet is explicitly amended before the
edit.

## Planned Work

1. Create a packet-local runner that loads WPR106-128 and WPR106-133 source
   artifacts and normalizes row identities, monthly/daily returns, and accepted
   trade schemas.
2. Build pre-May-only repair diagnostics for each row: annual losing-month
   counts, drawdown, best-month concentration, trade density, active coverage,
   cost-stress survival, daily downside, and selected source-family exposure.
3. Behavior-deduplicate rows by accepted trade timing/side/return signature.
4. Test pre-May-only row filters and small portfolios that combine lead-lag and
   VWAP rows with overlap-aware daily return aggregation and capped component
   exposure.
5. Select a fixed promising pre-May repair set, then benchmark only that fixed
   set on May 2026.
6. Record whether the repair reduces pre-May losing months without creating a
   May contradiction, and explicitly reject any weak rows/portfolios.
7. Document artifacts, interpretation, and validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; any compute acceleration is
limited to pandas/numpy vectorized artifact processing and must be reported
truthfully.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_207_leadlag_vwap_transfer_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Closeout Evidence

The completed runner loaded 52 WPR106-128 anchored-VWAP selected rows with
12,263 pre-May accepted trades and 59 WPR106-133 lead-lag selected rows with
17,305 pre-May accepted trades. It recomputed row metrics from trade-level
gross return and round-trip cost, behavior-deduped 111 source rows to 92 rows,
and selected only from 2024-01-01 through 2026-04-30 evidence before loading
May.

No individual component met the strict or annual target. The repair generated
35,420 small portfolios from the top 22 deduped components; 535 were strict
pre-May portfolios and 670 met the annual target. The fixed selected portfolio
set contains 60 strict annual-target portfolios, with median pre-May return
+1.064106 and median losing months 3.5.

May rejects the fixed portfolio set: 0 positive, 60 negative, 0 flat, median
May return -0.022084, best May return -0.020186, and worst May return
-0.023982. The component benchmark is mixed, with 15 positive components and
20 negative components; the best component May row is the already-known
WPR106-133 `leadlag-18708dffa1413dce` row, which had seven pre-May losing
months and failed the annual target before May was inspected.

WPR106-207 therefore rejects lead-lag / anchored-VWAP transfer repair as
candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready. The
packet shows that pre-May-only composition can reduce losing-month counts for
these rows, but the improvement does not transfer to May.

Final close validation passed:

```powershell
python -m compileall -q data\research\wpr106_207_leadlag_vwap_transfer_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
