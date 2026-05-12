# WPR94-12 Strategy Family Matrix Using Existing Plugins

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Define a research-only strategy family matrix using existing strategy plugins
instead of duplicating plugin implementations. Every selected family must carry
no-trade and transparent comparator coverage, and KNN overlays must never be the
only tested strategy for a family.

## Allowed Paths

- `docs/work_packets/WPR94-12-strategy-family-matrix-existing-plugins.md`
- `docs/stage_reports/STAGE_R94_STRATEGY_FAMILY_MATRIX_EXISTING_PLUGINS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/strategy_family_matrix_existing_plugins_v1.json`
- `configs/research/full_cycle_btcusdt_strategy_family_matrix_v1.json`
- `src/tradingbotsuite/research_cycle/spec.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/contracts/test_strategy_contracts.py`
- `tests/historical/test_full_cycle_synthetic.py`

## Scope

- Add a compact strategy-family matrix manifest that maps existing plugins to:
  trend continuation, range/chop reversion, funding/basis, OI flow, current
  GMM/regime, KNN overlay, and diagnostic liquidation families.
- Add a BTCUSDT historical-cycle config that exercises existing transparent
  plugins, no-trade comparators, KNN overlay, and exit variants without writing
  promotion artifacts.
- Extend research-cycle exit-policy parsing only as needed for the WPR94-11
  research exits.
- Add tests proving:
  - every selected family has a no-trade comparator;
  - KNN overlay families list transparent comparators;
  - diagnostic liquidation stays diagnostic-only;
  - current regime family wording remains GMM/current-regime truthful;
  - the matrix config parses as research-only evidence.

## Non-Goals

- No new strategy plugin implementation.
- No BTC/ETH candidate blueprint configs; those belong to the next packet.
- No cross-asset residual research.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, promotion readiness, candidate-pack writing, or sizing logic changes.

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
python -m json.tool configs\research\strategy_family_matrix_existing_plugins_v1.json > $null
python -m json.tool configs\research\full_cycle_btcusdt_strategy_family_matrix_v1.json > $null
git diff --check
```

Results:

- Focused WPR94-12 tests: 316 passed.
- Contracts: 393 passed.
- Research discovery: 144 passed.
- Compileall: passed.
- JSON parse checks: passed.
- Diff check: passed with existing CRLF conversion warnings only.

## Exit Evidence

- Added `strategy_family_matrix_existing_plugins_v1` as a research-only,
  observe-only, non-promotion matrix over existing strategy plugins.
- Added a BTCUSDT research-cycle config that references the matrix, existing
  plugins, no-trade and transparent comparators, and non-KNN WPR94-11 research
  exits without writing promotion artifacts.
- KNN remains an overlay/filter treatment with required non-KNN companion
  strategies and transparent comparators; KNN strategy and KNN exits are
  deferred in the BTCUSDT cycle until split-safe materialized prediction
  overlays exist.
- Current regime family wording is explicitly GMM/current-regime evidence and
  does not claim true HMM backend usage; no-regime and GMM mode requirements are
  explicit.
- The latest-month BTCUSDT cycle fixture is marked diagnostic-only and
  candidate-pack ineligible.
- Diagnostic liquidation remains diagnostic-only and candidate-pack ineligible.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, promotion readiness, candidate-pack writing, or sizing logic changed.
