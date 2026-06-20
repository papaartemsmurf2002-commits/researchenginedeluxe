# WPR106-184 WPR183 Behavior-Deduped Selector Controls

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Follow up WPR106-183 without defending the rejected selected set. WPR106-183
showed a broad multi-timeframe VWAP/residual state universe with many
profitable pre-May rows, but its fixed selected set was duplicate-heavy and
failed May. This packet tests whether a strictly May-blind behavior-deduped
selector over the WPR106-183 full replay universe can improve benchmark
transfer, or whether the family remains unstable even after deduplication and
diversity caps.

This is a selector/control packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May selection.

Inputs:

- WPR106-183 full pre-May replay ranking and packet-local runner.
- WPR106-96 BTCUSDT/ETHUSDT 15m bar context through May 2026 and 15m
  aggTrade-flow aggregation loaded through the WPR106-183/WPR106-126 helpers.

Selector dimensions:

- exact pre-May accepted-trade path hashes;
- behavior-deduped representatives;
- family/template/symbol/session/side diversity caps;
- annual losing-month caps and active-month coverage;
- return after dropping best three months;
- rolling 6-month floor;
- cost-stress survival and drawdown filters;
- active 1-5 trades/day behavior.

May must not be used for behavior hashing, pool construction, ranking,
deduplication, cap choice, row inclusion, or selection. May is benchmark-only
after fixed pre-May selection.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-184-wpr183-behavior-deduped-selector-controls.md`
- `docs/stage_reports/STAGE_R106_WPR183_BEHAVIOR_DEDUPED_SELECTOR_CONTROLS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/**`

## Plan

1. Reuse the WPR106-183 runner and its WPR106-126 accounting helpers.
2. Load WPR106-183 full pre-May replay rows and rebuild feature/context caches.
3. Replay eligible rows on pre-May with trade rows to compute exact accepted
   pre-May path hashes.
4. Deduplicate by pre-May behavior and rank representatives using only
   pre-May metrics and monthly diagnostics.
5. Select fixed behavior-deduped rows under diversity caps and active-rate
   constraints.
6. Replay only the fixed selected rows on May 2026.
7. Write dedup pool, selected metrics/monthly/daily/trade artifacts, summary,
   report, ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_184_wpr183_behavior_deduped_selector_controls\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12 as a negative selector/control result.

The packet-local runner
`data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/scripts/run_wpr106_184_wpr183_behavior_deduped_selector_controls.py`
loaded the WPR106-183 full replay ranking, replayed 3,409 eligible rows on
the pre-May window with accepted-trade ledgers, computed exact pre-May trade
path hashes, deduplicated to 1,823 behavior representatives, and selected 100
fixed rows using only pre-May metrics and diversity controls.

Pre-May behavior pool:

- 3,684 source ranking rows.
- 3,409 eligible source rows replayed with trades.
- 1,823 unique pre-May trade-path hashes.
- 1,823 deduplicated positive representatives.
- 4 annual-target rows, 677 loose rows, 0 strict rows.

Selected pre-May replay:

- 100 selected rows: 77 `dedup_dropout_repair`, 23 `dedup_loose`.
- 100 positive rows, 0 negative rows, 0 flat rows.
- 100 unique pre-May trade-path hashes.
- Median net return: +0.884393.
- Active mean net return: +0.784029.
- Best/worst selected rows: +1.460809 / +0.097654.

May 2026 benchmark replay:

- 21 positive rows, 79 negative rows, 0 flat rows.
- 54 unique May trade-path hashes.
- Median net return: -0.026900.
- Active mean net return: -0.029790.
- Best/worst selected rows: +0.028018 / -0.094876.
- Aggregate selected May total: -2.979006 across 639 trades.

Behavior deduplication removed the duplicate-heavy selected-set issue from
WPR106-183, but it did not solve May transfer. The fixed behavior-deduped set
is rejected as candidate-ready, portfolio-ready, or promotion-ready.

The strongest May diagnostic row is BTCUSDT
`session_vwap_reclaim_failure` / `session_vwap_reclaim`, direct both-side,
EU session, compressed volatility, flow-confirm filter, 64-bar hold, daily cap
1. It recorded +0.531281 pre-May across 403 trades with eight losing months,
then +0.028018 in May across 15 trades. Smaller BTC residual and session-VWAP
pockets also survived May, while the selected ETHUSDT inverse rolling-VWAP
extension cluster was broadly negative. These are research clues only.

Artifacts:

- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/eligible_source_pool.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/pre_may_behavior_replay_metrics.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/pre_may_behavior_monthly_returns.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/pre_may_behavior_trades.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/behavior_dedup_representatives.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/selected_pre_may_behavior_dedup.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/wpr106_184_wpr183_behavior_deduped_selector_controls_summary.json`

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_184_wpr183_behavior_deduped_selector_controls\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
