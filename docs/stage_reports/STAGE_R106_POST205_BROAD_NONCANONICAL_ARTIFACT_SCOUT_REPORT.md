# Stage R106 WPR106-206 Post-205 Broad Noncanonical Artifact Scout Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-206 restarts the broad 2024-forward search after WPR106-205 demoted
the WPR106-203/WPR106-204 canonical motif portfolio pocket. The packet scans
existing selected trade artifacts across prior WPR106 families, excluding
WPR106-203 through WPR106-205 and canonical motif row
`motif202-00860ffdbf2eb058`.

The scout recomputes comparable metrics from accepted trade artifacts. It is
an artifact-level scout, not a fresh strategy recomputation. Pre-May ranking,
behavior deduplication, and selected-row inclusion use only 2024-01-01 through
2026-04-30. May 2026 is benchmark-only after the selected set exists.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/scripts/run_wpr106_206_post205_broad_noncanonical_artifact_scout.py`

The runner discovers WPR106 selected pre-May metric/trade artifacts with
matching selected May trade artifacts, normalizes trade schemas, recomputes
metrics with the same WPR106-170 accounting helpers used by recent packets,
behavior-deduplicates accepted trade signatures, ranks only on pre-May
evidence, and benchmarks the fixed selected set on May.

Runtime was 78.97 seconds. CUDA was not used and no speedup claim was made.

## Results

WPR106-206 loaded 68 source artifact directories and 4,133 source rows. After
behavior deduplication:

- 2,604 pre-May rows.
- 2,604 positive pre-May rows.
- 157 annual-target rows.
- 45 strict-like pre-May rows.
- Median pre-May return: +0.473960.
- Median active months: 28.
- Median losing months: 8.

The fixed selected set contains 150 rows:

- 45 strict noncanonical source rows.
- 8 annual-target source rows.
- 97 positive active source rows.
- Median selected pre-May return: +1.204596.
- Median active months: 28.
- Median losing months: 5.
- 54 annual-target rows.

Source-family strict-like concentration:

- `wpr106_139_calendar_session_interaction_search`: 15 strict-like rows.
- `wpr106_173_anti_signal_entry_exit_screen`: 14 strict-like rows.
- `wpr106_188_diversity_capped_recent_family_portfolio_control`: 7
  strict-like rows.
- `wpr106_199_post190_cross_family_behavior_portfolio`: 6 strict-like rows.
- Smaller counts from WPR106-169, WPR106-130, and WPR106-151.

Best pre-May row:

- `scout206-ede0acdc38dd4fdc`, sourced from WPR106-139
  `calendar-31c7fbe72a20a7ac`.
- ETHUSDT `calendar_flow_impulse`.
- +2.480657 pre-May over 678 trades.
- 28 active months, four losing months.
- Loss-month counts 2/1/1 for 2024/2025/2026 Jan-Apr.
- Max drawdown -0.205831.
- Trades per active day 1.40.
- May benchmark -0.000748 over 24 trades.

Best stability row:

- `scout206-5cf9dedaa169bd91`, sourced from WPR106-139
  `calendar-72ffca0bffc82830`.
- ETHUSDT `calendar_session_momentum`.
- +2.232898 pre-May over 558 trades.
- 28 active months, three losing months.
- Loss-month counts 1/2/0 for 2024/2025/2026 Jan-Apr.
- Max drawdown -0.198850.
- Trades per active day 1.30.
- May benchmark -0.069423 over 16 trades.

## May Benchmark

May rejects the broad selected set:

- 22 positive May rows.
- 107 negative May rows.
- 21 flat May rows.
- Median selected May return: -0.018163.
- Active mean May return: -0.034232.
- Best selected May return: +0.065272.
- Worst selected May return: -0.133646.

Only four strict-like selected rows are May-positive, and all four are old
WPR106-199 post-190 cross-family behavior portfolio rows. Those rows are not
fresh independent evidence because WPR106-199/WPR106-200 already found source
concentration and missing ablations around that pocket.

The best May row is not strict-like:

- `scout206-d461af368da72034`, sourced from WPR106-133
  `leadlag-18708dffa1413dce`.
- ETHUSDT `cross_symbol_relative_strength`.
- +1.209539 pre-May over 451 trades, but seven losing months and annual target
  false.
- May +0.065272 over 17 trades.

## Interpretation

WPR106-206 rejects the broad noncanonical artifact scout set as
candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready. The
scan found strong pre-May noncanonical rows, especially calendar/session and
anti-signal/exit artifacts, but they mostly failed the May benchmark. The few
strict-like rows that did transfer to May are recycled WPR106-199 composite
rows already requiring source-level controls.

The useful follow-up is not promotion. It is either:

- a fresh calendar/session source reconstruction with causal controls and May
  still held out, because WPR106-139 contains the strongest pre-May profile but
  failed May; or
- a cross-symbol lead-lag / anchored-VWAP transfer repair, because those
  non-strict rows had the best May transfer but too many pre-May losing months.

No WPR106-206 row is candidate-ready or promotion-ready.

## Artifacts

- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/controls/source_artifact_index.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/controls/skipped_source_artifacts.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/controls/loaded_component_index.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/pre_may/broad_noncanonical_pre_may_metrics.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/pre_may/broad_noncanonical_pre_may_top5000.csv`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/pre_may/broad_noncanonical_pre_may_monthly_returns.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/pre_may/selected_pre_may_rows.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/pre_may/selected_pre_may_metrics.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/may_benchmark/broad_noncanonical_may_benchmark_metrics.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/may_benchmark/broad_noncanonical_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/source_family_summary.parquet`
- `data/research/wpr106_206_post205_broad_noncanonical_artifact_scout/wpr106_206_post205_broad_noncanonical_artifact_scout_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_206_post205_broad_noncanonical_artifact_scout\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
