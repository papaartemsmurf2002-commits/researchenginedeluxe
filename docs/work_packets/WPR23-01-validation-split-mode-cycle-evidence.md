# WPR23-01 Validation Split Mode Cycle Evidence

Status: closed
Owner: Codex Research Agent
Stage: Stage R23 validation split mode cycle evidence
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Make additional historical validation split modes available to the research cycle as explicit, evidence-recorded options while preserving the default purged walk-forward behavior.

The plan requires anchored, rolling, purged walk-forward, month holdout, stress-period holdout, and regime holdout validation. Builders exist for several modes, but the cycle runner currently executes only the purged walk-forward path.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR23-01-validation-split-mode-cycle-evidence.md`
- `docs/stage_reports/STAGE_R23_VALIDATION_SPLIT_MODE_CYCLE_EVIDENCE_REPORT.md`
- `src/tradingbotsuite/backtesting/splits.py`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/backtesting/test_splits.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_research_cycle_benchmark.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No default increase in CI cycle runtime.
- No candidate acceptance or promotion-ready claims.
- No model fitting inside validation splits.

## Implementation plan

1. Add validation spec fields for optional split modes, shifted anchors, and rolling train window size.
2. Preserve default `purged_embargoed_walk_forward` output and counts.
3. Add split builders for shifted walk-forward where needed.
4. Have the research cycle execute configured split modes for shortlisted candidates and record split-mode evidence.
5. Add focused tests for default preservation and explicit holdout/shifted split evidence.

## Exit criteria

- Default historical cycles retain existing split counts.
- Explicit validation split modes create additional split manifest entries and split backtest rows.
- Split records include validation method and split mode evidence.
- Contracts, historical tests, split tests, benchmark tests, and live preflight pass.

## Completion summary

- Added first-class `validation.split_modes` with default `purged_embargoed_walk_forward`, preserving legacy `walk_forward` compatibility and default split counts.
- Added explicit anchored, rolling, shifted purged, month holdout, stress-period holdout, and regime holdout cycle routing with fail-closed unavailable-mode behavior.
- Added shifted walk-forward split construction and split metadata for validation method, split mode, train/validation windows, purge/embargo, and anchor offsets.
- Added split evidence to `split_manifest.json`, `metrics_by_split.parquet`, and `backtest_index.parquet` without changing `evaluation_scope`.
- Preserved research-only, observe-only, and `promotion_ready: false` boundaries; no live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work was added.

## Validation evidence

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/backtesting/test_splits.py tests/contracts/test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests/historical/test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests/historical/test_research_cycle_benchmark.py -q
$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q
git diff --check
```

Results: all passed. `git diff --check` reported line-ending warnings only.
