# WPR106-253 Sandbox Artifact Integrity Verifier

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a read-only verifier for Rapid Strategy Iteration Sandbox run and suite
artifacts. Agents should be able to check manifest-recorded SHA-256 and
byte-size metadata before trusting a sandbox handoff, without rerunning
backtests, executing strict validation, or touching live-adjacent state.

## Scope

- Add a sandbox artifact-integrity verification module for existing run and
  suite manifests.
- Verify child artifact files against `artifact_integrity` metadata and report
  matched, missing, and mismatched rows.
- Write optional JSON/Parquet verification reports that remain sandbox-only,
  research-only, observe-only, and non-promotable.
- Add a CLI command for agent workflows.
- Register the command as a research command so live-mode guards reject it.
- Add focused tests for passing run verification, passing suite verification,
  tamper detection, and CLI output-root boundaries.
- Update the sandbox contract and active stage docs.

## Allowed Paths

- `docs/work_packets/WPR106-253-sandbox-artifact-integrity-verifier.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_INTEGRITY_VERIFIER_REPORT.md`
- `docs/contracts/boundary_contract.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/integrity.py`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/research_sandbox/**`
- `tests/live/test_cli_boundary.py`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Existing sandbox run manifests can be verified from a run directory or
  manifest path.
- Existing sandbox suite manifests can be verified from a suite directory or
  manifest path.
- Verification reports include expected and actual SHA-256 and byte size per
  child artifact.
- Missing metadata, missing files, and hash/size mismatches fail closed in the
  report.
- The verifier does not modify source child artifacts and does not run strict
  validation.
- The CLI writes only under the configured research output root when an output
  directory is provided.
- Generated verification reports remain sandbox-only, research-only,
  non-promotable, and ineligible for candidate packs.
- Validation includes focused sandbox tests, live CLI boundary tests,
  import-boundary tests, package compile, and the contract baseline when the
  local validation environment allows pytest-asyncio socket setup.

## Boundary

This packet is read-only with respect to existing sandbox run/suite artifacts
except for optional verification report output. It does not alter strategy
math, trial IDs, rankings, scoring, strict validation, candidate-pack gates,
live/paper signals, sizing, order placement, runtime mode, live configuration,
provider downloads, archive loading, or promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The sandbox now exposes
`verify_sandbox_artifact_integrity()` plus the
`verify-rapid-strategy-sandbox-artifacts` research CLI command. The verifier
accepts a run directory, suite directory, or manifest path under the research
output root, compares manifest-recorded SHA-256 and byte-size metadata against
current child artifacts, and writes optional JSON/Parquet verification reports.

Verification rows fail closed for missing integrity metadata, missing artifact
paths, missing files, and hash/size mismatches. Reports keep sandbox boundary
flags, record `strict_validation_executed: false` and
`candidate_pack_written: false`, and do not modify source child artifacts.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 78 sandbox tests passed, 20 live CLI boundary tests passed, 11
import-boundary tests passed, package compileall passed, and the full contract
baseline passed with 461 tests on rerun after one known local Windows
pytest-asyncio `WinError 10055` socket setup failure at 460 passed tests.
