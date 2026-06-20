# WPR106-257 Sandbox Archive Source Integrity Metadata

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make sandbox archive manifests more reproducible by recording SHA-256 and byte
size metadata for local source archive files. A local archive file edited in
place must be visible in the manifest/build-report evidence and must change
the deterministic archive manifest identity.

## Scope

- Add source-file integrity metadata to sandbox archive manifest build rows.
- Add source-file integrity metadata to generated venue archive descriptors.
- Preserve descriptor loading for older manifests that do not contain source
  integrity metadata.
- Include source integrity in archive manifest identity.
- Add focused tests that source hashes are present and manifest IDs change when
  a source archive file changes.
- Update sandbox contract and stage docs.

## Allowed Paths

- `docs/work_packets/WPR106-257-sandbox-archive-source-integrity-metadata.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_SOURCE_INTEGRITY_METADATA_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/archive_manifest.py`
- `src/tradingbotsuite/research_sandbox/spec.py`
- `src/tradingbotsuite/research_sandbox/intake.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Generated venue archive descriptors include `source_integrity.sha256` and
  `source_integrity.byte_size` for included local archive files.
- Archive build-report rows include source file SHA-256 and byte size.
- The same unchanged source file produces the same archive manifest ID.
- Editing a source file in place changes the generated archive manifest ID.
- Older descriptor manifests without source-integrity metadata still load.
- All metadata remains sandbox-only, research-only, non-promotable, and
  ineligible for candidate packs.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes archive manifest metadata only. It does not execute
sandbox sweeps, execute strict validation, change strategy math, change trial
IDs for completed runs, write candidate packs, create paper/live signals,
define sizing, place orders, change runtime mode, write live configuration,
download provider data, mutate source archive files, or claim promotion
readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Sandbox archive manifest build rows now
record `source_sha256` and `source_byte_size` for scanned local archive files.
Generated venue archive descriptors for included files carry matching
`source_integrity` metadata. Archive manifest identity now includes source
integrity so an in-place source file edit changes the generated manifest ID
while unchanged inputs remain idempotent.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_manifest_builder"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 archive-manifest focused sandbox tests passed, 84 sandbox
tests passed, 11 import-boundary tests passed, package compileall passed, and
the full contract baseline passed with 461 tests on rerun after one known local
Windows pytest-asyncio `WinError 10055` socket setup failure at 460 passed
tests.
