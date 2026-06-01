# Stage R106 Active Index Research Identity Report

Work packet:
`docs/work_packets/WPR106-32-active-index-research-identity.md`

Date: 2026-05-31

## Summary

WPR106-32 creates the active control index requested by the orchestrator
roadmap and clarifies the repository identity:

> ResearchEngineDeluxe is a research-only evidence system for BTC/ETH
> perpetual futures. The Python package name `tradingbotsuite` remains a
> compatibility implementation detail.

This packet is documentation and governance only. It does not edit source code,
tests, configs, dependency metadata, fixture packs, generated research
artifacts, live runtime behavior, order placement, sizing, candidate-pack
eligibility, or promotion logic.

## Inputs Read

Before edits, the packet read the required control documents and current repo
state:

- `AGENTS.md`
- `START_HERE.md`
- missing `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- latest R106 stage reports and work packets, especially WPR106-29 through
  WPR106-31
- `docs/contracts/README.md`
- `docs/repo_cartography/REPO_INVENTORY.md`
- current git branch/status

The current checkout is `main`, tracking `origin/main`. The pre-existing dirty
file `.pytest_cache/v/cache/nodeids` was not touched.

## Subagent Findings

Repo cartography found `docs/ACTIVE_INDEX.md` missing and confirmed that the
latest closed empirical packet is WPR106-31. It also confirmed that WPR106-21
documents `main` as the migrated R106 checkout mirror.

Safety review found a P0 credential-boundary risk: local Hyperliquid testnet
credential files can imply live/testnet enablement without explicit
`TBS_HL_ENABLE_LIVE=true`.

Data and validation review found P0 validation gaps around synthetic fallback,
implicit source selection, missing `LabelSpec`, and fixed-bar purge for labels
that need event-end-aware purging.

Execution and artifact review found P0 execution/artifact gaps: lower-timeframe
entry pricing is only labeled, not used, and generic live artifact validation
is not fail-closed for unknown manifests.

## Code And Docs Changes

Added:

- `docs/ACTIVE_INDEX.md`
- `docs/work_packets/WPR106-32-active-index-research-identity.md`
- `docs/stage_reports/STAGE_R106_ACTIVE_INDEX_RESEARCH_IDENTITY_REPORT.md`

Updated:

- `README.md`
- `START_HERE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

The active index now records:

- canonical ResearchEngineDeluxe identity;
- current local checkout as `main`;
- active Stage R106 state;
- WPR106-31 as latest replay evidence;
- no candidate-ready claim;
- open P0 blockers;
- required read order;
- near-term P0 work order;
- research-only boundary rules.

## Issue Registry Update

`docs/KNOWN_ISSUES.md` now records the actual active stop condition:

- `ISSUE-R106-008` resolved: active index and identity missing.
- `ISSUE-R106-009` open: CI/reproducible research install checks missing.
- `ISSUE-R106-010` open: synthetic fallback and source selection are not
  explicit enough.
- `ISSUE-R106-011` open: generic purge is fixed-bar based instead of
  label/event-end aware.
- `ISSUE-R106-012` open: lower-timeframe entry pricing is labeled but not used.
- `ISSUE-R106-013` open: credential files can imply Hyperliquid live/testnet
  enablement.
- `ISSUE-R106-014` open: runtime artifact validation is not mode-aware and not
  fail-closed for unknown manifests.

Current issue summary after this packet:

- P0 open: 6
- P0 resolved: 2
- P1 open: 1

Open P0 issues block stage advancement and empirical expansion.

## Interpretation

WPR106-31 replay evidence remains useful, but it is not enough to proceed into
candidate-ready claims. The next empirical R106 work remains the historical
cycle overlay/backtest/ranking path for replayed KNN prediction artifacts, then
full exit lab, multiple testing, validation floors, and candidate-pack
eligibility. That empirical work should wait until the registered P0 validation
and boundary issues are resolved.

Zero eligible candidates remains valid evidence. Candidate gates must not be
weakened.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Observed:

- compileall passed.
- contract tests: 427 passed in 5.86 seconds.
- `git diff --check` passed with line-ending warnings only.

## Boundary

This packet did not add strategies, filters, models, paper/live behavior,
promotion logic, candidate packs, generated research artifacts, runtime mode
changes, live configuration writes, sizing behavior, or order placement.

The correct next packet is P0-B or another explicitly scoped P0 closure packet,
not empirical expansion.
