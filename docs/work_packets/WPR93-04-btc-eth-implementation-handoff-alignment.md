# WPR93-04 BTC ETH Implementation Handoff Alignment

Status: closed
Owner: Codex Research Agent
Date: 2026-05-11

## Purpose

Analyze `C:/Users/papaa/Downloads/BTC_ETH_PERP_RESEARCH_IMPLEMENTATION_HANDOFF.md`
and fold useful, repo-aligned implementation points into the next-stage R94
development plan.

## Input

- `C:/Users/papaa/Downloads/BTC_ETH_PERP_RESEARCH_IMPLEMENTATION_HANDOFF.md`
- `docs/RESEARCH_NEXT_PHASE_REAL_STRATEGIES_FILTERS_FEATURES_PLAN.md`
- `docs/RESEARCH_BRANCH_AUDIT_AND_NEXT_STAGE_HANDOFF.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`

## Allowed Paths

- `docs/work_packets/WPR93-04-btc-eth-implementation-handoff-alignment.md`
- `docs/RESEARCH_NEXT_PHASE_REAL_STRATEGIES_FILTERS_FEATURES_PLAN.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Non-Goals

- No implementation code changes.
- No config behavior changes.
- No generated artifact changes.
- No live/promotion boundary changes.
- No acceptance of true HMM, L2 order book, or liquidation strategies as
  immediate default work before prerequisites are complete.

## Validation

- `git diff --check`

## Exit Criteria

- The R94 plan includes aligned useful findings from the BTC/ETH handoff.
- The plan preserves existing repo naming, guardrails, and staged packet order.
- The plan clearly marks deferred items and prerequisites.

## Output

- Updated `docs/RESEARCH_NEXT_PHASE_REAL_STRATEGIES_FILTERS_FEATURES_PLAN.md`
  with BTC/ETH handoff alignment decisions.
- Added staged WPR94 follow-on packets for:
  - perp context source/version audit
  - exit model upgrade and remaining-edge lab
  - BTC/ETH candidate blueprint configs
  - cross-asset BTC/ETH residual research
  - validation floors and blocker registry
- Preserved the current repo guardrails:
  - no code changes
  - no generated artifact changes
  - no live/promotion changes
  - no immediate true-HMM, L2, or liquidation-default work without prerequisites

## Validation Result

- `git diff --check` passed.
