# WPR94-13 BTC/ETH Candidate Blueprint Configs

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Convert the strongest BTC/ETH handoff ideas into explicit research-only
blueprint configs after the truthfulness, durable data, exit-lab, validation,
and strategy-family matrix packets. These are blueprints and runnable research
cycle configs where safe, not promotion artifacts.

## Allowed Paths

- `docs/work_packets/WPR94-13-btc-eth-candidate-blueprint-configs.md`
- `docs/stage_reports/STAGE_R94_BTC_ETH_CANDIDATE_BLUEPRINT_CONFIGS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/btc_eth_candidate_blueprints_v1.json`
- `configs/research/full_cycle_btcusdt_candidate_blueprints_v1.json`
- `configs/research/full_cycle_ethusdt_candidate_blueprints_blocked_v1.json`
- `tests/contracts/test_strategy_contracts.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`

## Scope

- Add research-only blueprint configs for:
  - `perp_basis_convergence_v3`
  - `oi_flow_breakout_v3`
  - `funding_crowding_fade_v3`
- Map blueprint IDs to existing executable strategy plugins rather than adding
  new strategy implementations.
- Define required ablations for basis/premium, funding, OI, aggTrade flow,
  no-regime baseline, no-KNN, fixed-hold, normalization exits, and
  OI-contraction exit evidence.
- Add a BTCUSDT cycle config that can run as diagnostic/screening research
  against current safe fixtures while blocking candidate-pack eligibility for
  latest-window evidence.
- Add an ETHUSDT blueprint config that is blocked until durable ETH fixture
  readiness is recorded.
- Add tests proving comparator coverage, required ablations, no-regime baseline
  requirements, KNN deferral, latest-window diagnostic-only scope, ETH durable
  fixture blocker, and research-only/non-promotion flags.

## Non-Goals

- No new strategy plugin implementation.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, promotion readiness, candidate-pack writing, or sizing logic changes.
- No cross-asset BTC/ETH residual feature work; that belongs to WPR94-14.
- No operator UI changes; those belong to the final UI packet.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\contracts\test_strategy_contracts.py tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

Passed on 2026-05-12.

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

## Exit Evidence

- Added `btc_eth_candidate_blueprints_v1` with research-only v3 blueprint IDs
  mapped to existing executable v2 strategy plugins.
- Added a BTCUSDT diagnostic research-cycle config using existing plugins,
  transparent/no-trade comparators, no-regime requirements, non-KNN exits, and
  latest-window candidate-pack blockers.
- Added a blocked ETHUSDT config that requires a durable ETH public-archive
  fixture manifest and fails rather than falling back to synthetic data.
- KNN remains deferred until split-safe materialized prediction overlays exist.
- Blueprint ablations cover basis/premium, funding, OI, aggTrade flow,
  no-regime, no-KNN, fixed-hold, normalization exits, OI-contraction exit, cost
  drag, and crowding-overfit checks.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, promotion readiness, candidate-pack writing, or sizing logic changed.
