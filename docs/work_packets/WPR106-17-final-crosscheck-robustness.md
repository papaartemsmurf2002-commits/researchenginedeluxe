# WPR106-17 Final Crosscheck Robustness

Status: closed

## Scope

Perform a final narrow crosscheck of the WPR106 research workflow completion
surface and harden fail-closed behavior where malformed research artifacts can
otherwise abort the frozen-entry exit-lab job.

This packet does not add new research capability, does not claim candidate-ready
performance, and does not promote any artifact beyond research-only analysis.

## Allowed paths

- `src/tradingbotsuite/research_discovery/frozen_entry_exit_lab.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/research_discovery/test_frozen_entry_exit_lab.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/contracts/boundary_contract.md`
- `docs/work_packets/WPR106-17-final-crosscheck-robustness.md`
- `docs/stage_reports/STAGE_R106_FINAL_CROSSCHECK_ROBUSTNESS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Constraints

- Preserve `research_only`, `observe_only`, and `promotion_ready: false` on
  all exit-lab artifacts.
- Do not place orders, change live runtime mode, write live configuration, or
  import live order-placement adapters into research code.
- Keep hardening limited to fail-closed handling and regression coverage.
- Treat malformed or unsupported research inputs as blocked evidence, not as
  accepted candidate evidence.

## Acceptance

- Frozen-entry exit-lab handles unsupported label horizons, invalid sides, and
  malformed market prices without uncaught simulation crashes.
- Service-layer candidate eligibility artifact paths are constrained to the
  configured research output root and malformed eligibility manifests do not
  satisfy completion checks.
- Operator autopilot runs cycle/discovery prerequisites for all requested
  symbols before later analysis, exit-lab, and eligibility steps.
- Blocked outputs preserve the canonical bridge-compatible candidate-gate
  schema and research-only boundary flags.
- Focused validation and the contracts baseline pass.

## Exit summary

- Hardened frozen-entry exit-lab normalization so unsupported horizons, invalid
  sides, malformed timestamps/prices, malformed Parquet inputs, and non-positive
  market prices produce blocked research artifacts instead of uncaught operator
  failures.
- Added service-layer candidate-eligibility path allowlisting, nested manifest
  required-output root checks, mixed-symbol evidence rejection, and stricter
  eligibility-manifest completion validation.
- Reordered research autopilot so cycle and exact-discovery prerequisites run
  for all requested symbols before analysis, deltas, exit labs, and eligibility.
- Updated the boundary command contract for the R106 operator research workflow
  command names.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_frozen_entry_exit_lab.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_candidate_eligibility_service_requires_research_root_paths tests\tradingbotsuite\test_operator_ui.py::test_operator_candidate_eligibility_service_rejects_manifest_outputs_outside_root tests\tradingbotsuite\test_operator_ui.py::test_operator_candidate_eligibility_service_rejects_mixed_symbol_inputs tests\tradingbotsuite\test_operator_ui.py::test_operator_candidate_eligibility_completion_rejects_malformed_manifest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_reuses_completed_outputs_and_runs_analysis_and_eligibility tests\tradingbotsuite\test_operator_ui.py::test_operator_research_autopilot_completes_all_discoveries_before_eligibility -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py::test_boundary_contract_lists_research_command_registry -q`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- `$env:PYTHONPATH='src'; python -m pytest -q`
