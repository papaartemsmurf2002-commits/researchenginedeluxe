# WPR41-01 Latest-Month Provider Context Cycle

Status: closed
Owner: Codex Research Agent
Stage: Stage R41 latest-month provider context cycle
Opened: 2026-05-05
Closed: 2026-05-05

## Objective

Use the direct research-only Binance USD-M collectors to build the broadest current BTCUSDT 15m provider-backed fixture that stays inside the open-interest endpoint's latest-month availability, then run the paired price/trend versus full-context comparator cycle with synthetic fallback disabled.

## Allowed paths

- `data/research/market_data/binance_usdm/wpr41_btcusdt_latest_month_context_provider_v1/**`
- `data/research/fixtures/btcusdt_context_provider_latest_month_v1/**`
- `data/research/historical_cycles/btcusdt_context_provider_latest_month_v1_cycle/**`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR41-01-latest-month-provider-context-cycle.md`
- `docs/stage_reports/STAGE_R41_LATEST_MONTH_PROVIDER_CONTEXT_CYCLE_REPORT.md`

## Inputs

- Direct Binance USD-M bar collector: `collect-binance-bars`.
- Direct Binance USD-M context collector: `collect-binance-context`.
- Target symbol and interval: `BTCUSDT`, `15m`.
- Target latest-month context window: `2026-04-05T00:00:00Z` through `2026-05-04T22:00:00Z`.
- Target primary fixture tail rows: the complete 15m bar rows available inside that latest-month window.
- Expected context families: `funding_rate`, `premium_index`, `open_interest`.

## Non-goals

- No legacy chart export, TradingView, Pine, parity, or synthetic input use.
- No live, paper, shadow, testnet, canary, promotion, order-placement, runtime-control, or capital-allocation work.
- No attempt to bypass Binance's one-month open-interest availability.
- No checked-in canonical fixture replacement.
- No OOS acceptance, performance claim, candidate promotion, or Stage 13 execution.

## Implementation plan

1. Collect current BTCUSDT 15m bars directly from Binance USD-M REST into the WPR41 local research data directory.
2. Collect funding-rate, premium-index, and open-interest context for the same latest-month window.
3. Build `btcusdt-context-provider-latest-month-v1` from the collected bar manifest and context manifests.
4. Run a bounded historical comparator cycle with `features_price_trend_vol` and `features_full_context_no_wt`.
5. Audit context joins, ablation evidence, candidate gates, live flags, hashes, and generated manifests.
6. Run focused validation plus the baseline compile/contracts checks and close the packet.

## Exit criteria

- Fresh provider bar and context manifests are collected locally with research-only/non-promotion flags.
- Open-interest row count exceeds the previous 500-row/7-day ceiling and covers the complete requested latest-month context window.
- Generated fixture validates with funding, premium, and open-interest families.
- Historical cycle consumes the fixture with synthetic fallback disabled and records comparator evidence.
- Candidate gate behavior is truthful and research-only.
- Validation evidence is recorded in the stage report.

## Completion evidence

- Collected direct Binance USD-M `BTCUSDT` 15m bars:
  - Rows: 2,873.
  - Source data SHA-256: `7805a3f2ef5a27e3c768c702fedf508632417bc188bc00b7ff9dbb5905c3d531`.
  - Manifest SHA-256: `4091e7a0543fb26efd2c2272a0c231cbee5ccbd471e3875fe1799ededc3b11d1`.
- Collected direct Binance USD-M context:
  - Funding rows: 91, content hash `sha256:51ab35c62ce7cbac72fe76bb1b789dc1bec226987951c4cf8d5abde36303e11b`.
  - Premium rows: 2,873, content hash `sha256:300d9f6a3761d9996e9db1a6ac55f4cf94fdcd57ba11c30a5b9d0373abebea08`.
  - Open-interest rows: 2,873, content hash `sha256:80073ee82e6bbfb74b63d4a30c56a0c506d6417d4d0712e6fc77e7bc9dcb2a0e`.
- Built fixture pack `data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json`.
- Fixture ID: `btcusdt-context-provider-latest-month-v1`.
- Fixture rows: 2,873.
- Fixture manifest SHA-256: `3f6264f446217fc0a81964ddff71f2f07f35c862665687bca27abe58136d46ac`.
- Fixture cycle dataset SHA-256: `acd93252a6e11a2cdae3c6cc9a0f3e07244a511da193c532507c71b0454cb92a`.
- Fixture bars SHA-256: `35bf9f495e10355ba27bd9a0ef147cc389590007682abc152e8a0151c55a3f13`.
- Historical cycle output: `data/research/historical_cycles/btcusdt_context_provider_latest_month_v1_cycle/run/research_cycle_manifest.json`.
- Cycle manifest SHA-256: `5110a9fd96c118a81dfe70db4761c703c86cf35b5d28e25b396497c104796d80`.
- Candidate rows: 16.
- Backtest index rows: 128, all `vector_fixed_holding`.
- Context join coverage: funding, premium, and open-interest each matched all 2,873 primary rows with zero unmatched rows.
- Ablation evidence statuses: 8 `baseline_feature_set_no_optional_claim`, 6 `comparator_feature_set_failed`, 2 `comparator_feature_set_passed`.
- Candidate pack status: `candidate_pack_written: false`, all gates blocked.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\contracts\test_historical_fixture_pack_contract.py -q` passed: 42 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
