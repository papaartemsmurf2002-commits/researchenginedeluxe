# Stage R106 Candidate Rejection Root-Cause And Gate Materialization Report

Work packet:
`docs/work_packets/WPR106-29-candidate-rejection-root-cause-and-gate-materialization.md`

Date: 2026-05-30

## Summary

WPR106-29 investigated why the current completed BTCUSDT/ETHUSDT autopilot
evidence still produces zero candidate-pack eligible rows. The result is not a
new live-safety issue and not a candidate-pack writer bug. Current exact
discovery candidates and current historical-cycle ranked candidates are separate
candidate universes:

- BTCUSDT exact discovery has 22,560 interesting KNN lead rows.
- ETHUSDT exact discovery has 23,040 interesting KNN lead rows.
- Each current historical cycle has 63 ranked research candidates.
- Discovery-to-cycle ranking overlap is 0 for both symbols.

The bridge is therefore correctly blocking all current discovery leads from the
existing research candidate-pack validator. It now records this fact directly in
the manifest as `candidate_universe_alignment`, `reason_counts`, and summary
overlap fields so agents do not have to infer it from a large rejection file.

No candidate pack was written. All generated bridge artifacts remain
`research_only: true`, `observe_only: true`, and `promotion_ready: false`.

## Evidence Roots

Gate materialization outputs:

- `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause/btcusdt/multiple_testing/discovery_multiple_testing_manifest.json`
- `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause/btcusdt/validation_floors/discovery_validation_floors_manifest.json`
- `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause/ethusdt/multiple_testing/discovery_multiple_testing_manifest.json`
- `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause/ethusdt/validation_floors/discovery_validation_floors_manifest.json`

Fresh bridge output from the working tree with capped rejection Markdown:

- `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause_capped/btcusdt/candidate_pack_eligibility/candidate_pack_eligibility_manifest.json`
- `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause_capped/btcusdt/candidate_pack_eligibility/candidate_pack_eligibility.parquet`
- `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause_capped/btcusdt/candidate_pack_eligibility/candidate_pack_bridge_rejections.md`
- `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause_capped/ethusdt/candidate_pack_eligibility/candidate_pack_eligibility_manifest.json`
- `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause_capped/ethusdt/candidate_pack_eligibility/candidate_pack_eligibility.parquet`
- `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause_capped/ethusdt/candidate_pack_eligibility/candidate_pack_bridge_rejections.md`

The capped bridge run was executed with `$env:PYTHONPATH='src'`. Running without
that environment variable can import a stale installed package instead of the
checkout code.

## BTCUSDT Result

Source evidence:

- discovery manifest:
  `data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-candidate-depth-v1/discovery_run_manifest.json`
- cycle manifest:
  `data/research/operator_runs/historical_cycles/r105-btcusdt-durable-public-archive-candidate-depth-v1/run-historical-research-cycle-3f12dcdc483945cfa753e4eb00d42280/research_cycle_manifest.json`
- exit-lab manifest:
  `data/research/operator_runs/frozen_entry_exit_lab/run-research-autopilot-52719942d4604874a51a67489bbbe98a-restart-retry-1-btcusdt-frozen-entry-exi/discovery_exit_lab_manifest.json`

Materialized gate summaries:

- multiple-testing rows: 22,560 candidate gates, 0 passed, 22,560 blocked.
- validation-floor rows: 22,560 candidate gates, 0 candidate-ready, 22,560 diagnostic.
- candidate-pack bridge rows: 22,560 candidates, 0 eligible, 22,560 blocked.
- cycle ranking candidates: 63.
- discovery-to-ranking overlap: 0.
- candidate universe status:
  `no_mapped_discovery_candidates_in_cycle_rankings`.
- candidate pack written: false.
- promotion ready: false.

Dominant blocker counts:

- `research_candidate_gate:candidate_missing_from_rankings`: 22,560.
- `multiple_testing_gate:split_window_concentration_required`: 22,560.
- `validation_floor_gate:candidate_ready_validation_required`: 22,560.
- `validation_floor_gate:exit_lab_gate_status_not_passed`: 22,560.
- `validation_floor_gate:overlap_ratio_above_ceiling`: 22,560.
- `validation_floor_gate:split_pass_ratio_required`: 22,560.
- `validation_floor_gate:cost_stress_survival_below_floor`: 22,560.
- `validation_floor_gate:stability_neighborhood_size_below_floor`: 22,560.
- `validation_floor_gate:source_provider_capability_missing`: 22,560.
- `validation_floor_gate:source_provider_capability_not_candidate_ready`: 22,560.
- `validation_floor_gate:baseline_comparator_missing`: 22,560.
- `validation_floor_gate:no_trade_comparator_missing`: 22,560.
- `validation_floor_gate:exit_lab_missing`: 22,560.
- `validation_floor_gate:filter_ablation_missing`: 22,560.
- `validation_floor_gate:feature_ablation_missing`: 22,560.
- `exit_lab_candidate_gate_row_required`: 22,548.
- 12 rows have exit-lab evidence, but each still blocks on
  `exit_lab_no_improving_exit_over_fixed_holding`,
  `exit_lab_status_not_complete`, and `frozen_entry_signals_missing`.

Bridge materialization performance:

- BTC capped bridge elapsed time: 8.698 seconds.
- BTC eligibility Parquet size: 975,959 bytes.
- BTC rejection Markdown size: 268,731 bytes.

## ETHUSDT Result

Source evidence:

- discovery manifest:
  `data/research/operator_runs/discovery_runs/exact-entry-sweep-ethusdt-candidate-depth-v1/discovery_run_manifest.json`
- cycle manifest:
  `data/research/operator_runs/historical_cycles/r105-ethusdt-durable-public-archive-candidate-depth-v1/run-research-autopilot-52719942d4604874a51a67489bbbe98a-ethusdt-cycle/research_cycle_manifest.json`
- exit-lab manifest:
  `data/research/operator_runs/frozen_entry_exit_lab/run-research-autopilot-9a4ce549dd1c4ffba99ab54449ef2a0b-restart-retry-1-ethusdt-frozen-entry-exi/discovery_exit_lab_manifest.json`

Materialized gate summaries:

- multiple-testing rows: 23,040 candidate gates, 0 passed, 23,040 blocked.
- validation-floor rows: 23,040 candidate gates, 0 candidate-ready, 23,040 diagnostic.
- candidate-pack bridge rows: 23,040 candidates, 0 eligible, 23,040 blocked.
- cycle ranking candidates: 63.
- discovery-to-ranking overlap: 0.
- candidate universe status:
  `no_mapped_discovery_candidates_in_cycle_rankings`.
- candidate pack written: false.
- promotion ready: false.

Dominant blocker counts:

- `research_candidate_gate:candidate_missing_from_rankings`: 23,040.
- `multiple_testing_gate:latest_window_only_evidence`: 23,040.
- `multiple_testing_gate:split_window_concentration_required`: 23,040.
- `validation_floor_gate:candidate_ready_validation_required`: 23,040.
- `validation_floor_gate:exit_lab_gate_status_not_passed`: 23,040.
- `validation_floor_gate:overlap_ratio_above_ceiling`: 23,040.
- `validation_floor_gate:split_pass_ratio_required`: 23,040.
- `validation_floor_gate:cost_stress_survival_below_floor`: 23,040.
- `validation_floor_gate:stability_neighborhood_size_below_floor`: 23,040.
- `validation_floor_gate:source_provider_capability_missing`: 23,040.
- `validation_floor_gate:source_provider_capability_not_candidate_ready`: 23,040.
- `validation_floor_gate:baseline_comparator_missing`: 23,040.
- `validation_floor_gate:no_trade_comparator_missing`: 23,040.
- `validation_floor_gate:exit_lab_missing`: 23,040.
- `validation_floor_gate:filter_ablation_missing`: 23,040.
- `validation_floor_gate:feature_ablation_missing`: 23,040.
- `exit_lab_candidate_gate_row_required`: 23,028.
- 12 rows have exit-lab evidence, but each still blocks on
  `exit_lab_no_improving_exit_over_fixed_holding`,
  `exit_lab_status_not_complete`, and `frozen_entry_signals_missing`.

Bridge materialization performance:

- ETH capped bridge elapsed time: 8.453 seconds.
- ETH eligibility Parquet size: 991,529 bytes.
- ETH rejection Markdown size: 281,430 bytes.

## Code Changes

`src/tradingbotsuite/research_discovery/candidate_pack_bridge.py` now:

- writes `reason_counts` into bridge manifests;
- writes `candidate_universe_alignment` into bridge manifests;
- includes overlap summary fields:
  `ranking_overlap_count`, `cycle_ranking_candidate_count`, and
  `candidate_universe_status`;
- caps rejection Markdown blocked-row output at 250 rows while keeping the full
  Parquet eligibility table;
- pre-indexes exit-lab, multiple-testing, and validation-floor candidate gate
  rows instead of filtering full gate DataFrames per discovery candidate;
- preserves fail-closed candidate-pack behavior when any gate is missing or
  blocked.

`src/tradingbotsuite/research_discovery/multiple_testing.py` now:

- derives stability-neighborhood sizes with one grouped pass instead of a
  candidate-by-candidate full-frame scan;
- prefers discovery manifest `budget.max_trials` or
  `counts.completed_trials` before scanning every trial JSON record to infer
  declared search space.

These are diagnostic and materialization efficiency changes only. They do not
make a research candidate eligible, write a candidate pack, or change any live
runtime behavior.

## Interpretation

The current one-button run can finish its checklist and still produce zero
eligible candidates. That is expected from the available evidence because the
exact-discovery KNN leads are not present in the historical-cycle ranking
universe that the existing candidate-pack validator requires.

The next empirical work should not weaken candidate-pack gates. The required
follow-up is a discovery-lead validation/materialization lane that either:

- turns discovery KNN leads into cycle/backtest/ranking-equivalent research
  candidates with full gate evidence; or
- provides a defensible candidate ID/signature map from discovery leads to
  already ranked cycle candidates.

Until that exists and the exit-lab, multiple-testing, validation-floor,
baseline/no-trade, ablation, provider-capability, and maturity gates pass, the
correct result remains `candidate_pack_written: false` and
`promotion_ready: false`.

No new P0 or P1 issue was opened because this packet did not find a branch
boundary, live-safety, corrupt-data, or broken-contract regression. It found a
truthful research pipeline gap and made the rejection evidence explicit enough
for the next packet.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py tests\research_discovery\test_multiple_testing.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py tests\tradingbotsuite\test_operator_ui.py -q
```

Observed:

- compileall passed;
- research-discovery tests: 39 passed;
- contract tests: 427 passed;
- candidate-pack/UI tests: 115 passed.
