# Work Packet WP12-02 - Research Track Gates And Limitations

Stage: Stage 12 - Later-stage research expansion and institutional tuning
Substages: 12.2 through 12.7
Owner: Orchestrator Agent
Status: closed with empirical limitations
Date: 2026-05-03

## Objective

Complete the reproducible planning, manifest, and rejection-gate layer for the remaining Stage 12 tracks without claiming empirical acceptance where no OOS/stress evidence exists.

## Scope

- Add `src/tradingbotsuite/research/stage12_research.py`.
- Add `plan-stage12-research` CLI command.
- Cover all required remaining tracks:
  - 12.2 Regime model comparison.
  - 12.3 KNN diagnostics and alternatives.
  - 12.4 Meta-model testing.
  - 12.5 Exit model research.
  - 12.6 Portfolio and capital allocation.
  - 12.7 ETH and multi-asset expansion.
- Write reproducible per-hypothesis experiment specs.
- Write aggregate Stage 12 manifest, summary CSV, rejected/blocked/pending hypotheses, and completion-limitations artifact.
- Keep new research command rejected in live mode.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_stage12_research_plan.py tests/tradingbotsuite/test_feature_ablation.py -q
$env:PYTHONPATH='src'; python -m pytest tests/live/test_preflight.py -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.main plan-stage12-research --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main plan-stage12-research --output-dir "$env:TEMP\stage12-full-smoke" --dataset-manifest-hash sha256:validation
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/live -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_stage12_research_plan.py tests/tradingbotsuite/test_feature_ablation.py tests/tradingbotsuite/test_experiment_runner.py -q
```

## Empirical limitation

The code can complete the reproducible experiment-manifest and evidence-gate layer. It cannot truthfully complete empirical acceptance for Stage 12 hypotheses without enough real OOS/stress evidence, dependency approval for optional model families, portfolio prerequisites, and ETH-specific data artifacts.
