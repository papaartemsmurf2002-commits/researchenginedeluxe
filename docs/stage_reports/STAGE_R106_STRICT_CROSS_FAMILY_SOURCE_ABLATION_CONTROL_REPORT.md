# Stage R106 WPR106-200 Strict Cross-Family Source Ablation Control Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-200 audited the WPR106-199 strict-tier diagnostic before treating it as
a lead. WPR106-199 found 10 strict pre-May portfolios, usually combining
WPR106-196 anchored/opening-range behavior, WPR106-197 opening-range short
controls, and one WPR106-190 or WPR106-191 KNN source. WPR106-200 tested
whether those KNN/non-opening members were genuinely complementary or whether
the strict pocket was mostly opening-range source concentration.

The 10 WPR106-199 strict parents were fixed before this packet. Every
ablation/control variant is a deterministic transform of those pre-May source
IDs. May 2026 remained benchmark-only after the fixed variant set existed.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_200_strict_cross_family_source_ablation_control/scripts/run_wpr106_200_strict_cross_family_source_ablation_control.py`

The runner imports WPR106-199 helpers, rebuilds the same normalized WPR106-190
through WPR106-198 source trade pools, and reuses the WPR106-199 equal-member
weighting, same-symbol overlap blocking, portfolio-level daily caps,
cost-stress, monthly, drawdown, and Sortino accounting.

Generated controls for each strict parent include:

- base;
- source-only;
- leave-one-source-out;
- opening-only;
- no-KNN;
- KNN-only;
- no-non-opening;
- non-opening-only;
- no-WPR106-196;
- no-WPR106-197;
- no-WPR106-198 where applicable;
- no-WPR106-190 or no-WPR106-191 where applicable;
- pair-only/no-pair for WPR106-195 parents.

Runtime was 5.59 seconds. CUDA was not used and no speedup claim was made.

## Results

WPR106-200 evaluated 150 fixed variants:

- 10 base rows.
- 30 source-only rows.
- 30 leave-one-source-out rows.
- 10 opening-only rows.
- 10 no-non-opening rows.
- 7 no-KNN rows.
- 7 KNN-only rows.
- 10 non-opening-only rows.
- 10 no-WPR106-196 rows.
- 10 no-WPR106-197 rows.
- 3 no-pair rows and 3 pair-only rows.

All variants are positive pre-May:

- 150 active rows.
- Median net return: +0.762252.
- Active mean net return: +0.723333.
- Best/worst rows: +1.196304 / +0.192660.

May benchmark for all fixed variants:

- 135 active rows and 15 flat rows.
- 117 positive rows, 18 negative rows, 15 flat rows.
- Median net return: +0.009201.
- Active mean net return: +0.010768.
- Best/worst rows: +0.053605 / -0.030679.

These aggregate control statistics are not candidate evidence because they are
post-diagnostic ablations of already selected strict parents. They are useful
for attributing which source classes helped or hurt the WPR106-199 strict
pocket.

## Base Rows

The 10 WPR106-199 strict parent rows reproduce as:

- Pre-May: 10 positive rows, median +0.653902, active mean +0.650454,
  median losing months 4.5.
- May: seven positive rows, three negative rows, median +0.006134,
  active mean +0.004812.

This confirms the WPR106-199 strict-tier diagnostic, but not candidate
readiness.

## Source Contribution

The KNN/non-opening contribution is weak.

No-KNN-like controls (`no_knn`, `opening_only`, and `no_non_opening`) improve
the parents:

- Median pre-May delta versus base: +0.123850.
- Median May delta versus base: +0.004206.
- `opening_only`: 10/10 May-positive, median May +0.012617.
- `no_non_opening`: 10/10 May-positive, median May +0.012617.
- `no_knn`: 7/7 May-positive, median May +0.009201.

KNN-only controls do not confirm KNN as the useful member:

- 7 rows.
- Pre-May median +0.588163 but median losing months 11.
- May has two positive rows and five flat rows.
- Median May return 0.000000.
- Median May delta versus base: -0.006134.

Non-opening-only controls are also weak:

- 10 rows.
- Pre-May median +0.446077 with median losing months 11.5.
- May has two positive rows, three negative rows, and five flat rows.
- May active mean -0.015807.

Pair-only controls are clearly weak:

- 3 rows.
- Pre-May median +0.192660 with median losing months 14.
- May median -0.030679.

## Opening Sources

WPR106-197 is the core source in this diagnostic:

- Source-only WPR106-197 variants produce the best May rows.
- Best May variant `ablate200-bff835f9b7ede5cd` is
  `WPR106-197:or197-aaf5acc56f96eddc` alone with pre-May +0.907051 over
  68 trades, 19 active months, three losing months, 100% cost-stress survival,
  and May +0.053605 over four trades.
- Removing WPR106-197 worsens May for every parent: `no_wpr106_197` has
  median May delta -0.003280.

WPR106-196 helps the pre-May stability profile but not May:

- `no_wpr106_196` has 10/10 May-positive rows and median May +0.025012,
  but median pre-May losing months worsens to 8.

Opening-only controls are therefore a research diagnostic, not a candidate:
they improve the strict parents, but they are source-concentrated and still
need independent source-level ablation, transparent baselines, stability-region
evidence, and candidate-pack gates.

## Interpretation

WPR106-200 rejects the WPR106-199 strict-tier result as a cross-family KNN
complementarity lead. The KNN and pair-spread sources generally weaken the
strict parents; removing non-opening sources improves both pre-May and May
median behavior.

The useful follow-up is narrower: audit WPR106-196 plus WPR106-197
opening-only/source-only controls as an opening-range diagnostic, with special
attention to WPR106-197 source sparsity. The best source-only WPR106-197 May
row is profitable and has only three pre-May losing months, but it is active in
only 19 pre-May months and cannot be called stable or candidate-ready.

No WPR106-200 row is candidate-ready, portfolio-ready, or promotion-ready.

## Artifacts

- `data/research/wpr106_200_strict_cross_family_source_ablation_control/pre_may/wpr106_199_strict_parent_portfolios.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/pre_may/strict_ablation_variants.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/pre_may/strict_ablation_pre_may_metrics.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/pre_may/strict_ablation_pre_may_monthly_returns.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/pre_may/strict_ablation_pre_may_daily_returns.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/pre_may/strict_ablation_pre_may_trades.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/may_benchmark/strict_ablation_may_benchmark_metrics.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/may_benchmark/strict_ablation_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/may_benchmark/strict_ablation_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/may_benchmark/strict_ablation_may_benchmark_trades.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/controls/paired_base_control_comparison.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/controls/pre_may_control_group_summary.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/controls/may_control_group_summary.parquet`
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/wpr106_200_strict_cross_family_source_ablation_control_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_200_strict_cross_family_source_ablation_control\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
