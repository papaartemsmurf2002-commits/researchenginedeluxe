# WPR78-01 Perp Context And Filter Ablation Matrix

Stage: R78 perp context and filter ablation matrix
Owner: Codex Research Agent
Status: closed
Created: 2026-05-08

## Goal

Add a discovery-side ablation matrix foundation that tracks no-perp,
perp-feature, perp-filter, perp-strategy, perp-exit, and feature-combination
comparisons without promoting filters by default. The packet should turn
available discovery or historical-cycle evidence into explicit pass/fail/pending
rows and keep missing evidence truthful.

## Allowed Paths

```text
src/tradingbotsuite/research_discovery/**
configs/discovery/**
tests/research_discovery/**
docs/work_packets/WPR78-01-perp-context-filter-ablation-matrix.md
docs/stage_reports/STAGE_R78_PERP_CONTEXT_FILTER_ABLATION_MATRIX_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Do not alter checked BTCUSDT/ETHUSDT historical-cycle configs or checked
  historical-cycle artifacts.
- Do not make any perp, microstructure, HMM, KNN, or WT/WT3D filter a default
  winner without comparator evidence.
- Keep all outputs `research_only`, `observe_only`, and `promotion_ready:
  false`.
- Do not add live execution, promotion behavior, candidate-pack bridging,
  operator UI behavior, sizing, or order placement.

## Required Output

- Discovery-side ablation matrix dataclasses and functions.
- Config under `configs/discovery/`.
- Artifact writer for matrix rows and manifest evidence.
- Focused tests for pending evidence, pass/fail comparator decisions,
  feature-combination stability diagnostics, guardrail flags, and artifact
  boundary flags.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
```

Run contracts before closing if shared contracts change.

## Close Evidence

- Added `tradingbotsuite.research_discovery.ablation_matrix` with a
  research-only perp/filter ablation matrix evaluator.
- Added checked discovery config
  `configs/discovery/perp_filter_ablation_matrix_v4.json`.
- Matrix rows now compare no-perp references, perp feature additions,
  HMM/KNN/perp filters, perp strategies, and perp-aware exits without making
  any filter default unless it beats its comparator after costs and floors.
- Added feature-combination stability diagnostics for no-WT baselines, WT3D,
  non-WT alternatives, perp-feature smoke sets, and future pending evidence.
- Added artifact writer for `perp_filter_ablation_manifest.json`,
  `perp_filter_ablation_matrix.parquet`, and
  `feature_combination_stability.parquet`.
- Added focused tests for pass/fail/pending matrix outcomes, default-filter
  guardrails, WT3D comparator diagnostics, artifact flags, and config
  validation.
- Validation passed on 2026-05-08 with compile and discovery tests.
