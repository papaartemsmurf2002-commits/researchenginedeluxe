# WPR106-275 Sandbox Full Preflight Blocker Counts

Status: closed
Owner: Codex Research Agent
Created: 2026-06-19

## Objective

Make sandbox agent briefs and iteration indexes carry full preflight blocker
reason counts so preflight repair queues expose complete repair context for
large strategy/archive matrices.

## Scope

- Write full preflight blocker reason counts into one-command iteration agent
  briefs.
- Preserve existing `top_preflight_blockers` compact summaries for display.
- Teach the iteration index to prefer full preflight blocker counts from briefs
  or manifests while remaining compatible with older artifacts that only have
  top preflight blockers.
- Include full preflight blocker counts in iteration index rows and action
  queue items.
- Add focused sandbox tests proving full preflight blockers survive even when
  the bounded top blocker list is incomplete or stale.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-275-sandbox-full-preflight-blocker-counts.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_FULL_PREFLIGHT_BLOCKER_COUNTS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- New agent briefs include `preflight_blocker_reason_counts`.
- Existing `top_preflight_blockers` remains present and bounded.
- Iteration indexes expose full preflight blocker counts in rows and queue
  items.
- Older artifacts with only top preflight blockers remain indexable.
- Queue payloads and rows keep required sandbox boundary flags and do not
  execute sandbox sweeps or strict validation.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds read-only preflight blocker-count metadata to sandbox
agent briefs and iteration indexes. It does not download provider data, execute
sandbox sweeps beyond tests, execute strict validation, write candidate
artifacts, create paper/live signals, define sizing, place orders, mutate
runtime mode, write live configuration, mutate source archive files, or claim
promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-19. One-command sandbox agent briefs now
include `preflight_blocker_reason_counts`, and iteration index rows/action
queue items preserve the full preflight blocker map. Index loading prefers
brief counts, then manifest counts, and falls back to bounded top preflight
blockers for older artifacts.

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
