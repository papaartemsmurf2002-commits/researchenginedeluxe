# Stage R106 WPR173 Strict Anti-Signal Fresh June Replay Report

Date: 2026-06-12
Work packet: WPR106-174-wpr173-strict-anti-signal-fresh-june-replay
Status: fixed strict-row replay completed, diagnostic revived but not
candidate-ready

## Scope

WPR106-174 replays only the 14 strict WPR106-173 pre-May descriptors on a fresh
non-May holdout: 2026-06-01 through 2026-06-11 UTC. The June data comes from
the WPR106-168 packet-local verified Binance Vision daily archives.

No May or June data is used for threshold choice, side-policy choice, row
inclusion, ranking, filtering, or selection. The replay keeps WPR106-173
feature definitions, pre-May score thresholds, pre-May regime thresholds,
inverse-signal side policy, conservative ATR barrier semantics, overlap
handling, daily caps, and cost accounting fixed.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

Inputs:

- WPR106-173 fixed selected rows, filtered to `strict_pre_may == true`;
- WPR106-173 May benchmark metrics for the same fixed rows;
- WPR106-96 BTCUSDT/ETHUSDT context through May 2026 as rolling-feature warmup;
- WPR106-168 BTCUSDT/ETHUSDT June 1-11 2026 15m bars and 1m aggTrade flow
  context.

The runner imports the WPR106-173 artifact runner and overrides only the base
frame loader so WPR106-96 history is concatenated with the WPR106-168 June
holdout rows. It computes WPR106-173 regime thresholds before moving the
benchmark window to June, preserving the 2024-01-01 through 2026-04-30
selection boundary.

The replay window is:

- start: 2026-06-01 00:00:00 UTC;
- end exclusive: 2026-06-12 00:00:00 UTC.

## Results

Fixed rows replayed:

| Metric | Value |
| --- | ---: |
| WPR106-173 strict rows | 14 |
| Source template | ETHUSDT `vol_breakout_follow` |
| Source side policy | inverse signal |
| Source exit | `barrier_h32_tp2_sl1` |
| June active rows | 14 |
| June-positive rows | 13 |
| June-negative rows | 1 |
| June-flat rows | 0 |
| Best June return | +0.059043 |
| Worst June return | -0.030856 |
| Median June return | +0.021485 |
| Active mean June return | +0.020151 |

The best June row is:

- candidate: `adaptexit-50477960d7635680`;
- pre-May trades: 2,144;
- pre-May net return: +1.386712;
- pre-May losing months: 4;
- May trades: 75;
- May net return: -0.028771;
- June trades: 26;
- June net return: +0.059043;
- June cost-stress survival: 4/4.

The only June-negative row is:

- candidate: `adaptexit-f487a2cc8b59117b`;
- pre-May trades: 690;
- pre-May net return: +0.891803;
- pre-May losing months: 5;
- May trades: 28;
- May net return: -0.024682;
- June trades: 10;
- June net return: -0.030856;
- June cost-stress survival: 0/4.

June aggregate diagnostics:

| Diagnostic | Value |
| --- | ---: |
| Total fixed-row June trades | 197 |
| Days with any June trade | 11 |
| Positive daily aggregate days | 8 |
| Negative daily aggregate days | 3 |
| Best aggregate day | +0.141676 |
| Worst aggregate day | -0.079327 |

## May vs June

For the same fixed 14 strict WPR106-173 rows:

| Benchmark | Active rows | Positive rows | Negative rows | Median return | Active mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| May 2026 | 4 | 0 | 4 | 0.000000 | -0.030600 |
| June 1-11 2026 | 14 | 13 | 1 | +0.021485 | +0.020151 |

June is materially better than May, but the result is still not candidate-ready
because May remains a failed benchmark and June covers only 11 calendar days.

## Decision

WPR106-174 does not promote the WPR106-173 strict anti-signal rows to
candidate-ready, portfolio-ready, or promotion-ready evidence. It does,
however, upgrade the WPR106-173 strict ETHUSDT volatility-breakout anti-signal
family from a May-rejected clue to a stronger research-only diagnostic that
deserves a later direct control packet or a longer fresh non-May holdout when
more post-May data is available.

The next useful work is source-level deduplication and controls around the
fixed descriptor family: remove duplicated threshold/cap variants, test
same-side and opposite-side controls, isolate high-volatility long-only versus
both-side behavior, and replay on a longer fresh post-May window if available.

## Artifacts

- Runner:
  `data/research/wpr106_174_wpr173_strict_anti_signal_fresh_june_replay/scripts/run_wpr106_174_wpr173_strict_anti_signal_fresh_june_replay.py`
- Summary:
  `data/research/wpr106_174_wpr173_strict_anti_signal_fresh_june_replay/wpr106_174_wpr173_strict_anti_signal_fresh_june_replay_summary.json`
- Fixed source rows:
  `data/research/wpr106_174_wpr173_strict_anti_signal_fresh_june_replay/fresh_june_replay/wpr173_fixed_strict_source_rows.parquet`
- June metrics:
  `data/research/wpr106_174_wpr173_strict_anti_signal_fresh_june_replay/fresh_june_replay/wpr173_strict_fresh_june_metrics.parquet`
- June trades:
  `data/research/wpr106_174_wpr173_strict_anti_signal_fresh_june_replay/fresh_june_replay/wpr173_strict_fresh_june_trades.parquet`
- Pre-May/May/June comparison:
  `data/research/wpr106_174_wpr173_strict_anti_signal_fresh_june_replay/fresh_june_replay/wpr173_strict_pre_may_may_june_comparison.parquet`

## Validation

Passed:

- `python -m compileall -q data\research\wpr106_174_wpr173_strict_anti_signal_fresh_june_replay\scripts`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

Contract result: 460 passed.
