# WPR106-267 Sandbox Archive Content Identity Inference

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Reduce manual setup friction for multi-venue local archive drops by allowing
the sandbox archive manifest builder to infer descriptor identity from file
content when paths are generic.

## Scope

- Extend `build_sandbox_archive_manifest()` to infer venue, symbol, data family,
  and interval from common OKX, Bybit, and Hyperliquid export columns when path
  tokens do not identify them.
- Record compact inference-source metadata in build-report rows so agents can
  see whether descriptor identity came from an override, path, content, or
  default.
- Preserve 2024+ filtering, source integrity metadata, deterministic manifest
  IDs, and sandbox boundary flags.
- Add focused sandbox tests using generic filenames with content-carried
  identity.
- Update the sandbox research contract, active index, stage ledger, and stage
  report.

## Allowed Paths

- `docs/work_packets/WPR106-267-sandbox-archive-content-identity-inference.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_CONTENT_IDENTITY_INFERENCE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/archive_manifest.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Generic local archive files can be turned into venue descriptors when content
  columns carry venue/exchange/provider, symbol/instrument/coin, interval/bar,
  or data-family/channel hints.
- Build-report rows expose inference-source fields for included descriptors.
- Existing path/override inference remains stable and deterministic.
- Generated descriptors retain source integrity metadata, diagnostic-only
  status, `research_only`, `observe_only`, `promotion_ready: false`, and
  `candidate_pack_eligible: false`.
- Validation includes focused archive-manifest tests, full sandbox tests,
  package compile, import-boundary tests, and the contract baseline when the
  local environment allows it.

## Boundary

This packet only improves local archive manifest construction from already
available local files. It does not download provider data, execute sandbox
sweeps, execute strict validation, write candidate artifacts, create paper/live
signals, define sizing, place orders, mutate runtime mode, write live
configuration, mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. The sandbox archive manifest builder now
falls back from overrides and path tokens to content-derived identity hints for
venue, symbol, data family, and interval. Build-report rows expose inference
source fields for included descriptors, and generated descriptors still carry
source integrity metadata and sandbox boundary flags.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_manifest_builder"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py -q -k "provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest"
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q -k "not provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest"
```

Final results: 4 focused archive-manifest tests passed, 96 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, full
contracts reached 460 passed tests and then hit known `ISSUE-R106-026` Windows
`WinError 10055` during pytest-asyncio event-loop socketpair setup before the
affected async test body, the isolated affected async test failed at the same
setup point, and the non-affected contract baseline passed with 460 tests and 1
deselected.
