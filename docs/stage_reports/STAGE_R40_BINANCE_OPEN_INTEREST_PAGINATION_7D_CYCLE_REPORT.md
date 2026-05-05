# Stage R40 Binance Open-Interest Pagination 7d Cycle Report

Date: 2026-05-05
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR40-01-binance-open-interest-pagination-7d-cycle.md`
Status: closed

## Scope

WPR40 fixed the research-only Binance USD-M open-interest collector pagination and reran the 7-day context fixture plus comparator cycle. It preserved all research/live boundaries and did not use legacy chart exports, Pine files, parity files, synthetic fallback, live execution, paper/shadow/testnet/canary flows, order placement, promotion, or candidate acceptance.

## Code Change

`src/tradingbotsuite/research/market_data.py` now fetches open-interest history pages backward from `endTime` for `/futures/data/openInterestHist`, which has a 500-row page limit. Funding and premium-index collection keep the existing forward pagination behavior.

Regression coverage:

- `tests/tradingbotsuite/test_market_data_collection.py::test_binance_usdm_open_interest_fetcher_pages_backward_from_endpoint_limit`

## Collected Context

Funding-rate collection:

- Path: `data/research/market_data/binance_usdm/wpr40_btcusdt_context_provider_7d_v2/BTCUSDT/funding_rate/BTCUSDT_funding_rate_1775546100000_1776178800000.manifest.json`
- Rows: 22
- Content hash: `sha256:bbd202761e1cb4288e9e92e28a60f0b44626ea812caf1b05e467858eb0a1e5fd`

Premium-index collection:

- Path: `data/research/market_data/binance_usdm/wpr40_btcusdt_context_provider_7d_v2/BTCUSDT/premium_index/15m/BTCUSDT_premium_index_15m_1775574000000_1776178800000.manifest.json`
- Rows: 673
- Content hash: `sha256:3fe4f4e35af577664d5016d3ff294cd3d5ddf097f85526c1b0c8e383b63ea240`

Open-interest collection:

- Path: `data/research/market_data/binance_usdm/wpr40_btcusdt_context_provider_7d_v2/BTCUSDT/open_interest/15m/BTCUSDT_open_interest_15m_1775574000000_1776178800000.manifest.json`
- Rows: 673
- Content hash: `sha256:8adc5458c3063bdb69babeabd4e47a4c2f9892eae065a824de19d5ec89fc5a39`

The open-interest collector now covers the full requested 7-day context window instead of returning only the last 500 rows.

## Fixture Pack

- Manifest: `data/research/fixtures/btcusdt_context_provider_7d_v2/fixture_pack_manifest.json`
- Fixture ID: `btcusdt-context-provider-7d-v2`
- Row count: 672
- Manifest SHA-256: `799666f7164652d2bc97353d8ffe91546956175e8ed2c3886589c03999bb2d81`
- Cycle dataset SHA-256: `d79b6a5acce2d6a82cf7f18aef368db2082ebcbf3e7a0ea03e874273050abcb9`
- Bars SHA-256: `b598209b802e0f5d9b9c03016329b403b62c5ade5100c0b3f54e7d138d567f86`

Included context families:

- `funding_rate`: 22 rows
- `premium_index`: 673 rows
- `open_interest`: 673 rows

The historical cycle materialization joined open interest across all 672 primary rows with `matched_row_count: 672`, `unmatched_row_count: 0`, and null rates of 0.0 for open-interest columns.

## Cycle Evidence

- Cycle manifest: `data/research/historical_cycles/btcusdt_context_provider_7d_v2_cycle/run/research_cycle_manifest.json`
- Cycle manifest SHA-256: `28d84bb1ee2b7a07c89fffb0bfd4ac20f1bb6119a95115ad2416a790cd0d1169`
- Feature sets: `features_price_trend_vol`, `features_full_context_no_wt`
- Candidate rows: 6
- Search mode: `explicit_search_spaces`
- Search method: `grid`
- Backtest index rows: 84
- Backtest backend used: `vector_fixed_holding`
- Split rows: 12
- Cost-stress rows: 66
- Stability rows: 6

## Gates And Boundary

All 6 candidates remained rejected and gate-blocked. No candidate pack was written. Full-context ablation evidence was now available; two full-context trend rows underperformed their price/trend comparators and one passed comparator evidence.

The fixture and cycle artifacts are `research_only`, `observe_only`, and `promotion_ready: false`. `live_signal_input`, `position_sizing_input`, `operator_control_input`, `live_execution_input`, `runtime_control_input`, `live_fetch_used`, and `order_placement_used` are all `false`.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q` passed: 15 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\contracts\test_historical_fixture_pack_contract.py -q` passed: 42 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `python -m compileall -q src\tradingbotsuite` passed.

## Close Decision

Stage R40 is closed. The collector now handles the Binance open-interest page limit correctly for the 7-day fixture window, and the branch has a complete 7-day provider-context comparator cycle with fail-closed gates.
