# WPR86-01 Discovery Runtime Optimization

## Objective

Reduce real discovery wall time and artifact overhead without weakening
research-only evidence, split safety, resume behavior, or live-boundary guards.

## Fit Check

The prior runtime estimate showed current deep discovery is serial per trial and
writes full HMM/KNN artifacts for every trial. The codebase can safely benefit
from bounded threading, in-run HMM reuse, and compact rejected-trial artifacts
because these changes stay inside the discovery package and do not alter live,
strategy, backtest, or candidate-pack ownership.

GPU acceleration and process-pool execution remain useful but need a later
packet because they require dependency/runtime decisions and more complicated
artifact/state merge handling on Windows.

## Allowed paths

- `src/tradingbotsuite/research_discovery/**`
- `configs/discovery/**`
- `tests/research_discovery/**`
- `docs/work_packets/WPR86-01-discovery-runtime-optimization.md`
- `docs/stage_reports/STAGE_R86_DISCOVERY_RUNTIME_OPTIMIZATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Planned changes

- Add discovery execution controls for max worker threads and full-artifact
  persistence policy.
- Evaluate pending trials in bounded worker-thread batches while the parent
  process remains the only writer of immutable trial records and run state.
- Reuse HMM materialization results within a run when trials share the same
  feature set, label horizon, split, and HMM settings.
- Allow standard/deep operator presets to persist full HMM/KNN/accounting
  artifacts only for interesting candidates, while blocked trials retain compact
  metrics and blocker evidence.
- Add feature preflight so empty/all-NaN/constant feature sets block quickly
  instead of wasting HMM/KNN compute.

## Exit criteria

- Serial behavior remains the default for old specs.
- New standard/deep configs opt into bounded workers and compact blocked
  artifacts.
- Real discovery tests cover threaded execution and compact blocked trials.
- Focused discovery tests, compile, and contract validation pass.
