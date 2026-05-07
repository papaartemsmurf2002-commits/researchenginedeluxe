# WPR77-01 WT/KNN Strategy Candidate Integration

Stage: R77 WT/KNN strategy candidate integration
Owner: Codex Research Agent
Status: closed
Created: 2026-05-07

## Goal

Wire split-safe discovery KNN predictions into the standard
`hmm_knn_local_analog_filter_v2` strategy path and expose raw signal, blocked
signal, and executed trade accounting for discovery candidates.

## Allowed Paths

```text
src/tradingbotsuite/research_discovery/**
src/tradingbotsuite/research_cycle/spec.py
src/tradingbotsuite/research_cycle/runner.py
src/tradingbotsuite/strategies/hmm_knn_local_analog_filter.py
tests/research_discovery/**
tests/contracts/test_research_cycle_contract.py
tests/contracts/test_strategy_contracts.py
docs/work_packets/WPR77-01-wt-knn-strategy-candidate-integration.md
docs/stage_reports/STAGE_R77_WT_KNN_STRATEGY_CANDIDATE_INTEGRATION_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Consume only materialized split-safe HMM/KNN columns; do not fit HMMs or
  recompute neighbors inside the strategy integration layer.
- Keep outputs `research_only`, `observe_only`, and `promotion_ready: false`.
- Preserve the standard strategy plugin and backtest engine boundary.
- Do not add live execution, promotion behavior, sizing, order placement,
  operator UI behavior, or candidate-pack promotion bridges.

## Required Output

- Discovery-side strategy candidate/accounting utilities for
  `hmm_knn_local_analog_filter_v2`.
- Opt-in historical-cycle materialized prediction overlays for
  `features_perp_context_v2`.
- Raw KNN-eligible row, plugin signal, backtest-executable signal, filter-block,
  and executed trade counts.
- Artifact writer for candidate accounting evidence.
- Focused tests proving materialized KNN rows flow into the plugin and that
  active plugin signals are executable by the backtest filter.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_strategy_contracts.py -q
```

Run full contracts before closing if shared contracts change.

## Close Evidence

- Added opt-in historical-cycle materialized prediction overlays under
  `features.materialized_prediction_overlays`.
- Overlay loading validates research/observe/promotion manifest flags, approved
  HMM/KNN columns, one-to-one row alignment, join-key uniqueness, and split-safe
  accepted neighbor boundaries.
- Overlay identity now updates the materialized feature-frame hash and feature
  build manifest before candidate backtests.
- Added discovery-side HMM/KNN strategy accounting artifacts with raw accepted
  rows, plugin signals, backtest-executable signals, filter blocks, and optional
  executed trade count.
- Corrected active `hmm_knn_local_analog_filter_v2` signals to emit empty
  `skip_reason` so the standard backtest engine can execute them.
- Validation passed on 2026-05-07 with compile, focused discovery tests,
  strategy contracts, research-cycle contracts, full contracts, and a temp
  historical-cycle overlay smoke run.
