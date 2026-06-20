# Stage R106 Diversity Robust Monthly Rotation Search Report

Date: 2026-06-12
Packet: WPR106-143
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

All source universe construction, exact behavior deduplication, candidate
grid choice, robustness criteria, reranking, and selected-row fixation used
only 2024-01-01 through 2026-04-30 evidence. May 2026 was replayed only after
fixed pre-May rows were selected. Diagnostic shuffled/shifted controls are
not strategies and are not candidate evidence.

## Method

The runner
`data/research/wpr106_143_diversity_robust_monthly_rotation_search/scripts/run_wpr106_143_diversity_robust_monthly_rotation_search.py`
imports the WPR106-141 artifact-local replay helpers and keeps the same
causal monthly selection and same-symbol overlap accounting.

It starts from the WPR106-141 trade-level source universe and removes exact
duplicate pre-May trade behavior, keeping the highest pre-May return row per
behavior hash. It then evaluates a stricter rotation grid on the deduplicated
universe:

- lookbacks: 3, 6, and 12 months;
- member counts: 5 and 8;
- max accepted trades/day: 1, 3, and 5;
- scoring modes: stable mean, recent stability, loss control, and loss
  complement;
- diversity modes: family, packet, and packet-family;
- max pairwise monthly-return correlations: 0.45, 0.65, and 0.85.

For the top pre-May diverse rows, the runner computes pre-May-only robustness
controls:

- leave-one-source for each source used across the row's pre-May member
  choices;
- leave-one-packet for each used packet;
- leave-one-family for each used family;
- no WPR106-133 cross-symbol lead-lag packet;
- no `cross_symbol_relative_strength` family;
- no calendar-like sources.

Rows were fixed for May only if they passed the pre-May reranking. Diagnostic
negative controls used permuted source histories, shuffled month order inside
each source, and reversed month order, then replayed actual trades from the
selected rows.

## Results

Deduplication:

- Source rows before dedup: 659.
- Source rows after dedup: 518.
- Duplicate-behavior rows removed: 141.

Pre-May strict diverse grid:

- Evaluated rows: 648.
- Positive pre-May rows: 648.
- Loose pre-May rows: 468.
- Strict pre-May rows: 18.
- Strict diverse pre-May rows: 18.
- Robustness pool: top 60 diverse loose/strict rows.
- Full robust-strict rows: 0.
- Core-strict rows: 12.

The selected tier was `core_strict`, not full robust-strict. The top selected
row was `monthrot-ce975a03077d89c2`:

- Lookback: 3 months.
- Members: 8.
- Max accepted trades/day: 5.
- Scoring: stable mean.
- Diversity: packet.
- Max pair correlation: 0.65.
- Pre-May trades: 938.
- Active days: 584.
- Trades per active day: 1.606164.
- Active months: 25.
- Losing months: 4.
- Annual losing months: 2024: 1, 2025: 2, 2026 Jan-Apr: 1.
- Pre-May net return: +0.527327.
- Max drawdown: -0.092025.
- Daily Sortino: 0.294033.
- Best-month share: 0.156923.
- Used packets: 10.
- Used families: 34.
- Source leave-one loose rate: 1.0.
- Source leave-one minimum net return: +0.447963.
- Packet leave-one loose rate: 1.0.
- Family leave-one loose rate: 1.0.
- No WPR106-133 stayed loose: true.
- No calendar-like stayed loose: false.

The selected 12 core-strict rows had active rates between roughly 1.52 and
1.68 trades per active day, 884 to 988 pre-May trades, 25 active months, and
4 losing pre-May months each. They were diverse and survived source/packet/
family leave-one controls at loose thresholds, but none survived the full
robustness requirement because calendar-like removal failed the loose floor.

May 2026 benchmark after fixed pre-May selection:

- Selected rows: 12.
- May-positive rows: 0.
- May-negative rows: 12.
- Best May net return: -0.019916.
- Worst May net return: -0.021032.
- Median May net return: -0.021032.
- May trades per selected row: 25 or 27.
- May max drawdown range: about -0.019404 to -0.020356.

Diagnostic controls:

- `negative_permute_source_history_seed7`: 79 pre-May strict/diverse rows,
  30 selected diagnostic rows, 0 May-positive rows, best May -0.003177.
- `negative_shuffle_months_seed11`: 28 pre-May strict/diverse rows,
  28 selected diagnostic rows, 0 May-positive rows, best May -0.001229.
- `negative_reverse_month_order`: 70 pre-May strict/diverse rows,
  30 selected diagnostic rows, 8 May-positive rows, best May +0.000846.
- Across all diagnostics: 88 selected rows, 8 May-positive rows, median May
  -0.019305.

## Decision

The stricter diversity and robustness search does not rescue the monthly
rotation family. Exact behavior deduplication, packet/family diversity, and
leave-one-source robustness produced better-looking pre-May core-strict rows
with acceptable 1-5 trades/day activity, but no full robust-strict row existed
and all 12 fixed core-strict rows lost money in the May holdout.

The diagnostic controls strengthen the rejection: distorted monthly evidence
can generate many pre-May strict/diverse rows, and the reversed-history control
even produced 8 May-positive diagnostic rows. That means pre-May strictness in
this rotation construction is not enough evidence of a stable causal edge.

This packet keeps the family fail-closed. The next broad-search work should
move away from defending monthly rotation and either search genuinely different
entry/exit logic or test specific source families directly with cleaner
causal filters.

## Artifacts

- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/wpr106_143_diversity_robust_monthly_rotation_summary.json`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/dedup_summary.json`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/source_load_metadata.json`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/deduped_source_universe.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/strict_diverse_rotation_ranking.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/strict_diverse_rotation_top2000.csv`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/strict_diverse_rotation_monthly_returns.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/strict_diverse_rotation_trades.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/strict_diverse_rotation_member_choices.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/robustness_summary.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/robustness_control_details.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/robustness_control_monthly_returns.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/robustness_reranked.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/may_benchmark/selected_may_benchmark_member_choices.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/diagnostics/diagnostic_summary.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/diagnostics/diagnostic_selected_pre_may.parquet`
- `data/research/wpr106_143_diversity_robust_monthly_rotation_search/diagnostics/diagnostic_may_metrics.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_143_diversity_robust_monthly_rotation_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
