# Stage R106 Post-May Non-May Holdout Availability And Replay Report

Date: 2026-06-12
Work packet: WPR106-168-post-may-non-may-holdout-availability-and-replay
Status: fresh non-May benchmark failed, descriptor rejected as current lead

## Scope

WPR106-168 tested whether the WPR106-167 WPR146 threshold-5 descriptor could
survive a fresh post-May, non-May benchmark.

The descriptor was frozen before this packet: WPR106-133 source parameters,
raw cap 5, the 17 WPR106-166 behavior representatives, the threshold-5
consensus rule, KNN parameters, and costs were not changed. May 2026 was not
used for selection, KNN history, parameter choice, or threshold choice. It was
only present as chronological rolling-feature warm-up for later June bars.

The packet is research-only and observe-only. It writes no candidate pack, no
paper/live artifact, no live configuration, no sizing change, no order path,
and no promotion claim.

## Data Availability

The shared local Binance Vision cache had no June 2026 BTCUSDT/ETHUSDT daily
archives for the required replay inputs.

Remote Binance Vision daily archives were available for a contiguous completed
fresh window:

| Item | Result |
| --- | ---: |
| Fresh window | 2026-06-01 through 2026-06-11 UTC |
| Complete replay days | 11 |
| Required archive families | BTC/ETH 15m klines and aggTrades |
| Packet-local archives downloaded | 44 |
| Checksums verified | 44 |
| CUDA used | false |
| Speed claim | false |

The packet also checked remote 1m kline availability for inventory, but did
not download 1m kline files because the frozen WPR146 replay only needs 15m
bars and aggTrade-flow context.

The transformed packet-local context contains 1,056 15m bars per symbol
covering 2026-06-01 00:00 through 2026-06-11 23:45 UTC. The aggTrade archives
contained 30,159,488 BTCUSDT rows and 23,956,287 ETHUSDT rows, aggregated into
15,840 one-minute flow rows per symbol with zero aggTrade ID order anomalies.

## Replay Result

The fresh June replay rejects the descriptor.

| Metric | Raw source | Raw cap 5 | Threshold-5 consensus |
| --- | ---: | ---: | ---: |
| Trades | 6 | 6 | 6 |
| Active days | 6 | 6 | 6 |
| Net return | -0.030098 | -0.030098 | -0.030098 |
| Gross return | -0.023114 | -0.023114 | -0.023114 |
| Expectancy | -0.005016 | -0.005016 | -0.005016 |
| Max drawdown | -0.056414 | -0.056414 | -0.056414 |
| Daily Sortino | -0.434106 | -0.434106 | -0.434106 |
| Cost-stress survival | 0.000000 | 0.000000 | 0.000000 |
| Losing months | 1 | 1 | 1 |

The source produced 10 candidate signals before overlap handling and skipped 4
by source overlap. All 6 accepted raw cap-5 trades reached the threshold-5
consensus vote requirement, so the consensus path matched raw cap 5 on this
short fresh window.

The 17 fixed behavior representatives were mixed:

| Representative summary | Value |
| --- | ---: |
| Rows | 17 |
| Positive | 10 |
| Negative | 7 |
| Best return | +0.003022 |
| Worst return | -0.030098 |
| Median return | +0.001916 |
| Mean return | -0.007561 |

The consensus trades were:

| Entry UTC | Side | Net return | Vote count |
| --- | --- | ---: | ---: |
| 2026-06-01 00:45 | long | -0.019519 | 14 |
| 2026-06-02 02:15 | short | -0.003776 | 17 |
| 2026-06-04 03:15 | long | -0.033120 | 7 |
| 2026-06-05 06:15 | short | +0.032307 | 17 |
| 2026-06-06 05:45 | long | +0.001106 | 11 |
| 2026-06-10 12:45 | long | -0.007096 | 17 |

## Decision

WPR106-168 closes the WPR146 threshold-5 defense path. WPR106-167 proved the
descriptor was reproducible and May-positive, but WPR106-168 shows that the
first available fresh non-May benchmark is negative after costs, negative under
cost stress, and too short/fragile to rescue as a candidate lead.

The result supports returning to the broader 2024-forward research search
rather than continuing to defend this narrow descriptor.

No candidate pack, paper/live artifact, order path, sizing change, runtime-mode
change, live config write, CUDA speedup claim, or promotion claim exists.

## Artifacts

- Runner:
  `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/scripts/run_wpr106_168_post_may_non_may_holdout_availability_and_replay.py`
- Summary:
  `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/wpr106_168_post_may_non_may_holdout_availability_and_replay_summary.json`
- Local inventory:
  `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/availability/local_june_archive_inventory.parquet`
- Remote availability:
  `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/availability/remote_june_archive_availability.parquet`
- Packet-local download manifest:
  `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/availability/packet_local_download_manifest.parquet`
- Fresh replay consensus metrics:
  `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/fresh_post_may_replay/direct_replay_consensus_threshold5_post_may_june_metrics.parquet`
- Fresh replay consensus trades:
  `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/fresh_post_may_replay/direct_replay_consensus_threshold5_post_may_june_trades.parquet`
- Fresh replay representative metrics/trades:
  `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/fresh_post_may_replay/direct_replay_representative_post_may_june_metrics.parquet`
  and
  `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/fresh_post_may_replay/direct_replay_representative_post_may_june_trades.parquet`
- June transformed context:
  `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/source_context/`

## Validation

Passed:

- `python -m compileall -q data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

Contract result: 460 passed.
