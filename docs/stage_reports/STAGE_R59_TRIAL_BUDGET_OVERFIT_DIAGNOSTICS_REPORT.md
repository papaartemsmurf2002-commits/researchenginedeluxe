# Stage R59 Trial-Budget And Overfit Diagnostics Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR59-01-trial-budget-overfit-diagnostic-reports.md`
Status: closed

## Scope

R59 added two historical research-cycle diagnostic outputs:

- `trial_budget_report.json`
- `overfit_adjustment_report.json`

Both reports are research-only, observe-only, promotion-ready false, and required as reproducible evidence artifacts. Their diagnostic scores and warnings do not change candidate rankings, candidate-pack metric gates, promotion gates, or live-readiness gates.

## Changes

- Added trial-budget report generation to the historical research-cycle runner.
- Added overfit-adjustment diagnostic report generation using existing rankings, stability, split, and cost-stress evidence.
- Added both reports to cycle `required_outputs` and candidate-pack required artifact validation.
- Added tests proving overfit diagnostic warnings do not block an otherwise eligible research candidate pack.
- Added synthetic-cycle tests for report presence, trial counts, explicit-search accounting, and diagnostic-only scope.

## Report Semantics

`trial_budget_report.json` records candidate-search breadth, comparator counts, shortlist counts, backtest evaluation counts, and trial counts by strategy, feature set, holding window, exit policy, candidate source, and search method.

`overfit_adjustment_report.json` records deterministic diagnostic proxies for trial-count penalty, family-rank PBO, split/cost-stress CPCV, stability penalty, and overfit-adjusted scores. These are diagnostics only, not formal OOS acceptance tests.

## Cycle Evidence

Generated local artifact roots:

```text
data/research/historical_cycles/btcusdt_perp_context_v2_foundation
data/research/historical_cycles/ethusdt_perp_context_v2_foundation
```

BTCUSDT summary:

- Candidate count: 156
- Aggregate backtests: 156
- Cost-stress backtests: 22
- Walk-forward split backtests: 4
- Total backtest evaluations: 182
- Trial-budget effective trials: 156
- Overfit candidate diagnostics: 156
- `trial_budget_report` in required outputs: true
- `overfit_adjustment_report` in required outputs: true
- Overfit candidate-pack gate enabled: false
- Candidate pack written: false
- Pack-eligible candidates: 0
- Acceptance scope: `research_gate_evaluated_fail_closed`

ETHUSDT summary:

- Candidate count: 156
- Aggregate backtests: 156
- Cost-stress backtests: 22
- Walk-forward split backtests: 4
- Total backtest evaluations: 182
- Trial-budget effective trials: 156
- Overfit candidate diagnostics: 156
- `trial_budget_report` in required outputs: true
- `overfit_adjustment_report` in required outputs: true
- Overfit candidate-pack gate enabled: false
- Candidate pack written: false
- Pack-eligible candidates: 0
- Acceptance scope: `research_gate_evaluated_fail_closed`

The checked provider cycles remain fail-closed. No candidate pack, promotion evidence, OOS acceptance, or performance claim was created.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\historical\test_full_cycle_synthetic.py tests\historical\test_full_cycle_local_fixture_pack.py tests\research_artifacts\test_candidate_pack.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Results:

- WPR59 validation suite: 82 passed.
- Full compile passed.
- Full contract suite: 235 passed.
- Diff whitespace check passed.

## Research Boundary

This stage does not add live signals, promotion readiness, live configuration writes, order placement, capital allocation, OOS performance claims, hard overfit gates, or changes to candidate-pack metric eligibility.

## Next Stage

WPR60 should be opened as a new packet before coding. The next planned item from `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md` is the split-safe HMM router, unless the plan is revised before implementation.
