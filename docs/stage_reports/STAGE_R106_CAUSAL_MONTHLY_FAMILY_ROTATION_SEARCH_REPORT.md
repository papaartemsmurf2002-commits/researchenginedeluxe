# Stage R106 Causal Monthly Family Rotation Search Report

Date: 2026-06-12
Packet: WPR106-141
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

All source-row universe construction, rule parameters, member counts, diversity
rules, daily caps, ranking, and selection choices used only 2024-01-01 through
2026-04-30. May 2026 was replayed only after the fixed pre-May strict rows were
selected. May member choice used source evidence completed through 2026-04-30;
no May source-row performance influenced May selection.

## Method

The runner
`data/research/wpr106_141_causal_monthly_family_rotation_search/scripts/run_wpr106_141_causal_monthly_family_rotation_search.py`
tests whether previously rejected or loose 2024-forward families have value
when combined by a causal monthly rotation rule.

Loaded trade-level source packets:

- WPR106-130 prior-day level/gap: 1 row, 261 pre-May trades, 3 May trades.
- WPR106-131 volatility term structure: 96 rows, 11,380 pre-May trades,
  436 May trades.
- WPR106-132 multi-horizon trend state: 135 rows, 20,763 pre-May trades,
  789 May trades.
- WPR106-133 cross-symbol lead-lag: 59 rows, 17,305 pre-May trades,
  631 May trades.
- WPR106-134 microstructure state transition: 55 rows, 10,803 pre-May trades,
  464 May trades.
- WPR106-135 microstructure annual-target portfolios: 100 rows,
  13,751 pre-May trades, 554 May trades.
- WPR106-136 cross-family KNN trade-veto overlays: 12 rows,
  1,730 pre-May trades, 96 May trades.
- WPR106-137 diversity-constrained KNN veto ensembles: 100 rows,
  39,654 pre-May trades, 1,964 May trades.
- WPR106-139 calendar/session interaction: 17 rows, 7,408 pre-May trades,
  239 May trades.
- WPR106-140 causal rolling calendar profile: 84 rows, 16,256 pre-May trades,
  348 May trades.

WPR106-138 was explicitly skipped because it has selected monthly metrics but
no selected trade-level artifacts, so it cannot be replayed with same-symbol
overlap and daily-cap accounting.

For each evaluated month, the runner selected source members using only earlier
monthly returns. It then replayed that month from source trade artifacts with
equal outer sleeves, source-level costs already embedded in trade returns,
same-symbol overlap skipping, and max accepted trades/day of 1, 3, or 5. The
grid covered:

- trailing lookback months: 3, 6, 12;
- member counts: 3, 5, 8;
- max accepted trades/day: 1, 3, 5;
- scoring modes: stable mean, recent stability, loss control, loss complement;
- diversity modes: none, family, packet, packet-family;
- max pairwise monthly-return correlation: 0.65, 0.85.

## Results

Pre-May screen:

- Source rows: 659.
- Source trade rows, pre-May: 139,311.
- Source trade rows, May: 5,524.
- Evaluated rotation rows: 864.
- Positive pre-May rows: 864.
- Loose pre-May rows: 668.
- Strict pre-May rows: 60.
- Fixed selected rows: 60 strict rows.

The top selected strict row is:

- Rule ID: `monthrot-ed7358029b345be5`.
- Lookback: 6 months.
- Member count: 5.
- Max accepted trades/day: 1.
- Scoring mode: `stable_mean`.
- Diversity mode: none.
- Max pair correlation: 0.85.
- Trades: 573.
- Active days: 573.
- Trades per active day: 1.000000.
- Active months: 25.
- Losing months: 3.
- Annual losses: 2024: 1, 2025: 2, 2026 Jan-Apr: 0.
- Pre-May net return: +0.359543.
- Max drawdown: -0.046434.
- Sortino daily: 0.214660.
- Best-month share: 0.190664.
- Cost-stress survival: 4/4.

The top rule's negative pre-May months were July 2024 (-0.023736), March 2025
(-0.012226), and December 2025 (-0.020378). It was flat during the initial
warm-up months January through March 2024.

May 2026 benchmark after fixed strict pre-May selection:

- May-positive selected rows: 3.
- May-negative selected rows: 57.
- May-flat selected rows: 0.
- Best May net return: +0.012442.
- Worst May net return: -0.032874.
- Median May net return: -0.021032.
- Mean May net return: -0.021583.

The rank-1 strict rule returned +0.008070 in May with 26 accepted trades over
26 active days and -0.006925 max drawdown. Its May member set was:

- WPR106-140 `rollcal-c5243a8990ca919f`, rolling calendar profile, ETHUSDT.
- WPR106-139 `calendar-00b929bff4330ae9`, calendar session profile, ETHUSDT.
- WPR106-139 `calendar-ad953bfdaa925347`, calendar session momentum, ETHUSDT.
- WPR106-133 `leadlag-18708dffa1413dce`, cross-symbol relative strength,
  ETHUSDT.
- WPR106-134 `microstate-3f8caf061556b8a2`, microstructure return streak,
  ETHUSDT.

The best May row was selection rank 52, `monthrot-1aba8024688465e2`, with 21
May trades, +0.012442 May net return, and -0.017197 May max drawdown. It used
three ETHUSDT members from WPR106-133, WPR106-139, and WPR106-140.

## Decision

The broad causal monthly rotation family is not accepted as a robust rescue of
the prior rejected families. The pre-May search produced many strict-looking
rules, but the fixed top-60 strict benchmark failed May decisively with 57 of
60 rows negative and median May -0.021032.

However, WPR106-141 did surface a narrow research-only follow-up lead:
`monthrot-ed7358029b345be5`. It has strong pre-May month stability, active
1-trade/day behavior, modest drawdown, full stress survival, and a positive
May benchmark. It is not candidate-ready because the packet did not perform
source deduplication beyond portfolio overlap, source/family ablations, shifted
or shuffled negative controls, transparent baseline comparison for the dynamic
rotation rule, or candidate-pack gate recheck. A follow-up should test whether
the rank-1 rule is genuinely robust or just a concentrated ETHUSDT
calendar/lead-lag artifact that happened to pass one holdout month.

## Artifacts

- `data/research/wpr106_141_causal_monthly_family_rotation_search/wpr106_141_causal_monthly_family_rotation_summary.json`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/pre_may/source_universe.parquet`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/pre_may/source_universe.csv`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/pre_may/source_load_metadata.json`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/pre_may/monthly_rotation_ranking.parquet`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/pre_may/monthly_rotation_top2000.csv`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/pre_may/monthly_rotation_monthly_returns.parquet`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/pre_may/monthly_rotation_trades.parquet`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/pre_may/monthly_rotation_member_choices.parquet`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/pre_may/selected_pre_may.csv`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_141_causal_monthly_family_rotation_search/may_benchmark/selected_may_benchmark_member_choices.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_141_causal_monthly_family_rotation_search/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
