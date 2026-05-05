# Stage R58 OI Contraction Exit Policy Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR58-01-oi-contraction-exit-policy.md`
Status: closed

## Scope

R58 added `oi_contraction_exit_v1` as a primary-bar research exit policy and included it as an additional checked exit policy in the BTCUSDT and ETHUSDT perp-context-v2 cycles.

## Changes

- Added `oi_contraction_exit_v1` to primary-bar research exits.
- Registered the policy in research-cycle spec validation.
- Added execution-simulator dispatch while keeping vector execution fixed-holding only.
- Preserved `features_perp_context_v2` OI and OI-quality columns in the backtest market frame.
- Added the policy to both checked perp-context-v2 cycle configs while keeping `fixed_holding_window` and `funding_aware_exit_v1` comparator coverage.
- Added focused tests for deterministic long/short OI-contraction exits, large-edge no-exit behavior, OI-quality-gap no-exit behavior, non-finite OI context rejection, missing OI context rejection, vector rejection, cache identity, spec acceptance, and BTC/ETH checked-cycle inclusion.

## Policy Semantics

`oi_contraction_exit_v1` exits when:

- `quality_has_oi_gap` is zero,
- optional `quality_provider_backed_all_required` is present and positive,
- `oi_delta_1h` is negative enough to pass `min_oi_delta_abs`,
- `oi_delta_z_7d` is below `-oi_delta_z_threshold`,
- current unrealized edge is less than or equal to `max_unrealized_edge_bps`.

The policy requires `oi_notional`, `oi_delta_1h`, `oi_delta_z_7d`, and `quality_has_oi_gap`. Row-level missing or non-finite context does not trigger an exit; it falls through to the normal time exit.

## Cycle Evidence

Generated local artifact roots:

```text
data/research/historical_cycles/btcusdt_perp_context_v2_foundation
data/research/historical_cycles/ethusdt_perp_context_v2_foundation
```

BTCUSDT summary:

- Candidate count: 156
- Aggregate backtests: 156
- Cost-stress backtests: 22
- Walk-forward split backtests: 4
- Backtest index rows: 182
- Exit policies: `fixed_holding_window`, `funding_aware_exit_v1`, `oi_contraction_exit_v1`
- Fixed-holding aggregate trades: 289
- Funding-aware aggregate trades: 301
- OI-contraction aggregate trades: 343
- Candidate pack written: false
- Pack-eligible candidates: 0
- Acceptance scope: `research_gate_evaluated_fail_closed`

ETHUSDT summary:

- Candidate count: 156
- Aggregate backtests: 156
- Cost-stress backtests: 22
- Walk-forward split backtests: 4
- Backtest index rows: 182
- Exit policies: `fixed_holding_window`, `funding_aware_exit_v1`, `oi_contraction_exit_v1`
- Fixed-holding aggregate trades: 295
- Funding-aware aggregate trades: 304
- OI-contraction aggregate trades: 332
- Candidate pack written: false
- Pack-eligible candidates: 0
- Acceptance scope: `research_gate_evaluated_fail_closed`

The new exit produced timing changes in provider-cycle evidence, but all candidates remained rejected by existing gates. This is research-only latest-window evidence, not OOS acceptance or promotion evidence.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\backtesting\test_exit_policy_expansion.py tests\backtesting\test_vector_engine_matches_reference.py tests\contracts\test_backtest_contracts.py tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_local_fixture_pack.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Results:

- WPR58 validation suite: 93 passed.
- Full compile passed.
- Full contract suite: 235 passed.
- Diff whitespace check passed.

## Research Boundary

This stage does not add live signals, promotion readiness, live configuration writes, order placement, capital allocation, candidate-pack promotion evidence, new data families, vector support for non-fixed exits, or OOS performance claims.

## Next Stage

WPR59 should be opened as a new packet before coding. The next planned item from `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md` is trial-budget and overfit-adjustment reporting, unless the plan is revised before implementation.
