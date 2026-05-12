# Stage R94 AggTrade Orderflow Feature Pack Report

Date: 2026-05-12
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR94-09-aggtrade-orderflow-feature-pack.md`

## Scope

WPR94-09 added a dedicated aggTrade trade-flow proxy feature pack and checked
feature manifests. It did not add provider intake, archive downloads, candidate
pack writes, promotion readiness, live execution, or sizing behavior.

## Completed

- Registered `aggtrade_orderflow_v1` and `features_aggtrade_orderflow_v1`.
- Added `features_price_perp_aggflow_no_wt`, combining price/trend/vol,
  `perp_context_v3`, aggTrade flow proxy, and calendar features without
  `microstructure_context_v1`.
- Added proxy columns for taker buy quote share, signed quote imbalance, square
  root signed imbalance, CVD slope, trade-count and quote-volume z-scores,
  large-trade side imbalance, flow burst, and sweep proxy.
- Added explicit aggTrade quality columns for missing context, source presence,
  latest-window diagnostic status, and `not_ofi` proxy truthfulness.
- Extended aggTrade fixture-family aliases for trade-count and large-trade
  proxy counts.
- Added contract and builder coverage for manifests, missingness, materialized
  aggTrade context, and exclusion of depth/book/true-OFI claims.

## Boundary Notes

- The new pack uses `agg_trade` only.
- `top_of_book_imbalance`, `queue_imbalance_l5`, L2/depth reconstruction, and
  true OFI are excluded from the new pack and combined preset.
- Roadmap WPR numbering in the planning document predates the active ledger
  numbering; this report follows the active ledger packet `WPR94-09`.
- Research outputs remain non-promotional; no live trading path changed.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py tests\contracts\test_feature_contracts.py -q
# 40 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 382 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 140 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with existing CRLF conversion warnings only
```

## Decision

WPR94-09 is complete. The next roadmap step is discovery compute telemetry and
cached KNN sweeps.
