# Stage R106 Sandbox Iteration Agent Brief Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-263-sandbox-iteration-agent-brief.md`
Status: closed

## Summary

WPR106-263 adds a compact research-only agent brief to each one-command
sandbox iteration. The brief gives agents a single JSON/Parquet artifact with
the next useful action, reason codes, important counts, blocker summaries,
top descriptor-only validation requests, and artifact pointers.

## Implementation

- Added `sandbox_iteration_agent_brief.json` and
  `sandbox_iteration_agent_brief.parquet` outputs to
  `tradingbotsuite.research_sandbox.iteration.run_sandbox_agent_iteration`.
- Completed iterations with descriptor-only strict-validation requests now get
  `next_action: review_descriptor_only_strict_validation_requests`.
- Preflight-blocked iterations now get
  `next_action: repair_preflight_blockers` with top preflight blockers.
- Briefs include coverage/preflight/result/request/leaderboard counts, top
  archive blockers, top preflight blockers, compact validation-request
  descriptors, artifact paths, and step summaries.
- Added `SANDBOX_ITERATION_AGENT_BRIEF_VERSION` to iteration identity so older
  manifests without briefs are not silently reused.
- Extended cached iteration validation to require brief JSON boundary checks
  and brief Parquet existence before returning `reused_existing: true`.
- Added `sandbox_iteration_agent_brief.json` to the sandbox artifact catalog as
  `agent_iteration_brief`.
- Updated the sandbox research contract and active index.

## Boundary

The packet only adds a read-only navigation artifact for research-only sandbox
iterations. It does not execute strict validation, write candidate artifacts,
change strategy math, change sweep execution, alter sandbox run trial IDs,
create paper/live signals, define sizing, place orders, mutate runtime mode,
write live configuration, download provider data, mutate source archive files,
or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "agent_iteration and (brief or materializes or skips_downstream or runs_sandbox_agent_iteration_under_research_root)"
# 5 passed, 87 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 92 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 460 passed, 1 warning, then known ISSUE-R106-026 WinError 10055 during
# pytest-asyncio event-loop socketpair setup before the affected async test body

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py::test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest -q
# same known ISSUE-R106-026 WinError 10055 during event-loop socketpair setup
```

## Remaining Work

The agent brief makes the one-command iteration more navigable for automated
research handoffs. Later packets can expose brief rows in operator UI or add
portfolio-level briefs across many iterations if that becomes useful.
