# Stage R94 Cross-Asset BTC/ETH Residual Research Report

Date: 2026-05-12
Branch: `research/v3-experimental-engine`
Packet: `docs/work_packets/WPR94-14-cross-asset-btc-eth-residual-research.md`

## Summary

WPR94-14 is complete. The branch now has a versioned
`cross_asset_btc_eth_v2` feature pack and matching
`features_cross_asset_btc_eth_v2` manifest for BTC/ETH residual research.

The `eth_btc_beta_residual_v2` candidate remains blocked until durable ETH
fixture readiness, cross-symbol point-in-time join proof, transparent
comparators, and correlation/stability evidence exist.

## Changes

- Added BTC/ETH matched returns, rolling ETH beta to BTC, residual return,
  residual z-score, ETHBTC trend/state, rolling correlation, funding spread, and
  OI delta spread features.
- Added cross-symbol quality flags for missing BTC/ETH, missing durable context,
  missing funding/OI spread context, future alignment risk, matched intervals,
  point-in-time join proof, and candidate-ready eligibility.
- Added `configs/features/features_cross_asset_btc_eth_v2.json`.
- Added `configs/research/cross_asset_btc_eth_residual_research_v1.json`.
- Added focused point-in-time and missing-context regression tests.

## Boundary

No live trading behavior, live config writes, order placement, promotion
readiness, candidate-pack writing, or sizing logic changed.

Research outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_feature_contracts.py tests\features\test_feature_builders.py tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
python -m json.tool configs\features\features_cross_asset_btc_eth_v2.json > $null
python -m json.tool configs\research\cross_asset_btc_eth_residual_research_v1.json > $null
git diff --check
```

Results:

- Focused WPR94-14 tests: 56 passed.
- Feature contract/builder focused tests: 43 passed.
- Contracts: 397 passed.
- Research discovery: 144 passed.
- Compileall: passed.
- JSON parse checks: passed.
- Diff check: passed with existing CRLF conversion warnings only.
