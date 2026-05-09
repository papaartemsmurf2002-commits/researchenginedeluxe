# WPR92-01 Final Branch Crosscheck

## Objective

Perform a final crosscheck of the research branch after the discovery runtime
optimization waves. Verify that the HMM/KNN/discovery logic, research safety
boundaries, documentation, and operator UI remain clean, tested, and aligned
with the branch architecture.

## Fit Check

This is an audit and hardening packet. It is allowed to touch broad branch
surfaces only if a concrete issue is found, because the user requested a whole
branch crosscheck. Any implementation fixes must remain research-only, preserve
existing contracts, and include focused validation.

## Allowed paths

- `src/tradingbotsuite/**`
- `tests/**`
- `configs/**`
- `docs/work_packets/WPR92-01-final-branch-crosscheck.md`
- `docs/stage_reports/STAGE_R92_FINAL_BRANCH_CROSSCHECK_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- Documentation under `docs/**` if the audit finds stale or misleading text

## Planned checks

- Run compile and contract baseline.
- Run discovery, HMM/KNN, live-boundary, historical-cycle, and UI tests.
- Inspect HMM/KNN/discovery implementation for split leakage, label leakage,
  deterministic ordering, artifact overwrite behavior, and research-only flags.
- Verify documentation and ledger are current.
- Use official external references for questionable algorithmic assumptions.
- Fix concrete issues found during the audit.

## Exit criteria

- Validation is green or any blocker is documented in `docs/KNOWN_ISSUES.md`.
- Stage report records what was checked, any fixes, and remaining risk.
- Git is clean and pushed when complete.

## Exit evidence

- Fixed KNN short-majority expectancy so expected value is side-adjusted.
- Fixed discovery trial metrics so realized expectancy and gross return are
  side-adjusted by predicted KNN side and only clear accepted rows count.
- Updated operator guide selection and Research UI documentation so the UI uses
  the canonical current docs.
- Real discovery probe completed with 4 trials, 2 interesting rows, 2 blocked
  rows, 4 snapshots, `promotion_ready: false`, and `order_placement_used: false`.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_knn_study.py tests\research_discovery\test_discovery_runner.py tests\tradingbotsuite\test_operator_ui.py tests\integration\test_research_ui.py -q`
  - `$env:PYTHONPATH='src'; python -m pytest tests\test_removed_source_boundaries.py -q`
  - `python -m tradingbotsuite.main benchmark-discovery-run --tier deep --repeat 1 --output-dir "$env:TEMP\tbs_wpr92_deep_benchmark"`
  - `$env:PYTHONPATH='src'; python -m pytest -q`
