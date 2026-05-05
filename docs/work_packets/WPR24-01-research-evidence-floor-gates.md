# WPR24-01 Research Evidence Floor Gates

Status: closed
Owner: Codex Research Agent
Stage: Stage R24 research evidence floor gates
Opened: 2026-05-04
Closed: 2026-05-04

## Objective

Tighten research candidate gates so split and stress evidence floors match the research completion plan. A candidate must not be pack-eligible merely because split and stress artifacts exist; it must meet per-split trade floors and survive the configured stress scenario set.

## Allowed paths

- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR24-01-research-evidence-floor-gates.md`
- `docs/stage_reports/STAGE_R24_RESEARCH_EVIDENCE_FLOOR_GATES_REPORT.md`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/research_artifacts/test_candidate_pack.py`
- `tests/live/test_preflight.py`

## Non-goals

- No live, paper, shadow, testnet, canary, promotion, order-placement, or capital allocation work.
- No candidate acceptance or promotion-ready claims.
- No changes to default research-cycle split counts.
- No model fitting or parameter optimization refactor.

## Implementation plan

1. Add validation spec evidence-floor fields while preserving existing defaults.
2. Require every validation split to meet the configured trade-count floor.
3. Require cost-stress survival to meet a configured minimum survival rate, defaulting to full scenario survival.
4. Record floor evidence in rankings, split metrics, and cost-stress metrics.
5. Mirror the runner gate semantics in durable research candidate-pack validation.

## Exit criteria

- Ranking gate details expose split trade-floor and stress-survival floor evidence.
- Candidate pack validation blocks below-floor split metrics and failed stress scenarios.
- Existing synthetic cycles remain rejected and default counts stay stable.
- Contracts, historical cycle tests, research artifact tests, live preflight, and diff check pass.

## Completion summary

- Added `validation.min_cost_stress_survival_rate` with a default full-survival floor of `1.0`.
- Added per-split trade-count floor evidence to split metrics and ranking gate details.
- Added cost-stress survival score/status evidence to stress metrics and ranking gate details.
- Tightened runner research gates for per-split trade floors, validation method coverage, configured stress-survival floors, and split dominance.
- Tightened durable candidate-pack validation to recompute split trade floors, validation method coverage, stress survival, and split dominance from artifact rows instead of trusting ranking summaries.
- Kept local fixture pack pass-path evidence explicit by configuring its lower stress-survival floor in the test spec.
- Preserved research-only, observe-only, and `promotion_ready: false` boundaries.

## Validation evidence

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_research_cycle_contract.py tests/historical/test_full_cycle_synthetic.py tests/research_artifacts/test_candidate_pack.py -q
python -m compileall -q src/tradingbotsuite; $env:PYTHONPATH='src'; python -m pytest tests/contracts tests/backtesting tests/historical tests/research_artifacts tests/live -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite tests/optimization tests/features tests/integration tests/unit -q
git diff --check
```

Results: focused WPR24 tests passed, broader baseline passed with 197 tests, supporting suites passed with 322 tests. `git diff --check` reported line-ending warnings only.
