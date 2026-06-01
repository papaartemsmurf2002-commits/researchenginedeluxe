# Start Here

This repository is being developed through gated stages.

## Current checkout and identity

ResearchEngineDeluxe is a research-only evidence system for BTC/ETH perpetual
futures. The active Python package is still named `tradingbotsuite` for
compatibility.

The current local checkout is `main`, documented by R106 as the migrated mirror
of `research/v3-experimental-engine`. Use this checkout for research platform
work only. The live runtime branch referenced by older docs is
`live/v1-runtime-hardening`.

## First files to read

1. `AGENTS.md`
2. `docs/ACTIVE_INDEX.md`
3. `docs/ORCHESTRATOR_STAGE_LEDGER.md`
4. `docs/KNOWN_ISSUES.md`
5. `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
6. `docs/BRANCH_PURPOSE.md`
7. `docs/contracts/README.md`
8. `docs/repo_cartography/REPO_INVENTORY.md`

## Research knowledge

Reference material that can help design future falsification packets lives in
`docs/research_knowledge/`. These documents are hypothesis catalogs only; they
are not implementation queues, candidate evidence, promotion evidence, or live
trading instructions.

## Current rule

Follow the active stage in `docs/ORCHESTRATOR_STAGE_LEDGER.md`. Open a work
packet before coding, keep edits inside that packet, and do not start
live/promotion execution work from this research branch unless a later ledger
decision explicitly scopes it. Do not add new strategy/model/filter or
paper/live behavior while open P0 blockers remain in `docs/KNOWN_ISSUES.md`.
