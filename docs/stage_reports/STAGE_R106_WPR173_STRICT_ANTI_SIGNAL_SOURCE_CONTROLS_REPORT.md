# Stage R106 WPR173 Strict Anti-Signal Source Controls Report

Date: 2026-06-12
Work packet: WPR106-175-wpr173-strict-anti-signal-source-controls
Status: fixed source-control audit completed, diagnostic remains rejected

## Scope

WPR106-175 audits the WPR106-173 strict ETHUSDT `vol_breakout_follow`
anti-signal rows after WPR106-174 found a positive June 1-11 2026 fresh
holdout replay. It asks whether the June improvement is specific to the
WPR106-173 inverse-signal source descriptors or whether it is also produced by
fixed controls.

No May or June data is used for threshold choice, side-policy choice, row
inclusion, ranking, filtering, or selection. The controls reuse the fixed
WPR106-173 pre-May score thresholds and WPR106-173 accounting code.

This packet is research-only and observe-only. It writes no candidate pack,
paper/live artifact, live configuration, sizing change, order path, CUDA
speedup claim, or promotion claim.

## Method

Inputs:

- WPR106-173 strict selected rows;
- WPR106-174 strict-row May and June comparison artifacts;
- WPR106-96 BTCUSDT/ETHUSDT context through May 2026 as rolling-feature
  warmup;
- WPR106-168 BTCUSDT/ETHUSDT June 1-11 2026 15m bars and 1m aggTrade flow
  context.

The runner imports the WPR106-173 artifact runner so score construction, exit
labels, conservative ATR barrier behavior, overlap handling, daily caps, and
cost accounting remain identical. It adds only a policy-aware wrapper so
`direct_signal` controls can be replayed beside the original `inverse_signal`
rows.

Fixed control grid:

- 14 strict source descriptors;
- side policies: inverse signal and direct signal;
- side modes: long, short, both;
- regimes: all and high-volatility;
- daily caps: 1, 3, 5.

This produces 504 fixed controls. Thresholds are not recalibrated for controls.
All pre-May metrics cover 2024-01-01 through 2026-04-30. May 2026 and June
1-11 2026 are replay-only benchmarks.

The runner completed in 42.3 seconds. CUDA was not used and no speedup is
claimed.

## Results

Overall fixed controls:

| Metric | Pre-May | May 2026 | June 1-11 2026 |
| --- | ---: | ---: | ---: |
| Rows | 504 | 504 | 504 |
| Active rows | 504 | 312 | 504 |
| Positive rows | 324 | 32 | 404 |
| Negative rows | 180 | 280 | 100 |
| Median return | +0.157164 | -0.005709 | +0.021703 |
| Best return | +2.330703 | +0.034902 | +0.112382 |
| Worst return | -2.028296 | -0.155960 | -0.042359 |

Original exact source descriptors reproduce WPR106-174:

| Metric | Value |
| --- | ---: |
| Exact source rows | 14 |
| May active rows | 4 |
| May-positive rows | 0 |
| May-negative rows | 4 |
| June active rows | 14 |
| June-positive rows | 13 |
| June-negative rows | 1 |
| June median return | +0.021485 |

Policy controls:

| Policy | Rows | Pre-May positive | Pre-May strict | June positive | June negative | June median | June mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `inverse_signal` | 252 | 252 | 56 | 188 | 64 | +0.013734 | +0.013852 |
| `direct_signal` | 252 | 72 | 0 | 216 | 36 | +0.029270 | +0.033169 |

The direct-signal controls are important. They are not strict pre-May and are
not a valid selected lead, but they outperform the inverse controls in June
under the same fixed thresholds. That means June 1-11 2026 is not an
independent confirmation of the WPR106-173 anti-signal edge.

Best June control:

- candidate: `ctrl-bf1711af5d7ca206`;
- source candidate: `adaptexit-94519e9111d4c1a1`;
- policy: direct signal;
- side mode: both;
- regime: all;
- daily cap: 3;
- June trades: 29;
- June return: +0.112382;
- pre-May return: -1.101597;
- May return: -0.114143.

Worst June control:

- candidate: `ctrl-1091b91e86576ed1`;
- source candidate: `adaptexit-9dfbb1f28f2b3bb0`;
- policy: inverse signal;
- side mode: both;
- regime: all;
- daily cap: 1;
- June trades: 9;
- June return: -0.042359.

## Deduplication

The 504 fixed controls collapse to 287 unique pre-May signal-side hashes:

| Diagnostic | Value |
| --- | ---: |
| Unique pre-May signal-side hashes | 287 |
| Duplicate signal-side groups | 143 |
| Largest duplicate group | 4 controls |

The exact source descriptors are not all independent. Several source rows share
identical pre-May signal-side behavior with nearby threshold/cap variants. This
does not invalidate the source accounting, but it weakens the interpretation of
the 14 strict rows as 14 independent discoveries.

## Decision

WPR106-175 rejects the WPR106-173/WPR106-174 strict anti-signal family as
candidate-ready, portfolio-ready, or promotion-ready evidence.

The family remains a useful research diagnostic because inverse-signal controls
are consistently pre-May positive and some strict variants have clean
month-to-month profiles before May. However, the source-level controls show
three fail-closed problems:

- May 2026 remains broadly negative or inactive for the family.
- June 1-11 2026 is positive for both inverse and direct controls, so it is not
  specific confirmation of the anti-signal hypothesis.
- Duplicate signal-side behavior reduces the effective independence of the
  strict source rows.

Useful follow-up evidence would require a longer fresh post-May window or a
causal pre-May regime classifier that explains why May should be skipped while
June should be active, then fixed replay on later data. No such classifier is
selected or claimed by this packet.

## Artifacts

- Runner:
  `data/research/wpr106_175_wpr173_strict_anti_signal_source_controls/scripts/run_wpr106_175_wpr173_strict_anti_signal_source_controls.py`
- Summary:
  `data/research/wpr106_175_wpr173_strict_anti_signal_source_controls/wpr106_175_wpr173_strict_anti_signal_source_controls_summary.json`
- Fixed descriptors:
  `data/research/wpr106_175_wpr173_strict_anti_signal_source_controls/source_controls/fixed_control_descriptors.parquet`
- Pre-May, May, and June metrics:
  `data/research/wpr106_175_wpr173_strict_anti_signal_source_controls/source_controls/fixed_control_pre_may_metrics.parquet`,
  `fixed_control_may_metrics.parquet`, and
  `fixed_control_june_metrics.parquet`
- Pre-May behavior dedup:
  `data/research/wpr106_175_wpr173_strict_anti_signal_source_controls/source_controls/fixed_control_pre_may_behavior_dedup.parquet`
- Pre-May/May/June comparison:
  `data/research/wpr106_175_wpr173_strict_anti_signal_source_controls/source_controls/fixed_control_pre_may_may_june_comparison.parquet`
- Aggregate summaries:
  `data/research/wpr106_175_wpr173_strict_anti_signal_source_controls/source_controls/fixed_control_aggregate_by_period_kind.parquet`
  and
  `fixed_control_aggregate_by_period_mode.parquet`

## Validation

Passed:

- `python -m compileall -q data\research\wpr106_175_wpr173_strict_anti_signal_source_controls\scripts`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`

Contract result: 460 passed.
