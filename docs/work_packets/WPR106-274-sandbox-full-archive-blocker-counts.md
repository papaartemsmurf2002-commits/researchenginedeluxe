# WPR106-274 Sandbox Full Archive Blocker Counts

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Make sandbox iteration manifests, briefs, and iteration indexes carry full
archive coverage blocker counts so agent action queues do not depend on
bounded top-blocker summaries.

## Scope

- Write full archive coverage blocker reason counts into one-command iteration
  manifests.
- Write the same full archive blocker counts into agent briefs.
- Preserve existing `top_archive_blockers` compact summaries for display.
- Teach the iteration index to prefer full archive blocker counts when
  deciding `archive_window_repair_queue` membership.
- Keep compatibility with older iteration artifacts that only have
  `top_archive_blockers`.
- Add focused sandbox tests proving `no_rows_in_requested_window` is queued
  even when omitted from top archive blockers.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-274-sandbox-full-archive-blocker-counts.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_FULL_ARCHIVE_BLOCKER_COUNTS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- New iteration manifests include `archive_coverage_blocker_reason_counts`.
- New agent briefs include `archive_blocker_reason_counts`.
- Existing `top_archive_blockers` remains present and bounded.
- Iteration indexes expose full archive blocker counts in rows and queue items.
- `archive_window_repair_queue` uses full blocker counts when available and
  still supports older artifacts with only `top_archive_blockers`.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds read-only blocker-count metadata to sandbox iteration
manifests, briefs, and indexes. It does not download provider data, execute
sandbox sweeps beyond tests, execute strict validation, write candidate
artifacts, create paper/live signals, define sizing, place orders, mutate
runtime mode, write live configuration, mutate source archive files, or claim
promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. One-command sandbox iteration manifests
now include `archive_coverage_blocker_reason_counts`, agent briefs include
`archive_blocker_reason_counts`, and iteration index rows/action queue items
preserve the full archive blocker map. The `archive_window_repair_queue`
prefers full counts for `no_rows_in_requested_window` membership and falls back
to top blockers for older artifacts.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused iteration-index tests passed, 113 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
