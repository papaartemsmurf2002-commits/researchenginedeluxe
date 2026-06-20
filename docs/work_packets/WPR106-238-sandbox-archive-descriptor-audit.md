# WPR106-238 Sandbox Archive Descriptor Audit

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a fast archive descriptor audit for Rapid Strategy Iteration Sandbox venue
manifests. Agents should be able to verify local OKX, Bybit, Hyperliquid,
Binance, or local descriptor data paths and 2024+ window coverage before
launching larger strategy sweeps.

## Scope

- Add a sandbox archive descriptor audit for venue archive manifest JSON files.
- Reuse existing sandbox venue descriptor and market-frame loaders.
- Support descriptor-local `data_path` routing and optional shared smoke
  `--market-data`.
- Write compact JSON and Parquet audit artifacts:
  - `archive_descriptor_audit.json`;
  - `archive_descriptor_audit.parquet`.
- Include descriptor ID, venue, symbol, family, interval, routing mode, source
  path, normalized row counts, descriptor-window row counts, timestamp bounds,
  OHLC availability, status, and blocker/warning reasons.
- Preserve required sandbox boundary flags on audit manifests and rows.
- Add a research CLI command `audit-rapid-strategy-sandbox-archives` with
  research-root `--output-dir` enforcement.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-238-sandbox-archive-descriptor-audit.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_DESCRIPTOR_AUDIT_REPORT.md`
- `docs/contracts/boundary_contract.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `src/tradingbotsuite/research_sandbox/**`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- The audit reports ready descriptors with normalized 2024+ row counts and
  descriptor-window row counts.
- The audit reports blocked descriptors for missing data paths or no rows in
  the requested 2024+ descriptor window.
- Descriptor-local relative paths resolve through the existing descriptor
  loader.
- Audit JSON and Parquet rows carry `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- The CLI rejects `--output-dir` outside the configured research output root.
- The CLI command is listed in the research command registry and boundary
  contract.
- Validation includes focused sandbox tests, CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline.

## Boundary

This packet audits local sandbox archive descriptors only. It does not execute
strategy sweeps, execute strict validation, write candidate packs, create
paper/live signals, define sizing, place orders, mutate runtime mode, write
live configuration, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added sandbox archive
descriptor auditing, descriptor-local and shared smoke market-data routing,
JSON/Parquet audit artifacts, `audit-rapid-strategy-sandbox-archives` CLI
wiring, research-command registry coverage, boundary-contract coverage, and
focused tests for ready descriptors, blocked descriptors, shared-market smoke
audits, idempotent agent preflight reruns, CLI artifact placement, and
research-root path rejection.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results were 49 sandbox tests passed, 14 CLI boundary tests passed, 11
import-boundary tests passed, package compileall passed, and 461 contract tests
passed.
