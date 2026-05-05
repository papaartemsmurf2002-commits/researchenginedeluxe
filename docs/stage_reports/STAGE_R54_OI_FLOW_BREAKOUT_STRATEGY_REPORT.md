# Stage R54 OI Flow Breakout Strategy Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR54-01-oi-flow-breakout-strategy.md`
Status: closed

## Scope

R54 added `oi_flow_breakout_v2` as the third transparent perpetual strategy using `features_perp_context_v2`, then included it in the checked BTCUSDT provider-backed perp-context cycle.

## Changes

- Added `OiFlowBreakoutStrategy` as a `RuleBasedStrategy` plugin.
- Registered `oi_flow_breakout_v2` in the strategy registry.
- Added bounded metadata and config for:
  - `oi_delta_z_threshold`
  - `oi_delta_min_notional`
  - `premium_confirmation_bps`
  - `premium_slope_min_bps`
  - `flow_z_threshold`
  - `flow_confirmation_policy`
  - `spacing_bars`
- Extended `configs/research/full_cycle_btcusdt_perp_context_v2.json` to include `oi_flow_breakout_v2`.
- Kept flow confirmation optional because the current durable provider fixture omits `agg_trade`; missing flow remains unavailable and is not zero-filled.
- Required OI expansion, premium/basis confirmation, and v2 quality context to be present and finite.
- Kept `quality_latest_window_context_only` as explicit provenance and not a signal blocker.
- Added contract tests for metadata, invalid feature/window rejection, standard signal output, missing required columns, invalid context values, positive OI expansion, optional/missing flow, required/misaligned flow, invalid spacing, and latest-window provenance.
- Added a candidate-space contract for the perp-context-v2 transparent strategy family.
- Added backtest-engine integration tests for execution and unsupported feature/window mapping.
- Updated historical cycle coverage to require the new strategy in candidate space, rankings, and backtest index, and to assert the compact provider fixture remains fail-closed with no candidate pack.

## Cycle Evidence

Generated local artifact root:

```text
data/research/historical_cycles/btcusdt_perp_context_v2_foundation
```

Summary:

- Fixture: `data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json`
- Joined context families: `funding_rate`, `premium_index`, `open_interest`
- Omitted flow source: `agg_trade`
- Flow feature missingness: 2,873/2,873 rows for `flow_buy_sell_ratio`, `flow_signed_taker_notional`, and `flow_signed_taker_z_7d`
- Feature set: `features_perp_context_v2`
- Strategies: `baseline_no_trade`, `perp_basis_convergence_v2`, `funding_crowding_fade_v2`, `oi_flow_breakout_v2`
- Candidate count: 40
- Aggregate backtests: 40
- Split backtests: 4
- Cost-stress backtests: 22
- Backtest index rows: 66
- Baseline comparator coverage: complete
- `oi_flow_breakout_v2` ranking rows: 12
- `oi_flow_breakout_v2` aggregate trade count across candidates: 197
- Candidate pack written: false
- Pack-eligible candidates: 0
- Acceptance scope: `research_gate_evaluated_fail_closed`

The new strategy produced provider-cycle trades using OI and premium/basis expansion, but all candidates remained rejected by existing evidence gates. This is the expected fail-closed result for latest-month local provider evidence and is not OOS acceptance evidence.

The generated cycle artifact directory remains under the repo's existing ignored `data/research/historical_cycles` policy; the checked spec and tests make the run reproducible.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\integration\test_backtest_engine_fixture.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_perp_context_v2_cycle_consumes_provider_context_fixture -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\contracts\test_strategy_contracts.py tests\integration\test_backtest_engine_fixture.py tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- Full compile passed.
- Focused strategy and integration tests: 113 passed.
- Checked perp-context historical test: 1 passed.
- WPR54 validation suite: 148 passed.
- Full contract suite: 196 passed.

## Review Fixes

- Flow policy aliases were tightened so behavior is represented by metadata-backed policy values.
- Invalid `spacing_bars` now fails closed with an empty signal frame instead of aborting prediction.
- The checked provider-cycle test now asserts the compact fixture remains fail-closed with no candidate pack and zero pack-eligible rows.

## Research Boundary

This stage does not add live signals, promotion readiness, live configuration writes, order placement, capital allocation, candidate-pack promotion evidence, cross-exchange behavior, fixture regeneration, or OOS performance claims.

## Next Stage

WPR55 should be opened as a new packet before coding. The next planned item from `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md` is `funding_window_timing_v1` unless the strategy plan is revised to prioritize ETHUSDT fixture and mirror-cycle evidence first.
