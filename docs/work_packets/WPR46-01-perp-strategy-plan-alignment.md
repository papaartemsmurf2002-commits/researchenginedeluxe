# WPR46-01 Perp Strategy Plan Alignment

Status: closed
Owner: Codex Research Agent
Stage: Stage R46 perp strategy plan alignment
Opened: 2026-05-05
Closed: 2026-05-05

## Objective

Curate the downloaded BTC/ETH perpetual strategy expansion plan into a repo-native agent development document that matches the current `research/v3-experimental-engine` architecture, names, stage numbering, contracts, and safety boundaries.

This packet is documentation-only. It does not implement data collectors, feature builders, strategies, exits, backtests, benchmarks, promotion flows, paper/shadow/testnet/live work, order placement, runtime-control writes, or capital-allocation behavior.

## Allowed paths

- `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR46-01-perp-strategy-plan-alignment.md`
- `docs/stage_reports/STAGE_R46_PERP_STRATEGY_PLAN_ALIGNMENT_REPORT.md`

## Inputs

- `C:/Users/papaa/Downloads/TBS_RESEARCH_V3_PERP_STRATEGY_IMPLEMENTATION_PLAN.md`
- `docs/RESEARCH_BRANCH_DISTILLATION.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- Current contracts in `src/tradingbotsuite/research_cycle/spec.py`
- Current feature, strategy, data, exit, and candidate-pack modules under `src/tradingbotsuite`

## Non-goals

- No code changes.
- No changes to the downloaded source plan.
- No live/promotion behavior.
- No external-source verification pass.
- No claim that the proposed strategies are profitable, accepted, or promotion-ready.

## Implementation plan

1. Identify naming and contract conflicts between the downloaded plan and the current branch.
2. Resolve trivial conflicts directly in a curated agent-development plan.
3. For non-trivial conflicts, document explicit compromises and stage gates.
4. Convert the roadmap into work packets that start after the closed R45 distillation stage.
5. Include ready-to-use instructions for the first implementation stage.
6. Validate documentation hygiene and close the packet.

## Exit criteria

- A curated plan exists at `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`.
- The plan uses current branch names or explicitly marks future additions.
- The plan does not require deleting or replacing core repo structure.
- Non-trivial changes are isolated into later dedicated packets.
- Validation results are recorded in the stage report.

## Completion evidence

- Added `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md`.
- Added `docs/stage_reports/STAGE_R46_PERP_STRATEGY_PLAN_ALIGNMENT_REPORT.md`.
- Updated `docs/ORCHESTRATOR_STAGE_LEDGER.md` with WPR46 closure.

## Validation

- Cross-checked the downloaded source plan against current cycle, data, feature, strategy, exit, and candidate-pack contracts.
- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `git diff --check` passed.
