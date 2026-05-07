# WPR74-01 Discovery Feature-Column Sets

Stage: R74 core discovery feature-pack foundation
Owner: Codex Research Agent
Status: closed
Created: 2026-05-07

## Goal

Add the first bounded V4 discovery feature-column set contract on top of
existing registered feature manifests. This packet defines KNN study column
sets as research variables without adding new feature math, HMM materialization,
KNN search, optimizer behavior, UI behavior, or candidate-pack bridge behavior.

## Allowed Paths

```text
src/tradingbotsuite/research_discovery/**
configs/discovery/**
tests/research_discovery/**
tests/contracts/test_import_boundaries.py
docs/work_packets/WPR74-01-discovery-feature-column-sets.md
docs/stage_reports/STAGE_R74_DISCOVERY_FEATURE_COLUMN_SETS_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Reuse existing registered feature-set manifests and columns.
- Keep KNN feature-column sets separate from persistent `features_*` manifests.
- WT/WT3D must be optional and require a no-WT comparator.
- Include at least one first-class non-WT alternative.
- Keep enabled first-wave sets bounded to a conservative maximum dimension.
- Do not add feature formulas, scalers, HMM/KNN fitting, live behavior,
  promotion behavior, sizing, or order placement.
- Preserve research-only, observe-only, promotion-ready false boundaries.

## Required Output

- Discovery feature-column set dataclasses, loader, validation, and manifest
  hash support.
- A checked `configs/discovery/feature_column_sets_v4.json` manifest with
  baseline, WT3D comparator, non-WT alternative, and one-at-a-time context
  additions or disabled placeholders for unavailable future math.
- Discovery run specs/manifests should record the configured feature-column set
  manifest and selected set IDs.
- Focused tests for validation, comparator requirements, unknown columns,
  bounded dimensions, and run-manifest propagation.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

## Close Evidence

- Added discovery-side feature-column set manifest support under
  `tradingbotsuite.research_discovery.feature_sets`.
- Added `configs/discovery/feature_column_sets_v4.json` with enabled bounded
  no-WT, WT3D, alternative non-WT, perp-addition, and liquidation-proxy smoke
  column sets, plus disabled placeholders for future NTRI/entropy/autocorr/HVR
  math.
- Wired discovery specs and run manifests to record feature-column set manifest
  paths, selected set IDs, hashes, WT/non-WT evidence, and research-only flags.
- Added focused validation for unknown columns, excessive dimensions, WT
  comparator requirements, disabled selections, hash mismatch, checked config
  validity, and run-manifest propagation.
- Validation passed on 2026-05-07 with compile, full contracts, focused
  discovery tests, and `git diff --check`.
