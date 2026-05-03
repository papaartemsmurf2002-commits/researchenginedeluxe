# Stage 12 Completion Limitations

Date: 2026-05-03
Branch: `research/v3-experimental-engine`

Stage 12 cannot be truthfully marked as empirically complete in this working copy.

## What is complete

- Every Stage 12 substage now has reproducible manifest/spec generation.
- Hypotheses are classified as accepted, rejected, blocked, or pending evidence.
- Acceptance is blocked unless OOS expectancy, stress gates, walk-forward splits, split-concentration, and side-separated outcomes pass.
- In-sample-only results are explicitly rejected.
- The new Stage 12 research-planning command is rejected in live mode.

## What is not complete

- No new real OOS/stress experiment evidence was supplied or generated for 12.2 through 12.7.
- Portfolio allocation tracks are blocked until single-strategy evidence passes.
- ETH and multi-asset expansion remains Phase 2 and needs ETH data inventory, provider manifests, feature-quality reports, cost/funding assumptions, independent ETH backtests, BTC-to-ETH spillover tests, and BTC-only artifact rejection evidence.
- XGBoost/LightGBM work remains blocked unless those dependencies are explicitly accepted for the environment.
- No Stage 12 hypothesis is promotion-ready from these planning artifacts.

## Required resolution

To fully complete empirical Stage 12, run the generated experiment specs against validated datasets and attach evidence manifests that satisfy each track's OOS/stress gates. Until then, Stage 12 is complete only as a reproducible research-planning and rejection-gate implementation.
