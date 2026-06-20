# WPR106-269 Sandbox Venue Identity Aliases

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Make local multi-venue archive manifests and archive-builder overrides less
brittle by canonicalizing common Binance USD-M, OKX, Bybit, and Hyperliquid
venue identity aliases before descriptor validation.

## Scope

- Add shared sandbox venue canonicalization for descriptor payloads and archive
  manifest builder overrides.
- Cover common local/export labels such as `okex`, `bybit_linear`,
  `bybit_usdm`, `binance_futures`, `binance_um`, `hyperliquid_perp`, and
  `hl_perp`.
- Preserve existing canonical values and descriptor IDs.
- Keep alias handling as descriptor identity normalization only; do not add
  provider downloads, account access, strategy math, or execution behavior.
- Add focused sandbox tests for direct descriptor manifest aliases and archive
  builder override aliases.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-269-sandbox-venue-identity-aliases.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_VENUE_IDENTITY_ALIASES_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/spec.py`
- `src/tradingbotsuite/research_sandbox/archive_manifest.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Direct venue archive manifests with common venue aliases load into canonical
  sandbox venues: `binance_usdm`, `okx`, `bybit`, and `hyperliquid`.
- Archive manifest builder `venue` overrides accept the same aliases while
  preserving deterministic sandbox descriptors and source-integrity metadata.
- Unsupported venue values still fail closed with a clear validation error.
- Generated descriptors retain `research_only`, `observe_only`,
  `promotion_ready: false`, `sandbox_only`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- Validation includes focused sandbox tests, full sandbox tests, package
  compile, import-boundary tests, and the contract baseline when the local
  environment allows it.

## Boundary

This packet only normalizes local sandbox venue descriptor identity. It does
not download provider data, execute sandbox sweeps, execute strict validation,
write candidate artifacts, create paper/live signals, define sizing, place
orders, mutate runtime mode, write live configuration, mutate source archive
files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Added shared sandbox venue alias
canonicalization for direct venue archive descriptors and archive manifest
builder overrides. Common local/export labels now normalize to canonical
`binance_usdm`, `okx`, `bybit`, and `hyperliquid` descriptor values while
unsupported venues still fail closed.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "venue_descriptor_loader_canonicalizes_common_venue_aliases or venue_descriptor_rejects_unknown_venue_alias or venue_override_aliases or archive_manifest_builder"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 10 focused alias/archive-manifest tests passed, 104 sandbox
tests passed, package compileall passed, 11 import-boundary tests passed, and
461 contract tests passed.
