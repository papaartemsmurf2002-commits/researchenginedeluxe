# WPR106-557 - V2 agent context cleanup and handoff

## Status

Complete.

## Objective

Clean up the current handoff conflict after WPR106-556 and add a deterministic
read-only agent context surface so autonomous research agents can start from
the current data/catalog truth instead of reconstructing it from scattered
docs.

The target outcome is practical:

- the docs distinguish the passed `autonomous_research_ready` manager gate from
  still-forbidden candidate, paper/live, order, sizing, runtime, promotion, or
  production-trading claims;
- agents can ask the repo for a machine-readable map of instruments, data
  stores, evidence reports, no-paid collection lanes, lockbox state, and minor
  self-repair rules;
- the command remains research-only and read-only, with no venue fetch, data
  mutation, strategy execution, or generated evidence rewrite.

## Allowed paths

- `docs/work_packets/WPR106-557-v2-agent-context-cleanup-and-handoff.md`
- `docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md`
- `docs/contracts/autonomous_research_agent_context_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `README.md`
- `START_HERE.md`
- `src/tradingbotsuite/v2/autonomy/__init__.py`
- `src/tradingbotsuite/v2/autonomy/agent_context.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_autonomy_agent_context_phase79.py`

If validation exposes a minor issue directly blocking this packet, amend this
section before editing additional paths.

## Out of scope

- No live, paper, order placement, sizing, runtime-mode, candidate-pack,
  promotion, or production-trading behavior.
- No provider downloads, venue API calls, WebSocket streams, or paid/requester-
  pays access.
- No mutation of `data/research/**` generated evidence, the central market-
  history store, or the external WPR106-549 raw-heavy archive.
- No strategy search, backtest execution, performance claim, or new readiness
  proof.

## Plan

1. Add a compact contract for the read-only agent context JSON.
2. Implement a `tradingbotsuite.v2.autonomy.agent_context` module that builds
   the context from stable catalog defaults and optional existing local report
   files.
3. Expose the context through `redx autonomy agent-context` with optional JSON
   output writing.
4. Update active handoff docs to resolve stale WPR106-553/WPR106-556 wording.
5. Add focused tests for schema content, path/policy guidance, boundary flags,
   no-paid collection rules, CLI output, and output-path hygiene.

## Research boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready=false`. The agent context is navigation and policy metadata
only. It is not accepted strategy evidence, a candidate pack, a signal, a
sizing instruction, a runtime-mode change, or a promotion artifact.

## Planned validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_cli_smoke.py tests\v2\test_autonomy_phase23.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Outcome

Implemented `redx autonomy agent-context` through
`src/tradingbotsuite/v2/autonomy/agent_context.py`. The command emits
`autonomous_research_agent_context_v1` JSON containing:

- WPR106-556 manager readiness status;
- 29 project symbols with Hyperliquid and Binance USD-M research identifiers;
- WPR106-546, WPR106-544, WPR106-549, WPR106-552, WPR106-556, product-scope,
  data-catalog, and known-issue refs;
- strict-free/no-paid collection rules;
- data-lane allowed/blocked uses;
- dynamic lockbox month and ordinary-iteration end-exclusive timestamp;
- scoped self-repair and escalation policy;
- first-read docs and command hints;
- full research-only boundary flags.

The current repo smoke reports:

```text
schema=autonomous_research_agent_context_v1 ready=True status=autonomous_research_ready symbols=29 lockbox=2026-05
```

Updated active handoff docs so WPR106-553 remains the final repo audit for
agentic iteration readiness while WPR106-556 is the current formal manager
autonomous-readiness verdict. Candidate-pack, paper/live, order/sizing/runtime,
promotion, and production-trading claims remain forbidden.

No provider data was fetched, no generated evidence was rewritten, and no live,
paper, order, sizing, runtime, candidate-pack, or promotion path was touched.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
# 4 passed

$env:PYTHONPATH='src'; python -m pytest tests\v2\test_cli_smoke.py tests\v2\test_autonomy_phase23.py -q
# 8 passed

python -m compileall -q src\tradingbotsuite

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed

$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
# 2 passed

$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root . --asof-date 2026-06-27
# current-repo smoke passed: autonomous_research_ready=true, 29 symbols, lockbox=2026-05

git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```
