# WPR94-09 AggTrade Orderflow Feature Pack

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Add a dedicated aggTrade trade-flow feature pack for durable public archive
research without calling it order-book imbalance or true OFI.

## Allowed Paths

- `docs/work_packets/WPR94-09-aggtrade-orderflow-feature-pack.md`
- `docs/stage_reports/STAGE_R94_AGGTRADE_ORDERFLOW_FEATURE_PACK_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/features/registry.py`
- `src/tradingbotsuite/features/packs.py`
- `src/tradingbotsuite/features/builders.py`
- `configs/features/features_aggtrade_orderflow_v1.json`
- `configs/features/features_price_perp_aggflow_no_wt.json`
- `tests/features/test_feature_builders.py`
- `tests/contracts/test_feature_contracts.py`

## Scope

- Add `aggtrade_orderflow_v1` and a preset manifest.
- Add a combined price/perp/aggflow no-WT preset if the registry pattern stays
  modular and reviewable.
- Build only from aggTrade-compatible trade-flow proxy columns.
- Keep missing aggTrade data as `NaN` with explicit missingness and quality
  flags.
- Keep `top_of_book_imbalance`, `queue_imbalance_l5`, depth/L2, and true OFI
  out of this pack.

## Non-Goals

- No true order-book imbalance, true OFI, L2/depth reconstruction, or
  liquidation candidate-ready claim.
- No live trading behavior, live config writes, order placement, runtime mode
  changes, promotion readiness, candidate-pack writing, or sizing logic changes.
- No data download or provider intake rewrite.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py tests\contracts\test_feature_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

- `$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py tests\contracts\test_feature_contracts.py -q` - 40 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` - 382 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q` - 140 passed.
- `python -m compileall -q src\tradingbotsuite` - passed.
- `git diff --check` - passed with existing CRLF conversion warnings only.

## Exit Evidence

- Added registered `aggtrade_orderflow_v1` and `features_aggtrade_orderflow_v1`.
- Added `features_price_perp_aggflow_no_wt` without `microstructure_context_v1`.
- Added trade-flow proxy features for taker buy share, signed quote imbalance,
  sqrt signed imbalance, CVD slope, count/volume z-scores, large-trade proxy,
  burst score, and sweep proxy.
- Kept missing aggTrade context as `NaN` plus explicit missingness and quality
  flags.
- Kept top-of-book, queue imbalance, L2/depth, and true OFI out of the new
  pack and manifests.
- Added focused registry, manifest, materialized fixture, and no-depth-leakage
  tests.
