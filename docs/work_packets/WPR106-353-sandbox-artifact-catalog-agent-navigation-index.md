# WPR106-353 Sandbox Artifact Catalog Agent Navigation Index

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add compact agent navigation metadata to sandbox artifact catalog sidecar-index
rows so agents can identify the first sidecars to inspect for strict-validation
triage, source coverage, iteration actions, and replay planning without reading
packet history or hard-coding sidecar filename order.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-353-sandbox-artifact-catalog-agent-navigation-index.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_AGENT_NAVIGATION_INDEX_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only
  where applicable, and promotion-ready false.
- Add read-order/navigation metadata only to catalog sidecar-index rows.
- Do not change sidecar row counts, sidecar payload schemas outside the
  sidecar-index schema, sandbox scoring, ranking math, falsification decisions,
  evidence-request selection, trial IDs, archive routing, source-integrity
  behavior, preflight behavior, replay readiness, or promotion state.
- Do not open per-run evidence request files, open or recompute global
  leaderboard Parquet files, execute sandbox sweeps, iteration replay commands,
  strict validation, provider downloads, candidate-pack writes, paper/live
  signal generation, sizing, order placement, runtime-mode changes, live
  configuration writes, strategy-catalog mutations, archive manifest/source
  mutations, or promotion claims.
- Preserve the 2024+ window policy and keep catalog output as read-only agent
  navigation metadata.

## Plan

1. Add deterministic agent navigation fields to sidecar-index rows.
2. Assign first-read/read-group hints for the highest-value catalog,
   strict-validation, iteration-action, and replay-batch sidecars.
3. Extend artifact catalog tests for the new sidecar-index schema and ordering.
4. Update the sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline and diff hygiene.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-352 added a source-priority sidecar,
  leaving agents with many valid sidecars but no compact read-order metadata in
  the catalog sidecar index itself.
- 2026-06-19: Added deterministic sidecar-index fields:
  `agent_read_order`, `agent_read_group`, `agent_first_read`, and
  `agent_navigation_hint`.
- 2026-06-19: Added explicit first-read navigation for the artifact catalog,
  global source-priority queue, global evidence-request priority queue,
  strict-validation descriptor queue, iteration action plan, and replay batch
  queue, plus deterministic category fallbacks for supporting sidecars.
- 2026-06-19: Extended artifact catalog tests to prove the sidecar index
  exposes the new schema, stable read order, and non-empty navigation hints.

## Validation

- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog"`
  - 2 passed, 172 deselected.
- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  - 174 passed.
- Passed:
  `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  - 11 passed.
- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - 461 passed.
- Passed:
  `git diff --check`
  - No whitespace errors; existing LF-to-CRLF warnings were reported.
- Passed:
  direct trailing-whitespace scan of packet-touched files.

## Closeout

- Closed 2026-06-19. The packet keeps all outputs research-only, observe-only,
  sandbox-only, descriptor-only where applicable, and promotion-ready false. It
  adds only sidecar-index read-order metadata and does not change sidecar row
  counts, sidecar payload schemas outside the sidecar index, artifact
  discovery, sandbox scoring, ranking math, falsification decisions,
  evidence-request selection, trial IDs, archive routing, source-integrity
  behavior, preflight behavior, replay readiness, strict validation behavior,
  candidate-pack state, or promotion state.
- No per-run evidence request file reopen, full leaderboard Parquet
  read/recompute, sandbox sweep execution, iteration replay command execution,
  strict validation execution, provider download, candidate-pack write,
  paper/live signal generation, sizing, order placement, runtime-mode change,
  live configuration write, strategy-catalog mutation, archive manifest/source
  mutation, or promotion claim exists.
