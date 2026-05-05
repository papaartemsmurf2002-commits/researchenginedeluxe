# WPR37-01 BTCUSDT Context Fixture Data Run

Status: closed
Owner: Codex Research Agent
Stage: Stage R37 BTCUSDT context fixture data run
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Use the research-only provider data tools to collect a small BTCUSDT Binance USD-M context dataset and build a generated context-aware fixture pack from the existing local provider kline cache plus newly collected funding, premium, and open-interest manifests.

## Allowed paths

- `data/research/market_data/binance_usdm/**`
- `data/research/fixtures/btcusdt_context_provider_v1/**`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR37-01-btcusdt-context-fixture-data-run.md`
- `docs/stage_reports/STAGE_R37_BTCUSDT_CONTEXT_FIXTURE_DATA_RUN_REPORT.md`

## Non-goals

- No TradingView export, Pine, or legacy parity input support.
- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital-allocation work.
- No checked-in replacement of the existing `btcusdt_v1` fixture.
- No OOS acceptance, performance claim, candidate promotion, or Stage 13 execution.

## Implementation plan

1. Reuse the local Binance USD-M kline cache manifest already used by WPR32.
2. Collect BTCUSDT funding-rate, premium-index, and open-interest context around the fixture tail window using `collect-binance-context`.
3. Remove any emitted legacy-source literal from generated fixture notes if artifact validation finds one.
4. Build a generated context-aware fixture pack using `build-historical-fixture-pack --context-manifest`.
5. Validate the generated fixture manifest and record hashes, row counts, context families, and limitations.
6. Stop and report if provider access fails or any generated manifest fails validation.

## Exit criteria

- Context manifests are collected locally with research-only/non-promotion flags.
- Generated fixture pack validates and includes funding, premium, and open-interest families.
- TradingView and synthetic provenance are absent.
- Validation evidence is recorded in a stage report.

## Completion evidence

- Reused local Binance USD-M kline cache manifest `data/research/chart_ohlcv_cache/BTCUSDT_15m_1760450400000_1776178800000.manifest.json`.
- Collected BTCUSDT funding-rate context for `1776021300000` to `1776178800000`: 5 rows, content hash `sha256:ecfb31b294d3c5b5c7a6641612a67055723b10eab78ea62936c4eb7a4a3876c0`.
- Collected BTCUSDT premium-index context for `1776049200000` to `1776178800000`: 145 rows, content hash `sha256:aeaef988d402b70725cef8f5f1cdf60317b87216cdfdd159f73bcd2ecb7dba7e`.
- Collected BTCUSDT open-interest context for `1776049200000` to `1776178800000`: 145 rows, content hash `sha256:65d7655303580df1106c57af4cef9a6129cca60238037ca1ae0c01fdf47f8818`.
- Built generated fixture pack `data/research/fixtures/btcusdt_context_provider_v1/fixture_pack_manifest.json`.
- Generated fixture ID: `btcusdt-context-provider-v1`.
- Generated fixture row count: 144.
- Generated fixture manifest hash: `7c97dfb0abfd8459e72998815b8fee25af42aac78fd0e9bd1cf9ef3523e26464`.
- Included optional context families: `funding_rate`, `premium_index`, `open_interest`.
- Omitted optional families: `agg_trade`, `lower_timeframe_bars`.
- Artifact audit confirmed `tradingview_source_used: false`, `synthetic_source_used: false`, and no deprecated chart-export source text in artifact string values.

## Validation

- `collect-binance-context` succeeded for funding-rate, premium-index, and open-interest context manifests.
- `build-historical-fixture-pack` succeeded with all three collected context manifests.
- Explicit fixture manifest validation through `assert_valid_historical_fixture_pack_manifest` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py -q` passed: 27 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `git diff --check` reported only pre-existing CRLF normalization warnings.
