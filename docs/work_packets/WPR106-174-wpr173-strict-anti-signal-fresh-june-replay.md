# WPR106-174 WPR173 Strict Anti-Signal Fresh June Replay

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search after WPR106-173 found strict
pre-May ETHUSDT anti-signal rows but May 2026 rejected them. Replay only those
fixed strict WPR106-173 rows on the fresh non-May June 2026 holdout already
collected by WPR106-168.

This packet does not tune on May or June. It is a fixed descriptor replay to
test whether the first recent broad-screen strict pre-May diagnostic survives a
second post-selection holdout.

## Scope

Selection/tuning source:

- WPR106-173 fixed strict rows selected using only 2024-01-01 00:00:00 UTC
  through 2026-04-30 23:59:59 UTC.

Fresh non-May benchmark:

- 2026-06-01 through 2026-06-11 UTC, from WPR106-168 packet-local verified
  Binance Vision daily archives.

May 2026 remains benchmark-only historical evidence from WPR106-173 and must
not be used for parameter choice, threshold choice, row inclusion, ranking, or
selection. June 2026 must also not be used for any tuning; it may only be
replayed after fixed WPR106-173 strict rows are loaded.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-174-wpr173-strict-anti-signal-fresh-june-replay.md`
- `docs/stage_reports/STAGE_R106_WPR173_STRICT_ANTI_SIGNAL_FRESH_JUNE_REPLAY_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_174_wpr173_strict_anti_signal_fresh_june_replay/**`

## Plan

1. Load WPR106-173 selected pre-May rows and retain only `strict_pre_may`
   descriptors.
2. Load WPR106-96 May context as rolling-feature warmup and WPR106-168 June
   packet-local BTCUSDT/ETHUSDT bars and 1m aggTrade flow context as fresh
   holdout rows.
3. Reuse WPR106-173 score, anti-signal side policy, conservative ATR barrier
   semantics, overlap handling, daily caps, and cost accounting without changing
   parameters.
4. Compute regime thresholds from pre-May data only, replay fixed strict rows
   on 2026-06-01 through 2026-06-11, and write June metrics/trades/monthly/daily
   artifacts.
5. Compare June replay to WPR106-173 May benchmark for the same fixed rows.
6. Write research-only artifacts, report, ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_174_wpr173_strict_anti_signal_fresh_june_replay\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Completed as an artifact-only fixed replay packet. The runner loaded the 14
WPR106-173 strict pre-May rows and replayed them unchanged on the WPR106-168
fresh June 1-11 2026 holdout. WPR106-96 context through May was used only as
rolling-feature warmup, and WPR106-173 regime thresholds were computed before
moving the benchmark window to June so the 2024-01-01 through 2026-04-30 tuning
boundary remained intact.

June was materially better than May for the same fixed descriptors: all 14
strict rows were active, 13 were June-positive, one was June-negative, best
June return was +0.059043, worst -0.030856, median +0.021485, and active mean
+0.020151. The same rows were May-rejected in WPR106-173 with four active rows,
all four negative, and active mean -0.030600.

Decision: keep the WPR106-173 ETHUSDT volatility-breakout anti-signal strict
family research-only. June improves the diagnostic, but May remains a failed
benchmark and June covers only 11 calendar days. No candidate pack, paper/live
artifact, order/sizing/runtime change, live config write, CUDA speedup claim,
or promotion claim exists.

Validation passed: scoped script compile, `src/tradingbotsuite` compile, and
contracts. Contracts reported 460 passed.
