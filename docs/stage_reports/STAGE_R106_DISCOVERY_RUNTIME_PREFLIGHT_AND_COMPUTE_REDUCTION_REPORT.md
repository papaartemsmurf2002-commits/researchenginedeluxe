# Stage R106 Discovery Runtime Preflight And Compute Reduction Report

Date: 2026-06-07
Work packet: `docs/work_packets/WPR106-68-discovery-runtime-preflight-and-compute-reduction.md`

## Boundary

This packet changes discovery runtime/accounting, operator evidence checks, and
research-only exact discovery configs. It does not rewrite generated research
artifacts, create candidate packs, place orders, change live/paper runtime
mode, change sizing, or make promotion-ready claims.

## Latest Run Diagnosis

Latest forced autopilot run:
`run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e`.

Compared with the prior forced run
`run-research-autopilot-93c17f8f75b742ceba023cba6fea3c5b`, the latest run
proved the WPR106-66 historical-cycle schema handoff fix at operator scale: it
completed forced upstream sequencing instead of failing before compute. Runtime
was about 61.06 hours. The expensive steps were BTC exact discovery
(`92630.45s`) and ETH exact discovery (`107330.24s`); downstream analysis,
delta, exit-lab, and eligibility took about 2.45 minutes total.

The historical-cycle outputs remain valid negative fixed-holding evidence:
BTCUSDT and ETHUSDT each produced 63 rejected candidates, zero positive
net-return candidates, zero positive costed-expectancy candidates, and no
candidate pack.

The latest exact-discovery outputs are invalid as lead evidence. BTC and ETH
each wrote 570240 blocked rows with `blocker_code: trial_execution_error` and
sampled trial records failed with `regime_model_backend must match
regime_mode`. Previous stable discovery evidence had valid blocker structure
with 22560 BTC and 23040 ETH interesting rows, so the latest discovery delta is
a runtime-regression signal, not proof the strategy surface degraded.

## Changes

- No-regime runtime fix: cached KNN base materialization now receives
  `regime_model_backend` from each trial spec, so no-regime trials preserve the
  `none` backend instead of inheriting the GMM default.
- Preflight: large real-discovery runs execute a representative bounded
  preflight before full process-pool execution. Any failed preflight trial
  blocks the run and skips the full sweep.
- Accounting: manifests, snapshots, and compute telemetry now separate
  `completed_trials`, `failed_trials`, `durable_trial_records`, and
  `processed_trial_records`.
- Terminal status: real-discovery runtime failures now make the run `blocked`
  instead of `completed`, while writing partial ledgers and durable trial JSONs
  for debugging.
- Bridge/operator gates: candidate-pack eligibility reports
  `discovery_failed_trial_records_present`, and operator required-evidence
  checks reject failed-trial manifests plus legacy blocked ledgers where every
  row is `trial_execution_error`.
- Compute reduction: checked BTC/ETH exact discovery configs now plan 3456
  no-regime trials per symbol, a roughly 165x reduction from the former 570240
  trial grid for the next bounded research phase.
- UI/tests: Research UI copy and operator progress tests now describe the
  reduced exact no-regime sweep rather than the old 570240-trial default.

## Research Notes

The next empirical action should be a bounded clean discovery run, not another
multi-day full-grid attempt. If the 3456-trial phase produces successful
interesting rows, downstream work should prioritize sparse event construction,
exit/context surfaces, and explicit discovery-to-cycle overlay alignment.
Fixed-holding transparent cycle candidates remain useful negative controls, not
candidate-pack targets.

Old generated failed discovery artifacts remain historical evidence of the
runtime regression only. They must not be used for lead selection, exit labs,
multiple-testing, validation floors, candidate-pack eligibility, or promotion
claims.

## Validation

Focused validation passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/research_discovery/test_discovery_runner.py::test_discovery_runner_passes_trial_knn_payload_to_evaluator tests/research_discovery/test_discovery_runner.py::test_discovery_runner_failed_real_trial_preserves_search_payload tests/research_discovery/test_discovery_runner.py::test_discovery_runner_large_real_preflight_blocks_failed_screening_before_full_sweep tests/research_discovery/test_discovery_spec.py::test_real_discovery_configs_generate_non_placeholder_search_templates tests/research_discovery/test_discovery_spec.py::test_exact_r104_discovery_search_space_dimensions_match_configured_axes tests/research_discovery/test_candidate_pack_bridge.py::test_bridge_reports_failed_discovery_trial_records -q
```

Result: 6 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py::test_operator_research_progress_api_reports_r104_milestones tests/tradingbotsuite/test_operator_ui.py::test_operator_progress_accepts_candidate_depth_catalog_artifact_ids tests/tradingbotsuite/test_operator_ui.py::test_operator_research_autopilot_force_upstream_recompute_runs_isolated_prerequisites -q
```

Result: 3 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py::test_operator_discovery_completion_rejects_legacy_all_execution_error_ledger tests/tradingbotsuite/test_operator_ui.py::test_operator_progress_accepts_candidate_depth_catalog_artifact_ids -q
```

Result: 2 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only -q
```

Result: 1 passed.

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/research_discovery/test_discovery_state.py tests/research_discovery/test_candidate_pack_bridge.py::test_bridge_reports_failed_discovery_trial_records tests/research_discovery/test_discovery_runner.py::test_discovery_runner_failed_real_trial_preserves_search_payload tests/research_discovery/test_discovery_runner.py::test_discovery_runner_large_real_preflight_blocks_failed_screening_before_full_sweep tests/research_discovery/test_discovery_spec.py::test_real_discovery_configs_generate_non_placeholder_search_templates tests/research_discovery/test_discovery_spec.py::test_exact_r104_discovery_search_space_dimensions_match_configured_axes -q
```

Result: 9 passed.

Baseline validation passed:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Result: compile passed; contracts reported 441 passed.

`git diff --check` passed.
