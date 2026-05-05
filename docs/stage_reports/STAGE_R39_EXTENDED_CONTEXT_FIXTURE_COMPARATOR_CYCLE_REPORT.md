# Stage R39 Extended Context Fixture Comparator Cycle Report

Date: 2026-05-05
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR39-01-extended-context-fixture-comparator-cycle.md`
Status: closed

## Scope

WPR39 attempted to expand the WPR38 context fixture execution into a broader provider-data cycle with feature ablation comparators. It used the existing local Binance USD-M kline cache and fresh Binance USD-M REST context manifests.

The packet did not use legacy chart exports, Pine files, parity files, synthetic fallback, live execution, paper/shadow/testnet/canary flows, order placement, promotion, or candidate acceptance.

## Provider Limitation

The initial 30-day funding and premium context collections succeeded, but the 30-day open-interest request returned HTTP 400 from Binance USD-M. The 7-day open-interest request succeeded but returned exactly 500 rows, exposing the endpoint row/retention limit for this collector path.

The packet therefore narrowed the clean fixture target to the 500-row tail where funding, premium, and open-interest can all join without synthetic or partial open-interest coverage.

## Collected Context

Funding-rate collection:

- Path: `data/research/market_data/binance_usdm/wpr39_btcusdt_context_provider_7d_v1/BTCUSDT/funding_rate/BTCUSDT_funding_rate_1775546100000_1776178800000.manifest.json`
- Rows: 22
- Content hash: `sha256:bbd202761e1cb4288e9e92e28a60f0b44626ea812caf1b05e467858eb0a1e5fd`
- Source: `binance_usdm_rest`

Premium-index collection:

- Path: `data/research/market_data/binance_usdm/wpr39_btcusdt_context_provider_7d_v1/BTCUSDT/premium_index/15m/BTCUSDT_premium_index_15m_1775574000000_1776178800000.manifest.json`
- Rows: 673
- Content hash: `sha256:3fe4f4e35af577664d5016d3ff294cd3d5ddf097f85526c1b0c8e383b63ea240`
- Source: `binance_usdm_rest`

Open-interest collection:

- Path: `data/research/market_data/binance_usdm/wpr39_btcusdt_context_provider_7d_v1/BTCUSDT/open_interest/15m/BTCUSDT_open_interest_15m_1775574000000_1776178800000.manifest.json`
- Rows: 500
- Content hash: `sha256:d41d798601daf115575b20c562652c7c4da22b30305f120e103be9b46f66fbeb`
- Source: `binance_usdm_rest`

## Generated Fixture Pack

- Manifest: `data/research/fixtures/btcusdt_context_provider_oi500_v1/fixture_pack_manifest.json`
- Fixture ID: `btcusdt-context-provider-oi500-v1`
- Row count: 500
- Time span: `2026-04-09T10:15:00Z` to `2026-04-14T15:00:00Z`
- Manifest SHA-256: `dcd7db61b2e03455e01b7f52a74f7f1b19d2230437ba73fc4812e85a2210b6c9`
- Cycle dataset SHA-256: `bc4256660d3a581804dc406369358f209e210fdc05382bf8cdf8cb13677d5e6a`
- Bars SHA-256: `da58e1c7003420e208d318f51dc32a7b7ad8192033f7b64659c8473091b41317`

Included context families:

- `funding_rate`: fixture rows 16
- `premium_index`: fixture rows 501
- `open_interest`: fixture rows 500

Omitted optional families:

- `agg_trade`
- `lower_timeframe_bars`

## Cycle Command

```powershell
$env:PYTHONPATH='src'
$env:TBS_RUNTIME_MODE='paper'
python -m tradingbotsuite.main run-historical-research-cycle --spec data\research\historical_cycles\btcusdt_context_provider_oi500_cycle\specs\btcusdt_context_provider_oi500_cycle.json
```

## Cycle Evidence

- Cycle manifest: `data/research/historical_cycles/btcusdt_context_provider_oi500_cycle/run/research_cycle_manifest.json`
- Cycle manifest SHA-256: `83b9b33d9bcbf9441d7206fcd28a42107e622b8dc83edfcd13d4c146d4e15e49`
- Feature sets: `features_price_trend_vol`, `features_full_context_no_wt`
- Candidate rows: 6
- Search mode: `explicit_search_spaces`
- Search method: `grid`
- Backtest index rows: 84
- Backtest backend used: `vector_fixed_holding`
- Split rows: 12
- Cost-stress rows: 66
- Stability rows: 6

## Ablation And Gates

The paired search-space setup produced feature ablation comparator evidence:

- `features_price_trend_vol`: 3 rows with `baseline_feature_set_no_optional_claim`
- `features_full_context_no_wt`: 3 rows with `comparator_feature_set_passed`

The ablation report decision remained `no_feature_claim_accepted` because no candidate passed the full research candidate gates. All 6 candidates were rejected and all 6 gate rows were blocked. No candidate pack was written.

Common blockers:

- no-trade baseline not beaten
- cost-stress survival below floor
- split dominance evidence incomplete
- stability region not accepted
- side/regime evidence floors not met for pack eligibility

## Boundary Notes

- The fixture and cycle artifacts are `research_only`, `observe_only`, and `promotion_ready: false`.
- `live_signal_input`, `position_sizing_input`, `operator_control_input`, `live_execution_input`, `runtime_control_input`, `live_fetch_used`, and `order_placement_used` are all `false`.
- The generated data paths remain local ignored research artifacts and do not replace the checked-in fixture.
- This packet records local execution evidence only. It is not OOS acceptance evidence and does not support performance claims.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 97 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 26 tests.
- `git diff --check` reported only existing LF-to-CRLF normalization warnings.

## Close Decision

Stage R39 is closed. The branch now has a broader local provider-context cycle with ablation comparator evidence and fail-closed candidate gates, while preserving research-only boundaries and avoiding legacy chart exports.
