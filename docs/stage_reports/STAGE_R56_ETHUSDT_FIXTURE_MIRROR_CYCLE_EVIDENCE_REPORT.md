# Stage R56 ETHUSDT Fixture Mirror Cycle Evidence Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR56-01-ethusdt-fixture-mirror-cycle-evidence.md`
Status: closed

## Scope

R56 added durable ETHUSDT provider-backed fixture evidence and a checked ETHUSDT perp-context-v2 mirror cycle using the same feature set, strategy set, validation shape, and research boundaries as the current BTCUSDT perp-context-v2 cycle.

## Changes

- Added bounded backward pagination for Binance USD-M open-interest REST collection so each request stays inside the endpoint page window.
- Added a regression test for bounded open-interest pagination.
- Preserved fixture-family latest-window provenance through fixture validation and feature materialization, including legacy checked fixtures that predate explicit retention metadata.
- Collected ETHUSDT Binance USD-M 15m bars, funding, premium index, and open interest through normalized provider collectors.
- Built `ethusdt-context-provider-latest-month-v1` as a compact fixture pack.
- Added `configs/research/full_cycle_ethusdt_perp_context_v2.json`.
- Added fixture-contract and historical-cycle tests for the checked ETHUSDT fixture and cycle.
- Updated `.gitignore` so only the compact ETH fixture pack is trackable; raw REST cache output remains ignored.

## Provider Collection

Raw local cache root:

```text
data/research/market_data/binance_usdm/wpr56_ethusdt_latest_month_context_provider_v1
```

The raw cache is local/generated and remains ignored. The durable checked fixture is:

```text
data/research/fixtures/ethusdt_context_provider_latest_month_v1
```

Collected source rows:

- Bars: 2,873 rows from `2026-04-05T00:00:00Z` through `2026-05-04T22:00:00Z`, zero gaps, zero duplicates.
- Funding rate: 91 rows from `2026-04-04T16:00:00Z` through `2026-05-04T16:00:00.003Z`, zero gaps, zero duplicates.
- Premium index: 2,873 rows from `2026-04-05T00:00:00Z` through `2026-05-04T22:00:00Z`, zero gaps, zero duplicates.
- Open interest: 2,810 rows from `2026-04-05T15:45:00Z` through `2026-05-04T22:00:00Z`, zero gaps, zero duplicates.

The original BTC mirror start `2026-04-05T00:00:00Z` was rejected by the current Binance open-interest endpoint with `parameter 'startTime' is invalid`. R56 therefore uses the maximal complete ETHUSDT tail shared by bars, premium, funding, and open interest. This is latest-window direct-endpoint evidence only, not broad OOS or multi-year coverage.

## Fixture Evidence

Fixture summary:

- Fixture ID: `ethusdt-context-provider-latest-month-v1`
- Symbol: `ETHUSDT`
- Base interval: `15m`
- Row count: 2,810
- First fixture bar: `2026-04-05T15:45:00Z`
- Last fixture bar: `2026-05-04T22:00:00Z`
- Included context families: `funding_rate`, `premium_index`, `open_interest`
- Omitted optional families: `agg_trade`, `lower_timeframe_bars`
- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- TradingView source used: false
- Synthetic source used: false

## Cycle Evidence

Generated local artifact root:

```text
data/research/historical_cycles/ethusdt_perp_context_v2_foundation
```

Summary:

- Feature set: `features_perp_context_v2`
- Feature rows: 2,810
- Joined context families: `funding_rate`, `premium_index`, `open_interest`
- Timing feature missingness: 0 rows for `cal_time_since_last_funding_h` and `cal_time_to_next_funding_h`; 19 rows for rolling `perp_funding_z_7d`
- Latest-window provenance flag: `quality_latest_window_context_only` is 1.0 for all feature rows
- Strategies: `baseline_no_trade`, `perp_basis_convergence_v2`, `funding_crowding_fade_v2`, `oi_flow_breakout_v2`, `funding_window_timing_v1`
- Candidate count: 52
- Aggregate backtests: 52
- Cost-stress backtests: 22
- Walk-forward split backtests: 4
- Backtest index rows: 78
- Baseline comparator coverage: complete
- Aggregate trade counts:
  - `baseline_no_trade`: 0
  - `perp_basis_convergence_v2`: 59
  - `funding_crowding_fade_v2`: 68
  - `oi_flow_breakout_v2`: 141
  - `funding_window_timing_v1`: 27
- Candidate pack written: false
- Pack-eligible candidates: 0
- Acceptance scope: `research_gate_evaluated_fail_closed`

The ETH mirror cycle produced research trades across all transparent strategy families, but all candidates remained rejected by existing evidence gates. This is the expected fail-closed result for latest-window provider evidence and is not promotion evidence or a performance claim.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py::test_binance_usdm_open_interest_fetcher_pages_backward_with_bounded_endpoint_windows -q
$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py::test_perp_context_v2_preserves_latest_window_fixture_family_provenance -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py::test_checked_in_ethusdt_context_provider_fixture_pack_manifest_validates -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_eth_perp_context_v2_cycle_consumes_provider_context_fixture tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_perp_context_v2_cycle_consumes_provider_context_fixture -q
$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py tests\tradingbotsuite\test_market_data_collection.py tests\contracts\test_historical_fixture_pack_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Results:

- Open-interest pagination regression: 1 passed.
- Latest-window provenance feature regression: 1 passed.
- ETH fixture contract: 1 passed.
- BTC and ETH checked historical cycles: 2 passed.
- WPR56 focused suite: 74 passed.
- Full compile passed.
- Full contract suite: 235 passed.
- Diff whitespace check passed.

## Review Fixes

- Latest-window context provenance now survives fixture-pack validation and feature materialization. The checked BTC and ETH perp-context-v2 cycle tests assert `quality_latest_window_context_only` is 1.0 for provider latest-window fixtures.
- Removed the stale unreferenced local ETH feature-cache directory from the pre-fix cycle run; the current ignored cycle manifest references the regenerated cache with latest-window flags set to 1.0.

## Research Boundary

This stage does not add live signals, promotion readiness, live configuration writes, order placement, capital allocation, candidate-pack promotion evidence, cross-asset behavior, or OOS performance claims.

## Next Stage

WPR57 should be opened as a new packet before coding. The next planned item from `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md` is funding-adverse exit improvements or a dedicated funding-aware exit policy, unless the plan is revised before implementation.
