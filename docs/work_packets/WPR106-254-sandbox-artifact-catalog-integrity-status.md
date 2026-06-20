# WPR106-254 Sandbox Artifact Catalog Integrity Status

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make sandbox artifact discovery safer for agent workflows by surfacing run and
suite child-artifact integrity status directly in the sandbox artifact catalog.
Agents should see whether indexed run/suite artifacts still match manifest
SHA-256 and byte-size metadata without executing sweeps or strict validation.

## Scope

- Extend sandbox artifact catalog rows for run and suite manifests with
  read-only integrity verification summary fields.
- Reuse the WPR106-253 verifier in no-report mode.
- Preserve existing catalog artifact kinds, paths, row counts, and boundary
  flags.
- Keep non-run/suite artifacts indexed without integrity verification.
- Add focused tests for passed and failed integrity status in catalog rows.
- Update sandbox contract and stage docs.

## Allowed Paths

- `docs/work_packets/WPR106-254-sandbox-artifact-catalog-integrity-status.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_INTEGRITY_STATUS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Catalog rows for `manifest.json` include integrity verification status and
  checked/matched/failed counts.
- Catalog rows for `suite_manifest.json` include integrity verification status
  and checked/matched/failed counts.
- A tampered run child artifact is visible as failed integrity in the catalog.
- Non-run/suite artifacts remain indexed with `integrity_verification_status`
  set to `not_applicable`.
- Catalog indexing remains read-only with respect to source artifacts and does
  not write verifier reports.
- All catalog rows remain sandbox-only, research-only, non-promotable, and
  ineligible for candidate packs.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes only artifact catalog metadata. It does not execute sandbox
sweeps, execute strict validation, alter strategy math, change trial IDs, write
candidate packs, create live/paper signals, define sizing, place orders, change
runtime mode, write live configuration, download provider data, mutate source
artifacts, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Sandbox artifact catalog rows for
`manifest.json` and `suite_manifest.json` now include integrity verification
summary fields populated by the WPR106-253 verifier in no-report mode. The
catalog records passed, failed, missing, mismatched, and verification-error
states without writing verifier reports or modifying source artifacts.

Non-run/suite artifacts remain indexed with
`integrity_verification_status: not_applicable`. Catalog rows preserve existing
artifact kind, path, count, and sandbox boundary fields.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 79 sandbox tests passed, 11 import-boundary tests passed,
package compileall passed, and the full contract baseline passed with 461
tests on rerun after one known local Windows pytest-asyncio `WinError 10055`
socket setup failure at 460 passed tests.
