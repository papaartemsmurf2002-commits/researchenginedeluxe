# WPR36-01 Binance USD-M Context Collector

Status: closed
Owner: Codex Research Agent
Stage: Stage R36 Binance USD-M context collector
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Add research-only Binance USD-M provider context collection for funding rate, premium index, and open interest so context-aware fixture packs can be built from fresh non-TradingView provider manifests when the user requests data collection.

## Allowed paths

- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/command_registry.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `tests/live/test_preflight.py`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR36-01-binance-usdm-context-collector.md`
- `docs/stage_reports/STAGE_R36_BINANCE_USDM_CONTEXT_COLLECTOR_REPORT.md`

## Non-goals

- No TradingView export, Pine, or legacy parity input support.
- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital-allocation work.
- No automatic fixture-pack generation or historical-cycle execution in this packet.
- No Binance Vision downloader changes.
- No claims that collected rows are promotion-ready or OOS acceptance evidence.

## Implementation plan

1. Add a local research collector for Binance USD-M funding-rate, premium-index, and open-interest REST context endpoints.
2. Normalize collected rows to deterministic JSONL with `source_name: binance_rest`, `symbol`, `data_family`, `event_time_ms`, and supported context columns.
3. Write manifests with research-only flags, content hashes, row counts, endpoint metadata, no TradingView/synthetic provenance, and receive-time limitations.
4. Allow the fixture builder to consume these Binance REST context manifests without widening legacy or synthetic inputs.
5. Add CLI `collect-binance-context` with bounded approved symbols/families and live-mode rejection.
6. Add focused tests for normalization, manifest shape, builder compatibility, CLI payload, unsupported inputs, and live-preflight registration.
7. Record validation evidence and close only after review and focused validation pass.

## Exit criteria

- The collector writes fixture-builder-compatible local context manifests for supported families.
- CLI output is research-only, observe-only, and not promotion-ready.
- Unsupported symbols/families/periods fail closed.
- Live preflight rejects the new command.
- Focused tests, compile, contracts or relevant suite, live preflight, and diff check pass.

## Completion evidence

- Added research-only Binance USD-M REST context collection for `funding_rate`, `premium_index`, and `open_interest`.
- Collector writes deterministic JSONL plus manifests with `source_name: binance_usdm_rest`, `source_type: rest_backfill`, `event_time_field: event_time_ms`, hashes, row counts, endpoint metadata, and receive-time limitations.
- Collector output remains `research_only`, `observe_only`, and `promotion_ready: false`.
- Added CLI `collect-binance-context` and registered it as a research command rejected by live preflight.
- Fixture builder accepts `binance_usdm_rest` context manifests for funding, premium, and open-interest families.
- Regression coverage verifies a real collector-emitted context manifest can be consumed by `build_provider_kline_fixture_pack`.
- Review found one P1 compatibility bug where a safety note contained the legacy source name and caused fixture-builder rejection; the note was rewritten and the collector-to-builder regression test now covers the path.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\contracts\test_historical_fixture_pack_contract.py tests\live\test_preflight.py -q` passed: 67 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `git diff --check` reported only pre-existing CRLF normalization warnings.
