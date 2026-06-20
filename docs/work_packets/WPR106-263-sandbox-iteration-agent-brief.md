# WPR106-263 Sandbox Iteration Agent Brief

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a compact research-only agent brief to each one-command sandbox iteration
so agents can identify the next useful action, important blockers, top
descriptor-only validation requests, and artifact paths without opening every
child JSON/Parquet file.

## Scope

- Write `sandbox_iteration_agent_brief.json` and
  `sandbox_iteration_agent_brief.parquet` for completed and
  preflight-blocked sandbox agent iterations.
- Include next-action labels, reason codes, coverage/preflight/sweep/request
  counts, top blocker summaries, top validation-request descriptors, and
  artifact pointers.
- Add the brief step version to iteration identity so older manifests lacking a
  brief are not silently reused.
- Require cached iteration reuse to validate the brief JSON boundary flags and
  brief Parquet existence.
- Index the brief in the sandbox artifact catalog.
- Add focused sandbox tests for completed runs, blocked runs, cached reuse, and
  artifact catalog discovery.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-263-sandbox-iteration-agent-brief.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_AGENT_BRIEF_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Completed iterations write an agent brief with `next_action:
  review_descriptor_only_strict_validation_requests` when descriptor-only
  validation requests exist.
- Preflight-blocked iterations write an agent brief with a repair-oriented
  next action and explicit blocker summaries.
- Cached iteration reuse fails closed when brief artifacts are missing or lose
  sandbox boundary metadata.
- Sandbox artifact catalog discovery includes the brief artifact kind.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only adds a read-only research navigation artifact for sandbox
iterations. It does not execute strict validation, write candidate artifacts,
change strategy math, change sweep execution, alter trial IDs inside sandbox
runs, create paper/live signals, define sizing, place orders, mutate runtime
mode, write live configuration, download provider data, mutate source archive
files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. One-command sandbox iterations now write
`sandbox_iteration_agent_brief.json` and
`sandbox_iteration_agent_brief.parquet`. Completed iterations with descriptor
requests get `next_action:
review_descriptor_only_strict_validation_requests`; preflight-blocked
iterations get `next_action: repair_preflight_blockers`. Briefs include compact
counts, reason codes, top archive/preflight blockers, compact descriptor-only
validation requests, artifact paths, and step summaries. Cached iteration reuse
now validates brief JSON boundary flags and brief Parquet existence, and the
sandbox artifact catalog indexes `agent_iteration_brief` rows.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "agent_iteration and (brief or materializes or skips_downstream or runs_sandbox_agent_iteration_under_research_root)"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py::test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest -q
```

Final results: 5 focused iteration tests passed, 92 sandbox tests passed,
package compileall passed, and 11 import-boundary tests passed. The full
contract baseline reached 460 passed tests and then hit known
`ISSUE-R106-026`, Windows `WinError 10055`, during pytest-asyncio event-loop
socketpair setup before the affected async test body ran. The isolated affected
async contract test failed at the same socketpair setup point.
