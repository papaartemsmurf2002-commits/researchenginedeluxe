# WPR106-345 Sandbox Global Leaderboard Evidence-Request Source Context

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose bounded source context for global leaderboard evidence-request trial IDs
so agents can route strict-validation descriptors from global leaderboard and
catalog artifacts without reopening each per-run `evidence_requests.json`
payload.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-345-sandbox-global-leaderboard-evidence-request-source-context.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_LEADERBOARD_EVIDENCE_REQUEST_SOURCE_CONTEXT_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/leaderboard.py`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only,
  and promotion-ready false.
- Derive source context only from already loaded sandbox
  `evidence_requests.json` descriptors and global leaderboard JSON preview
  rows.
- Keep context previews bounded and compact; do not make global leaderboard or
  catalog sidecars a full replay of per-run evidence request files.
- Do not execute sandbox sweeps, iteration replay commands, strict validation,
  provider downloads, candidate-pack writes, paper/live signal generation,
  sizing, order placement, runtime-mode changes, live configuration writes,
  strategy-catalog mutations, archive manifest/source mutations, or promotion
  claims.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  the 2024+ window policy.

## Plan

1. Add a bounded evidence-request source-context preview to global leaderboard
   top hypothesis rows from loaded descriptor payloads.
2. Flatten compact source-context fields into global catalog evidence-request
   rows and the bounded priority queue where a preview row is available.
3. Preserve stable empty-schema Parquet behavior and non-authorizing boundary
   flags.
4. Extend focused global leaderboard and artifact catalog regression coverage.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-344 added a bounded catalog priority
  queue but left top request rows without the source-trial market/archive
  context already present in per-run evidence request descriptors.
- 2026-06-19: Added a bounded 50-row
  `evidence_request_source_contexts` preview to global leaderboard top
  hypotheses from already-loaded evidence-request descriptors.
- 2026-06-19: Flattened compact source context fields into catalog global
  evidence-request rows and the bounded global evidence-request priority queue.
- 2026-06-19: Added catalog context availability/routing summaries, stable
  empty-schema Parquet coverage, and focused regression assertions.
- 2026-06-19: Updated the sandbox contract, active index, stage ledger, and
  stage report.

## Validation

- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "global_leaderboard or artifact_catalog"`
  - 4 passed, 170 deselected.
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
  does not execute sandbox sweeps, iteration replay commands, strict
  validation, provider downloads, candidate-pack writes, paper/live signal
  generation, sizing, order placement, runtime-mode changes, live
  configuration writes, strategy-catalog mutations, archive manifest/source
  mutations, or promotion claims.
