# Stage R106 Causal Side-Policy Switch Search Report

Date: 2026-06-12
Work packet: WPR106-176-causal-side-policy-switch-search
Status: side-policy switch search completed, no candidate-ready lead

## Scope

WPR106-176 continues the 2024-forward broad research search after WPR106-175
showed that June 1-11 2026 favored both direct and inverse volatility-breakout
controls. It tests whether causal completed-bar rules can switch between
direct, inverse, and skip behavior using only pre-May evidence.

All score thresholds, policy rules, row inclusion, ranking, and selection use
only 2024-01-01 through 2026-04-30. May 2026 and June 1-11 2026 are replayed
only after fixed pre-May rows are selected.

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

The runner imports the WPR106-173 artifact runner and reuses its feature,
score, exit-label, overlap, daily-cap, cost, and metric code. It adds only
causal side-policy rules.

Search grid:

- symbols: BTCUSDT and ETHUSDT;
- templates: `vol_breakout_follow`, `flow_burst_follow`,
  `compression_breakout_follow`, and `trend_pullback_follow`;
- normalization windows: 96 and 384 bars;
- sessions: all and US;
- raw score targets: 1, 3, and 5 signals/day;
- side modes: both, long, and short;
- exits: `fixed_64` and `barrier_h32_tp2_sl1`;
- daily caps: 1, 3, and 5;
- policy rules: direct, inverse, high-volatility skip/switch, flow
  confirm/contra switch, trend aligned/contra switch, and range-compression
  skip rules.

The runner evaluated 14,880 pre-May rows. CUDA was not used and no speedup is
claimed. Runtime was 143.6 seconds.

## Pre-May Results

Full grid:

| Metric | Value |
| --- | ---: |
| Evaluated rows | 14,880 |
| Positive pre-May rows | 5,945 |
| Annual-target rows | 1,273 |
| Loose rows | 299 |
| Strict rows | 10 |

Selected fixed set:

| Metric | Value |
| --- | ---: |
| Selected rows | 100 |
| Strict selected rows | 10 |
| Loose selected rows | 90 |
| Best selected pre-May return | +1.899726 |
| Median selected pre-May return | +0.756446 |
| Worst selected pre-May return | +0.523173 |

All 10 strict rows are ETHUSDT `vol_breakout_follow` variants with
`barrier_h32_tp2_sl1` exits:

| Policy rule | Strict rows |
| --- | ---: |
| `inverse_high_vol_skip` | 4 |
| `inverse_all` | 3 |
| `inverse_high_vol_direct_else` | 2 |
| `inverse_flow_confirm_direct_contra_skip` | 1 |

The top strict row is:

- candidate: `switch-38c9b9b0c29e19df`;
- symbol: ETHUSDT;
- template: `vol_breakout_follow`;
- policy rule: `inverse_all`;
- side mode: both;
- exit: `barrier_h32_tp2_sl1`;
- daily cap: 3;
- pre-May trades: 1,750;
- pre-May return: +1.371242;
- losing months: 3;
- cost-stress survival: 3/4.

## May And June Benchmarks

May 2026 rejects the fixed selected set:

| Metric | May 2026 | June 1-11 2026 |
| --- | ---: | ---: |
| Rows | 100 | 100 |
| Active rows | 77 | 100 |
| Positive rows | 19 | 81 |
| Negative rows | 58 | 19 |
| Flat rows | 23 | 0 |
| Median return | -0.002036 | +0.026792 |
| Best return | +0.041807 | +0.073901 |
| Worst return | -0.074505 | -0.052324 |
| Active mean return | -0.010022 | +0.025377 |

The strict subset is not May-confirmed:

| Strict diagnostic | Value |
| --- | ---: |
| Strict selected rows | 10 |
| May-positive strict rows | 0 |
| May-negative strict rows | 6 |
| May-flat strict rows | 4 |
| June-positive strict rows | 10 |
| June-negative strict rows | 0 |

The best May row is loose, not strict:

- candidate: `switch-ab82ae3dfcb80c2b`;
- symbol: ETHUSDT;
- template: `vol_breakout_follow`;
- policy rule: `direct_trend_aligned_inverse_contra_skip`;
- exit: `fixed_64`;
- May trades: 6;
- May return: +0.041807;
- June trades: 5;
- June return: +0.057030;
- pre-May return: +1.174347;

The best June row is also loose:

- candidate: `switch-62523b8ce83a5778`;
- symbol: ETHUSDT;
- template: `vol_breakout_follow`;
- policy rule: `inverse_flow_confirm_direct_contra_skip`;
- exit: `barrier_h32_tp2_sl1`;
- June trades: 18;
- June return: +0.073901;
- May return: -0.007962;
- pre-May return: +1.114042.

## Decision

WPR106-176 rejects the causal side-policy switch search as candidate-ready,
portfolio-ready, or promotion-ready evidence.

The useful research finding is narrower: pre-May can select several
volatility-breakout side-policy rules, and loose direct/flow/trend switch rows
can be May-positive. However, no strict row is May-positive, the fixed selected
set has a negative May median and active mean, and June again looks broadly
favorable after May rejection. Flat May rows from high-volatility skip rules are
not evidence of May robustness.

The family remains a research-only diagnostic. A future packet should avoid
reselecting the same ETHUSDT volatility-breakout inverse cluster unless it adds
a genuinely new causal validation design or a longer fresh post-May window.

## Artifacts

- Runner:
  `data/research/wpr106_176_causal_side_policy_switch_search/scripts/run_wpr106_176_causal_side_policy_switch_search.py`
- Summary:
  `data/research/wpr106_176_causal_side_policy_switch_search/wpr106_176_causal_side_policy_switch_search_summary.json`
- Candidate descriptors:
  `data/research/wpr106_176_causal_side_policy_switch_search/pre_may/switch_candidate_descriptors.parquet`
- Pre-May ranking:
  `data/research/wpr106_176_causal_side_policy_switch_search/pre_may/switch_pre_may_ranking.parquet`
- Selected descriptors:
  `data/research/wpr106_176_causal_side_policy_switch_search/pre_may/selected_pre_may.parquet`
- Selected pre-May, May, and June metrics:
  `data/research/wpr106_176_causal_side_policy_switch_search/selected_replay/selected_pre_may_replay_metrics.parquet`,
  `selected_may_metrics.parquet`, and `selected_june_metrics.parquet`
- Selected pre-May/May/June comparison:
  `data/research/wpr106_176_causal_side_policy_switch_search/selected_replay/selected_pre_may_may_june_comparison.parquet`
- Selected trade ledgers:
  `data/research/wpr106_176_causal_side_policy_switch_search/selected_replay/selected_pre_may_trades.parquet`,
  `selected_may_trades.parquet`, and `selected_june_trades.parquet`

## Validation

Passed:

- `python -m compileall -q data\research\wpr106_176_causal_side_policy_switch_search\scripts`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

Contract result: 460 passed.
