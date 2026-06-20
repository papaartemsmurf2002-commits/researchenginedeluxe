# Stage R106 WPR106-205 Canonical Motif Timing Falsification Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-205 tests the canonical motif dependency left by WPR106-204. WPR106-204
showed that every strict-like WPR106-203 control depends on canonical motif
component `motif202-00860ffdbf2eb058`. This packet asks whether the apparent
stability is specific to that motif component's exact trade timing and return
sequence.

The controls fix the WPR106-203 selected parents and WPR106-201/WPR106-202
component trade artifacts. Control construction and pre-May evaluation use
only 2024-01-01 through 2026-04-30. May 2026 is benchmark-only after the fixed
control universe exists.

These are artifact-level falsification controls. They perturb stored
trade-level timestamps and returns; they do not recompute fresh market labels
from shifted entries.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_205_canonical_motif_timing_falsification/scripts/run_wpr106_205_canonical_motif_timing_falsification.py`

The runner imports WPR106-203 replay helpers so costs, same-symbol no-overlap
blocking, daily caps, health gates, and monthly diagnostics match the
WPR106-203 portfolio accounting.

Control families:

- base replay;
- motif return shuffles over all 100 selected parents;
- motif return rotations;
- motif timestamp shifts of +/-8, +/-24, and +/-72 hours;
- motif zero-return baseline;
- motif global-mean and month-mean return baselines;
- motif sign-flip baseline;
- opening-return shuffle contrast controls.

Runtime was 122.13 seconds. CUDA was not used and no speedup claim was made.

## Results

WPR106-205 evaluated 2,200 fixed controls:

- 2,182 positive pre-May rows and 18 negative rows.
- Median pre-May return: +0.802069.
- Median active months: 25.
- Median losing months: 4.
- 1,324 annual-target rows.
- 1,210 strict-like rows.

The WPR106-203 base replay reproduced:

- 100/100 positive pre-May rows.
- 100/100 strict-like rows.
- Median pre-May return: +0.812433.
- Median active months: 25.
- Median losing months: 4.

The falsification controls preserve too much of the apparent stability:

- Motif return shuffle: 310/500 strict-like rows, median pre-May +0.808987,
  median losing months 3.
- Motif return rotation: 152/300 strict-like rows, median pre-May +0.827243,
  median losing months 5.
- Motif timestamp shift: 440/600 strict-like rows, median pre-May +0.812137,
  median losing months 4.
- Motif global/month mean return baselines: 200/200 strict-like rows, median
  pre-May +0.807909, median losing months 2.5.

Controls that remove or invert motif return contribution do weaken the pocket:

- Motif zero-return baseline: 8/100 strict-like rows, median pre-May
  +0.491938, median active months 23.
- Motif sign-flip baseline: 0/100 strict-like rows, 18 negative rows, median
  pre-May +0.133596, median active months 19, median losing months 7.
- Opening-return shuffles: 0/300 strict-like rows, median losing months 6.5.

This means returns from the canonical motif component matter, but exact motif
trade timing and exact return sequence are not proven by artifact-level
evidence. Constant positive motif contribution is enough to preserve all
strict-like parent rows, which is a serious falsification of timing-specific
edge claims.

## May Benchmark

May 2026 stayed benchmark-only. Across all fixed controls:

- 1,964 positive May rows.
- 78 negative May rows.
- 158 flat May rows.
- Median May return: +0.018368.
- Active mean May return: +0.015858.

Base replay median May was +0.018368. Non-base controls had median May
+0.018148. The May benchmark therefore does not rescue the lead, because the
pre-May falsification controls show that artifact-level perturbations can
preserve the same stability profile.

## Interpretation

WPR106-205 rejects the WPR106-203/WPR106-204 canonical-motif portfolio as a
candidate-ready or portfolio-ready lead. The result remains useful as a
research-only diagnostic: opening components plus positive canonical motif
return contribution can construct stable-looking monthly portfolios. But the
strict-like behavior is too easy to reproduce with shuffled, shifted, rotated,
and constant motif-return controls.

The canonical motif neighborhood should not be promoted without fresh market
recomputation from perturbed entries, transparent baselines, source
reconstruction, broader negative controls, and candidate-pack gate
materialization. The practical next step is to move back to broader
2024-forward search or rebuild the motif source from first principles with
proper label/timing controls rather than defending this artifact-level
portfolio pocket.

No WPR106-205 row is candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready.

## Artifacts

- `data/research/wpr106_205_canonical_motif_timing_falsification/controls/control_universe.parquet`
- `data/research/wpr106_205_canonical_motif_timing_falsification/pre_may/control_pre_may_metrics.parquet`
- `data/research/wpr106_205_canonical_motif_timing_falsification/pre_may/control_pre_may_monthly_returns.parquet`
- `data/research/wpr106_205_canonical_motif_timing_falsification/may_benchmark/control_may_benchmark_metrics.parquet`
- `data/research/wpr106_205_canonical_motif_timing_falsification/may_benchmark/control_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_205_canonical_motif_timing_falsification/control_pre_may_may_comparison.parquet`
- `data/research/wpr106_205_canonical_motif_timing_falsification/control_type_summary.parquet`
- `data/research/wpr106_205_canonical_motif_timing_falsification/strict_like_control_rows.parquet`
- `data/research/wpr106_205_canonical_motif_timing_falsification/wpr106_205_canonical_motif_timing_falsification_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, `control_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_205_canonical_motif_timing_falsification\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
