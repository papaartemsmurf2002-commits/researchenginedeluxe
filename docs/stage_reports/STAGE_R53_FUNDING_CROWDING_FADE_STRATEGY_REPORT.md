# Stage R53 Funding Crowding Fade Strategy Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR53-01-funding-crowding-fade-strategy.md`
Status: closed

## Scope

R53 added `funding_crowding_fade_v2` as the second transparent perpetual strategy using `features_perp_context_v2`, then included it in the checked BTCUSDT provider-backed perp-context cycle.

## Changes

- Added `FundingCrowdingFadeStrategy` as a `RuleBasedStrategy` plugin.
- Registered `funding_crowding_fade_v2` in the strategy registry.
- Added bounded metadata and config for:
  - `funding_z_threshold`
  - `funding_rate_abs_bps_threshold`
  - `premium_confirmation_bps`
  - `min_edge_bps`
  - `oi_confirmation_z_min`
  - `funding_momentum_policy`
  - `spacing_bars`
- Extended `configs/research/full_cycle_btcusdt_perp_context_v2.json` to include `funding_crowding_fade_v2`.
- Kept flow context optional because the current durable provider fixture omits `agg_trade`; missing flow remains unavailable, not zero.
- Required funding, premium/basis, OI, and v2 quality context to be present and finite.
- Kept `quality_latest_window_context_only` as explicit provenance and not a signal blocker.
- Added contract tests for metadata, invalid feature/window rejection, standard signal output, missing required columns, invalid quality/context values, OI confirmation, and latest-window provenance.
- Added backtest-engine integration tests for execution and unsupported feature/window mapping.
- Updated historical cycle coverage to require the new strategy in candidate space, rankings, and backtest index.

## Cycle Evidence

Generated local artifact root:

```text
data/research/historical_cycles/btcusdt_perp_context_v2_foundation
```

Summary:

- Fixture: `data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json`
- Joined context families: `funding_rate`, `premium_index`, `open_interest`
- Feature set: `features_perp_context_v2`
- Strategies: `baseline_no_trade`, `perp_basis_convergence_v2`, `funding_crowding_fade_v2`
- Candidate count: 28
- Aggregate backtests: 28
- Split backtests: 4
- Cost-stress backtests: 22
- Backtest index rows: 54
- Baseline comparator coverage: complete
- `funding_crowding_fade_v2` aggregate trade count across candidates: 37
- Candidate pack written: false
- Pack-eligible candidates: 0
- Acceptance scope: `research_gate_evaluated_fail_closed`

The new strategy produced provider-cycle trades, but all candidates remained rejected by existing evidence gates, including low signal density, side/regime evidence requirements, feature-ablation requirements, split/cost-stress requirements, and stability-region requirements. This is the expected fail-closed result for latest-month local provider evidence and is not OOS acceptance evidence.

The generated cycle artifact directory remains under the repo's existing ignored `data/research/historical_cycles` policy; the checked spec and tests make the run reproducible.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\integration\test_backtest_engine_fixture.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_perp_context_v2_cycle_consumes_provider_context_fixture -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\contracts\test_strategy_contracts.py tests\integration\test_backtest_engine_fixture.py tests\historical\test_full_cycle_local_fixture_pack.py -q
git diff --check
```

Results:

- Full compile passed.
- Focused strategy and integration tests: 78 passed.
- Checked perp-context historical test: 1 passed.
- WPR53 validation suite: 111 passed.
- `git diff --check` passed with CRLF working-copy warnings only.

## Research Boundary

This stage does not add live signals, promotion readiness, live configuration writes, order placement, capital allocation, candidate-pack promotion evidence, cross-exchange behavior, or OOS performance claims.

## Next Stage

WPR54 should be opened as a new packet before coding. The next planned item is `oi_flow_breakout_v2`; because durable `agg_trade` is absent from the current checked fixture, WPR54 should either keep flow optional or first add durable aggregate-trade fixture evidence.
