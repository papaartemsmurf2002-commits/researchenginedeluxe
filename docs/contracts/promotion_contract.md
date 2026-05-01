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
