# WPR73-01 Discovery Run Manager

Stage: R73 discovery run manager foundation
Owner: Codex Research Agent
Status: closed
Created: 2026-05-07

## Goal

Implement the V4 discovery run manager foundation before any HMM/KNN math,
feature-pack expansion, UI work, or candidate-pack bridge. The manager must
parse bounded discovery specs, create isolated research-only output trees,
write reproducible run manifests and resolved specs, maintain resumable run
state, write immutable completed-trial records, and produce atomic snapshots
and candidate ledgers.

## Allowed Paths

```text
src/tradingbotsuite/research_discovery/**
configs/discovery/**
tests/research_discovery/**
tests/contracts/test_import_boundaries.py
docs/work_packets/WPR73-01-discovery-run-manager.md
docs/stage_reports/STAGE_R73_DISCOVERY_RUN_MANAGER_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Research-only foundation only.
- Do not implement HMM materialization, KNN search, feature math, optimizer
  changes, operator UI changes, live behavior, promotion behavior, sizing, or
  order placement.
- Keep all generated artifacts `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Discovery output paths must stay isolated under the configured research
  output root.
- Completed trial records are immutable on resume.
- Completed runs must refuse overwrite unless a later packet defines an
  explicit archival/extension policy.

## Required Output

- `src/tradingbotsuite/research_discovery/` package with spec, manifest, state,
  snapshot, and runner modules.
- Quick smoke config in `configs/discovery/`.
- Focused tests for spec validation, path safety, state immutability, atomic
  snapshots, resume behavior, completed-run overwrite refusal, and placeholder
  ledger outputs.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

## Close Evidence

- Added `src/tradingbotsuite/research_discovery/` with discovery spec parsing,
  output path resolution under the configured research output root, run
  manifests, resolved specs, resumable run state, immutable trial records,
  atomic snapshots, and placeholder candidate ledgers.
- Added `configs/discovery/quick_smoke_btcusdt_v4.json`.
- Added focused discovery tests for spec/path validation, state immutability,
  snapshot atomicity, resume determinism, completed-run overwrite refusal, and
  placeholder ledger outputs.
- Added import-boundary coverage for the new discovery package.
- Validation passed on 2026-05-07 with compile, full contracts, focused
  discovery tests, and `git diff --check`.
