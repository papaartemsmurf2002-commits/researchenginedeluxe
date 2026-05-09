# Stage R84 Full Research Run Fix Report

Date: 2026-05-09

## Scope

WPR84 diagnosed the latest operator full-research run artifacts and fixed two
operator-visible failure causes:

- The latest BTCUSDT historical cycle completed but wrote no candidate pack.
  Every `features_perp_context_v2` row carried the false blocker
  `feature_ablation_comparator_missing`, because the historical gate expected a
  same-strategy `features_price_trend_vol` comparator that current perp-context
  strategies cannot run.
- The "Run Full Research Review" button queued provider, experiment, and
  historical-cycle jobs, but did not queue the V4 discovery run that writes
  discovery ledgers and blocker diagnostics.

## Changes

- Treated `features_perp_context_v2` and `features_liquidation_context_v1` as
  required context feature sets with no runnable same-strategy price-only
  ablation comparator.
- Preserved comparator requirements for optional feature claims such as WT3D and
  full-context ablation paths.
- Updated the full-review UI flow to queue the discovery ledger run after the
  historical cycle.
- Added regression coverage for the historical ablation status and full-review
  UI orchestration.

## Boundaries

- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- No live order adapters, runtime-mode changes, position sizing, or live signal
  inputs were added.
- This fix does not claim that the latest-month fixture should produce a
  candidate pack. Remaining blockers such as low signal density, split trade
  count, cost-stress survival, and stability rejection still fail closed.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
# 35 passed

$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
# 13 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q
# 35 passed

python -m compileall -q src\tradingbotsuite

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed
```

## Result

The false ablation blocker is removed from perp-context historical cycles, and
operator full review now includes discovery ledger execution. Historical-cycle
candidate packs still remain fail-closed when the actual evidence is weak.
