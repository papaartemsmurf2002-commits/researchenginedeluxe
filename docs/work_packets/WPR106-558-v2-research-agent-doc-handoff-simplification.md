# WPR106-558 - V2 research agent doc handoff simplification

## Status

Implemented and validated.

## Objective

Make the documents used by autonomous research agents clean, current, and low
friction. The current facts are mostly correct after WPR106-557, but the
default reading path still pushes agents through long historical/audit files
that add avoidable complexity and contain stale intermediate statuses.

The target outcome is a short current operating guide that agents can use
before opening historical ledgers, plus updated first-read pointers and agent
context output that direct agents to that guide.

## Allowed paths

- `docs/work_packets/WPR106-558-v2-research-agent-doc-handoff-simplification.md`
- `docs/RESEARCH_AGENT_QUICKSTART.md`
- `AGENTS.md`
- `START_HERE.md`
- `README.md`
- `docs/ACTIVE_INDEX.md`
- `docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md`
- `docs/contracts/autonomous_research_agent_context_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/autonomy/agent_context.py`
- `tests/v2/test_autonomy_agent_context_phase79.py`

No no-touch paths, generated evidence paths, live/runtime paths, or strategy
artifact paths are in scope.

## Out of scope

- No strategy search, backtest run, data collection, materialization, ledger
  append, Lead Book mutation, candidate pack, paper/live signal, order/sizing
  behavior, runtime-mode change, promotion artifact, or production-trading
  claim.
- No deletion or rewrite of historical audit evidence. Long docs may be
  reclassified as historical/reference, but they remain available.

## Plan

1. Add `docs/RESEARCH_AGENT_QUICKSTART.md` as the compact current operating
   guide for research agents.
2. Update first-read docs to point at the quickstart and clearly demote long
   ledgers/audit indices to conditional reference material.
3. Update the agent-context JSON `first_files_to_read` and tests so agents get
   the shorter path by default.
4. Register WPR106-558 in the audit index and stage ledger.
5. Validate focused docs/context behavior and baseline syntax.

## Research boundary

This is documentation and read-only context hygiene only. The packet must keep
all research outputs `research_only`, `observe_only`, and
`promotion_ready=false`.

## Planned validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

## Outcome

- Added `docs/RESEARCH_AGENT_QUICKSTART.md` as the concise current operating
  guide for autonomous research agents.
- Repointed `AGENTS.md`, `START_HERE.md`, `README.md`, `docs/ACTIVE_INDEX.md`,
  and `docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md` so agents start
  from the quickstart, data catalog, product scope, known issues, and latest
  relevant packet.
- Reclassified long ledgers, audit files, decision registers, dependency fuse,
  roadmap status, and stage reports as conditional references rather than the
  default read path.
- Updated the autonomous agent-context contract and JSON output so
  `first_files_to_read` is the compact current handoff list.
- Registered the change in `docs/audit/V2_AUDIT_INDEX.md` and
  `docs/ORCHESTRATOR_STAGE_LEDGER.md`.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
# 4 passed

$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
# 2 passed

$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root . --asof-date 2026-06-27
# first_files_to_read:
# AGENTS.md
# docs/RESEARCH_AGENT_QUICKSTART.md
# docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md
# docs/PRODUCT_SCOPE.md
# docs/KNOWN_ISSUES.md

git diff --check
# passed; only LF-to-CRLF working-copy warnings were printed
```
