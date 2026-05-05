# WPR59-01 Trial-Budget And Overfit Diagnostic Reports

Owner: Codex Research Agent
Status: closed
Stage: R59 trial-budget and overfit diagnostics
Date opened: 2026-05-05

## Goal

Add `trial_budget_report.json` and `overfit_adjustment_report.json` to historical research-cycle outputs as research-only diagnostics. The reports must account for candidate-search breadth and overfit-adjusted diagnostics without changing candidate-pack pass/fail gates in this packet.

## Allowed Paths

```text
src/tradingbotsuite/research_cycle/runner.py
src/tradingbotsuite/research_artifacts/candidate_pack.py
tests/contracts/test_research_cycle_contract.py
tests/historical/test_full_cycle_synthetic.py
tests/historical/test_full_cycle_local_fixture_pack.py
tests/research_artifacts/test_candidate_pack.py
configs/research/full_cycle_btcusdt_perp_context_v2.json
configs/research/full_cycle_ethusdt_perp_context_v2.json
data/research/historical_cycles/btcusdt_perp_context_v2_foundation/**
data/research/historical_cycles/ethusdt_perp_context_v2_foundation/**
docs/work_packets/WPR59-01-trial-budget-overfit-diagnostic-reports.md
docs/stage_reports/STAGE_R59_TRIAL_BUDGET_OVERFIT_DIAGNOSTICS_REPORT.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Keep both reports research-only, observe-only, and promotion-ready false.
- Do not make deflated Sharpe, PBO, CPCV, or adjusted-score diagnostics hard candidate-pack gates in this packet.
- Add reports to cycle `required_outputs` only together with candidate-pack required-output validation support.
- Do not add live execution, promotion readiness, order placement, capital allocation, runtime-control writes, or OOS performance claims.
- Do not change strategy, feature, holding-window, exit-policy, vector, or provider collection behavior.

## Report Scope

`trial_budget_report.json` should summarize candidate-search breadth and trial accounting by strategy, feature set, holding window, exit policy, candidate source, and optimizer stage/source.

`overfit_adjustment_report.json` should expose diagnostic-only adjusted scores and overfit warnings derived from existing rankings, stability, split, and cost-stress evidence. It must clearly state that hard gates are disabled for this packet.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_synthetic.py tests\historical\test_full_cycle_local_fixture_pack.py tests\research_artifacts\test_candidate_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close Evidence

Record report schemas, checked-cycle evidence, unchanged fail-closed candidate-pack status, validation results, and residual risks in `docs/stage_reports/STAGE_R59_TRIAL_BUDGET_OVERFIT_DIAGNOSTICS_REPORT.md`, then close this work packet and ledger row if validation is clean.

Closed 2026-05-05 with validation and cycle evidence recorded in `docs/stage_reports/STAGE_R59_TRIAL_BUDGET_OVERFIT_DIAGNOSTICS_REPORT.md`.
