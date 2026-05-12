# WPR94-03 Mandatory Exit-Lab Gate

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Require discovery leads to carry completed exit-lab evidence before the
discovery candidate-pack bridge can mark them eligible for the existing
candidate-pack validator. Entry-label wins must remain discovery leads until
an executable exit hypothesis beats the fixed-holding reference with auditable
evidence.

## Allowed Paths

- `docs/work_packets/WPR94-03-mandatory-exit-lab-gate.md`
- `docs/stage_reports/STAGE_R94_MANDATORY_EXIT_LAB_GATE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/research_discovery/exit_lab.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `src/tradingbotsuite/research_discovery/__init__.py`
- `src/tradingbotsuite/main.py`
- `configs/discovery/discovery_exit_lab_v4.json`
- `configs/discovery/discovery_candidate_pack_bridge_v4.json`
- `tests/research_discovery/test_exit_lab.py`
- `tests/research_discovery/test_candidate_pack_bridge.py`

## Scope

- Extend discovery exit-lab artifacts with candidate-tied gate evidence:
  - `exit_lab_status`
  - `exit_lab_best_family`
  - fixed-holding comparator delta
  - cost-stress behavior
  - entry-lead evidence hash
  - explicit reason when no exit improves executable expectancy
- Add candidate bridge requirements:
  - exit-lab evidence is present and complete
  - the evidence hash matches the current discovery lead
  - the best exit family is not `fixed_holding_only`
  - the candidate keeps existing historical-cycle gate evidence
- Add focused tests for pass, missing exit lab, hash mismatch, fixed-holding
  only, and no-improvement blocker paths.
- Preserve research-only, observe-only, no-promotion boundaries.

## Non-Goals

- No new exit execution model beyond the existing discovery exit-lab
  comparisons.
- No candidate-pack writing or promotion readiness.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, or sizing logic changes.
- No broad UI modernization.
- No multiple-testing/stability gate changes; those remain later WPR94 work.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_exit_lab.py tests\research_discovery\test_candidate_pack_bridge.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

Passed on 2026-05-12:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_exit_lab.py tests\research_discovery\test_candidate_pack_bridge.py -q
# 28 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 102 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with line-ending warnings only
```

## Exit Evidence

- Discovery exit-lab artifacts now include candidate-tied gate rows with
  `exit_lab_status`, `exit_lab_gate_status`, `exit_lab_best_family`, fixed
  holding deltas, cost-stress status, and entry-lead evidence hashes.
- The bridge now requires an exit-lab manifest and blocks missing, tampered,
  hash-mismatched, fixed-holding-only, or no-improvement exit evidence before
  considering historical-cycle candidate-gate eligibility.
- The existing historical-cycle gate remains mandatory after an exit-lab pass.
- Bridge artifacts remain audit-only with `candidate_pack_written: false`,
  `candidate_pack_paths: []`, and `promotion_ready: false`.
