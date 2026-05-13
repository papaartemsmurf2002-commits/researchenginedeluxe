# WPR102-01 Branch Completion Implementation

Owner: Codex Research Agent
Stage: R102 contract and boundary gap closure
Status: closed
Created: 2026-05-13

## Goal

Close the actionable issues found in the R101 branch completion review without
weakening the research-only boundary. This packet implements source provider
capability validation, direct CLI output-root allowlisting, import-boundary
coverage expansion, first capability-aware readiness gates, packaging identity
cleanup, and durable-data completion scaffolding/evidence where feasible in this
branch.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `docs/contracts/**`
- `README.md`
- `pyproject.toml`
- `configs/research/**`
- `configs/discovery/**`
- `data/research/fixtures/**`
- `data/research/historical_cycles/**`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/data/**`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/research_artifacts/**`
- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/promotion/**`
- `tests/contracts/**`
- `tests/historical/**`
- `tests/live/**`
- `tests/research_artifacts/**`
- `tests/research_discovery/**`
- `tests/tradingbotsuite/**`

## Constraints

- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Do not place orders, change live runtime mode, write live configuration, or
  import order-placement adapters into research modules.
- Do not overwrite checked generated artifacts unless the change is deliberate
  and recorded in the stage report.
- Treat durable-data work as candidate evidence only if source capability,
  validation floors, source health, and gate evidence pass. Diagnostic fixtures
  must stay non-promotable.
- Preserve existing uncommitted user/stage work and do not revert unrelated
  changes.

## Planned implementation

1. Add top-level fixture source provider-capability validation and tests.
2. Route direct research CLI `--output-dir` handling through a shared
   research-output-root resolver and add boundary tests.
3. Expand import-boundary tests to live-adjacent research packages.
4. Feed provider capability metadata into research-cycle/candidate/discovery
   readiness reasons so diagnostic/default-false capabilities block candidate
   readiness explicitly.
5. Resolve the package identity weak point or document a deliberate
   compatibility decision if a distribution rename would be unsafe in this
   dirty branch state.
6. Reassess durable BTC/ETH evidence. If full durable fixture generation cannot
   be completed safely in one packet, add executable scaffolding and gate
   evidence that keeps the branch honest and records the remaining data blocker.

## Validation target

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts tests/live tests/historical tests/research_artifacts tests/research_discovery tests/tradingbotsuite -q
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
```

## Exit evidence

Implemented:

- Top-level fixture source provider-capability validation now rejects tampered
  source capability metadata before it can become provenance evidence.
- Direct research CLI `--output-dir` handling now uses the shared
  research-output-root allowlist resolver; input/source paths remain ordinary
  input paths.
- Import-boundary contract coverage now includes `research_cycle`,
  `optimization`, and `research_artifacts`.
- Provider capability and durable public-archive readiness are first-class
  inputs to research-cycle gates, discovery validation floors, bridge evidence,
  and research candidate-pack source evidence.
- The active project distribution name is now `tradingbotsuite`, while legacy
  console/package compatibility is retained.
- Durable BTC/ETH multi-window archive evidence was not fabricated. The
  remaining data-acquisition blocker stays open as `ISSUE-R101-003` and should
  be handled by R103.

Validation:

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
