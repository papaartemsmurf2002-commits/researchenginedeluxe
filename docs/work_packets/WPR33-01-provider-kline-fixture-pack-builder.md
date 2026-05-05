# WPR33-01 Provider Kline Fixture Pack Builder

Status: closed
Owner: Codex Research Agent
Stage: Stage R33 provider kline fixture pack builder
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Add a reproducible research-only builder that converts local provider kline manifests into validated historical fixture packs, so checked-in or local BTCUSDT/ETHUSDT fixture packs can be regenerated without ad hoc scripts or TradingView exports.

## Allowed paths

- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/live/test_preflight.py`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR33-01-provider-kline-fixture-pack-builder.md`
- `docs/stage_reports/STAGE_R33_PROVIDER_KLINE_FIXTURE_PACK_BUILDER_REPORT.md`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No TradingView, Pine, marker-parity, or legacy chart-export input support.
- No provider download in this packet; the builder consumes already-local provider manifests and data files.
- No claims that generated compact fixture packs are OOS, stress, profitability, promotion, or performance evidence.

## Implementation plan

1. Add a provider kline fixture-pack builder API to `historical_fixture_pack.py`.
2. Support local Binance USD-M kline cache manifests and local provider JSONL kline manifests produced by existing research collectors.
3. Write cycle and required bars Parquet families with embedded provider provenance and validated manifest hashes.
4. Add CLI command `build-historical-fixture-pack` with explicit research-only output payload.
5. Add the command to the research command registry so live preflight rejects it.
6. Add contract tests for provider-cache input, provider JSONL input, no-TradingView rejection, validation of generated packs, and CLI payload shape.
7. Record validation evidence and close the packet.

## Exit criteria

- Builder output validates with `assert_valid_historical_fixture_pack_manifest`.
- Generated cycle Parquet embeds provider provenance and contiguous source row evidence.
- TradingView/unsupported manifests fail closed.
- CLI command writes a fixture pack from a local provider manifest and reports research-only, observe-only, promotion-ready-false metadata.
- Live preflight rejects `build-historical-fixture-pack`.
- Focused tests, live preflight, compile, contracts, and diff check pass.

## Completion evidence

- Added `build_provider_kline_fixture_pack()` in `src/tradingbotsuite/data/historical_fixture_pack.py`.
- Added CLI command `build-historical-fixture-pack`.
- Registered `build-historical-fixture-pack` as a research command rejected by live preflight.
- Builder supports local Binance USD-M kline cache manifests and provider JSONL kline manifests.
- Builder rejects TradingView provenance, synthetic provenance anywhere in the source manifest, unsupported source/family pairs, source hash mismatches, symbol mismatches, and row interval mismatches.
- Builder writes `cycle_dataset.parquet`, required bars Parquet, and `fixture_pack_manifest.json`, then validates the generated manifest before returning.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\live\test_preflight.py -q` passed: 38 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 83 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py tests\live\test_preflight.py -q` passed: 32 tests.
- CLI smoke against `data\research\chart_ohlcv_cache\BTCUSDT_15m_1760450400000_1776178800000.manifest.json` passed and wrote a validated 12-row temp fixture pack.
- Review found two issues: synthetic provenance outside `source` and row interval mismatch handling. Both were fixed and covered by regression tests.
