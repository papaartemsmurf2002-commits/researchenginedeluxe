# Stage R106 WPR106-204 WPR203 Component Ablation Control Audit Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-204 audits the WPR106-203 cross-diagnostic component-portfolio lead.
WPR106-203 produced strict pre-May rows with positive May benchmark behavior,
but every strict WPR106-203 row used the same WPR106-202 motif component:
`motif202-00860ffdbf2eb058`.

This packet fixes the WPR106-203 selected parents and component pools, then
builds May-blind controls from 2024-01-01 through 2026-04-30 only. May 2026 is
used only as a benchmark after the fixed control universe exists.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_204_wpr203_component_ablation_control_audit/scripts/run_wpr106_204_wpr203_component_ablation_control_audit.py`

The runner imports WPR106-203 replay helpers so costs, same-symbol no-overlap
blocking, daily caps, health-gate timing, monthly diagnostics, and strict-like
gates are directly comparable to WPR106-203.

Control families:

- base replay;
- opening-only and motif-only source controls;
- no-health-gate ablations;
- daily-cap neighbors;
- priority-mode neighbors, including opening-first;
- opening-weight neighborhoods;
- motif-component swaps across the WPR106-203 motif pool;
- opening-component swaps across the WPR106-203 opening pool;
- bounded deterministic return-permutation controls for the top 10 selected
  parents.

Runtime was 160.36 seconds. CUDA was not used and no speedup claim was made.

## Results

WPR106-204 evaluated 2,922 fixed controls:

- 2,922/2,922 positive pre-May rows.
- Median pre-May return: +0.790345.
- Median active months: 25.
- Median losing months: 5.
- 1,803 annual-target rows.
- 1,328 strict-like pre-May rows.

The WPR106-203 base replay reproduced:

- 100/100 positive pre-May rows.
- 100/100 strict-like rows.
- Median pre-May return: +0.812433.
- Median active months: 25.
- Median losing months: 4.

Source-only controls do not reproduce the strict profile:

- 200/200 positive pre-May source-only rows.
- Zero strict-like source-only rows.
- Median source-only return: +0.762014.
- Median active months: 22.
- Median losing months: 5.
- Opening-only median: +0.890884, 23 active months, five losing months.
- Motif-only median: +0.651137, 18 active months, five losing months.

Motif-component swaps also do not reproduce the strict profile:

- 900/900 positive pre-May motif-swap rows.
- 337 annual-target rows.
- Zero strict-like motif-swap rows.
- Median motif-swap return: +0.705664.
- Median active months: 21.
- Median losing months: 6.

Strict-like controls are broad only inside the canonical-motif neighborhood:

- 1,328 strict-like rows total.
- 1,328/1,328 strict-like rows use `motif202-00860ffdbf2eb058`.
- 0 strict-like rows use any alternate motif component.
- Opening-component swaps contribute 676 strict-like rows, but all use the
  canonical motif.
- Priority neighbors contribute 200 strict-like rows.
- Weight neighbors contribute 186 strict-like rows.
- Daily-cap neighbors contribute 98 strict-like rows.
- No-health ablations contribute 50 strict-like rows.

The bounded return-permutation control is a caution:

- 60 return-permutation rows were evaluated for the top 10 parents.
- 18 are strict-like.
- The strict-like permutation rows are motif-return permutations and still use
  the canonical motif component.

This means the WPR106-203 strict pocket is not just an exact parameter typo,
but it is still concentrated around one post-selected motif component, and a
small permutation control does not fully prove that exact motif timing is the
source of the edge.

## May Benchmark

May 2026 stayed benchmark-only. Across all fixed controls:

- 2,771 positive May rows.
- 115 negative May rows.
- 36 flat May rows.
- Median May return: +0.018368.
- Active mean May return: +0.017089.

Median May by major control family:

- Base replay: +0.018368.
- Source-only: +0.023420.
- Motif swaps: +0.013014.

The higher source-only May median does not rescue source-only controls because
they fail the pre-May strict-like activity/stability profile.

## Interpretation

WPR106-204 keeps WPR106-203 alive as a research-only diagnostic component
portfolio, but it does not make it candidate-ready. The audit supports genuine
two-component complementarity versus source-only rows, because source-only
controls produce zero strict-like rows. It also supports some parameter and
opening-component robustness as long as the canonical motif component remains.

The blocker is motif concentration: every strict-like row depends on
`motif202-00860ffdbf2eb058`, and no alternate motif component reaches the
strict-like profile. The bounded return-permutation control also leaves timing
specificity unproven.

The next useful work is a canonical-motif falsification packet: broader
negative controls, motif-source reconstruction, timing shifts, shuffled-label
or shuffled-return controls, transparent baselines, and independent
candidate-pack gate materialization for the canonical-motif neighborhood.

No WPR106-204 row is candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready.

## Artifacts

- `data/research/wpr106_204_wpr203_component_ablation_control_audit/controls/control_universe.parquet`
- `data/research/wpr106_204_wpr203_component_ablation_control_audit/pre_may/control_pre_may_metrics.parquet`
- `data/research/wpr106_204_wpr203_component_ablation_control_audit/pre_may/control_pre_may_monthly_returns.parquet`
- `data/research/wpr106_204_wpr203_component_ablation_control_audit/may_benchmark/control_may_benchmark_metrics.parquet`
- `data/research/wpr106_204_wpr203_component_ablation_control_audit/may_benchmark/control_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_204_wpr203_component_ablation_control_audit/control_pre_may_may_comparison.parquet`
- `data/research/wpr106_204_wpr203_component_ablation_control_audit/control_type_summary.parquet`
- `data/research/wpr106_204_wpr203_component_ablation_control_audit/strict_like_motif_component_counts.parquet`
- `data/research/wpr106_204_wpr203_component_ablation_control_audit/strict_like_opening_component_counts.parquet`
- `data/research/wpr106_204_wpr203_component_ablation_control_audit/wpr106_204_wpr203_component_ablation_control_audit_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, `control_only` where
applicable, and `promotion_ready: false`. No candidate pack, paper/live
artifact, order path, sizing change, runtime-mode change, live configuration
write, CUDA speedup claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_204_wpr203_component_ablation_control_audit\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
