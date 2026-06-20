# WPR106-209 Cross-Flow Exhaustion Transfer Repair

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Continue the 2024-forward broad strategy search by testing a new order-flow
interaction family instead of defending prior rejected leads. This packet
starts from two research-only diagnostics:

- WPR106-154 found a narrow BTCUSDT -> ETHUSDT synchronized-flow /
  cross-divergence long near-miss that met the annual loss target but missed
  active-month and May robustness requirements.
- WPR106-194 found ETHUSDT EU late-flow exhaustion fade variants that were
  May-positive but unstable pre-May.

The packet asks whether a pre-May-only interaction between cross-symbol
intrabar flow transfer, target-symbol late-flow exhaustion, and market-state
filters can improve month-to-month stability without tuning on May 2026.

## Data And Selection Policy

- Optimize, filter, rank, and select only on 2024-01-01 through 2026-04-30.
- Keep May 2026 fully out of feature thresholding, score construction,
  state/filter choice, row ranking, de-duplication, and selected-row inclusion.
- Replay May 2026 only after fixed promising rows are selected from pre-May
  evidence.
- Permit active rates up to 1-5 trades per active day when overlap blocking,
  daily caps, cost stress, drawdown, and monthly stability are explicitly
  measured.
- All outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-209-cross-flow-exhaustion-transfer-repair.md`
- `docs/stage_reports/STAGE_R106_CROSS_FLOW_EXHAUSTION_TRANSFER_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/**`

No source package, checked strategy config, fixture catalog, live, runtime,
order-placement, sizing, candidate-pack, paper, or promotion path is in scope
unless this packet is amended before the edit.

## Planned Work

1. Create a packet-local artifact runner that imports the WPR106-153 and
   WPR106-154 source helpers for WPR106-96 BTCUSDT/ETHUSDT bars and 1m
   aggTrade intrabar features.
2. Build new transfer/exhaustion interaction scores from completed 15m bars,
   including leader/target flow synchronization, target late-flow exhaustion,
   flow/price divergence, relative flow gaps, absorption proxies, and recent
   trend/volatility state.
3. Evaluate a bounded grid over BTCUSDT/ETHUSDT leader-target pairs,
   hold windows, sessions, side policies, daily caps, target entry rates,
   and pre-May-only state gates.
4. Score rows for annual loss caps, active-month coverage, cost-stress
   survival, drawdown, drop-best-month robustness, rolling six-month stability,
   and recent 2026 Jan-Apr coverage.
5. Behavior-de-duplicate selected rows by accepted pre-May trade path before
   May replay.
6. Benchmark May 2026 only for the fixed selected rows and document whether
   any lead survives as research-only evidence.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned. Compute acceleration is limited
to cached source contexts/features and vectorized pandas/numpy artifact
processing; any multiprocessing or CUDA claim must be truthful and recorded.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_209_cross_flow_exhaustion_transfer_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Closeout Evidence

The completed runner imported WPR106-153/WPR106-154 artifact helpers and kept
all new score, gate, ranking, and behavior de-duplication logic inside the
WPR106-209 artifact tree. It evaluated 93,312 pre-May rows across BTCUSDT /
ETHUSDT leader-target pairs, 96/384-bar normalization windows, 8/16/32-bar
holds, all/EU/US sessions, six templates, six state gates, 1/2/3/5 target
signals per day, 1/3/5 daily caps, and two throttle modes.

The pre-May screen found 3,197 positive rows, 324 loose rows, zero
annual-target rows, and zero strict rows. It preselected 118 rows, replayed
them with accepted trade output, and behavior-deduplicated them to 25 fixed
selected rows before any May benchmark. Selected pre-May replay had 25
positive rows, median return +0.319612, best +0.672164, and worst +0.127749.

May 2026 rejected the fixed set as a candidate lead: 9 positive rows, 12
negative rows, 4 flat rows, median May return 0.000000, best +0.062942, and
worst -0.088245. The best pre-May and best May row was BTCUSDT-led ETHUSDT
`relative_gap_absorption_reversion`, but it had only 21 active pre-May months
and 2024/2025/2026 Jan-April losing-month counts of 4/3/0, so it fails the
requested annual stability target.

WPR106-209 rejects the cross-flow exhaustion transfer repair as
candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready. Useful
diagnostic evidence remains in BTCUSDT-led ETHUSDT relative-flow absorption
reversion and leader-late transfer, but both still require a genuinely new
pre-May-only stability mechanism.

Final validation passed:

```powershell
python -m compileall -q data\research\wpr106_209_cross_flow_exhaustion_transfer_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed. No CUDA path was used and no speedup was
claimed.
