# Stage R94 Validation Floors And Blocker Registry Report

Date: 2026-05-12
Owner: Codex Research Agent

## Summary

WPR94-06 implemented a discovery-side validation-floor artifact and canonical
blocker registry. The discovery bridge now requires source-matched,
record-hash-matched validation-floor evidence before marking any lead eligible
for the existing historical candidate-pack validator.

## Changes

- Added `src/tradingbotsuite/research_discovery/validation_floors.py`.
- Added screen-worthy and candidate-ready floor defaults:
  - independent event counts
  - overlap ceilings
  - split pass ratios
  - side concentration ceilings
  - cost-stress survival floors
  - stability-neighborhood floors
  - comparator, no-regime baseline, exit, filter, and feature-ablation gates
- Added maturity labels: `diagnostic`, `screen-worthy`, `candidate-ready`.
- Added a standard blocker registry and registry hash in validation manifests.
- Added experiment-budget ledger metadata to validation manifests and bridge
  manifests.
- Updated the bridge CLI/config to accept `--validation-floors-manifest`.

## Boundary

All new outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

No live trading behavior, live configuration, order placement, runtime mode, or
sizing logic changed. The bridge still writes eligibility evidence only and
does not write candidate packs.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_validation_floors.py tests\research_discovery\test_candidate_pack_bridge.py -q
# 32 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 140 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with line-ending warnings only
```

## Next

Continue the roadmap order with durable BTC/ETH public archive fixture
readiness.
