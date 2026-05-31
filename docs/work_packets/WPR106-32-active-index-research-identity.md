# WPR106-32 Active Index And Research-Only Identity

## Goal

Create the missing active control index, make the repo identity unambiguous as
ResearchEngineDeluxe research-only evidence machinery, and register newly
confirmed P0 blockers without changing source behavior.

This packet does not implement strategies, filters, models, live/paper
behavior, promotion logic, candidate-pack writing, execution changes, data
refreshes, or expensive research runs.

## Current Repo Facts

- Current checkout: `main`, tracking `origin/main`.
- Pre-existing dirty file: `.pytest_cache/v/cache/nodeids`.
- `docs/ACTIVE_INDEX.md` is missing.
- `docs/ORCHESTRATOR_STAGE_LEDGER.md` says Stage R106 is in progress and
  WPR106-01 through WPR106-31 are closed.
- Latest empirical evidence is WPR106-31 discovery-lead replay entry evidence.
  It produced replayed BTC/ETH entry-signal artifacts and blocked top-3
  frozen-entry exit-lab slices.
- No candidate-ready trading claim exists.
- `docs/KNOWN_ISSUES.md` currently reports 0 open P0 issues and 1 open P1, but
  this packet's pre-edit audit found P0 validation and boundary blockers that
  must be tracked before further empirical expansion.

## Conflicts And Stale Docs Found

- `START_HERE.md` and `AGENTS.md` still name `research/v3-experimental-engine`
  as the current branch, while WPR106-21 documents `main` as the migrated R106
  checkout mirror.
- `README.md` opens as `TradingBotSuite Workspace`; the repo identity should be
  ResearchEngineDeluxe, with `tradingbotsuite` kept as the current package
  implementation detail.
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md` remains a useful safety fuse but
  its practical next-work wording is older than WPR106-31.
- Historical stage reports are not rewritten; newer active docs should point to
  current issue status instead.

## Allowed Edit Paths

- `docs/work_packets/WPR106-32-active-index-research-identity.md`
- `docs/ACTIVE_INDEX.md`
- `START_HERE.md`
- `README.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_ACTIVE_INDEX_RESEARCH_IDENTITY_REPORT.md`

## Forbidden Edit Paths

- `src/**`
- `tests/**`
- `configs/**`
- `data/research/**`
- fixture packs
- generated operator-run artifacts
- dependency metadata
- live/runtime/promotion/sizing/order-placement behavior
- `.pytest_cache/**`

## Subagents Used

- Repo Cartographer: docs/tree/stage/known-issues map.
- Safety Gatekeeper: live/research import boundaries, credential risk, artifact
  mode safety.
- Data Contract + Validation Engineer: synthetic fallback, fixture selection,
  label/purge semantics.
- Execution + Artifact Gatekeeper: latency entry pricing and runtime artifact
  validation.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Artifacts Expected

- New active index.
- Updated README/START_HERE identity and current-checkout guidance.
- Updated known-issues registry with newly discovered P0 blockers.
- Updated ledger top status pointing to this packet and preventing stage
  advancement while open P0s exist.
- New stage report.

No generated research data artifacts, candidate packs, or runtime artifacts are
expected.

## Definition Of Done

- Agents have one active index that points to the current stage, latest evidence,
  open blockers, and required next work.
- `KNOWN_ISSUES.md` no longer falsely reports zero open P0 issues.
- ResearchEngineDeluxe is described as a research-only evidence system for
  BTC/ETH perpetual futures; `tradingbotsuite` remains a compatibility package
  name.
- The docs explicitly preserve that zero eligible candidates is valid evidence
  and research outputs are not live signals.
- Baseline compile/contracts/diff validation passes or any failures are
  reported with blockers.

## Rollback Plan

Revert only the WPR106-32 documentation edits listed in the allowed paths. Do
not touch unrelated `.pytest_cache` state, generated evidence, fixture packs, or
source behavior.
