# V2 Validation Contract

Status: v2 Phase 20 deep-validation and final hard-test governance contract
Audit IDs: `V2-AUD-VAL-001`, `V2-AUD-FINAL-001`, `V2-AUD-VAL-002`

## Purpose

Validation prevents leakage, overfit, and weak evidence claims.

## Initial Schema Names

- `ValidationConfig`
- `LockboxPolicy`
- `WalkForwardConfig`
- `WalkForwardFold`
- `FoldMetric`
- `FoldStabilitySummary`
- `TrialResult`
- `SweepCompletenessReport`
- `TrialFamilyReport`
- `DeepValidationScorecard`
- `DeepValidationManifest`
- `Pre2024FallbackDiagnostic`
- `FinalHardTestSlot`
- `FinalSurvivorReport`

## Required Rules

- Start date >= 2024-01-01.
- Usable months >= 6.
- Lockbox excluded until frozen final hard-test review.
- The dynamic lockbox is the latest complete UTC calendar month as of the
  request evaluation date. With the default one-month policy and an as-of date
  inside June 2026, the lockbox is `[2026-05-01T00:00:00Z,
  2026-06-01T00:00:00Z)`.
- Backtest-data warmup rows do not count toward usable reported months.
- Walk-forward validation, purge/embargo where labels overlap, multiple-testing
  accounting, concentration checks, ablations, negative controls, stability,
  and cost stress are recorded where relevant.
- Walk-forward folds are strictly time ordered, with train rows before
  validation rows and explicit purge/embargo row gaps.
- Sweep validation requires complete trial logging for every expected trial.
- Trial-family diagnostics group by experiment/family, report trial count,
  best-vs-median behavior, fold stability, and a PBO/CSCV-style diagnostic
  when enough trials/folds exist.
- Post-lockbox parameter tuning is rejected.
- Leaderboard evidence includes trial count and fold stability where ledger
  fold metrics are available.
- Deep validation workflow permits only one active serious lead at a time.
- Deep validation manifests must record the full required scorecard, including
  modern 2024+ history, six-month minimum, lockbox exclusion, as-of universe,
  walk-forward validation, negative controls, ablations, exit lab, cost stress,
  concentration, stability, robustness, diminishing returns, and failure-mode
  checks.
- Pre-2024 fallback evidence is diagnostic only, requires the
  `diagnostic_fallback_only` label, and cannot substitute for mandatory 2024+
  evidence.
- Final hard-test workflow has at most 3 active slots.
- Final hard-test slots require frozen strategy spec hash, params hash, data
  manifest hash, universe snapshot ID, cost model hash, and final-phase
  manifest ID before lockbox access is represented.
- Parameter edits after lockbox access are forbidden.
- Final survivor reports must carry a non-live disclaimer and must not imply
  paper/live/trade readiness.

## Forbidden

- Tuning on lockbox results.
- Treating final hard-test survivor as live/paper/trade ready.
- Treating sandbox/current-universe reads as accepted validation evidence.
- Counting warmup data as reported PnL evidence.
- Ranking incomplete sweeps as if every trial were logged.
- Treating a best trial from a large weak family as stable without warnings.
- More than one active serious-lead deep validation.
- More than three active final hard-test slots.
- Final hard-test slots without frozen strategy, params, data, universe, cost,
  and final-phase manifest evidence.
- Promotion-ready, candidate-pack, sizing, order, runtime, or paper/live claims
  from deep-validation or final-survivor governance records.
