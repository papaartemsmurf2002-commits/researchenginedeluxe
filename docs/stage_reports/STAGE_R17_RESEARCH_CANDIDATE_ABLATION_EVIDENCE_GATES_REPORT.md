# Stage R17 Research Candidate Ablation And Stress Evidence Gates Report

Date: 2026-05-04

## Scope

Closed `WPR17-01-research-candidate-ablation-evidence-gates`.

The packet made candidate-pack eligibility depend on candidate-tied ablation evidence and the full research stress scenario set. This remains historical research only; no live, paper, shadow, testnet, canary, promotion, order-placement, or capital-allocation work was added.

## Implemented

- Ranking rows now expose feature-ablation status, comparator feature-set/candidate identity, ablation deltas, and ablation failure reasons.
- `ablation_report.json` now includes candidate rows that mirror the ranking evidence and can be checked independently.
- Candidate-pack durable gates now reject missing or failed candidate ablation evidence.
- The stress registry now covers base costs, 2x slippage, 3x slippage, adverse funding, wide spread, missing optional context, high-volatility, low-volatility, trend-only, range-only, and shock/transition-only scenarios.
- `metrics_by_cost_stress.parquet` now records scenario groups, filters/transforms, spread, source row counts, stress dataset hashes, and scenario status.
- Candidate-pack durable gates now reject base-only/four-scenario stress evidence, missing required scenarios, unevaluated/no-source stress rows, zero-trade stress rows, and missing stress manifests.
- The complete fixture pass path still writes a research-only, observe-only, non-promotable pack; synthetic and incomplete evidence remain fail-closed.

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts/test_candidate_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests/historical -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite -q
git diff --check
```

Results:

- `compileall`: passed.
- `tests/research_artifacts/test_candidate_pack.py`: 23 passed.
- `tests/historical`: 10 passed.
- `tests/contracts`: 59 passed.
- `tests/live/test_preflight.py`: 24 passed.
- `tests/tradingbotsuite`: 273 passed.
- `git diff --check`: passed with existing LF-to-CRLF warnings only.

## Boundary

Research candidate packs remain evidence archives only. They are `research_only`, `observe_only`, `promotion_ready: false`, and rejected by live/preflight validation as live inputs.
