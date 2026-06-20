# WPR106-271 Sandbox Archive Manifest Window Filter

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Reduce one-command sandbox iteration setup cost by filtering archive-root
manifest materialization to the resolved 2024+ sandbox data window before
preflight and sweep execution.

## Scope

- Add optional requested-window filtering to `build_sandbox_archive_manifest`.
- Include only local archive files whose normalized 2024+ timestamp bounds
  overlap the requested window.
- Report out-of-window local files explicitly in the build report instead of
  silently dropping them.
- Feed the resolved generated/spec data window from
  `run_sandbox_agent_iteration` into archive-root manifest building.
- Preserve existing behavior for direct venue archive manifests and archive
  builder calls that do not supply a requested window.
- Preserve deterministic manifest IDs, source-integrity metadata, descriptor
  boundaries, and 2024+ filtering.
- Add focused sandbox tests for builder filtering and one-command iteration
  archive-root filtering.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-271-sandbox-archive-manifest-window-filter.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_MANIFEST_WINDOW_FILTER_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/archive_manifest.py`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Archive manifest builder calls with a requested window include only files
  whose normalized 2024+ bounds overlap that window.
- Build-report rows for non-overlapping files show an explicit
  `outside_requested_window` skip reason and requested-window metadata.
- One-command sandbox iterations that materialize archive roots pass the
  resolved data window into archive manifest building.
- Direct existing venue archive manifest runs keep existing behavior.
- Generated descriptors retain source integrity and required sandbox boundary
  flags.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only filters local sandbox archive manifest construction before
preflight. It does not download provider data, execute strict validation, write
candidate artifacts, create paper/live signals, define sizing, place orders,
mutate runtime mode, write live configuration, mutate source archive files, or
claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. `build_sandbox_archive_manifest()` now
accepts an optional requested sandbox data window and skips loaded local files
whose normalized 2024+ timestamp bounds do not overlap that window. Skipped
files remain visible in the build report with `outside_requested_window` and
requested-window metadata. One-command sandbox iterations resolve their data
window before archive-root materialization and pass that window to the archive
manifest builder.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "requested_window or filters_archive_roots"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 2 focused archive-window tests passed, 109 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
