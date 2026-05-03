# Promotion Contract

Promotion is an artifact review process, not a merge.

## Minimum review state

A promotion candidate must remain rejected or shadow-only until it passes all promotion checks. Promotion review must include:

- dataset manifest hash
- feature manifest hash
- strategy version
- validation split summary
- cost, slippage, and funding assumptions
- side-separated metrics
- regime-separated metrics
- feature missingness summary
- non-promotable reasons
- operator-visible skip reasons

## Evidence floors

The candidate must document whether it meets the evidence floors from the development plan. Falling below a floor does not automatically fail research, but it blocks promotion.

## Live boundary

The live branch may load promotion artifacts only through an approved validator and initially only in shadow mode.

Stage 11 promotion candidates must:

- use `promotion_candidate_manifest_version`;
- set `research_only: true`, `observe_only: true`, `promotion_ready: false`, and `shadow_only: true`;
- declare `live_signal_input: false`, `position_sizing_input: false`, `live_execution_input: false`, `operator_control_input: false`, and `runtime_control_input: false` when those fields are present;
- include dataset, feature, strategy, split, side, regime, cost, missingness, and operator-visible skip-reason evidence;
- pass the development-plan evidence floors before shadow review is accepted.

Shadow loading is diagnostic only. It may compare live feature availability, spread/basis/depth assumptions, timing drift, feature drift, calibration drift, and skip reasons, but it must not create execution intents, change runtime mode, or enable live order placement.

When a configured artifact manifest is a Stage 11 promotion candidate, runtime startup may attach the shadow loader report to engine state only in `shadow` mode. The candidate must not instantiate an acceptance scorer, size positions, alter runtime mode, or become an execution input.
