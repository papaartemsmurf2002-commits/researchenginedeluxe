# WPR94-06 Validation Floors And Blocker Registry

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Make the roadmap validation floors executable at the discovery bridge boundary
and expose canonical blocker codes instead of prose-only warnings. Discovery
leads must remain diagnostic or screen-worthy until independent-event,
overlap, split, side, stability, comparator, no-regime, exit, filter, and
feature-ablation evidence is complete enough for candidate-ready handling.

## Allowed Paths

- `docs/work_packets/WPR94-06-validation-floors-blocker-registry.md`
- `docs/stage_reports/STAGE_R94_VALIDATION_FLOORS_BLOCKER_REGISTRY_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/research_discovery/validation_floors.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `src/tradingbotsuite/research_discovery/__init__.py`
- `src/tradingbotsuite/main.py`
- `configs/discovery/discovery_candidate_pack_bridge_v4.json`
- `tests/research_discovery/test_validation_floors.py`
- `tests/research_discovery/test_candidate_pack_bridge.py`

## Scope

- Add canonical validation floor defaults for screen-worthy and
  candidate-ready research maturity.
- Add a standard blocker registry covering leakage, latest-window, depth,
  liquidation, KNN overlap, baseline, and large-grid failure modes.
- Classify discovery bridge rows as `diagnostic`, `screen_worthy`, or
  `candidate_ready`.
- Require candidate-ready validation-floor evidence before the bridge can mark
  a lead eligible for the existing historical candidate-pack validator.
- Add an experiment-budget ledger summary to the bridge manifest.

## Non-Goals

- No live trading behavior, live config writes, order placement, runtime mode
  changes, or sizing logic changes.
- No candidate-pack writing or promotion readiness.
- No changes to historical candidate-pack acceptance semantics.
- No new strategy family or data provider implementation.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_validation_floors.py tests\research_discovery\test_candidate_pack_bridge.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

Passed on 2026-05-12:

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

## Exit Evidence

- Added research-only validation-floor artifacts with candidate gate rows.
- Added standard blocker registry codes for leakage, KNN overlap,
  latest-window, liquidation, depth, barrier-ordering, funding overfit,
  cross-symbol alignment, large-grid isolation, sample-reduction-only filters,
  and baseline/no-regime/exit/filter/feature validation failures.
- Candidate rows are classified as `diagnostic`, `screen-worthy`, or
  `candidate-ready`.
- The discovery bridge now requires source-matched validation-floor evidence
  before eligibility and exposes maturity, floor metrics, blocker reasons, and
  experiment-budget ledger metadata.
- Bridge outputs remain audit-only and candidate-pack writing remains disabled.
