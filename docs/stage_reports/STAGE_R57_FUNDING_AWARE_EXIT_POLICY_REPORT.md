# Stage R57 Funding-Aware Exit Policy Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR57-01-funding-aware-exit-policy.md`
Status: closed

## Scope

R57 added `funding_aware_exit_v1` as a primary-bar research exit policy and included it as an additional checked exit policy in the BTCUSDT and ETHUSDT perp-context-v2 cycles.

## Changes

- Added `funding_aware_exit_v1` to primary-bar research exits.
- Registered the policy in research-cycle spec validation.
- Added execution-simulator dispatch while keeping vector execution fixed-holding only.
- Preserved `perp_last_funding_rate`, funding-window timing columns, and latest-window quality flags in the backtest market frame.
- Added the policy to both checked perp-context-v2 cycle configs while keeping `fixed_holding_window` as comparator coverage.
- Added focused tests for long/short funding-aware exits, sufficient-edge no-exit behavior, policy-default isolation from generic target/stop fallbacks, missing context rejection, registered v2 funding-column support, vector rejection, cache identity, spec acceptance, and BTC/ETH checked-cycle inclusion.

## Policy Semantics

`funding_aware_exit_v1` exits before a near adverse funding window when:

- the row is inside `pre_funding_window_h`,
- funding is adverse to side and exceeds `funding_threshold`,
- expected funding cost exceeds `min_expected_cost_bps`,
- current unrealized edge is less than or equal to expected funding cost plus `edge_buffer_bps`.

The policy supports `funding_rate`, `perp_last_funding_rate`, or `last_funding_rate`, and requires `cal_time_to_next_funding_h`, `hours_to_next_funding`, or `time_to_next_funding_ms`. It does not model funding payments as backtest cashflows; it only changes exit timing.

## Cycle Evidence

Generated local artifact roots:

```text
data/research/historical_cycles/btcusdt_perp_context_v2_foundation
data/research/historical_cycles/ethusdt_perp_context_v2_foundation
```

BTCUSDT summary:

- Candidate count: 104
- Aggregate backtests: 104
- Cost-stress backtests: 22
- Walk-forward split backtests: 4
- Backtest index rows: 130
- Exit policies: `fixed_holding_window`, `funding_aware_exit_v1`
- Fixed-holding aggregate trades: 289
- Funding-aware aggregate trades: 301
- Candidate pack written: false
- Pack-eligible candidates: 0
- Acceptance scope: `research_gate_evaluated_fail_closed`

ETHUSDT summary:

- Candidate count: 104
- Aggregate backtests: 104
- Cost-stress backtests: 22
- Walk-forward split backtests: 4
- Backtest index rows: 130
- Exit policies: `fixed_holding_window`, `funding_aware_exit_v1`
- Fixed-holding aggregate trades: 295
- Funding-aware aggregate trades: 304
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

- WPR57 validation suite: 85 passed.
- Full compile passed.
- Full contract suite: 235 passed.
- Diff whitespace check passed.

## Research Boundary

This stage does not add live signals, promotion readiness, live configuration writes, order placement, capital allocation, candidate-pack promotion evidence, funding cashflow modeling, vector support for non-fixed exits, or OOS performance claims.

## Next Stage

WPR58 should be opened as a new packet before coding. The next planned item from `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md` is `oi_contraction_exit_v1`, unless the plan is revised before implementation.
