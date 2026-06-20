# WPR106-334 Sandbox Analysis Bucket Rollups

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add bounded, agent-readable bucket rollups to sandbox run analysis reports so
agents can identify promising or failing venue, family, exit, filter, and
venue/family clusters without scanning every ranking row.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-334-sandbox-analysis-bucket-rollups.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ANALYSIS_BUCKET_ROLLUPS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/analytics.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep analysis outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Derive rollups only from existing integrity-checked sandbox ranking rows and
  descriptor-only evidence requests.
- Do not execute sandbox sweeps, iteration replay commands, strict validation,
  provider downloads, candidate-pack writes, paper/live signal generation,
  sizing, order placement, runtime-mode changes, live configuration writes,
  strategy-catalog mutations, archive manifest/source mutations, or promotion
  claims.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness,
  strict-validation descriptor queues, artifact catalog sidecars, and the
  2024+ window policy.

## Plan

1. Add a bounded rollup builder over existing ranking rows and
   evidence-request source trial IDs.
2. Expose rollups in `analysis_summary.json` with bucket identity, counts,
   best representative trial, and non-authorizing boundary fields.
3. Extend sandbox regressions for populated rollups and report parity.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-333. Current analysis reports expose
  counts and top rows but no compact bucket-level leaderboard for agent
  triage.
- 2026-06-19: Added bounded analysis bucket rollups for venue, family, exit
  profile, exit variant, filter variant, and venue/family clusters.
- 2026-06-19: Added representative best-trial fields, status counts,
  positive-net counts, evidence-request counts, and explicit non-authorizing
  flags to each rollup while preserving source rankings.
- 2026-06-19: Extended the compact sandbox analysis regression to assert
  populated rollups, boundary flags, representative trial identity, and JSON
  report parity.

## Validation

- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "sandbox_analysis_summarizes_compact_artifacts"`
  passed with 1 passed and 173 deselected.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  passed with 174 passed.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
  passed.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  passed with 11 passed.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  passed with 461 passed.

## Closeout

Closed 2026-06-19. WPR106-334 keeps sandbox analysis reports research-only and
non-authorizing while adding compact bucket rollups for faster agent triage of
promising or failing run clusters. No candidate pack, paper/live signal,
order/sizing/runtime change, provider download, replay execution, validation
execution, strategy catalog mutation, archive manifest/source mutation, live
configuration write, or promotion claim was added.
