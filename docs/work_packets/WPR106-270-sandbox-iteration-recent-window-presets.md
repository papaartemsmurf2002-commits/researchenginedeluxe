# WPR106-270 Sandbox Iteration Recent Window Presets

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make one-command sandbox iterations faster for current research loops by adding
a generated-spec recent-window preset that resolves to a 2024+ clipped trailing
window and records the resolved window metadata.

## Scope

- Add a bounded recent-window resolver for generated sandbox iteration specs.
- Support a trailing-day preset such as `recent_365d` with an explicit
  `as_of_date` for deterministic agent workflows and tests.
- Clip resolved windows to `2024-01-01` so no generated sandbox iteration can
  include pre-2024 rows.
- Record window-selection metadata in the iteration manifest, agent brief, and
  step payloads where useful for agent handoff.
- Wire CLI options for generated-spec iteration runs.
- Preserve explicit `--window-start` / `--window-end` behavior and existing
  spec-file behavior.
- Add focused sandbox and CLI tests.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-270-sandbox-iteration-recent-window-presets.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_RECENT_WINDOW_PRESETS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `src/tradingbotsuite/main.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- `recent_365d` resolves to a trailing 365-day window ending at the supplied
  `as_of_date`, with the start clipped to `2024-01-01` when necessary.
- Explicit generated-spec windows retain existing behavior and metadata.
- Existing spec-file runs are not silently overridden by recent-window options.
- CLI options pass the preset/as-of/lookback values into the iteration runner.
- Iteration manifests and agent briefs expose resolved window metadata while
  retaining all required sandbox boundary flags.
- Validation includes focused sandbox tests, CLI boundary coverage, full
  sandbox tests, package compile, import-boundary tests, and the contract
  baseline when the local environment allows it.

## Boundary

This packet only selects generated sandbox iteration data windows. It does not
download provider data, execute strict validation, write candidate artifacts,
create paper/live signals, define sizing, place orders, mutate runtime mode,
write live configuration, mutate source archive files, or claim promotion
readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Generated one-command sandbox iteration
specs now support `recent_365d`, `recent_days`, and `recent_<N>d` window
presets. Presets resolve before preflight, clip any start date earlier than
`2024-01-01`, and record `window_selection` metadata in the iteration manifest
and agent brief. Spec-file runs reject recent-window override arguments instead
of silently rewriting explicit specs.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "recent_window or cli_command_runs_sandbox_agent_iteration"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 4 focused recent-window/CLI tests passed, 107 sandbox tests
passed, 22 live CLI boundary tests passed, package compileall passed, 11
import-boundary tests passed, and 461 contract tests passed.
