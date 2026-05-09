# WPR88-01 Discovery HMM Label Cache

## Objective

Reduce deep discovery runtime by caching repeated label/split preparation and
reusing split-safe HMM regime materializations across label horizons, while
preserving horizon-specific labels for KNN study and trial metrics.

## Fit Check

This fits the current discovery architecture because it stays inside the
research-only discovery runner, preserves HMM/KNN artifact contracts, keeps
train-only split safety, and does not introduce new dependencies, process
pools, GPU paths, live behavior, or candidate-pack gate changes.

## Allowed paths

- `src/tradingbotsuite/research_discovery/runner.py`
- `tests/research_discovery/test_discovery_runner.py`
- `docs/work_packets/WPR88-01-discovery-hmm-label-cache.md`
- `docs/stage_reports/STAGE_R88_DISCOVERY_HMM_LABEL_CACHE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Planned changes

- Cache per feature-column-set and per label-horizon labeled frames plus splits.
- Remove label horizon from the HMM cache key because HMM fitting depends on
  features, HMM settings, and split settings, not future-return labels.
- When an HMM cache entry is reused for another horizon, graft the cached HMM
  posterior/router columns onto the current horizon-labeled frame so KNN still
  sees the correct `label_up` and `label_return`.
- Add trial payload telemetry for label/split cache hits and HMM cache hits.
- Add regression coverage proving HMM is computed once across two horizons and
  KNN receives horizon-specific labels in both trials.

## Exit criteria

- Focused discovery runner tests pass.
- Full discovery test suite passes.
- Compile and contract baseline pass.
- Stage report records implementation and validation.
