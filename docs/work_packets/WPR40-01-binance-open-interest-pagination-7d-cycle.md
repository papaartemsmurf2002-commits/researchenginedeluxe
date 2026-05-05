# WPR40-01 Binance Open Interest Pagination 7d Cycle

Status: closed
Owner: Codex Research Agent
Stage: Stage R40 Binance open-interest pagination and 7d context cycle
Opened: 2026-05-05
Closed: 2026-05-05

## Objective

Fix the research-only Binance USD-M open-interest collector so it pages across the endpoint's 500-row limit instead of silently returning only the last page, then rebuild and run a 7-day context-aware comparator cycle with complete open-interest coverage.

## Allowed paths

- `src/tradingbotsuite/research/market_data.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `data/research/market_data/binance_usdm/wpr40_btcusdt_context_provider_7d_v2/**`
- `data/research/fixtures/btcusdt_context_provider_7d_v2/**`
- `data/research/historical_cycles/btcusdt_context_provider_7d_v2_cycle/**`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR40-01-binance-open-interest-pagination-7d-cycle.md`
- `docs/stage_reports/STAGE_R40_BINANCE_OPEN_INTEREST_PAGINATION_7D_CYCLE_REPORT.md`

## Inputs

- Official Binance USD-M open-interest history endpoint: `/futures/data/openInterestHist`
- Relevant endpoint limits: `limit` max 500 and latest one-month availability.
- Existing kline source manifest: `data/research/chart_ohlcv_cache/BTCUSDT_15m_1760450400000_1776178800000.manifest.json`
- Target 7-day primary fixture rows: 672 15-minute rows
- Primary fixture tail window: `1775574900000` to `1776178800000`
- Context request windows:
  - Funding: `1775546100000` to `1776178800000`
  - Premium/open-interest: `1775574000000` to `1776178800000`

## Non-goals

- No legacy chart export, Pine, parity, or synthetic input use.
- No live, paper, shadow, testnet, canary, promotion, order-placement, runtime-control, or capital-allocation work.
- No attempt to bypass Binance's one-month retention window.
- No checked-in canonical fixture replacement.
- No OOS acceptance, performance claim, candidate promotion, or Stage 13 execution.

## Implementation plan

1. Add fail-closed tests for Binance USD-M open-interest backward pagination across multiple 500-row pages.
2. Update the REST context fetcher to collect open-interest pages backward from `endTime` while preserving funding and premium forward pagination.
3. Recollect 7-day BTCUSDT funding, premium, and open-interest context.
4. Build `btcusdt-context-provider-7d-v2` with `--row-limit 672`.
5. Run the same paired price/trend versus full-context comparator cycle used in WPR39.
6. Audit context coverage, ablation evidence, gates, live flags, and validation.

## Exit criteria

- Open-interest collector test proves multi-page retrieval beyond 500 rows.
- Recollected 7-day open-interest rows cover the full 673-row context request window.
- Generated 672-row fixture validates and includes funding, premium, and open-interest families.
- Historical cycle consumes the fixture with synthetic fallback disabled and records ablation comparator evidence.
- Candidate gate behavior is truthful and research-only.
- Validation evidence is recorded in the stage report.

## Completion evidence

- Added backward pagination for Binance USD-M open-interest history pages.
- Added regression test `test_binance_usdm_open_interest_fetcher_pages_backward_from_endpoint_limit`.
- Recollected WPR40 context:
  - Funding rows: 22, content hash `sha256:bbd202761e1cb4288e9e92e28a60f0b44626ea812caf1b05e467858eb0a1e5fd`.
  - Premium rows: 673, content hash `sha256:3fe4f4e35af577664d5016d3ff294cd3d5ddf097f85526c1b0c8e383b63ea240`.
  - Open-interest rows: 673, content hash `sha256:8adc5458c3063bdb69babeabd4e47a4c2f9892eae065a824de19d5ec89fc5a39`.
- Built fixture pack `data/research/fixtures/btcusdt_context_provider_7d_v2/fixture_pack_manifest.json`.
- Fixture ID: `btcusdt-context-provider-7d-v2`.
- Fixture rows: 672.
- Fixture manifest SHA-256: `799666f7164652d2bc97353d8ffe91546956175e8ed2c3886589c03999bb2d81`.
- Historical cycle output: `data/research/historical_cycles/btcusdt_context_provider_7d_v2_cycle/run/research_cycle_manifest.json`.
- Cycle manifest SHA-256: `28d84bb1ee2b7a07c89fffb0bfd4ac20f1bb6119a95115ad2416a790cd0d1169`.
- Backtest rows: 84, all `vector_fixed_holding`.
- Candidate pack status: `candidate_pack_written: false`, all gates blocked.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q` passed: 15 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\contracts\test_historical_fixture_pack_contract.py -q` passed: 42 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `python -m compileall -q src\tradingbotsuite` passed.
