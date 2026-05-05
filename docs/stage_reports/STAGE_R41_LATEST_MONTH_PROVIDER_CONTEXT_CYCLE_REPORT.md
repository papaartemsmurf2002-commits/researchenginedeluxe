# Stage R41 Latest-Month Provider Context Cycle Report

Date: 2026-05-05
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR41-01-latest-month-provider-context-cycle.md`
Status: closed

## Scope

WPR41 used direct research-only Binance USD-M REST collectors for both bars and context, then ran a latest-month BTCUSDT context-aware comparator cycle. It did not use legacy TradingView exports, Pine files, parity files, synthetic fallback, live execution, paper/shadow/testnet/canary flows, order placement, promotion, or candidate acceptance.

The first cycle invocation failed before outputs were produced because the draft 12h search space used `slope_threshold: 0.1`, which is outside the current strategy metadata domain for that holding window. The spec was corrected to use metadata-backed values `0.12` and `0.16`, then the cycle completed.

## Collected Provider Data

Bars:

- Path: `data/research/market_data/binance_usdm/wpr41_btcusdt_latest_month_context_provider_v1/BTCUSDT/15m/BTCUSDT_15m_1775347200000_1777932000000.manifest.json`
- Source: `binance_usdm_klines`
- Rows: 2,873
- Gap count: 0
- Duplicate count: 0
- Source data SHA-256: `7805a3f2ef5a27e3c768c702fedf508632417bc188bc00b7ff9dbb5905c3d531`
- Manifest SHA-256: `4091e7a0543fb26efd2c2272a0c231cbee5ccbd471e3875fe1799ededc3b11d1`

Funding-rate context:

- Path: `data/research/market_data/binance_usdm/wpr41_btcusdt_latest_month_context_provider_v1/BTCUSDT/funding_rate/BTCUSDT_funding_rate_1775318400000_1777932000000.manifest.json`
- Rows: 91
- Content hash: `sha256:51ab35c62ce7cbac72fe76bb1b789dc1bec226987951c4cf8d5abde36303e11b`
- Source hash: `sha256:632b14dbc317afeff69de68d988f2ae3960ba463f42b0c8d051a9417a41a773a`

Premium-index context:

- Path: `data/research/market_data/binance_usdm/wpr41_btcusdt_latest_month_context_provider_v1/BTCUSDT/premium_index/15m/BTCUSDT_premium_index_15m_1775347200000_1777932000000.manifest.json`
- Rows: 2,873
- Content hash: `sha256:300d9f6a3761d9996e9db1a6ac55f4cf94fdcd57ba11c30a5b9d0373abebea08`
- Source hash: `sha256:5907cf66799a0913ce177f51be5e908b8f471d32e7ff1daa76bb1d54ac543cfa`

Open-interest context:

- Path: `data/research/market_data/binance_usdm/wpr41_btcusdt_latest_month_context_provider_v1/BTCUSDT/open_interest/15m/BTCUSDT_open_interest_15m_1775347200000_1777932000000.manifest.json`
- Rows: 2,873
- Content hash: `sha256:80073ee82e6bbfb74b63d4a30c56a0c506d6417d4d0712e6fc77e7bc9dcb2a0e`
- Source hash: `sha256:6565310e1c63bf25350aaa7f77fa22b539ec955db4706f03c7088feac1b7314a`

All collected manifests are `research_only`, `observe_only`, and `promotion_ready: false`.

## Fixture Pack

- Manifest: `data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json`
- Fixture ID: `btcusdt-context-provider-latest-month-v1`
- Row count: 2,873
- Manifest SHA-256: `3f6264f446217fc0a81964ddff71f2f07f35c862665687bca27abe58136d46ac`
- Cycle dataset SHA-256: `acd93252a6e11a2cdae3c6cc9a0f3e07244a511da193c532507c71b0454cb92a`
- Bars SHA-256: `35bf9f495e10355ba27bd9a0ef147cc389590007682abc152e8a0151c55a3f13`

Included context families:

- `funding_rate`: 91 rows
- `premium_index`: 2,873 rows
- `open_interest`: 2,873 rows

The fixture derivation records `tradingview_source_used: false` and `synthetic_source_used: false`.

## Cycle Evidence

- Cycle spec: `data/research/historical_cycles/btcusdt_context_provider_latest_month_v1_cycle/specs/btcusdt_context_provider_latest_month_v1_cycle.json`
- Cycle manifest: `data/research/historical_cycles/btcusdt_context_provider_latest_month_v1_cycle/run/research_cycle_manifest.json`
- Cycle manifest SHA-256: `5110a9fd96c118a81dfe70db4761c703c86cf35b5d28e25b396497c104796d80`
- Feature sets: `features_price_trend_vol`, `features_full_context_no_wt`
- Holding windows: `4h`, `12h`
- Candidate rows: 16
- Backtest index rows: 128
- Backtest backend used: `vector_fixed_holding`
- Split rows: 24
- Cost-stress rows: 88
- Stability rows: 16

Context materialization joined all supplied families for all rows:

- Funding matched rows: 2,873; unmatched rows: 0
- Premium matched rows: 2,873; unmatched rows: 0
- Open interest matched rows: 2,873; unmatched rows: 0

## Ablation And Gates

Ablation evidence statuses:

- `baseline_feature_set_no_optional_claim`: 8
- `comparator_feature_set_failed`: 6
- `comparator_feature_set_passed`: 2

The ablation decision remained `no_feature_claim_accepted`. All 16 candidate gate rows were `blocked`, and no candidate pack was written.

Common blockers included no-trade baseline not beaten, trade-count floor failures, cost-stress survival below floor, split dominance concentration, incomplete side/regime evidence, and stability-region acceptance requirements.

## Boundary Notes

- The fixture and cycle artifacts are `research_only`, `observe_only`, and `promotion_ready: false`.
- `live_signal_input`, `position_sizing_input`, `operator_control_input`, `live_execution_input`, `runtime_control_input`, `live_fetch_used`, and `order_placement_used` are all `false`.
- Generated data paths are local research artifacts and do not replace the checked-in fixture.
- This is broader local research evidence, not OOS acceptance evidence, promotion evidence, or a performance claim.
- Minor audit note: `cycle_spec_resolved.json` still includes default `synthetic_row_count` and `synthetic_variant` fields even though `synthetic_fixture` is `false`. The fixture manifest and cycle source prove no synthetic source use, but later metadata cleanup should avoid carrying irrelevant defaults into resolved non-synthetic specs.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\contracts\test_historical_fixture_pack_contract.py -q` passed: 42 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.

## Close Decision

Stage R41 is closed. The branch now has a direct-provider, latest-month BTCUSDT context fixture and comparator cycle that scales beyond WPR40 while preserving fail-closed research boundaries.
