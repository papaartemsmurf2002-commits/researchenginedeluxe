# Stage R52 Provider Perp Context Cycle Evidence Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR52-01-provider-perp-context-cycle-evidence.md`
Status: closed

## Scope

R52 added and executed the first provider-backed BTCUSDT historical research cycle for `features_perp_context_v2` and `perp_basis_convergence_v2`.

## Changes

- Added checked cycle spec `configs/research/full_cycle_btcusdt_perp_context_v2.json`.
- Allowed `baseline_no_trade` to consume `features_perp_context_v2` so same-feature no-trade comparator coverage is complete.
- Added historical coverage proving the checked spec:
  - consumes the provider-backed BTCUSDT latest-month fixture,
  - materializes `features_perp_context_v2`,
  - includes `perp_basis_convergence_v2` and `baseline_no_trade`,
  - writes rankings, backtest index, feature-build, gate, and manifest artifacts,
  - stays `research_only`, `observe_only`, and `promotion_ready: false`.
- Ran the checked cycle into `data/research/historical_cycles/btcusdt_perp_context_v2_foundation`.

## Cycle Evidence

Generated local artifact root:

```text
data/research/historical_cycles/btcusdt_perp_context_v2_foundation
```

Summary:

- Fixture: `data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json`
- Joined context families: `funding_rate`, `premium_index`, `open_interest`
- Feature set: `features_perp_context_v2`
- Strategies: `baseline_no_trade`, `perp_basis_convergence_v2`
- Candidate count: 16
- Aggregate backtests: 16
- Split backtests: 4
- Cost-stress backtests: 22
- Backtest index rows: 42
- Baseline comparator coverage: complete
- Candidate pack written: false
- Pack-eligible candidates: 0
- Acceptance scope: `research_gate_evaluated_fail_closed`

Top candidates were rejected by existing evidence gates, primarily missing ablation evidence, incomplete long/short side evidence, split/cost-stress evidence requirements, and stability-region requirements. This is the intended fail-closed outcome for a compact latest-month provider fixture and is not OOS acceptance evidence.

The generated cycle artifact directory remains under the repo's existing ignored `data/research/historical_cycles` policy; the checked spec and tests make the run reproducible.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py tests\historical\test_full_cycle_local_fixture_pack.py::test_checked_in_perp_context_v2_cycle_consumes_provider_context_fixture -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\contracts\test_strategy_contracts.py tests\historical -q
git diff --check
```

Results:

- Full compile passed.
- Focused WPR52 tests: 40 passed.
- WPR52 validation suite: 96 passed.
- `git diff --check` passed with CRLF working-copy warnings only.

## Research Boundary

This stage does not add live signals, promotion readiness, live configuration writes, order placement, capital allocation, candidate-pack promotion evidence, or OOS performance claims.

## Next Stage

WPR53 should be opened as a new packet before coding. The next planned item is a transparent `funding_crowding_fade_v2` strategy, but it needs explicit packet scope and tests before implementation.
