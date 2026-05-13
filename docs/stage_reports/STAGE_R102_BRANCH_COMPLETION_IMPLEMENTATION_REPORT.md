# Stage R102 Branch Completion Implementation Report

Date: 2026-05-13
Branch: `research/v3-experimental-engine`
Packet: `docs/work_packets/WPR102-01-branch-completion-implementation.md`

## Scope

R102 closed the actionable contract, boundary, and packaging issues from the
R101 review, while keeping durable empirical data acquisition separate. The
work stayed inside the research branch boundary: no live execution, live config
write, runtime-mode change, order placement, sizing behavior, promotion
authorization, or live artifact path was added.

## Implemented Changes

- Fixture source provider capability is now validated at the top-level source
  manifest, not only inside context-family metadata. Tampered source identity
  or durability-class payloads fail fixture validation.
- Direct research CLI commands now resolve output directories through the
  shared research output-root allowlist. The tests cover direct CLI attempts to
  write outside the configured research output root.
- Import-boundary coverage now includes `research_cycle`, `optimization`, and
  `research_artifacts`, and the boundary contract names those live-adjacent
  research roots explicitly.
- Research-cycle data-source evidence now carries fixture source capability and
  durable public-archive readiness. Candidate ranking/gate reports include the
  resulting source blockers.
- Discovery validation floors and the candidate-pack bridge now treat source
  capability and durable readiness as semantic blockers. Default-conservative
  provider capabilities do not silently pass; durable public archive readiness
  must be present and ready.
- Candidate-pack source evidence now includes provider capability, durable
  public archive readiness, source capability gate reasons, and an
  evidence-completeness check that fails when source capability gates are open.
- The active distribution name is now `tradingbotsuite`. Legacy `tradingbot`
  console/package compatibility remains available for existing workflows.

## Issue Outcomes

- `ISSUE-R101-001` resolved: top-level fixture source capability is revalidated.
- `ISSUE-R101-002` resolved: direct research CLI output dirs use the allowlist
  resolver.
- `ISSUE-R101-003` remains open: durable BTC/ETH multi-window public archive or
  vendor-backed fixture acquisition is still required before candidate-ready
  empirical claims can exist.
- `ISSUE-R101-004` resolved: import-boundary tests cover the missed research
  roots.
- `ISSUE-R101-005` resolved: provider capability metadata and durable archive
  readiness are first-class gate inputs.
- `ISSUE-R101-006` resolved: package distribution identity now matches
  `tradingbotsuite`.

## Remaining Branch Completion Blocker

R102 intentionally did not fabricate durable data. The branch still needs R103
to build validated BTCUSDT/ETHUSDT multi-window fixture packs from public
archive or vendor-backed sources, with source-health evidence, gap/duplicate
checks, capability metadata, and diagnostic/latest-window separation. Until
that evidence exists, candidate packs must stay blocked or absent.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\contracts\test_import_boundaries.py tests\research_discovery\test_validation_floors.py tests\research_artifacts\test_candidate_pack.py -q
# 97 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py tests\tradingbotsuite\test_market_data_collection.py tests\tradingbotsuite\test_feature_ablation.py tests\tradingbotsuite\test_stage12_research_plan.py tests\tradingbotsuite\test_hmm_knn.py -q
# 74 passed, 2 warnings

$env:PYTHONPATH='src'; python -m pytest tests\historical tests\research_artifacts tests\research_discovery tests\live -q
# 288 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 422 passed

$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite -q
# 296 passed, 2 warnings

$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\optimization tests\features -q
# 153 passed, 1 skipped

$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py tests\research_discovery\test_validation_floors.py tests\historical\test_full_cycle_local_fixture_pack.py tests\research_discovery\test_candidate_pack_bridge.py -q
# 87 passed

$env:PYTHONPATH='src'; python -m pytest -q
# 1335 passed, 1 skipped, 92 warnings

git diff --check
# passed with line-ending warnings only
```

The full-suite warnings were existing legacy pandas FutureWarnings from
`src/tradingbot/lorentz_lc.py`, local XGBoost device fallback warnings, local
CUDA/CuPy path warnings, and one async thread warning in the operator research
job test. No warning changed the research-only boundary result.

## Boundary Statement

All new readiness behavior is research-only gate logic. R102 did not write a
candidate pack from weak data, did not mark any research artifact
`promotion_ready: true`, did not promote latest-window or free-sample data, and
did not add live order-placement imports to research packages.
