# WPR106-376 - Deterministic Archive Fixture Checksums

## Status

closed

## Objective

Repair a broad validation blocker where generated Binance Vision fixture ZIP
payloads could hash differently between the archive fetch and `.CHECKSUM`
fetch because the test helper regenerated ZIP metadata on each call.

## Dependencies

- `RAPID_STRATEGY_SANDBOX_AUDIT.md`
- `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md`
- `docs/work_packets/WPR106-363-red-test-repair-strategy-discovery-resume.md`
- `docs/work_packets/WPR106-375-sandbox-container-loader-bounds.md`

## Allowed paths

- `tests/tradingbotsuite/test_market_data_collection.py`
- `docs/work_packets/WPR106-376-deterministic-archive-fixture-checksums.md`
- `docs/stage_reports/STAGE_R106_DETERMINISTIC_ARCHIVE_FIXTURE_CHECKSUMS_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Boundary constraints

- Test-fixture determinism only.
- Do not change production archive download, checksum validation, quality
  gates, candidate-depth thresholds, sandbox behavior, provider downloads, live
  behavior, candidate-pack gates, or promotion semantics.

## Acceptance criteria

- Fixture ZIP payload generation is byte-stable across repeated calls with the
  same rows and member name.
- The duplicate-source-bars regression reaches the intended quality gate
  failure instead of an incidental checksum mismatch.
- Broader `tests/tradingbotsuite tests/integration` chunk no longer fails on
  the checksum fixture.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py::test_collect_candidate_depth_public_archive_fixtures_rejects_duplicate_source_bars -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite tests\integration -q -p no:cacheprovider
git diff --check
```

Exit evidence:

- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py::test_archive_fixture_zip_payload_helper_is_byte_stable tests\tradingbotsuite\test_market_data_collection.py::test_collect_candidate_depth_public_archive_fixtures_rejects_duplicate_source_bars -q`
  - `2 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_engine.py::test_hyperliquid_stream_dedupes_duplicate_fills_across_channels -q -p no:cacheprovider`
  - `1 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite tests\integration -q -p no:cacheprovider`
  - `410 passed, 2 warnings`
- `python -m compileall -q src\tradingbotsuite`
  - passed
- `git diff --check`
  - passed with existing LF-to-CRLF warnings only

Note: the first broad retry after the checksum fix hit Windows `WinError
10055` during pytest-asyncio event-loop setup before the affected test body
ran. The targeted async test passed on direct retry, and the full
`tests\tradingbotsuite tests\integration` chunk then passed.

## Stop conditions

- A test-only fix weakens checksum validation or archive quality validation.
- Production downloader behavior changes.
