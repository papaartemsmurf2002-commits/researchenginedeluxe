# Stage R106 Non-Breakout Flow/Trend/Range Rotation Report

Date: 2026-06-12
Work packet: WPR106-177-non-breakout-flow-trend-range-rotation
Status: non-breakout search completed, no candidate-ready replacement

## Scope

WPR106-177 continues the 2024-forward broad research search after WPR106-175
and WPR106-176 rejected the repeated ETHUSDT volatility-breakout cluster. This
packet deliberately excludes `vol_breakout_follow` and tests non-breakout
completed-bar families instead.

All score definitions, thresholds, policy rules, row inclusion, ranking, and
selection use only 2024-01-01 through 2026-04-30. May 2026 and June 1-11 2026
are replayed only after fixed pre-May rows are selected.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m bars from 2024-01-01 through 2026-05-31;
- WPR106-96 BTCUSDT/ETHUSDT 1m aggTrade rows aggregated into completed 15m
  flow-pressure features;
- WPR106-168 BTCUSDT/ETHUSDT June 1-11 2026 15m bars and 1m aggTrade flow
  context for fresh non-May replay.

The runner imports WPR106-173 feature/context/exit/accounting helpers and
WPR106-176 replay helpers, then supplies new non-breakout score arrays.

Score variants:

- `flow_absorption_fade`;
- `flow_burst_nonbreakout_follow`;
- `range_zscore_flow_revert`;
- `trend_pullback_flow_resume`;
- `wick_absorption_reversal`;
- `compression_release_follow`;
- `cross_relative_reversion`.

Search grid:

- symbols: BTCUSDT and ETHUSDT;
- normalization windows: 96 and 384 bars;
- sessions: all and US;
- raw score targets: 1, 3, and 5 signals/day;
- policy rules: direct, inverse, high-volatility skip, flow confirm/contra
  switch, trend aligned/contra switch, and range-compression skip;
- side modes: both, long, and short;
- exits: fixed 32, fixed 64, ATR barrier `h16 tp1/sl1`, and ATR barrier
  `h32 tp2/sl1`;
- accepted-trade daily caps: 1, 3, 5.

The runner evaluated 60,480 pre-May rows. Runtime was 552.3 seconds. CUDA was
not used and no speedup is claimed.

## Pre-May Results

Full grid:

| Metric | Value |
| --- | ---: |
| Evaluated rows | 60,480 |
| Positive pre-May rows | 10,930 |
| Annual-target rows | 287 |
| Loose rows | 235 |
| Strict rows | 0 |

Selected fixed set:

| Metric | Value |
| --- | ---: |
| Selected rows | 100 |
| Strict selected rows | 0 |
| Loose selected rows | 100 |
| Best selected pre-May return | +1.496901 |
| Median selected pre-May return | +0.497283 |
| Worst selected pre-May return | +0.265327 |

Template summary:

| Template | Loose rows | Median pre-May return | Best pre-May return |
| --- | ---: | ---: | ---: |
| `trend_pullback_flow_resume` | 54 | -0.146212 | +0.985441 |
| `cross_relative_reversion` | 48 | -0.084295 | +1.351610 |
| `range_zscore_flow_revert` | 35 | -0.135047 | +1.321027 |
| `compression_release_follow` | 28 | -0.250178 | +1.554072 |
| `flow_absorption_fade` | 25 | -0.178307 | +1.568398 |
| `flow_burst_nonbreakout_follow` | 25 | -0.157781 | +1.093143 |
| `wick_absorption_reversal` | 20 | -0.282282 | +0.858638 |

The top selected row is:

- candidate: `nonbrk-a65cac6d3d7430c7`;
- symbol: ETHUSDT;
- template: `flow_absorption_fade`;
- policy: `inverse_high_vol_skip`;
- side mode: both;
- exit: `fixed_64`;
- daily cap: 1;
- pre-May trades: 221;
- pre-May return: +1.496901;
- losing months: 7;
- cost-stress survival: 4/4.

The top row is loose rather than strict because monthly loss count and drawdown
do not satisfy strict stability.

## May And June Benchmarks

The fixed selected set does not transfer:

| Metric | May 2026 | June 1-11 2026 |
| --- | ---: | ---: |
| Rows | 100 | 100 |
| Active rows | 47 | 80 |
| Positive rows | 14 | 32 |
| Negative rows | 33 | 48 |
| Flat rows | 53 | 20 |
| Median return | 0.000000 | 0.000000 |
| Active mean return | -0.016519 | -0.006525 |
| Best return | +0.091878 | +0.135191 |
| Worst return | -0.077051 | -0.118114 |

Selected benchmark by template:

| Template | Rows | May pos/neg/flat | June pos/neg/flat | May median | June median |
| --- | ---: | ---: | ---: | ---: | ---: |
| `wick_absorption_reversal` | 4 | 4/0/0 | 4/0/0 | +0.012068 | +0.051381 |
| `flow_burst_nonbreakout_follow` | 13 | 3/7/3 | 9/4/0 | -0.031112 | +0.006439 |
| `cross_relative_reversion` | 19 | 3/0/16 | 6/7/6 | 0.000000 | 0.000000 |
| `compression_release_follow` | 10 | 3/3/4 | 1/9/0 | 0.000000 | -0.022858 |
| `range_zscore_flow_revert` | 12 | 1/9/2 | 9/2/1 | -0.036788 | +0.033087 |
| `flow_absorption_fade` | 17 | 0/14/3 | 3/14/0 | -0.008116 | -0.024216 |
| `trend_pullback_flow_resume` | 25 | 0/0/25 | 0/12/13 | 0.000000 | 0.000000 |

The best May row is:

- candidate: `nonbrk-90f70abdf6532086`;
- symbol: ETHUSDT;
- template: `range_zscore_flow_revert`;
- policy: `direct_range_compression_skip`;
- side mode: short;
- exit: `fixed_64`;
- May trades: 10;
- May return: +0.091878;
- June trades: 0;
- June return: 0.000000;
- pre-May return: +0.356469;
- pre-May losing months: 7.

The best June row is:

- candidate: `nonbrk-55f851e0154bd3a0`;
- symbol: ETHUSDT;
- template: `flow_burst_nonbreakout_follow`;
- policy: `direct_trend_aligned_inverse_contra_skip`;
- side mode: short;
- exit: `fixed_64`;
- May trades: 6;
- May return: +0.016401;
- June trades: 5;
- June return: +0.135191;
- pre-May return: +0.715914;
- pre-May losing months: 7.

The only selected template pocket that is positive in both May and June is the
small BTCUSDT `wick_absorption_reversal` group with four selected rows. It is
not candidate-ready because it is loose-only, duplicated by nearby caps, and
has eight pre-May losing months.

## Decision

WPR106-177 rejects the non-breakout flow/trend/range rotation search as
candidate-ready, portfolio-ready, or promotion-ready evidence.

The packet does broaden the falsification evidence away from the repeated
ETHUSDT volatility-breakout cluster. It shows that non-breakout variants can
produce many positive pre-May rows and some May/June-positive pockets, but no
strict pre-May rows exist and the fixed selected set has negative active means
in both May and June.

Useful diagnostics to preserve:

- BTCUSDT `wick_absorption_reversal` under high-volatility inverse policy is
  small but positive in both benchmarks.
- ETHUSDT `flow_burst_nonbreakout_follow` short with trend switch has the best
  June row and positive May, but remains loose-only with seven pre-May losing
  months.

Neither diagnostic supports a candidate claim.

## Artifacts

- Runner:
  `data/research/wpr106_177_non_breakout_flow_trend_range_rotation/scripts/run_wpr106_177_non_breakout_flow_trend_range_rotation.py`
- Summary:
  `data/research/wpr106_177_non_breakout_flow_trend_range_rotation/wpr106_177_non_breakout_flow_trend_range_rotation_summary.json`
- Candidate descriptors:
  `data/research/wpr106_177_non_breakout_flow_trend_range_rotation/pre_may/non_breakout_candidate_descriptors.parquet`
- Pre-May ranking:
  `data/research/wpr106_177_non_breakout_flow_trend_range_rotation/pre_may/non_breakout_pre_may_ranking.parquet`
- Selected descriptors:
  `data/research/wpr106_177_non_breakout_flow_trend_range_rotation/pre_may/selected_pre_may.parquet`
- Selected pre-May, May, and June metrics:
  `data/research/wpr106_177_non_breakout_flow_trend_range_rotation/selected_replay/selected_pre_may_replay_metrics.parquet`,
  `selected_may_metrics.parquet`, and `selected_june_metrics.parquet`
- Selected pre-May/May/June comparison:
  `data/research/wpr106_177_non_breakout_flow_trend_range_rotation/selected_replay/selected_pre_may_may_june_comparison.parquet`
- Selected trade ledgers:
  `data/research/wpr106_177_non_breakout_flow_trend_range_rotation/selected_replay/selected_pre_may_trades.parquet`,
  `selected_may_trades.parquet`, and `selected_june_trades.parquet`

## Validation

Passed:

- `python -m compileall -q data\research\wpr106_177_non_breakout_flow_trend_range_rotation\scripts`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

Contract result: 460 passed.
