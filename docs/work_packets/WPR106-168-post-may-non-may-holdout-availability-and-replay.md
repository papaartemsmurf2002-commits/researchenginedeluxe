# WPR106-168 Post-May Non-May Holdout Availability And Replay

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Determine whether a fresh post-May, non-May holdout is locally or remotely
available for the WPR106-167 direct WPR146 threshold-5 descriptor. If enough
BTCUSDT and ETHUSDT Binance Vision data is available for a complete June 2026
window, replay the frozen descriptor on that window without using May 2026 for
selection, tuning, feature choice, parameter choice, or model updates.

This packet is an availability and benchmark replay packet only. It must not
change the descriptor, candidate family, thresholds, behavior representatives,
KNN parameters, or cost assumptions selected by WPR106-166/WPR106-167.

## Allowed Paths

- `docs/work_packets/WPR106-168-post-may-non-may-holdout-availability-and-replay.md`
- `docs/stage_reports/STAGE_R106_POST_MAY_NON_MAY_HOLDOUT_AVAILABILITY_AND_REPLAY_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/**`

## Inputs

- Read-only WPR106-167 direct rebuild outputs under
  `data/research/wpr106_167_wpr146_consensus_direct_rebuild/**`.
- Read-only WPR106-166 consensus artifacts under
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/**`.
- Read-only WPR106-133 and WPR106-126 source replay helper scripts under
  `data/research/wpr106_133_cross_symbol_lead_lag_search/**` and
  `data/research/wpr106_126_liquidity_sweep_wick_failure_search/**`.
- Read-only local Binance Vision cache under
  `data/research/historical_data_cache/binance_vision_public_archive/**`.
- Optional remote Binance Vision availability checks and downloads for June
  2026 daily archive files, written only under this packet's output tree.

## Method

- Inventory local BTCUSDT and ETHUSDT post-May archive files for 15m klines,
  1m klines, and aggTrades.
- Check remote Binance Vision daily archive availability for complete June
  2026 UTC days available before the current date.
- If a complete replay window exists, build packet-local 15m bar and 1m
  aggTrade-flow inputs from checksum-verifiable archives.
- Reuse the frozen WPR106-133 relative-strength source parameters and the
  frozen WPR106-166/WPR106-167 threshold-5 consensus construction.
- Apply the frozen descriptor to the fresh non-May window only after the
  descriptor is fixed.
- Record trade metrics, monthly/daily behavior, cost-stress notes, data
  availability, hash evidence, and fail-closed boundary metadata.
- If no complete post-May window is available, write the availability evidence
  and do not fabricate or extrapolate a replay.

## Validation

- `python -m compileall -q data/research/wpr106_168_post_may_non_may_holdout_availability_and_replay/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write a machine-readable availability/replay summary under the packet output
  tree.
- Write the stage report and update the stage ledger with the packet decision.
- Keep all outputs `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Do not write a candidate pack or make paper/live/promotion claims.

## Result

WPR106-168 found no local June 2026 BTCUSDT/ETHUSDT daily archive files in the
shared Binance Vision cache, but remote Binance Vision daily archives were
available for a contiguous fresh post-May window from 2026-06-01 through
2026-06-11 UTC. The packet downloaded the required 15m kline and aggTrade daily
archives under its own output tree, verified all 44 archive checksums, and
transformed them into packet-local 15m bar and 1m aggTrade-flow context.

The frozen WPR106-167 threshold-5 descriptor was replayed on 2026-06-01 through
2026-06-11 without changing the WPR106-133 source parameters, raw cap,
behavior representatives, consensus threshold, KNN parameters, costs, or
selection criteria. May 2026 was not used for selection, KNN history, parameter
choice, or threshold choice; it was only present as chronological rolling
feature warm-up for the later June bars.

The fresh non-May benchmark rejects the WPR146 threshold-5 descriptor as a
current lead: raw source, raw cap 5, and threshold-5 consensus all produced 6
June trades, -0.030098 total net return after costs, -0.056414 max drawdown,
negative daily Sortino, one losing June month, and 0/4 cost-stress survival.
The 17 fixed representatives were mixed, with 10 positive and 7 negative rows,
best +0.003022, worst -0.030098, median +0.001916, and mean -0.007561. This
overturns the prior May-positive story on the first fresh non-May replay.

The packet rejects WPR106-168 as candidate-ready, portfolio-ready, or
promotion-ready evidence and closes the WPR146 threshold-5 defense path. No
candidate pack, paper/live artifact, live config, order path, sizing change,
CUDA speedup claim, or promotion claim was written. Focused script compile,
package compile, and contracts passed; contracts reported 460 passed.
