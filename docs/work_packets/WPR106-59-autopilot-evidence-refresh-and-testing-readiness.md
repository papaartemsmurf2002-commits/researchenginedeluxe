# Work Packet: WPR106-59 Autopilot Evidence Refresh And Testing Readiness

## Goal

Finish the current R106 research-iteration wiring so the operator UI and
autopilot truthfully distinguish reused closed evidence from newly executed
work, and so candidate eligibility uses the latest same-symbol gate evidence
when available.

## Current Repo Facts

- Current branch: `main`.
- WPR106-57 and WPR106-58 are uncommitted local UI/catalog fixes in this
  working tree and must be preserved.
- The latest local autopilot run completed with zero executed helper steps
  because every required artifact was already considered complete.
- WPR106-49 generated replay-scope multiple-testing and validation-floor
  manifests, but the autopilot eligibility helper currently passes those inputs
  as `None`.
- `docs/research_knowledge` is a documentation-only hypothesis catalog, not an
  executable theory registry.

## Allowed Edit Paths

- `docs/work_packets/WPR106-59-*.md`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`
- `tests/research_discovery/test_candidate_pack_bridge.py`

## Research Boundary

- Do not start catalog rebuilds, historical cycles, exact discovery, or other
  long-running compute jobs.
- Do not change strategy math, candidate gates, generated historical evidence,
  live/paper/runtime behavior, order placement, sizing, or promotion
  authorization.
- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Plan

1. Add autopilot summary/result fields that identify zero-execution completed
   runs as reused existing evidence.
2. Auto-select latest same-symbol multiple-testing and validation-floor
   manifests before autopilot candidate eligibility runs.
3. Add a lightweight testing-readiness payload to research progress and render
   it in the Research tab.
4. Update focused operator UI and bridge tests.
5. Run focused validation plus compile/contracts/operator UI baseline.

## Acceptance Criteria

- A zero-execution completed autopilot run surfaces `reused_existing_evidence`
  in API/UI summaries.
- Autopilot eligibility uses latest same-symbol gate manifests when present and
  still fails closed when they are absent.
- The Research tab shows executed/skipped counts and testing-readiness status
  without implying candidate readiness.
- Knowledge base status is explicit: documentation-only hypothesis material,
  while executable testing surfaces are separately listed.
- Focused tests and baseline validation pass.

## Outcome

- Implemented zero-execution autopilot completion semantics:
  `execution_status` / `status_detail` report `reused_existing_evidence` when
  a completed run executed no helper steps, otherwise `executed_new_evidence`.
- Wired autopilot candidate eligibility to auto-select the latest same-symbol
  `discovery_multiple_testing_manifest.json` and
  `discovery_validation_floors_manifest.json` when present.
- Added selected gate manifest paths and gate selection status into the
  candidate eligibility step result and candidate eligibility artifact summary.
- Added a research progress testing-readiness audit payload:
  documentation-only knowledge base status, executable testing surfaces,
  latest autopilot freshness, gate manifest alignment, blockers, and top gate
  reasons.
- Updated the Research tab current evidence board to show autopilot execution
  state, executed/skipped counts, and testing-readiness status.
- Added operator UI/autopilot tests for latest gate manifest selection and
  zero-execution reused-evidence reporting.
- Added candidate bridge coverage proving selected multiple-testing and
  validation-floor manifests remove their required-manifest blockers without
  bypassing other required gates.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed:
  441 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  passed: 84 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py tests\research_discovery\test_multiple_testing.py tests\research_discovery\test_validation_floors.py -q`
  passed: 55 tests.
