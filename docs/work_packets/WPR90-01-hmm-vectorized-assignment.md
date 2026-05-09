# WPR90-01 HMM Vectorized Assignment

## Objective

Reduce HMM materialization overhead by replacing per-row/per-state pandas
posterior assignment with vectorized column assignment, preserving the emitted
posterior/router columns and split-safety semantics.

## Fit Check

This fits the current research-discovery architecture because it stays inside
the HMM materializer, does not change model fitting, split construction,
features, labels, artifacts, candidate gates, promotion readiness, or live
behavior.

## Allowed paths

- `src/tradingbotsuite/research_discovery/hmm_materialization.py`
- `tests/research_discovery/test_hmm_materialization.py`
- `docs/work_packets/WPR90-01-hmm-vectorized-assignment.md`
- `docs/stage_reports/STAGE_R90_HMM_VECTORIZED_ASSIGNMENT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Planned changes

- Assign posterior probability columns for all validation positions in one
  operation per state.
- Assign top regime, probability, entropy, flip, no-trade, model, feature-pack,
  split, and source-row fields with vectorized arrays.
- Add manifest telemetry for the assignment engine.
- Add focused regression coverage comparing vectorized assignment with the
  prior scalar assignment behavior on deterministic posterior inputs.

## Exit criteria

- Focused HMM tests pass.
- Full discovery tests pass.
- Compile and contract baseline pass.
- Stage report records implementation and validation.
