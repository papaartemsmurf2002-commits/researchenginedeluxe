# Stage R23 Validation Split Mode Cycle Evidence Report

Date: 2026-05-04
Owner: Codex Research Agent
Status: closed

## Scope

Stage R23 made validation split modes configurable in the historical research cycle while preserving the default purged walk-forward behavior.

No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work was performed. All outputs remain `research_only`, `observe_only`, and `promotion_ready: false`.

## Changes

- Added first-class `validation.split_modes` to historical cycle specs with default `purged_embargoed_walk_forward`.
- Preserved the legacy `validation.walk_forward` field without reinterpreting it as additional split modes.
- Added explicit cycle routing for:
  - `purged_embargoed_walk_forward`
  - `anchored_walk_forward`
  - `rolling_walk_forward`
  - `shifted_purged_walk_forward`
  - `month_holdout`
  - `stress_period_holdout`
  - `regime_holdout`
- Added shifted walk-forward split construction.
- Added fail-closed behavior when an explicitly configured split mode cannot be built.
- Added validation method, split mode, window, purge/embargo, and anchor-offset evidence to split metrics and backtest index records.
- Added richer split manifest evidence for requested modes, method counts, split-mode counts, and split configuration.

## Default Preservation

Default historical cycle specs still build only `purged_embargoed_walk_forward` splits.

The existing synthetic full-cycle default remains:

- `split_count`: 2
- `split_backtest_count`: 4
- `evaluation_scope`: unchanged as `walk_forward_split`

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/backtesting/test_splits.py tests/contracts/test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests/historical/test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests/historical/test_research_cycle_benchmark.py -q
$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q
git diff --check
```

Results: all passed. `git diff --check` reported line-ending warnings only.

## Decision

Stage R23 is closed. Configured validation split modes are now evidence-recorded historical research options. This does not make any candidate accepted, promotion-ready, or live-ready.
