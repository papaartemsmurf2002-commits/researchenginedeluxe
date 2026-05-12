# Stage R97 Research UI Fastest Compute Summary Report

Date: 2026-05-12
Work packet: `docs/work_packets/WPR97-06-research-ui-fastest-compute-summary.md`

## Summary

WPR97-06 wires the final R97 compute default into the operator Research UI
artifact surface. Historical-cycle artifact summaries now expose:

- compute profile
- CPU thread count
- aggregate backtest workers used
- backend used counts
- GPU execution status
- selected CUDA backend
- CUDA runtime checked flag
- R97 batched CUDA requested flag
- Tensor Core screening requested flag

The Research artifact card now displays compute profile, worker count, backend
mix, GPU status, and whether CUDA was selected. Raw manifest details remain
available for complete audit context.

## Boundary

This is UI/read-only artifact summary wiring only. It does not change research
execution, live mode, live config, order placement, promotion readiness, or
position sizing.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_artifacts_include_historical_cycle_profitability_summary tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only -q
```
