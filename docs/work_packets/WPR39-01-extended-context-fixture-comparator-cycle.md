# WPR39-01 Extended Context Fixture Comparator Cycle

Status: closed
Owner: Codex Research Agent
Stage: Stage R39 extended context fixture and comparator cycle
Opened: 2026-05-05
Closed: 2026-05-05

## Objective

Create a larger local BTCUSDT context fixture from the existing Binance USD-M kline cache plus fresh Binance USD-M REST context, then run a historical cycle with feature comparators so ablation and candidate gates receive broader real evidence than the compact WPR38 smoke cycle.

## Allowed paths

- `data/research/market_data/binance_usdm/wpr39_btcusdt_context_provider_30d_v1/**`
- `data/research/market_data/binance_usdm/wpr39_btcusdt_context_provider_7d_v1/**`
- `data/research/fixtures/btcusdt_context_provider_oi500_v1/**`
- `data/research/historical_cycles/btcusdt_context_provider_oi500_cycle/**`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR39-01-extended-context-fixture-comparator-cycle.md`
- `docs/stage_reports/STAGE_R39_EXTENDED_CONTEXT_FIXTURE_COMPARATOR_CYCLE_REPORT.md`

## Inputs

- Existing kline source manifest: `data/research/chart_ohlcv_cache/BTCUSDT_15m_1760450400000_1776178800000.manifest.json`
- Initial 30-day primary target: 2880 15-minute rows
- Initial 30-day primary window: `1773587700000` to `1776178800000`
- Provider limitation discovered: 30-day open-interest history request returned HTTP 400, consistent with the endpoint's latest-month retention limit and the cache tail crossing that boundary.
- The 7-day open-interest request returned 500 rows starting at `1775729700000`, so the active fixture is narrowed to complete context coverage.
- Active primary row count: 500 15-minute rows
- Active primary fixture window: `1775729700000` to `1776178800000`
- Active funding context window: `1775546100000` to `1776178800000`
- Active premium/open-interest context manifests: `1775574000000` to `1776178800000`

## Non-goals

- No legacy chart export, Pine, parity, or synthetic input use.
- No live, paper, shadow, testnet, canary, promotion, order-placement, runtime-control, or capital-allocation work.
- No checked-in canonical replacement of the existing BTCUSDT fixture.
- No OOS acceptance, performance claim, candidate promotion, or Stage 13 execution.

## Implementation plan

1. Collect BTCUSDT funding-rate, premium-index, and open-interest context for the 7-day tail window using the research-only Binance USD-M REST collector.
2. Build `btcusdt-context-provider-oi500-v1` with `build-historical-fixture-pack --row-limit 500`.
3. Validate the generated fixture manifest and record hashes, row counts, optional families, and limitations.
4. Run a bounded historical cycle against the 30-day fixture with `features_price_trend_vol`, `features_full_context_no_wt`, and `features_perp_context_only` to provide ablation comparators.
5. Audit rankings, candidate gates, feature context materialization, candidate-pack status, and research-only boundary flags.
6. Run validation baseline and close the packet.

## Exit criteria

- 7-day context manifests are collected locally with research-only/non-promotion flags.
- 500-row fixture pack validates with funding, premium, and open-interest families.
- Historical cycle consumes the 500-row fixture with synthetic fallback disabled.
- Feature ablation comparator evidence is present for context feature sets.
- Candidate gate behavior is recorded truthfully, whether passing or fail-closed.
- Validation evidence is recorded in the stage report.

## Completion evidence

- 30-day funding and premium context collection succeeded, but 30-day open-interest collection returned HTTP 400 from Binance USD-M.
- 7-day context collection succeeded:
  - Funding rows: 22, content hash `sha256:bbd202761e1cb4288e9e92e28a60f0b44626ea812caf1b05e467858eb0a1e5fd`.
  - Premium rows: 673, content hash `sha256:3fe4f4e35af577664d5016d3ff294cd3d5ddf097f85526c1b0c8e383b63ea240`.
  - Open-interest rows: 500, content hash `sha256:d41d798601daf115575b20c562652c7c4da22b30305f120e103be9b46f66fbeb`.
- Built fixture pack `data/research/fixtures/btcusdt_context_provider_oi500_v1/fixture_pack_manifest.json`.
- Fixture ID: `btcusdt-context-provider-oi500-v1`.
- Fixture rows: 500.
- Fixture manifest SHA-256: `dcd7db61b2e03455e01b7f52a74f7f1b19d2230437ba73fc4812e85a2210b6c9`.
- Fixture context families: `funding_rate`, `premium_index`, `open_interest`.
- Historical cycle output: `data/research/historical_cycles/btcusdt_context_provider_oi500_cycle/run/research_cycle_manifest.json`.
- Cycle manifest SHA-256: `83b9b33d9bcbf9441d7206fcd28a42107e622b8dc83edfcd13d4c146d4e15e49`.
- Candidate rows: 6.
- Backtest index rows: 84.
- Backtest backend used: `vector_fixed_holding`.
- Ablation statuses: 3 `baseline_feature_set_no_optional_claim`, 3 `comparator_feature_set_passed`.
- Candidate pack status: `candidate_pack_written: false`, all gates blocked.
- Scope remains `research_only`, `observe_only`, and `promotion_ready: false`.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `git diff --check` reported only existing LF-to-CRLF normalization warnings.
