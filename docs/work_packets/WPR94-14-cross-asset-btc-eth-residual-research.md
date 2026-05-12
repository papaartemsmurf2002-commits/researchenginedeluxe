# WPR94-14 Cross-Asset BTC/ETH Residual Research

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Add a versioned BTC/ETH cross-asset residual research contract while keeping the
ETH/BTC beta-residual candidate blocked until durable ETH fixture readiness and
cross-symbol point-in-time joins are proven.

## Allowed Paths

- `docs/work_packets/WPR94-14-cross-asset-btc-eth-residual-research.md`
- `docs/stage_reports/STAGE_R94_CROSS_ASSET_BTC_ETH_RESIDUAL_RESEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/features/features_cross_asset_btc_eth_v2.json`
- `configs/research/cross_asset_btc_eth_residual_research_v1.json`
- `src/tradingbotsuite/features/packs.py`
- `src/tradingbotsuite/features/registry.py`
- `tests/contracts/test_feature_contracts.py`
- `tests/features/test_feature_builders.py`
- `tests/historical/test_full_cycle_synthetic.py`

## Scope

- Add `cross_asset_btc_eth_v2` as a feature pack/preset with BTC/ETH matched
  return, rolling ETH beta to BTC, residual return/z-score, ETHBTC trend/state,
  rolling correlation, funding-spread z-score, OI-delta spread, and explicit
  point-in-time join quality flags.
- Add tests proving the feature builder uses only as-of/current-or-past BTC/ETH
  bars and detects missing or future-aligned cross-symbol rows.
- Add research config metadata for `eth_btc_beta_residual_v2` that remains
  blocked until durable ETH fixture readiness, cross-symbol join proof,
  transparent comparator evidence, and correlation/stability checks exist.

## Non-Goals

- No new strategy plugin implementation.
- No BTC/ETH candidate-pack writing or promotion readiness.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, or sizing logic changes.
- No UI changes; those belong to the operator UI packet.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_feature_contracts.py tests\features\test_feature_builders.py tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

Passed on 2026-05-12.

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

## Exit Evidence

- Added `features_cross_asset_btc_eth_v2` and `cross_asset_btc_eth_v2`.
- Added BTC/ETH matched return, rolling beta, residual return/z-score, ETHBTC
  trend/state, rolling correlation, funding spread, OI delta spread, and
  explicit cross-symbol quality flags.
- Added tests proving future BTC/ETH rows do not change prior features and
  future-aligned source timestamps fail the point-in-time join/candidate-ready
  flags.
- Missing funding/OI/cross-symbol context remains `NaN` with quality flags, not
  zero-filled.
- Added blocked `eth_btc_beta_residual_v2` research metadata with durable ETH
  fixture, cross-symbol join, comparator, and correlation blockers.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, promotion readiness, candidate-pack writing, or sizing logic changed.
