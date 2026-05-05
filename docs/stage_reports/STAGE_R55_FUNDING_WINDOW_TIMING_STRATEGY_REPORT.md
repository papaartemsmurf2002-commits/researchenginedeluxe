# Stage R55 Funding Window Timing Strategy Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR55-01-funding-window-timing-strategy.md`
Status: closed

## Scope

R55 added `funding_window_timing_v1` as the fourth transparent perpetual strategy using `features_perp_context_v2`, then included it in the checked BTCUSDT provider-backed perp-context cycle.

## Changes

- Added `FundingWindowTimingStrategy` as a `RuleBasedStrategy` plugin.
- Registered `funding_window_timing_v1` in the strategy registry.
- Added bounded metadata and config for:
  - `funding_z_threshold`
  - `funding_rate_abs_bps_threshold`
  - `premium_confirmation_bps`
  - `entry_window_h`
  - `window_mode`
  - `funding_momentum_policy`
  - `oi_confirmation_z_min`
  - `spacing_bars`
- Extended `configs/research/full_cycle_btcusdt_perp_context_v2.json` to include `funding_window_timing_v1`.
- Required funding, timing, premium/basis, OI, and v2 quality context to be present and finite.
- Kept flow out of the strategy because the checked durable provider fixture omits `agg_trade`.
- Kept `quality_latest_window_context_only` as explicit provenance and not a signal blocker.
- Added contract tests for metadata, invalid feature/window rejection, standard signal output, missing required columns, invalid context values, funding-window gating, post-funding mode, momentum filtering, invalid spacing, malformed numeric parameters, and latest-window provenance.
- Added backtest-engine integration tests for execution and unsupported feature/window mapping.
- Updated the perp-context-v2 candidate-space and checked-cycle tests to require `funding_window_timing_v1` in generated strategies, rankings, and backtest index.

## Cycle Evidence

Generated local artifact root:

```text
data/research/historical_cycles/btcusdt_perp_context_v2_foundation
```

Summary:

- Fixture: `data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json`
- Joined context families: `funding_rate`, `premium_index`, `open_interest`
- Feature rows: 2,873
- Timing feature missingness: 0 rows for `cal_time_since_last_funding_h`, `cal_time_to_next_funding_h`, and `perp_last_funding_rate`; 19 rows for rolling `perp_funding_z_7d`
- Feature set: `features_perp_context_v2`
- Strategies: `baseline_no_trade`, `perp_basis_convergence_v2`, `funding_crowding_fade_v2`, `oi_flow_breakout_v2`, `funding_window_timing_v1`
- Candidate count: 52
- Aggregate backtests: 52
- Split backtests: 4
- Cost-stress backtests: 22
- Backtest index rows: 78
- Baseline comparator coverage: complete
- `funding_window_timing_v1` ranking rows: 12
- `funding_window_timing_v1` aggregate trade count across candidates: 5
- Candidate pack written: false
- Pack-eligible candidates: 0
- Acceptance scope: `research_gate_evaluated_fail_closed`

The new strategy produced provider-cycle trades using funding-window timing, funding stretch, and premium/basis confirmation, but all candidates remained rejected by existing evidence gates. This is the expected fail-closed result for latest-month local provider evidence and is not OOS acceptance evidence.

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
- Focused strategy and integration tests passed.
- Checked perp-context historical test: 1 passed.
- WPR55 validation suite: 188 passed.
- Full contract suite: 234 passed.

## Review Fixes

- Malformed numeric strategy parameters now fail closed with an empty signal frame instead of falling back to defaults and emitting signals.
- The stage report was added before closing the work packet and ledger row.

## Research Boundary

This stage does not add live signals, promotion readiness, live configuration writes, order placement, capital allocation, candidate-pack promotion evidence, funding cashflow modeling, fixture regeneration, cross-exchange behavior, or OOS performance claims.

## Next Stage

WPR56 should be opened as a new packet before coding. The next planned item from `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md` is ETHUSDT fixture and mirror-cycle evidence unless the plan is revised to prioritize funding exit improvements first.
