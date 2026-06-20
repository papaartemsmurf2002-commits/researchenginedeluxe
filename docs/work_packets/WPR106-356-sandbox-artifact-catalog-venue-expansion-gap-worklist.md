# WPR106-356 - Sandbox Artifact Catalog Venue Expansion Gap Worklist

## Status

closed

## Objective

Add a compact catalog-level Parquet worklist that flattens already-emitted
iteration action-plan venue-expansion samples into one queryable sidecar for
agents. The sidecar must let follow-on agents find OKX, Bybit, and
Hyperliquid archive descriptor repair/add targets without opening every
iteration index JSON or action-plan row.

## Allowed paths

- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/contracts/sandbox_research_contract.md`
- `docs/work_packets/WPR106-356-sandbox-artifact-catalog-venue-expansion-gap-worklist.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_VENUE_EXPANSION_GAP_WORKLIST_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Boundary constraints

- Research-only output only.
- Derive rows only from already-loaded iteration index action-plan payloads.
- Do not mutate archive manifests, source files, strategy catalogs, or
  generated iteration artifacts.
- Do not download venue data.
- Do not execute replay commands, sandbox sweeps, strict validation, or
  candidate-pack writes.
- Do not weaken the 2024+ sandbox window boundary.
- Preserve trial IDs, scoring, ranking, evidence-request selection, archive
  routing, preflight behavior, replay readiness, and promotion state.

## Implementation notes

- Add a sidecar named
  `sandbox_artifact_catalog_iteration_venue_expansion_gap_worklist.parquet`.
- Register it in the catalog sidecar index with first-read agent navigation
  metadata for iteration action triage.
- Flatten only `repair_or_add_venue_expansion_archives` action-plan items and
  their bounded `venue_expansion_gap_samples`.
- Expose top-level catalog counts by target venue, target action, target
  status, and source iteration/action identity.
- Write an empty-schema Parquet file when no venue-expansion action samples
  exist.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "iteration_index_summarizes_agent_iterations_and_briefs or artifact_catalog"`
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
- `git diff --check`

## Closure

Closed after the sandbox artifact catalog writes
`sandbox_artifact_catalog_iteration_venue_expansion_gap_worklist.parquet`,
registers it in the sidecar index with first-read agent navigation metadata,
and exposes top-level worklist counts without changing archive descriptors,
replay execution, strict validation, candidate-pack state, or promotion state.
Validation is recorded in
`docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_VENUE_EXPANSION_GAP_WORKLIST_REPORT.md`.
