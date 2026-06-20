# WPR106-200 Strict Cross-Family Source Ablation Control

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Objective

Audit the WPR106-199 strict-tier cross-family diagnostic before treating it as
a lead. WPR106-199 found a small pre-May strict pocket that often combines
WPR106-196 anchored/opening-range behavior, WPR106-197 opening-range short
controls, and one WPR106-190 or WPR106-191 KNN source. This packet tests
whether that pocket has real source complementarity or whether the apparent
improvement is mostly source concentration in the opening-range family.

## Data And Selection Policy

- Base portfolios are the WPR106-199 strict selected rows, which were selected
  using only 2024-01-01 through 2026-04-30 UTC evidence.
- Control and ablation variants are deterministic transforms of those strict
  rows: base, source-only, leave-one-source-out, opening-only, no-KNN,
  KNN-only, no-WPR106-196, no-WPR106-197, no-WPR106-198, and no-non-opening
  variants when applicable.
- Variant construction, ranking, grouping, and interpretation use only pre-May
  source IDs and pre-May evidence. May 2026 is benchmark-only after the fixed
  variant set exists.
- Existing source trades already include packet-local costs. This packet keeps
  WPR106-199 equal-member weighting, same-symbol overlap blocking, and
  portfolio-level daily caps.
- All outputs are `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-200-strict-cross-family-source-ablation-control.md`
- `docs/stage_reports/STAGE_R106_STRICT_CROSS_FAMILY_SOURCE_ABLATION_CONTROL_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered
- `data/research/wpr106_200_strict_cross_family_source_ablation_control/**`

No source package, config, fixture, live, runtime, order-placement, sizing, or
promotion path is in scope.

## Planned Work

1. Create a packet-local runner that imports WPR106-199 helpers and reads
   WPR106-199 strict selected portfolios.
2. Rebuild WPR106-190 through WPR106-198 source trade pools with the same
   normalization used by WPR106-199.
3. Generate deterministic ablation/control variants for each strict WPR106-199
   row without consulting May 2026.
4. Replay every variant on pre-May evidence and May 2026 benchmark using the
   same overlap, equal-member weighting, daily cap, cost-stress, monthly,
   drawdown, and Sortino accounting.
5. Write variant metrics, monthly/daily/trade artifacts, paired base-vs-control
   comparisons, grouped summaries, and a JSON summary.
6. Document whether KNN/non-opening sources improve pre-May and May behavior
   or whether opening-range-only controls explain the strict pocket.
7. Update the stage report and ledger, then run validation.

## Research Boundary

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim. CUDA is not planned; if the runner is CPU/vectorized
only, the manifest must say so truthfully.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_200_strict_cross_family_source_ablation_control\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Exit Evidence

WPR106-200 completed the strict-tier source ablation/control audit. It fixed
the 10 WPR106-199 strict parent portfolios, generated 150 deterministic
pre-May source ablation variants, and benchmarked May only after those variants
existed.

The base WPR106-199 strict rows reproduce with pre-May median +0.653902, 10/10
positive rows, median losing months 4.5, and May median +0.006134 with 7/10
May-positive rows. KNN/non-opening sources do not explain the strict pocket:
`opening_only`, `no_non_opening`, and `no_knn` controls improve median pre-May
and median May behavior versus base. KNN-only controls have pre-May median
+0.588163 but median losing months 11 and May median 0.000000. Pair-only
controls have May median -0.030679.

The best May variant is WPR106-197 source-only:
`WPR106-197:or197-aaf5acc56f96eddc` records +0.907051 pre-May over 68 trades,
19 active months, three pre-May losing months, 100% cost-stress survival, and
+0.053605 in May over four trades. It remains diagnostic-only because it is
inactive for nine pre-May months and lacks independent source-level ablation,
transparent baselines, stability-region evidence, and candidate-pack gates.

WPR106-200 rejects the WPR106-199 strict-tier result as a cross-family KNN
complementarity lead. It preserves WPR106-196 plus WPR106-197 opening-only and
WPR106-197 source-only behavior as research-only diagnostics. No candidate
pack, paper/live artifact, order/sizing/runtime change, live config write,
CUDA speedup claim, or promotion claim exists.

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_200_strict_cross_family_source_ablation_control\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
