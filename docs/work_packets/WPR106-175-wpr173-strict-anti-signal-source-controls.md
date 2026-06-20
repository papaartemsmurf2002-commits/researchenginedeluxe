# WPR106-175 WPR173 Strict Anti-Signal Source Controls

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search after WPR106-174 revived the
WPR106-173 strict ETHUSDT volatility-breakout anti-signal rows on the fresh
June 1-11 2026 holdout. Audit whether that diagnostic is source-family
specific or explainable by duplicate threshold/cap variants, same-side
behavior, broad `all` regime exposure, or daily-cap effects.

This packet does not tune on May or June. It replays fixed WPR106-173 strict
descriptor controls using the same pre-May thresholds and accounting.

## Scope

Selection/tuning source:

- WPR106-173 strict rows selected using only 2024-01-01 00:00:00 UTC through
  2026-04-30 23:59:59 UTC.

Benchmark-only windows:

- May 2026 from WPR106-96/WPR106-173 benchmark context.
- June 1-11 2026 from WPR106-168 packet-local verified Binance Vision daily
  archives, with WPR106-96 context through May used only as rolling-feature
  warmup.

Fixed controls:

- source strict WPR106-173 inverse-signal descriptors;
- same-side direct-signal controls using the exact same score thresholds;
- side-mode controls for long, short, and both;
- regime controls for `all` and `high_vol`;
- daily-cap controls for 1, 3, and 5 accepted trades/day;
- source-level deduplication and family-level aggregate diagnostics.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-175-wpr173-strict-anti-signal-source-controls.md`
- `docs/stage_reports/STAGE_R106_WPR173_STRICT_ANTI_SIGNAL_SOURCE_CONTROLS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_175_wpr173_strict_anti_signal_source_controls/**`

## Plan

1. Load the 14 WPR106-173 strict selected rows and WPR106-174 June comparison
   artifacts.
2. Import the WPR106-173 runner so score construction, exit labels, overlap
   handling, daily caps, conservative ATR barrier behavior, and costs stay
   identical.
3. Build May-warmup plus June contexts as in WPR106-174, computing regime
   thresholds from pre-May data before moving the benchmark period.
4. Construct fixed descriptor controls from the strict-row source descriptors
   without recalibrating thresholds.
5. Replay controls on pre-May, May, and June, then write metrics, monthly,
   daily, trade, dedup, and aggregate comparison artifacts.
6. Decide whether the WPR106-173/WPR106-174 diagnostic survives controls or
   remains a rejected clue.
7. Write the report, ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_175_wpr173_strict_anti_signal_source_controls\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Completed as an artifact-only fixed source-control audit. The runner loaded the
14 WPR106-173 strict ETHUSDT `vol_breakout_follow` anti-signal descriptors,
reused WPR106-173 score, exit, overlap, daily-cap, ATR barrier, and cost
accounting, and built 504 fixed controls across inverse/direct side policy,
long/short/both side mode, `all`/`high_vol` regime, and 1/3/5 daily caps. No
threshold was recalibrated for controls.

The original exact source descriptors reproduce WPR106-174: May has four
active rows, all negative, while June has all 14 rows active, 13 positive, one
negative, and median +0.021485. The broader control audit rejects the family as
candidate-ready evidence because June is not specific to the anti-signal
hypothesis. Same-threshold direct-signal controls have zero strict pre-May rows
but are stronger in June than inverse controls, with 216/252 positive direct
rows, median +0.029270, and mean +0.033169. May remains broadly negative with
only 32/504 positive controls and 280/504 negative controls.

Deduplication also weakens independence: 504 controls collapse to 287 unique
pre-May signal-side hashes, with 143 duplicate signal-side groups and a largest
duplicate group of four controls.

Decision: keep the WPR106-173/WPR106-174 ETHUSDT volatility-breakout
anti-signal family research-only as a diagnostic, not as candidate-ready,
portfolio-ready, or promotion-ready evidence. A later follow-up would need a
longer fresh post-May window or a causal pre-May regime classifier that explains
why May should be skipped while June should be active, then fixed replay on
later data.

Validation passed: scoped script compile, `src/tradingbotsuite` compile, and
contracts. Contracts reported 460 passed. No candidate pack, paper/live
artifact, order/sizing/runtime change, live config write, CUDA speedup claim,
or promotion claim exists.
