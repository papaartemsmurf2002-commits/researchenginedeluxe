# WPR71-01 Operator Historical-Cycle Job UX

Stage: R71 operator historical-cycle job UX
Owner: Codex Research Agent
Status: closed
Created: 2026-05-06

## Goal

Fix the Research tab historical-cycle UX so operators do not need to copy a
repo-relative terminal command that fails outside the repository root. Add a
safe operator job endpoint/button for historical cycles, provide a full-run
button for the main research workflow, persist local UI action history, and
protect checked research evidence from accidental overwrites.

## Allowed paths

```text
src/tradingbotsuite/operator_console.py
src/tradingbotsuite/main.py
src/tradingbotsuite/web/operator.py
src/tradingbotsuite/web/templates/research.html
tests/tradingbotsuite/test_operator_ui.py
tests/historical/test_full_cycle_synthetic.py
docs/work_packets/WPR71-01-operator-historical-cycle-job-ux.md
docs/stage_reports/STAGE_R71_OPERATOR_HISTORICAL_CYCLE_JOB_UX_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Preserve historical-cycle research semantics.
- Do not run historical cycles into checked artifact directories from the
  operator job path.
- Do not add live controls, promotion shortcuts, mode switches, or order
  placement behavior.
- Keep operator jobs blocked in live mode by the existing research job guard.
- Keep research artifacts `research_only`, `observe_only`, and
  `promotion_ready: false` unless an existing artifact says otherwise.

## Exit validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\test_operator_ui.py -q
```

## Close evidence

- Added `/api/operator/research/jobs/run-historical-research-cycle`.
- Historical-cycle operator jobs now rewrite selected specs into isolated
  job-specific output directories under
  `research.output_dir/operator_runs/historical_cycles/...`.
- Checked config output directories are not used by operator historical-cycle
  jobs, preventing accidental overwrite of committed evidence.
- Added `Run Historical Cycle` and `Run Full Research Review` buttons.
- Added browser-local Research tab action history and active/latest job status.
- Copied PowerShell commands now change into the repository root before running.
- Historical-cycle CLI spec paths now resolve against the repository root when
  a relative path is not valid from the current shell directory.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\test_operator_ui.py tests\historical\test_full_cycle_synthetic.py::test_historical_research_cycle_cli_resolves_repo_relative_spec -q`
    - 46 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
    - 367 passed
  - Research page embedded script parse check passed with Node.
  - From `C:\Users\papaa`, `_resolve_cli_path('configs/research/full_cycle_btcusdt_perp_context_v2.json')` resolves to the repository config path.
  - `git diff --check`
