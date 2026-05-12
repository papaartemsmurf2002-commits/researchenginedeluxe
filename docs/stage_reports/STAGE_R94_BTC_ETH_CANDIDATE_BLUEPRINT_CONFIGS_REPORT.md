# Stage R94 BTC/ETH Candidate Blueprint Configs Report

Date: 2026-05-12
Branch: `research/v3-experimental-engine`
Packet: `docs/work_packets/WPR94-13-btc-eth-candidate-blueprint-configs.md`

## Summary

WPR94-13 is complete. The branch now has research-only candidate blueprint
metadata for `perp_basis_convergence_v3`, `oi_flow_breakout_v3`, and
`funding_crowding_fade_v3`, with each blueprint mapped to existing executable
v2 strategy plugins.

BTCUSDT has a diagnostic research-cycle config that can exercise existing
plugins and WPR94-11 exits while remaining candidate-pack ineligible because it
uses latest-window evidence. ETHUSDT is explicitly blocked until durable ETH
public-archive fixture readiness is recorded; the blocked config declares a
required fixture manifest path so it cannot silently fall back to synthetic data.

## Changes

- Added `configs/research/btc_eth_candidate_blueprints_v1.json`.
- Added `configs/research/full_cycle_btcusdt_candidate_blueprints_v1.json`.
- Added `configs/research/full_cycle_ethusdt_candidate_blueprints_blocked_v1.json`.
- Added contract coverage for blueprint IDs, executable v2 mappings, comparator
  coverage, ablations, no-regime/GMM truthfulness, KNN deferral, latest-window
  diagnostic-only scope, and ETH durable-fixture blocking.

## Boundary

No live trading behavior, live config writes, order placement, promotion
readiness, candidate-pack writing, or sizing logic changed.

Research outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\contracts\test_strategy_contracts.py tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
python -m json.tool configs\research\btc_eth_candidate_blueprints_v1.json > $null
python -m json.tool configs\research\full_cycle_btcusdt_candidate_blueprints_v1.json > $null
python -m json.tool configs\research\full_cycle_ethusdt_candidate_blueprints_blocked_v1.json > $null
git diff --check
```

Results:

- Focused WPR94-13/WPR94-12 tests: 319 passed.
- Contracts: 396 passed.
- Research discovery: 144 passed.
- Compileall: passed.
- JSON parse checks: passed.
- Diff check: passed with existing CRLF conversion warnings only.
