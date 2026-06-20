# WPR106-236 Sandbox Strict Validation Request Bundle

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a descriptor-only handoff bundle from Rapid Strategy Iteration Sandbox
evidence requests into the existing strict historical validation cycle. Agents
should be able to collect, dedupe, and prioritize run-level or suite-level
sandbox evidence requests without executing strict validation, writing
candidate packs, or creating live/paper artifacts.

## Scope

- Add a sandbox validation-request bundle writer for a single sandbox run.
- Add a sandbox validation-request bundle writer for a sandbox suite.
- Read only existing sandbox evidence-request JSON artifacts.
- Validate sandbox boundary flags on source manifests and request descriptors.
- Dedupe requests deterministically by strict-validation target identity.
- Write compact descriptor artifacts:
  - `strict_validation_request_bundle.json`;
  - `strict_validation_request_bundle.parquet`;
  - `suite_strict_validation_request_bundle.json`;
  - `suite_strict_validation_request_bundle.parquet`.
- Include strict-cycle handoff metadata such as requested command,
  descriptor-only execution mode, required evidence, source run/suite/case
  provenance, and source sandbox metrics.
- Preserve `research_only`, `observe_only`, `promotion_ready: false`,
  `sandbox_only`, `candidate_evidence: false`, and `candidate_pack_eligible:
  false` on bundle manifests and descriptor rows.
- Add a research CLI command
  `export-rapid-strategy-sandbox-validation-requests` with mutually exclusive
  `--run-dir` and `--suite-dir` inputs under the configured research output
  root.
- Register the command as research-owned and add boundary contract coverage.
- Add focused sandbox and live-boundary tests.
- Update sandbox docs and stage closeout docs.

## Allowed Paths

- `docs/work_packets/WPR106-236-sandbox-strict-validation-request-bundle.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_REQUEST_BUNDLE_REPORT.md`
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

- A run-level bundle reads `evidence_requests.json`, dedupes descriptors, and
  writes JSON/Parquet handoff artifacts beside the sandbox run by default.
- A suite-level bundle reads `suite_evidence_requests.json`, dedupes
  descriptors, and writes JSON/Parquet handoff artifacts beside the sandbox
  suite by default.
- Bundle descriptor rows include source request/trial/run IDs, hypothesis,
  family, venue, symbol, strict validation command, required evidence,
  descriptor-only execution mode, source metrics, and provenance paths.
- Bundle and row payloads carry the required sandbox boundary flags.
- The CLI rejects `--run-dir`, `--suite-dir`, or `--output-dir` outside the
  configured research output root.
- The CLI command is listed in the research command registry and boundary
  contract.
- Validation includes focused sandbox tests, CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline.

## Boundary

This packet emits strict-validation request descriptors only. It does not
execute strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, mutate runtime mode, write live configuration, or
claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The packet added run-level and
suite-level strict-validation request bundle exports, deterministic request
dedupe, JSON/Parquet descriptor writing,
`export-rapid-strategy-sandbox-validation-requests` CLI wiring,
research-command registry coverage, boundary-contract coverage, and focused
tests for descriptor-only handoff fields, suite request dedupe, CLI output-root
enforcement, and research-root path rejection.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results were 43 sandbox tests passed, 12 CLI boundary tests passed, 11
import-boundary tests passed, package compileall passed, and 461 contract tests
passed.
