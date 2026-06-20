# WPR106-239 Sandbox Archive Manifest Builder

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a fast local archive manifest builder for the Rapid Strategy Iteration
Sandbox. Agents should be able to point at one or more local archive roots and
materialize a loadable venue archive manifest for 2024+ sandbox sweeps without
hand-writing descriptor JSON.

## Scope

- Add a sandbox archive manifest builder for local CSV, TSV, JSON, JSONL,
  Parquet, and simple Binance Vision kline ZIP files.
- Infer venue, symbol, data family, and interval from archive paths and file
  names, with optional CLI overrides for controlled agent workflows.
- Reuse the existing sandbox market-frame loader so pre-2024 rows are ignored
  before descriptor windows are written.
- Write compact research-only artifacts:
  - `venue_archives.json`;
  - `archive_manifest_build_report.json`;
  - `archive_manifest_build_report.parquet`.
- Report included descriptors, skipped files, row counts, timestamp bounds,
  inferred fields, and skip reasons.
- Keep repeated builds deterministic and idempotent for agent preflight loops.
- Add a research CLI command `build-rapid-strategy-sandbox-archive-manifest`
  with research-root `--output-dir` enforcement.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-239-sandbox-archive-manifest-builder.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_MANIFEST_BUILDER_REPORT.md`
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

- The builder writes a loadable `venue_archives.json` manifest from local
  archive files with 2024+ descriptor windows.
- The builder skips unsupported files, files that cannot be loaded, files with
  no 2024+ rows, or files with insufficient inferred/overridden descriptor
  identity, and records explicit skip reasons.
- Optional venue/symbol/data-family/interval overrides work for local archive
  folders whose names are not self-describing.
- Manifest and report rows carry `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Repeated builds with the same roots and overrides refresh the same
  deterministic artifact directory.
- The CLI rejects `--output-dir` outside the configured research output root.
- The CLI command is listed in the research command registry and boundary
  contract.
- Validation includes focused sandbox tests, CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline.

## Boundary

This packet builds local sandbox archive descriptor manifests only. It does not
download provider data, execute strategy sweeps, execute strict validation,
write candidate packs, create paper/live signals, define sizing, place orders,
mutate runtime mode, write live configuration, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added local sandbox archive
manifest building, path/name inference for venue, symbol, data family, and
interval, explicit CLI overrides, deterministic/idempotent manifest directories,
skip-reason reporting, JSON/Parquet build reports,
`build-rapid-strategy-sandbox-archive-manifest` CLI wiring,
research-command registry coverage, boundary-contract coverage, sandbox
contract coverage, artifact-catalog discovery for generated manifests/reports,
and focused tests for multi-venue inference, skipped files, downstream audit
consumption, catalog indexing, idempotent overrides, CLI execution, and
research-root path rejection.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final focused results were 52 sandbox tests passed, 15 CLI boundary tests
passed, 11 import-boundary tests passed, and package compileall passed. The
full contract baseline was attempted repeatedly and reached 460 passed tests
before failing during pytest-asyncio event-loop socketpair setup for one async
contract test with Windows `WinError 10055`, before the test body ran. The
targeted async contract rerun and selector-policy rerun failed the same way.
`ISSUE-R106-026` records this local validation-environment blocker.
