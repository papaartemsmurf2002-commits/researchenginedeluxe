# WPR106-211 Anti-Signal Regime Gate Repair

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Continue the 2024-forward broad strategy search by revisiting the rejected
WPR106-173 ETHUSDT volatility-breakout anti-signal family after WPR106-175
showed that May 2026 failed while June 1-11 2026 was not source-specific
confirmation.

This packet asks whether a causal, pre-May-only regime or trade-health gate can
repair the family before May 2026 is replayed. The target is month-to-month
stability, not one large profitable window.

## Data And Selection Policy

- Optimize, filter, rank, and select only on 2024-01-01 through 2026-04-30.
- Keep May 2026 fully out of gate construction, threshold selection, row
  scoring, behavior de-duplication, and selected-row inclusion.
- Replay May 2026 only after fixed rows are selected from pre-May evidence.
- Reuse WPR106-173 score, exit, overlap, daily-cap, ATR barrier, and cost
  accounting where possible.
- Include WPR106-175-style inverse/direct signal controls so any repair is not
  merely an anti-signal narrative fit.
- Permit active rates up to 1-5 trades per active day when overlap blocking,
  daily caps, costs, drawdown, and monthly stability are measured.
- All outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-211-anti-signal-regime-gate-repair.md`
- `docs/stage_reports/STAGE_R106_ANTI_SIGNAL_REGIME_GATE_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_211_anti_signal_regime_gate_repair/**`

No shared source package, checked strategy config, fixture catalog, live,
runtime, order-placement, sizing, candidate-pack, paper, or promotion path is
in scope unless this packet is amended before the edit.

## Planned Work

1. Create a packet-local artifact runner that imports the WPR106-173 runner and
   starts from the WPR106-175 fixed control descriptor set.
2. Add causal pre-May gates that can be evaluated from already accepted trade
   history or completed-bar state before each trade, such as prior-month
   health, rolling monthly health, drawdown throttle, volatility/flow state, and
   session/state constraints.
3. Replay pre-May rows with those gates, score only pre-May stability, and
   behavior-deduplicate exact accepted trade paths.
4. Freeze a selected set from pre-May evidence only, then replay May 2026 as a
   benchmark holdout.
5. Decide whether any gated anti-signal or direct-control variant remains a
   research-only promising lead, or whether the family stays rejected.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned. Compute acceleration is limited
to vectorized pandas/numpy artifact processing and reuse of existing WPR106-173
cached source logic.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_211_anti_signal_regime_gate_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Closeout Evidence

Completed as an artifact-only causal gate overlay around the rejected
WPR106-173/WPR106-175 ETHUSDT volatility-breakout anti-signal family. The
runner imported WPR106-173 score, exit, overlap, daily-cap, ATR barrier, and
cost accounting, then started from the 504 fixed WPR106-175 source-control
descriptors.

The pre-May-only grid evaluated 28,224 gated variants across seven completed-bar
state gates and eight causal health gates. May 2026 was not used for gate
construction, row scoring, behavior de-duplication, or selected-row inclusion.

Pre-May evidence was strong in-sample: 13,850 rows were positive, 6,660 passed
annual-target loss counts, 4,980 were loose, and 1,047 were strict. After
preselecting 320 rows and de-duplicating exact accepted pre-May trade paths,
the fixed selected set contained 97 strict-stable rows. Selected pre-May replay
had 97/97 positive rows, median return +1.277867, active mean +1.323948, best
+1.800202, and worst +0.941856.

May 2026 rejected the repair. The selected set had 0 positive rows, 66 negative
rows, and 31 flat rows; active May rows averaged -0.033615, median May return
was -0.012779, and worst May return was -0.106343. The selected set was still
entirely inverse-signal behavior; direct-signal controls produced pre-May
positive and annual-target rows but zero strict rows.

WPR106-211 therefore rejects the anti-signal regime gate repair as
candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready. The
useful evidence is falsification: causal completed-bar state gates and
prior-history health throttles can make this family look much stronger before
May, but they do not repair May 2026 transfer.

Final validation passed:

```powershell
python -m compileall -q data\research\wpr106_211_anti_signal_regime_gate_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed. No CUDA path was used and no speedup was
claimed. No candidate pack, paper/live artifact, order/sizing/runtime change,
live configuration write, or promotion claim exists.
