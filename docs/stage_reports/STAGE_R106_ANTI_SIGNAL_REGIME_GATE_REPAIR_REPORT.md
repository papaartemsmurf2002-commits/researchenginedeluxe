# Stage R106 Anti-Signal Regime Gate Repair Report

Date: 2026-06-13
Work packet: WPR106-211-anti-signal-regime-gate-repair
Status: completed, rejected as candidate-ready evidence

## Scope

WPR106-211 revisits the rejected WPR106-173 ETHUSDT
`vol_breakout_follow` anti-signal family after WPR106-175 showed that May 2026
failed and June 1-11 2026 was not source-specific confirmation.

The packet tests whether causal pre-May completed-bar state gates or
prior-history trade-health gates can repair the family before May 2026 is
benchmarked. Selection, scoring, and behavior de-duplication use only
2024-01-01 through 2026-04-30. May 2026 is benchmark-only.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

The runner imports the WPR106-173 artifact runner so score construction, exit
labels, conservative ATR barrier behavior, overlap handling, daily caps, and
cost accounting remain identical. It starts from the 504 fixed descriptors
created by WPR106-175, including inverse-signal and direct-signal controls.

State gates are evaluated on completed signal-bar information before overlap
and daily-cap accounting:

- `state_any`
- `state_high_vol_not_extreme`
- `state_flow_confirm`
- `state_flow_contra`
- `state_trend_aligned`
- `state_trend_contra`
- `state_range_compression`

Health gates are evaluated sequentially from prior accepted trade history only:

- `health_none`
- `health_prior_month_nonnegative`
- `health_prior3m_net_positive`
- `health_prior3m_loss_count_le1`
- `health_prior6m_net_positive`
- `health_drawdown_above_minus05`
- `health_drawdown_above_minus10`
- `health_same_calendar_month_nonnegative`

The full pre-May grid is 28,224 variants. The runner scores pre-May monthly
stability, recent Jan-April 2026 return, last-six-month return,
drop-best-month return, drawdown, cost stress, active months, and losing-month
clusters. It preselects 320 rows and de-duplicates exact accepted pre-May trade
paths before replaying May 2026 for the frozen selected set.

The runner completed in 305.4 seconds. CUDA was not used.

## Results

Full pre-May gated universe:

| Metric | Value |
| --- | ---: |
| Source controls | 504 |
| Gated variants | 28,224 |
| Positive pre-May rows | 13,850 |
| Annual-target rows | 6,660 |
| Loose rows | 4,980 |
| Strict rows | 1,047 |
| Strict-stable selection-tier rows | 973 |

Selected fixed set after behavior de-duplication:

| Metric | Value |
| --- | ---: |
| Selected rows | 97 |
| Selected tier | 97 strict-stable |
| Selected side policy | 97 inverse-signal |
| Positive pre-May selected rows | 97 |
| Median pre-May return | +1.277867 |
| Active mean pre-May return | +1.323948 |
| Best pre-May return | +1.800202 |
| Worst pre-May return | +0.941856 |

The selected state-gate mix was 60 `state_any`, 22 `state_trend_contra`, and
15 `state_flow_contra`. The selected health-gate mix was 32
`health_same_calendar_month_nonnegative`, 25
`health_prior_month_nonnegative`, 19 `health_none`, 10
`health_prior3m_loss_count_le1`, 8 `health_drawdown_above_minus10`, 2
`health_prior6m_net_positive`, and 1 `health_prior3m_net_positive`.

May 2026 benchmark:

| Metric | Value |
| --- | ---: |
| Rows | 97 |
| Active rows | 66 |
| Positive rows | 0 |
| Negative rows | 66 |
| Flat rows | 31 |
| Total May trades across selected rows | 3,220 |
| Median May return | -0.012779 |
| Active mean May return | -0.033615 |
| Best May return | 0.000000 |
| Worst May return | -0.106343 |

Direct-signal controls were useful as a falsification guard. Across the full
pre-May gated universe they produced 3,121 positive rows, 2,634 annual-target
rows, and 96 loose rows, but zero strict rows. The selected strict-stable set
remained entirely inverse-signal behavior.

## Decision

WPR106-211 rejects the anti-signal regime gate repair as candidate-ready,
portfolio-ready, paper/live-ready, or promotion-ready.

The useful evidence is falsification: causal completed-bar state gates and
prior-history health throttles can make the rejected WPR106-173/WPR106-175
family look much stronger before May, but they do not repair May 2026 transfer.
Every active selected row still loses in May, and the inactive rows are flat
rather than positive benchmark evidence.

No candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, CUDA speedup claim, or promotion claim exists.

## Artifacts

- Runner:
  `data/research/wpr106_211_anti_signal_regime_gate_repair/scripts/run_wpr106_211_anti_signal_regime_gate_repair.py`
- Summary:
  `data/research/wpr106_211_anti_signal_regime_gate_repair/wpr106_211_anti_signal_regime_gate_repair_summary.json`
- Gated pre-May ranking:
  `data/research/wpr106_211_anti_signal_regime_gate_repair/pre_may/gated_pre_may_ranking.parquet`
- Selected pre-May descriptors:
  `data/research/wpr106_211_anti_signal_regime_gate_repair/pre_may/selected_gated_pre_may.parquet`
- Selected pre-May replay:
  `data/research/wpr106_211_anti_signal_regime_gate_repair/pre_may/selected_pre_may_replay_metrics.parquet`
- May benchmark:
  `data/research/wpr106_211_anti_signal_regime_gate_repair/may_benchmark/selected_may_benchmark_metrics.parquet`

## Validation

Passed:

- `python -m compileall -q data\research\wpr106_211_anti_signal_regime_gate_repair\scripts`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

Contract result: 460 passed.
