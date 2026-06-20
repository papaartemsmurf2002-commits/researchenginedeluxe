# Stage R106 Side-Veto Gate Evidence Closure Report

Date: 2026-06-10

Work packet: `docs/work_packets/WPR106-84-side-veto-gate-evidence-closure.md`

## Scope

WPR106-84 closed the explicit one-sided side-veto gate representation blocker
without relaxing candidate-pack safety. The packet audited the optimized
BTCUSDT aggTrade sparse lead from WPR106-82, added paired opposite-side control
semantics, added transparent and no-trade baseline requirements, fixed sparse
aggTrade ablation matching, separated side-veto stability families, and made
side metric accounting explicit.

The tested lead was:

`941c7d1a1a3b8669c66e816ee465dc30cf18b1fba56c54b95555a027cdf046d6`

## Code Changes

- `src/tradingbotsuite/research_cycle/runner.py` now distinguishes legacy
  missing long/short side evidence from declared one-sided
  `sparse_event_filter_v1` contracts.
- Explicit one-sided side-veto rows require an exact opposite-side control with
  matching non-side parameters, no-trade underperformance by that control, and
  transparent-baseline evidence for the lead.
- Sparse aggTrade feature-ablation matching ignores flow-only parameters when
  matching the price-only comparator for the same core sparse contract.
- `src/tradingbotsuite/optimization/stability.py` keeps opposite-side controls
  out of same-side stability neighborhoods.
- `src/tradingbotsuite/research_artifacts/candidate_pack.py` accepts declared
  one-sided side metric rows only when the paired control evidence passed, and
  otherwise remains fail-closed.
- Side metrics now write compounded
  `net_return_after_fees_slippage_funding` and retain
  `summed_net_return_after_fees_slippage_funding` for the summed trade-return
  interpretation.

## Artifacts

Generated research-only cycle outputs:

- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/research_cycle_manifest.json`
- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/candidate_rankings.parquet`
- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/candidate_gate_report.parquet`
- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/metrics_by_side.parquet`
- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/metrics_by_split.parquet`
- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/metrics_by_cost_stress.parquet`
- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/stability_regions.parquet`
- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/ablation_report.json`

Cycle counts:

- candidates: 8;
- aggregate backtests: 8;
- split backtests: 4;
- cost-stress backtests: 22;
- candidate packs written: 0.

## Evidence

The lead still records the same aggregate performance as WPR106-82:

- aggregate net return after cycle costs: +20.174216043772766;
- long trades: 319;
- side compounded net return: +20.174216043772766;
- side summed net return retained separately: +3.3980650008983098.

The previously missing gate evidence is now represented:

- side evidence status: complete;
- side evidence policy: `explicit_one_sided_side_veto`;
- required side: `long`;
- paired short control:
  `3518d10a359694814ef453358ed3a26b0b24065bfb749d265a5b3ab1b7ee4809`;
- short control status: passed;
- short control trades: 335;
- short control expectancy versus no-trade: -0.004003;
- short control net return: -0.855344;
- feature ablation passed: true;
- price-only comparator:
  `9af7ae11c5165cd12555125e59cca4eae99149800a74c2b05a8f1a9781d666ce`;
- ablation expectancy delta: +0.004376325170812691;
- ablation final score delta: +15.477198074259224;
- cost stress: 11/11 scenarios passed;
- stability region status: accepted, validation enriched, 2 validated members.

Split evidence remains the blocker:

- split-01: 109 trades, +1.639084 net return, +0.009772 expectancy,
  -0.188289 max drawdown;
- split-02: 121 trades, +0.039327 net return, +0.001001 expectancy,
  -0.370509 max drawdown;
- max single split PnL share: 0.9765691016445411;
- split dominance status: incomplete.

## Gate Outcome

The one-sided side-veto representation blocker is resolved as a code and
artifact-contract issue, but the lead is not eligible. The final lead decision
is `rejected` with `max_single_split_pnl_share_above_limit`.

Candidate-pack recheck with `PYTHONPATH=src` remains blocked with reasons:

- `ranking_decision_not_research_gate_passed`;
- `split_dominance_evidence_required`;
- `max_single_split_pnl_share_above_limit`;
- `candidate_gate_report_status_not_passed`;
- `candidate_gate_report_not_pack_eligible`;
- `candidate_gate_report_reasons_not_empty`;
- `candidate_split_metric_max_single_split_pnl_share_above_limit`.

## Research Boundary

The final manifest records:

- `research_only: true`;
- `observe_only: true`;
- `promotion_ready: false`;
- `candidate_pack_written: false`;
- `live_fetch_used: false`;
- `order_placement_used: false`;
- `position_sizing_used: false`;
- `runtime_mode_changed: false`;
- `live_config_written: false`.

No candidate pack, paper/live artifact, order placement, position sizing,
runtime-mode change, live configuration write, or promotion claim was produced.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/optimization/test_region_of_stability.py::test_sparse_side_veto_stability_keeps_allowed_side_separate -q
$env:PYTHONPATH='src'; python -m pytest tests/historical/test_full_cycle_synthetic.py::test_sparse_aggflow_ablation_matches_price_only_core_parameters tests/historical/test_full_cycle_synthetic.py::test_side_veto_details_require_declared_side_and_negative_control tests/historical/test_full_cycle_synthetic.py::test_side_veto_details_fail_closed_without_control -q
$env:PYTHONPATH='src'; python -m pytest tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_accepts_declared_one_sided_metric_rows tests/research_artifacts/test_candidate_pack.py::test_research_candidate_pack_blocks_one_sided_rows_without_control_evidence -q
$env:PYTHONPATH='src'; python -m pytest tests/optimization/test_region_of_stability.py tests/research_artifacts/test_candidate_pack.py tests/historical/test_full_cycle_synthetic.py::test_sparse_aggflow_ablation_matches_price_only_core_parameters tests/historical/test_full_cycle_synthetic.py::test_side_veto_details_require_declared_side_and_negative_control tests/historical/test_full_cycle_synthetic.py::test_side_veto_details_fail_closed_without_control -q
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Final focused touched-path validation passed with 52 tests. The contracts suite
passed with 451 tests.
