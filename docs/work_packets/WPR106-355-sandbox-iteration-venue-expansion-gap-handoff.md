# WPR106-355 - Sandbox Iteration Venue Expansion Gap Handoff

## Status

closed

## Objective

Surface the WPR106-354 venue-expansion archive gap diagnostics in the one-command
sandbox iteration manifest, agent brief, iteration index, action queues, and agent
action plan so follow-on agents can immediately repair or add OKX, Bybit, and
Hyperliquid archive descriptors without opening the archive coverage JSON first.

## Allowed paths

- `src/tradingbotsuite/research_sandbox/iteration.py`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/contracts/sandbox_research_contract.md`
- `docs/work_packets/WPR106-355-sandbox-iteration-venue-expansion-gap-handoff.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_VENUE_EXPANSION_GAP_HANDOFF_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Boundary constraints

- Research-only output only.
- Do not mutate archive manifests or source data.
- Do not download venue data.
- Do not run strict validation, write candidate packs, or change promotion flags.
- Do not weaken the 2024+ sandbox window boundary.
- Keep venue-expansion rows diagnostic and descriptor-oriented.

## Implementation notes

- Add compact venue-expansion gap samples and counts to iteration manifests.
- Add the same compact metadata to agent briefs and artifact path references.
- Add iteration-index fields and a queue/action-plan action for venue expansion
  archive work.
- Preserve existing archive coverage and preflight semantics.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "agent_iteration or iteration_index or archive_coverage"`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- `git diff --check`

## Closure

Closed after the sandbox iteration manifest, agent brief, iteration index, queue
rollups, and action plan expose bounded venue-expansion archive gap handoff
metadata while preserving research-only behavior and existing candidate-pack
guards. Validation is recorded in
`docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_VENUE_EXPANSION_GAP_HANDOFF_REPORT.md`.
