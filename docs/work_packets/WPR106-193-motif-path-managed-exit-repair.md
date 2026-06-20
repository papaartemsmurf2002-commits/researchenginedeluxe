# WPR106-193 Motif Path-Managed Exit Repair

Status: closed
Owner: Codex Research Agent
Date: 2026-06-13

## Objective

Continue the 2024-forward broad search after WPR106-192 found active May
transfer in causal state/motif entries but rejected the family for excessive
pre-May losing months and drawdown. This packet tests whether conservative
path-managed exits can repair WPR106-192 motif entries without changing their
May-blind source selection.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May exit-policy selection.

Inputs:

- WPR106-192 selected motif source rows and WPR106-192 runner logic.
- WPR106-96 BTCUSDT/ETHUSDT 15m and aggTrade-flow context loaded through the
  same helper path.
- Embedded WPR106 research cost model.

Search family:

- fixed WPR106-192 selected motif entry definitions;
- conservative primary-bar path exits using completed OHLC within the holding
  window;
- stop-loss and take-profit barrier variants;
- stop-first sequencing when stop and target are both touched inside the same
  15m bar;
- optional shorter maximum hold fractions;
- same-symbol overlap blocking using the actual earlier exit index;
- pre-May-only ranking by annual losing-month limits, drawdown, cost-stress,
  active-rate behavior, recent activity, and best-month concentration;
- May replay of fixed selected exit-policy rows only.

May must not be used for source inclusion, exit-policy choice, stop/target
choice, maximum-hold choice, row ranking, or tie-breaking. May is
benchmark-only after fixed pre-May selection.

## Allowed Paths

- `docs/work_packets/WPR106-193-motif-path-managed-exit-repair.md`
- `docs/stage_reports/STAGE_R106_MOTIF_PATH_MANAGED_EXIT_REPAIR_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_193_motif_path_managed_exit_repair/**`

## Plan

1. Load WPR106-192 selected source rows.
2. Rebuild WPR106-192 motif lookup state using WPR106-192/WPR106-170 helpers.
3. Generate fixed source entry signals without May feedback.
4. Evaluate path-managed stop/target/max-hold exit variants on pre-May.
5. Select fixed exit rows from pre-May diagnostics only.
6. Replay the fixed selected exit rows on May 2026.
7. Write ranking, monthly/daily/trade artifacts, summary, report, ledger
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
python -m compileall -q data\research\wpr106_193_motif_path_managed_exit_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.

## Exit Evidence

WPR106-193 evaluated 2,442 exit rows over 74 fixed WPR106-192 selected motif
source rows and 33 exit policies. The exit policy grid included the fixed-hold
baseline plus stop/target primary-bar exits with conservative stop-first
same-bar sequencing and half/full maximum hold variants.

The pre-May screen found 524 positive rows, zero annual-target rows, five
loose rows, and zero strict rows. The five loose rows were BTCUSDT
`flow_absorption` stop/target variants with much lower drawdown, but they
failed the latest-four-month activity floor used for fixed selection and did
not meet the annual-target standard.

The fixed selected set contained 97 fallback `positive_recent_stability` rows:
88 ETHUSDT and 9 BTCUSDT. Selected pre-May replay was 97 positive rows, zero
negative rows, median +0.201987, active mean +0.209225, best +0.489121, and
worst +0.028659. May benchmark was weaker than WPR106-192: all 97 rows were
active, but 46 were positive and 51 were negative, with median -0.002639,
active mean +0.004805, best +0.090413, and worst -0.074075.

Path-managed exits did not improve the promising WPR106-192 May behavior. The
best May row remained the original ETHUSDT `trend_pullback_clock` fixed-hold
baseline, not a stop/target exit. Stop/target selected rows had May median
-0.004568 and 7 positive / 28 negative rows.

WPR106-193 therefore rejects motif path-managed exit repair as candidate-ready,
portfolio-ready, or promotion-ready. It preserves the negative diagnostic that
simple primary-bar stop/target exits reduce some drawdowns but do not repair
month-to-month stability or May transfer for the active WPR106-192 motif rows.
