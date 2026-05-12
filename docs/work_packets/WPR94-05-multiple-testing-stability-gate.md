# WPR94-05 Multiple-Testing And Stability Gate

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Keep sparse large-grid discovery winners from being overinterpreted. Discovery
leads must carry explicit multiple-testing and stability gate evidence before
the discovery bridge can mark them eligible for the existing candidate-pack
validator.

## Allowed Paths

- `docs/work_packets/WPR94-05-multiple-testing-stability-gate.md`
- `docs/stage_reports/STAGE_R94_MULTIPLE_TESTING_STABILITY_GATE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/research_discovery/multiple_testing.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `src/tradingbotsuite/research_discovery/__init__.py`
- `src/tradingbotsuite/main.py`
- `configs/discovery/discovery_candidate_pack_bridge_v4.json`
- `tests/research_discovery/test_multiple_testing.py`
- `tests/research_discovery/test_candidate_pack_bridge.py`

## Scope

- Add a research-only discovery multiple-testing/stability artifact with:
  - declared search space
  - sampled fraction
  - effective trial count
  - best-candidate concentration
  - stability-neighborhood size
  - split/window concentration
  - side concentration
  - latest-window-only penalty
- Add candidate-level gate rows and explicit blocker reasons.
- Require the discovery bridge to consume passed multiple-testing/stability
  gate rows before eligibility.
- Keep all candidate wording as leads unless gates are complete.

## Non-Goals

- No candidate-pack writing or promotion readiness.
- No optimizer algorithm rewrite.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, or sizing logic changes.
- No UI modernization.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_multiple_testing.py tests\research_discovery\test_candidate_pack_bridge.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

Passed on 2026-05-12:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_multiple_testing.py tests\research_discovery\test_candidate_pack_bridge.py -q
# 27 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 131 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with line-ending warnings only
```

## Exit Evidence

- Added a discovery-side multiple-testing/stability artifact with candidate
  gate rows.
- Artifact construction can derive declared search space and sampled fraction
  from a discovery run manifest, resolved spec, ledgers, and trial records.
- Candidate gate rows carry `record_sha256` and source discovery manifest hash.
- The bridge now requires source-matched multiple-testing/stability evidence
  and blocks missing manifests, missing gate rows, candidate hash mismatches,
  latest-window-only evidence, concentrated winners, unstable neighborhoods,
  split/window concentration, and side concentration.
- Bridge outputs remain audit-only and candidate-pack writing remains disabled.
