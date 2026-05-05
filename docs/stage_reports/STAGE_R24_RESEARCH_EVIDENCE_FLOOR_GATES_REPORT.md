# Stage R24 Research Evidence Floor Gates Report

Date: 2026-05-04
Owner: Codex Research Agent
Status: closed

## Scope

Stage R24 tightened research candidate evidence floors for historical cycles and durable candidate-pack validation.

No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work was performed. All artifacts remain research-only, observe-only, and not promotion-ready.

## Changes

- Added `validation.min_cost_stress_survival_rate` with default `1.0`.
- Added split metric evidence for `trade_count_floor` and `trade_count_floor_status`.
- Added cost-stress metric evidence for `stress_survival_score` and `stress_survival_status`.
- Runner research gates now enforce:
  - per-split trade-count floors;
  - configured validation method coverage;
  - configured cost-stress survival floors;
  - split dominance limits.
- Candidate-pack validation now durably recomputes:
  - per-split trade floor failures;
  - validation method coverage and counts from `split_manifest.json`;
  - stress survival from `metrics_by_cost_stress.parquet`;
  - split dominance from `metrics_by_split.parquet`.

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_research_cycle_contract.py tests/historical/test_full_cycle_synthetic.py tests/research_artifacts/test_candidate_pack.py -q
python -m compileall -q src/tradingbotsuite; $env:PYTHONPATH='src'; python -m pytest tests/contracts tests/backtesting tests/historical tests/research_artifacts tests/live -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite tests/optimization tests/features tests/integration tests/unit -q
git diff --check
```

Results:

- Focused WPR24 tests: passed.
- Contracts/backtesting/historical/research-artifacts/live: 197 passed.
- Tradingbotsuite/optimization/features/integration/unit: 322 passed.
- `git diff --check`: line-ending warnings only.

## Decision

Stage R24 is closed. Historical research candidates now face stricter split and stress evidence floors, but no candidate is promoted, live-ready, or executable from this work.
