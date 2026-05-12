# Stage R94 Matched Filter Ablation V2 Report

Date: 2026-05-12
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR94-04-matched-filter-ablation-v2.md`

## Summary

WPR94-04 added a matched-filter ablation policy that distinguishes true edge
improvement from sample reduction and blocks filter defaults unless a filter
beats an exact matched no-filter comparator.

Implemented:

- Added `filter_ablation_matrix_v5.json` for matched filter-on/filter-off
  comparisons.
- Added matched-filter decision labels:
  `edge_improving`, `sample_reducing_only`, `unstable`, `side_specific`,
  `not_testable`, and `harmful`.
- Added required matched grouping over entry family, feature set, feature
  column set, label horizon, regime mode, KNN settings, exit policy, split id,
  and cost model id.
- Added finite/provider-backed evidence checks for required filter columns.
- Added planned filter families: HVP/realized-vol, ATR, ER/chop, volatility
  shock, funding, basis/premium, OI, aggTrade flow, and liquidation.
- Locked `filter_default_allowed` so only V2 `edge_improving` matched-filter
  rows can default.
- Changed legacy V4 broad ablation rows to diagnostic-only default behavior.

## Boundary Notes

- Research outputs remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- No candidate packs are written and no promotion readiness is claimed.
- No live order placement, live config writes, runtime mode changes, or sizing
  behavior was added.
- AggTrade rows are labeled as trade-flow proxy evidence, not order-book
  imbalance or true OFI.
- Liquidation filters remain not testable unless finite provider-backed
  evidence is present.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_ablation_matrix.py -q
# 26 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 123 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with line-ending warnings only
```

## Next Packet

Continue the explicit R94 priority list with a multiple-testing and stability
gate upgrade before validation-floor and blocker-registry work.
