# WPR106-29 Candidate Rejection Root-Cause And Gate Materialization

## Summary

Investigate why the completed R106 autopilot produced zero eligible BTC/ETH
candidate-pack rows even though the required workflow checklist is complete.
Separate real research rejection from join/materialization bugs, then patch only
confirmed diagnostics or gate-materialization issues needed to make the next
eligibility run truthful and actionable.

## Allowed Paths

Edit scope:

- `docs/work_packets/WPR106-29-candidate-rejection-root-cause-and-gate-materialization.md`
- `docs/stage_reports/STAGE_R106_CANDIDATE_REJECTION_ROOT_CAUSE_AND_GATE_MATERIALIZATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a new blocking issue is found
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `src/tradingbotsuite/research_discovery/multiple_testing.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/research_discovery/test_candidate_pack_bridge.py`
- `tests/research_discovery/test_multiple_testing.py`
- `tests/research_artifacts/test_candidate_pack.py`
- `tests/tradingbotsuite/test_operator_ui.py`

Generated research artifacts may be read for diagnostics. Do not rewrite
historical cycle, discovery, or fixture artifacts in-place. If a rerun is needed
for validation, write isolated operator-run outputs only.

## Audit Plan

1. Inspect latest BTC/ETH candidate eligibility manifests and rejection reports.
2. Compare discovery candidate IDs and signatures against current cycle ranking
   and gate evidence.
3. Determine whether `candidate_missing_from_rankings` is a true no-overlap
   result or a schema/key mismatch.
4. Inspect missing gate blockers:
   - `exit_lab_candidate_gate_row_required`
   - `multiple_testing_manifest_required`
   - `validation_floor_manifest_required`
   - ETH `frozen_entry_signals_missing`
5. Patch minimal code/UI diagnostics or gate-materialization behavior if the
   root cause is implementation-side.
6. Validate with focused tests and update the stage report.

## Acceptance Criteria

- Report states whether the zero eligible candidates are expected from current
  evidence or caused by a code/materialization bug.
- Report lists blocker counts by symbol and blocker class.
- If a patch is made, tests cover the fixed behavior.
- No candidate pack is written unless all existing candidate-pack gates pass.
- No live execution, live config, runtime mode, sizing, order placement, or
  promotion readiness behavior is introduced.
