# Stage R51 Perp Basis Convergence Strategy Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR51-01-perp-basis-convergence-strategy.md`
Status: closed

## Scope

R51 added the first transparent perpetual strategy plugin, `perp_basis_convergence_v2`, using `features_perp_context_v2` and the existing research-only strategy signal contract.

## Changes

- Added `PerpBasisConvergenceStrategy` as a `RuleBasedStrategy` plugin.
- Registered `perp_basis_convergence_v2` in the strategy registry.
- Added bounded metadata for `basis_vol_threshold`, `premium_z_threshold`, `min_edge_bps`, `funding_policy`, and `spacing_bars`.
- Added checked config at `configs/strategies/perp_basis_convergence_v2.json`.
- Implemented single-leg directional convergence proxy rules:
  - long when basis/premium context is sufficiently negative,
  - short when basis/premium context is sufficiently positive,
  - entry requires carry-adjusted edge and valid provider-backed context quality.
- Required all core `features_perp_context_v2` signal inputs and quality flags, including `quality_latest_window_context_only`, while allowing latest-window provenance as explicit non-promotion context evidence.
- Kept the strategy fail-closed on missing required columns, invalid quality flags, non-finite context values, unsupported feature sets, and unsupported holding windows.
- Added contract and backtest-engine coverage for standard signal output, feature/window rejection, metadata coverage, and research-only behavior.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\integration\test_backtest_engine_fixture.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
git diff --check
```

Results:

- Full compile passed.
- Focused WPR51 tests: 45 passed.
- Full contract suite: 130 passed.
- Historical synthetic smoke: 12 passed.
- `git diff --check` passed with CRLF working-copy warnings only.

## Research Boundary

This stage adds research-only strategy generation. It does not add live signals, promotion readiness, live configuration writes, order placement, capital allocation, hedged arbitrage behavior, liquidation/L2 requirements, or cross-exchange behavior.

## Remaining Notes

- WPR52 must run provider-backed cycle evidence and keep any candidate-pack outcome fail-closed unless the existing evidence floors pass.
- `baseline_no_trade` comparator support for `features_perp_context_v2` is a prerequisite for complete same-feature comparator coverage in WPR52.
