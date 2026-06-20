# Stage R106 Causal Accepted-Trade Throttle Overlay Report

Date: 2026-06-12
Work packet: WPR106-179-causal-accepted-trade-throttle-overlay
Status: overlay search completed, no May-confirmed lead

## Scope

WPR106-179 tests whether causal accepted-trade throttle overlays can improve
the WPR106-178 selected trade ledgers after the monthly stability selector
cleaned up pre-May behavior but still failed May.

This packet does not create new entry signals. It overlays already accepted
WPR106-178 trades, and a skipped accepted trade does not open any later raw
signal that WPR106-178 had skipped.

Overlay selection uses only 2024-01-01 through 2026-04-30 accepted trade
history. May 2026 and June 1-11 2026 are fixed benchmark replays after overlay
selection. May and June are not used for threshold choice, row inclusion,
ranking, or selection.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

Inputs:

- WPR106-178 selected stability rows;
- WPR106-178 selected pre-May accepted trade ledger;
- WPR106-178 selected May 2026 accepted trade ledger;
- WPR106-178 selected June 1-11 2026 accepted trade ledger.

The runner generates conservative throttle variants per WPR106-178 selected
row:

- pre-May score quantile tightening at 0.00, 0.50, 0.65, and 0.80;
- all-side versus best-side filtering from pre-May side evidence;
- cooldown after 0, 1, or 2 accepted losing trades;
- daily loss stop off or -0.015;
- daily losing-count stop off or 2 accepted losing trades;
- monthly loss stop off, -0.04, or -0.08.

The overlay replay is causal over the accepted trade sequence. It does not
look ahead within May or June, and it does not use May or June for any overlay
choice.

The runner evaluated 28,800 overlay descriptors. Runtime was 588.4 seconds.
CUDA was not used and no speedup is claimed.

## Pre-May Results

Full overlay grid:

| Metric | Value |
| --- | ---: |
| Overlay descriptors | 28,800 |
| Positive pre-May overlays | 25,178 |
| Annual-target pre-May overlays | 1,863 |
| Loose pre-May overlays | 4,798 |
| Strict pre-May overlays | 231 |

Selected fixed set:

| Metric | Value |
| --- | ---: |
| Selected overlays | 100 |
| Strict selected overlays | 16 |
| Annual selected overlays | 1 |
| Other overlay selected rows | 83 |
| Best selected pre-May return | +1.938118 |
| Median selected pre-May return | +1.106529 |
| Worst selected pre-May return | +0.320027 |
| Active mean selected pre-May return | +1.121298 |

The overlay search made pre-May replay cleaner than WPR106-178. It found many
positive and strict pre-May overlays, and the selected set has no negative
pre-May rows. However, the strict pocket is still concentrated in the
already-rejected ETHUSDT `vol_breakout_follow` cluster.

Pre-May overlay source/template summary:

| Source | Symbol | Template | Rows | Strict | Annual | Loose | Median | Best |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| WPR106-176 | ETHUSDT | `vol_breakout_follow` | 5,184 | 231 | 399 | 2,373 | +0.543931 | +1.953506 |
| WPR106-177 | ETHUSDT | `cross_relative_reversion` | 5,184 | 0 | 576 | 384 | +0.397796 | +1.405325 |
| WPR106-176 | BTCUSDT | `vol_breakout_follow` | 5,184 | 0 | 432 | 480 | +0.070498 | +0.888470 |
| WPR106-177 | ETHUSDT | `range_zscore_flow_revert` | 3,168 | 0 | 216 | 148 | +0.259272 | +1.428098 |
| WPR106-177 | ETHUSDT | `flow_absorption_fade` | 2,592 | 0 | 156 | 132 | +0.293043 | +1.496901 |
| WPR106-177 | ETHUSDT | `flow_burst_nonbreakout_follow` | 864 | 0 | 72 | 24 | +0.230701 | +0.958424 |
| WPR106-176 | ETHUSDT | `flow_burst_follow` | 3,168 | 0 | 12 | 1,113 | +0.270460 | +1.321261 |
| WPR106-177 | BTCUSDT | `flow_absorption_fade` | 2,880 | 0 | 0 | 144 | +0.212918 | +0.851444 |
| WPR106-176 | BTCUSDT | `trend_pullback_follow` | 576 | 0 | 0 | 0 | -0.243255 | +0.000841 |

## Benchmarks

Fixed selected overlays:

| Metric | Pre-May Replay | May 2026 | June 1-11 2026 |
| --- | ---: | ---: | ---: |
| Rows | 100 | 100 | 100 |
| Active rows | 100 | 53 | 96 |
| Positive rows | 100 | 7 | 72 |
| Negative rows | 0 | 46 | 24 |
| Flat rows | 0 | 47 | 4 |
| Median return | +1.106529 | 0.000000 | +0.024723 |
| Active mean return | +1.121298 | -0.025601 | +0.015573 |
| Best return | +1.938118 | +0.034386 | +0.059909 |
| Worst return | +0.320027 | -0.077051 | -0.099033 |

May remains the rejection point. The selected overlay set has more May-negative
than May-positive active rows, and the active May mean is worse than the
WPR106-178 baseline.

Selected benchmark by source/template:

| Source | Symbol | Template | Rows | May pos/neg | May median | June pos/neg | June median |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| WPR106-177 | ETHUSDT | `flow_absorption_fade` | 16 | 6/10 | -0.008116 | 0/16 | -0.041736 |
| WPR106-176 | BTCUSDT | `vol_breakout_follow` | 3 | 1/1 | 0.000000 | 3/0 | +0.023633 |
| WPR106-176 | ETHUSDT | `flow_burst_follow` | 20 | 0/6 | 0.000000 | 20/0 | +0.051645 |
| WPR106-176 | ETHUSDT | `vol_breakout_follow` | 20 | 0/13 | -0.020775 | 18/2 | +0.038420 |
| WPR106-177 | ETHUSDT | `cross_relative_reversion` | 20 | 0/0 | 0.000000 | 16/0 | +0.000897 |
| WPR106-177 | ETHUSDT | `range_zscore_flow_revert` | 15 | 0/10 | -0.015358 | 10/5 | +0.039843 |
| WPR106-177 | ETHUSDT | `flow_burst_nonbreakout_follow` | 5 | 0/5 | -0.042255 | 5/0 | +0.040871 |
| WPR106-177 | BTCUSDT | `flow_absorption_fade` | 1 | 0/1 | -0.077051 | 0/1 | -0.014950 |

Best May overlay:

- overlay: `throttle-221319b8e7d4fb3e`;
- source candidate: `switch-d1d985b91f7164fa`;
- template: `vol_breakout_follow`;
- May trades: 10;
- May return: +0.034386;
- June return: +0.023633.

Best June overlay:

- overlay: `throttle-02f620a6e731c0ac`;
- source candidate: `switch-1d295c96eb6a466c`;
- template: `flow_burst_follow`;
- June trades: 5;
- June return: +0.059909;
- May return: -0.074505.

## Decision

WPR106-179 rejects the accepted-trade throttle overlay as candidate-ready,
portfolio-ready, or promotion-ready evidence.

The overlay family is useful diagnostically because it shows that pre-May
accepted-trade throttles can produce cleaner monthly evidence and stricter
pre-May rows. It is not a candidate lead because:

- fixed May 2026 transfer is negative on active rows;
- only 7 of 100 selected overlays are May-positive;
- 46 of 100 selected overlays are May-negative;
- strict selected overlays remain tied to the already-rejected ETHUSDT
  `vol_breakout_follow` cluster;
- June improves but does not override the benchmark-only May failure.

Useful diagnostics to preserve:

- BTCUSDT WPR106-176 `vol_breakout_follow` with the best May overlay remains a
  small research-only clue because it is positive in May and June, but only
  three selected overlays survive in that group.
- ETHUSDT `flow_burst_follow`, `vol_breakout_follow`,
  `range_zscore_flow_revert`, and `flow_burst_nonbreakout_follow` remain
  June-positive but May-negative diagnostics, so they are not candidate-ready.

## Artifacts

- Runner:
  `data/research/wpr106_179_causal_accepted_trade_throttle_overlay/scripts/run_wpr106_179_causal_accepted_trade_throttle_overlay.py`
- Summary:
  `data/research/wpr106_179_causal_accepted_trade_throttle_overlay/wpr106_179_causal_accepted_trade_throttle_overlay_summary.json`
- Overlay descriptors:
  `data/research/wpr106_179_causal_accepted_trade_throttle_overlay/overlay/overlay_descriptors.parquet`
- Overlay pre-May metrics and monthly rows:
  `data/research/wpr106_179_causal_accepted_trade_throttle_overlay/overlay/overlay_pre_may_metrics.parquet` and
  `overlay_pre_may_monthly.parquet`
- Selected overlays:
  `data/research/wpr106_179_causal_accepted_trade_throttle_overlay/overlay/selected_overlays.parquet`
- Selected pre-May, May, and June metrics:
  `data/research/wpr106_179_causal_accepted_trade_throttle_overlay/selected_replay/selected_pre_may_metrics.parquet`,
  `selected_may_metrics.parquet`, and `selected_june_metrics.parquet`
- Selected pre-May/May/June comparison:
  `data/research/wpr106_179_causal_accepted_trade_throttle_overlay/selected_replay/selected_pre_may_may_june_comparison.parquet`
- Selected trade ledgers:
  `data/research/wpr106_179_causal_accepted_trade_throttle_overlay/selected_replay/selected_pre_may_trades.parquet`,
  `selected_may_trades.parquet`, and `selected_june_trades.parquet`

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_179_causal_accepted_trade_throttle_overlay\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contract result: 460 passed.
