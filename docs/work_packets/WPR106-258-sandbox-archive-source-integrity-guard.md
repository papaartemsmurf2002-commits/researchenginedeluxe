# WPR106-258 Sandbox Archive Source Integrity Guard

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make sandbox archive consumers fail closed when a venue descriptor carries
source-file integrity metadata that no longer matches the current local file.
Archive audit, compatibility preflight, and archive-backed sweeps must not
silently read a changed source file after manifest generation.

## Scope

- Add shared descriptor source-integrity validation for local archive files.
- Use the validation before descriptor-routed market-frame reads.
- Surface source-integrity mismatches as audit/preflight blocker reasons.
- Preserve shared-market-data smoke behavior and older descriptors without
  source-integrity metadata.
- Add focused tests for loader, audit, and preflight mismatch behavior.
- Update sandbox contract and stage docs.

## Allowed Paths

- `docs/work_packets/WPR106-258-sandbox-archive-source-integrity-guard.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_SOURCE_INTEGRITY_GUARD_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/market_data.py`
- `src/tradingbotsuite/research_sandbox/archive_audit.py`
- `src/tradingbotsuite/research_sandbox/preflight.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Descriptor-routed market-frame loading raises on source SHA-256 or byte-size
  mismatch when descriptor `source_integrity` is present.
- Archive descriptor audits report source-integrity mismatches as blockers
  instead of marking a descriptor ready.
- Compatibility preflight reports source-integrity mismatches as blockers
  instead of runnable trials.
- Shared-market-data smoke mode remains available and is not bound to
  descriptor source integrity.
- Older descriptors without source-integrity metadata still load.
- All outputs remain sandbox-only, research-only, non-promotable, and
  ineligible for candidate packs.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet changes local archive source validation only. It does not execute
strict validation, change strategy math, change trial IDs, write candidate
packs, create paper/live signals, define sizing, place orders, change runtime
mode, write live configuration, download provider data, mutate source archive
files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Added shared descriptor source-integrity
validation for local archive files and wired it into descriptor-routed market
frame loading, archive descriptor audit, and compatibility preflight.

Descriptor-routed loads now raise before reading when descriptor
`source_integrity` no longer matches the current local file. Archive audits and
preflights surface `source_integrity_sha256_mismatch` and
`source_integrity_byte_size_mismatch` as blocker reasons. Shared-market-data
smoke mode remains available and is not bound to descriptor source hashes.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "source_integrity or descriptor_source"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 2 source-integrity focused sandbox tests passed, 86 sandbox
tests passed, 11 import-boundary tests passed, package compileall passed, and
the full contract baseline passed with 461 tests.
