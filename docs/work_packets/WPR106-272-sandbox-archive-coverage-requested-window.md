# WPR106-272 Sandbox Archive Coverage Requested Window

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make sandbox archive audits and coverage matrices reflect the active 2024+
requested data window so agents can triage existing multi-venue archive
manifests before preflight or sweep execution.

## Scope

- Add optional requested-window metadata to archive descriptor audits.
- Count rows inside the requested window separately from descriptor-window
  rows.
- Mark otherwise loadable descriptors as blocked for the active request when
  they have zero rows in the requested window.
- Aggregate requested-window counts and blockers into archive coverage rows.
- Pass one-command sandbox iteration specs into archive coverage so existing
  venue archive manifests get the same window-aware launch signal as
  archive-root materialization.
- Expose requested-window options on archive audit/coverage CLI helpers when
  useful for direct agent workflows.
- Preserve existing audit and coverage behavior when no requested window is
  supplied.
- Add focused sandbox tests for audit, coverage, iteration, and CLI behavior.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-272-sandbox-archive-coverage-requested-window.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_COVERAGE_REQUESTED_WINDOW_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research_sandbox/archive_audit.py`
- `src/tradingbotsuite/research_sandbox/archive_coverage.py`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Archive audits without a requested window keep existing descriptor-window
  readiness semantics.
- Archive audits with a requested window report requested-window metadata,
  requested-window row counts, and an explicit blocker when a descriptor has
  no rows in that requested window.
- Coverage matrices aggregate requested-window row counts and blocker reasons
  by venue/symbol/data-family/interval bucket.
- One-command sandbox iterations pass the resolved spec data window into
  archive coverage for both existing venue archive manifests and materialized
  archive roots.
- CLI audit/coverage helpers can request the same window-aware diagnostics
  without executing sweeps or strict validation.
- Validation includes focused sandbox tests, relevant live CLI boundary tests,
  package compile, import-boundary tests, and the contract baseline when the
  local environment allows it.

## Boundary

This packet only adds requested-window diagnostics to sandbox archive audit
and coverage artifacts. It does not download provider data, execute sandbox
sweeps by itself, execute strict validation, write candidate artifacts, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Archive descriptor audits now accept an
optional requested sandbox data window, report requested-window row counts and
observed bounds, and block otherwise loadable descriptors with
`no_rows_in_requested_window` when the active requested window has zero rows.
Archive coverage matrices aggregate those requested-window counts and blockers.
One-command sandbox iterations pass the resolved spec data window into archive
coverage, including existing venue archive manifest workflows. Archive audit
and coverage CLI helpers accept optional requested-window bounds.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "requested_window or existing_archive_coverage or audits_archive_descriptors_under_research_root or summarizes_archive_coverage_under_research_root"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 6 focused requested-window/CLI tests passed, 112 sandbox tests
passed, 22 live CLI boundary tests passed, package compileall passed, 11
import-boundary tests passed, and 461 contract tests passed.
