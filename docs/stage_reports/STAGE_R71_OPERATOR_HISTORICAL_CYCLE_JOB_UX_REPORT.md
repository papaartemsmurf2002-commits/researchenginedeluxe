# Stage R71 Operator Historical-Cycle Job UX Report

Date: 2026-05-06
Work packet: `docs/work_packets/WPR71-01-operator-historical-cycle-job-ux.md`

## Summary

R71 fixes the historical-cycle review workflow reported after R70. The copied
terminal command no longer assumes the current shell is already at the
repository root, and the Research tab now exposes historical-cycle execution as
a normal operator research job.

This stage keeps historical-cycle research semantics unchanged. The safety
change is in the operator execution wrapper: UI-triggered historical cycles
write to isolated job-specific output directories so checked evidence
directories are not overwritten.

## Implementation

- Added robust repo-relative spec resolution for the historical-cycle CLI path
  in `src/tradingbotsuite/main.py`.
- Added a `run-historical-research-cycle` operator job type in
  `src/tradingbotsuite/operator_console.py`.
- Added `/api/operator/research/jobs/run-historical-research-cycle` in
  `src/tradingbotsuite/web/operator.py` with spec-path allowlisting.
- The operator job path:
  - reads the selected checked spec,
  - writes an isolated resolved spec under `research.output_dir/operator_runs`,
  - replaces `output_dir` with a job-specific isolated directory,
  - runs the normal historical-cycle engine from that resolved spec,
  - returns paths to the manifest, rankings, backtest index, and rejection
    report.
- Updated `src/tradingbotsuite/web/templates/research.html` with:
  - `Run Historical Cycle`,
  - `Run Full Research Review`,
  - safer PowerShell copy command with `Set-Location`,
  - browser-local action history,
  - active/latest job status.
- Added tests for isolated output protection, unallowlisted spec rejection,
  rendered UI controls, and repo-relative CLI spec resolution.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
```

Passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py tests\test_operator_ui.py tests\historical\test_full_cycle_synthetic.py::test_historical_research_cycle_cli_resolves_repo_relative_spec -q
```

Passed: 46 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Passed: 367 passed.

```powershell
@'
const fs = require("fs");
const html = fs.readFileSync("src/tradingbotsuite/web/templates/research.html", "utf8");
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(match => match[1]);
for (const code of blocks) new Function(code);
console.log("ok", blocks.length);
'@ | node
```

Passed: `ok 1`.

```powershell
Set-Location C:\Users\papaa
$env:PYTHONPATH='C:\Users\papaa\Music\tradingbotsuite\src'
python -c "from tradingbotsuite.main import _resolve_cli_path; print(_resolve_cli_path('configs/research/full_cycle_btcusdt_perp_context_v2.json'))"
```

Passed: `C:\Users\papaa\Music\tradingbotsuite\configs\research\full_cycle_btcusdt_perp_context_v2.json`.

```powershell
git diff --check
```

Passed.

## Boundary

No live command endpoints, mode switches, manual-signal controls, smoke-live
controls, promotion shortcuts, or order-placement behavior were added. Research
jobs remain blocked in live mode by the existing operator research-job guard.
