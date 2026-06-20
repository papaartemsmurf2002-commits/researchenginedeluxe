# Stage R106 WPR146 Consensus Direct Rebuild Report

Date: 2026-06-12
Work packet: WPR106-167-wpr146-consensus-direct-rebuild
Status: reproducibility pass, rejected as candidate-ready and promotion-ready
evidence

## Scope

WPR106-167 rebuilt the WPR106-166 behavior-consensus threshold 5 descriptor
directly from source trades, WPR106-136 features, and fixed WPR106-146
behavior-representative KNN parameters.

All fixed representatives and the threshold 5 rule came from WPR106-166
pre-May evidence. The direct rebuild used 2024-01-01 through 2026-04-30 for
source replay and kept May 2026 benchmark-only after the descriptor was fixed.

The packet is research-only and observe-only. It writes no candidate pack, no
paper/live artifact, no live configuration, no sizing change, no order path,
and no promotion claim.

## Method

The runner:

- loaded the 17 WPR106-166 behavior-deduped representatives;
- rebuilt WPR106-133 source trades, May trades, source lookup, and feature
  cache through WPR106-146/WPR106-136 helpers;
- re-evaluated each fixed representative KNN parameter row from source trades;
- rebuilt the raw source cap-5 baseline directly from source trades;
- recomputed vote counts over raw cap-5 trades;
- applied the fixed threshold 5 consensus rule;
- compared direct rebuild trade keys and metrics with WPR106-166 frozen
  artifacts.

No parameter selection, threshold selection, or row ranking used May.

## Direct Rebuild Result

The threshold 5 direct rebuild exactly reproduces WPR106-166:

| Metric | Direct rebuild |
| --- | ---: |
| Pre-May trades | 254 |
| Pre-May active months | 26 |
| Pre-May losing months | 2 |
| Annual losses | 1/1/0 |
| Pre-May net return | +1.155278 |
| Pre-May expectancy | +0.004548 |
| Pre-May max drawdown | -0.141007 |
| Pre-May best-month share | 0.146280 |
| Cost-stress survival | 1.000000 |
| May trades | 17 |
| May net return | +0.065272 |
| May expectancy | +0.003840 |

The direct raw cap-5 rebuild also matches the prior raw source path:

| Metric | Raw cap 5 |
| --- | ---: |
| Pre-May trades | 451 |
| Pre-May active months | 28 |
| Pre-May losing months | 7 |
| Annual losses | 4/3/0 |
| Pre-May net return | +1.209539 |
| Pre-May max drawdown | -0.243442 |
| May trades | 17 |
| May net return | +0.065272 |

The 17 direct representative rows remain 17/17 May-positive, with best
+0.067949, worst +0.015398, median +0.030569, and mean +0.037985.

## Parity

All direct rebuild parity checks passed:

- representative trade-key parity: exact for all 17 representatives across
  pre-May and May;
- raw cap-5 trade-key parity: exact for pre-May and May;
- threshold-5 consensus metric parity: exact for pre-May trade count, pre-May
  return, pre-May losing months, May trade count, and May return.

The parity deltas were zero:

- pre-May trade count delta: 0;
- pre-May total net return delta: 0.000000;
- pre-May losing months delta: 0;
- May trade count delta: 0;
- May total net return delta: 0.000000.

## Decision

WPR106-167 proves the WPR106-166 threshold-5 descriptor is reproducible from
source trades and fixed KNN parameters. That is useful: the descriptor no
longer depends only on frozen selected-trade artifacts.

It still is not candidate-ready. The May benchmark is the same raw WPR106-133
source path, May was already involved in motivating this research branch, and
there is still no fresh non-May holdout. The descriptor should remain
research-only until a later-data retest or equivalent independent benchmark is
available.

The best next object for future work is:

- source: WPR106-133 `leadlag-18708dffa1413dce`;
- fixed behavior representatives: the 17 WPR106-166 representatives;
- consensus rule: raw cap-5 trade accepted when at least 5 fixed
  representatives accept the same trade key;
- benchmark boundaries: optimize through 2026-04-30, May 2026 benchmark-only,
  and any later data reserved as a fresh non-May holdout.

No candidate pack, paper/live artifact, order path, sizing change, runtime-mode
change, live config write, CUDA speedup claim, or promotion claim exists.

## Artifacts

- Runner:
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/scripts/run_wpr106_167_wpr146_consensus_direct_rebuild.py`
- Summary:
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/wpr106_167_wpr146_consensus_direct_rebuild_summary.json`
- Direct representative metrics:
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/pre_may/direct_rebuild_representative_metrics.parquet`
- Direct representative trades:
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/pre_may/direct_rebuild_representative_trades.parquet`
  and
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/may_benchmark/direct_rebuild_representative_trades.parquet`
- Direct raw cap-5 metrics/trades:
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/pre_may/direct_rebuild_raw_cap5_metrics.parquet`
  and
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/pre_may/direct_rebuild_raw_cap5_trades.parquet`
- Direct threshold-5 consensus metrics/trades:
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/pre_may/direct_rebuild_consensus_threshold5_metrics.parquet`
  and
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/pre_may/direct_rebuild_consensus_threshold5_trades.parquet`
- May threshold-5 consensus trades:
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/may_benchmark/direct_rebuild_consensus_threshold5_trades.parquet`
- Parity artifacts:
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/parity/representative_trade_key_parity.parquet`,
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/parity/raw_cap5_trade_key_parity.parquet`, and
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/parity/consensus_threshold5_metric_parity.json`

## Validation

Passed:

- `python -m compileall -q data/research/wpr106_167_wpr146_consensus_direct_rebuild/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

Contract result: 460 passed.
