# Stage R50 Perp Context V2 Feature Pack Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR50-01-perp-context-v2-feature-pack.md`
Status: closed

## Scope

R50 added `features_perp_context_v2` as a registered research feature set built from current durable context families: funding rate, premium index, open interest, and optional aggregate trade context.

## Changes

- Registered `perp_context_v2` and preset `features_perp_context_v2`.
- Added checked feature manifest config at `configs/features/features_perp_context_v2.json`.
- Added WPR50 columns:
  - premium/basis, funding, OI, aggregate-flow, and quality/context flags.
- Kept completed-bar and backward-as-of behavior through existing feature materialization.
- Derived 1h, 8h, and 7d windows from the active bar interval.
- Passed through aggregate-trade quote-volume fields during fixture-family context materialization so flow-notional features are real when `agg_trade` exists.
- Preserved missing optional context as `NaN` plus `missing_*` and quality columns.
- Preserved feature-cache context identity through the existing `fixture_family_context_sha256`.
- Removed a context-heavy feature-frame fragmentation warning by concatenating passthrough columns in one operation.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite\features
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_feature_contracts.py tests\features -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py tests\historical\test_full_cycle_local_fixture_pack.py -q
```

Results:

- Feature compile passed.
- Focused feature tests: 23 passed.
- Full compile passed.
- Full contract suite: 105 passed.
- Selected historical cycle tests: 20 passed.

## Research Boundary

This stage adds registered research features only. It does not add live signals, promotion readiness, live configuration writes, capital allocation, order placement, liquidation/L2 requirements, cross-exchange requirements, or multi-symbol cycle behavior.
