# Stage R106 Cycle Manifest Evidence Portability Report

Work packet: `docs/work_packets/WPR106-25-cycle-manifest-evidence-portability.md`

Date: 2026-05-29

## Summary

WPR106-25 fixes the follow-up autopilot failure after WPR106-24. The latest
run was `run-research-autopilot-d77072dd939744e296edbddac253e29b`. It got
past the previous discovery-manifest `blocked_candidates` handoff failure,
skipped the already complete BTC/ETH cycle and exact-discovery artifacts, then
failed during BTC candidate eligibility on a stale BTC historical-cycle
evidence path.

The new failure was:

```text
research manifest required output must stay inside the configured research output directory: ablation_report
```

This was the same migrated-checkout class as WPR106-24, but on
historical-cycle `required_outputs` rather than discovery manifest ledgers. The
completed BTC cycle manifest under the current checkout still recorded
absolute evidence paths under `C:\Users\papaa\Music\tradingbotsuite`, while
the mirrored evidence files exist under
`C:\Users\papaa\Music\researchenginedeluxe`.

## Latest Run Findings

- Job id: `run-research-autopilot-d77072dd939744e296edbddac253e29b`.
- Final status: failed.
- Failure timestamp: `2026-05-29T15:13:41Z`.
- Failure class: migrated historical-cycle evidence path portability.
- Failed step: BTC `candidate_eligibility`.
- Autopilot progress before failure:
  - historical catalog skipped as already candidate-depth ready;
  - BTC historical cycle skipped as complete;
  - BTC exact discovery skipped as complete;
  - ETH historical cycle skipped as complete;
  - ETH exact discovery skipped as complete;
  - BTC research analysis skipped as complete;
  - BTC analysis delta skipped as complete;
  - BTC frozen-entry exit lab skipped as complete;
  - BTC candidate eligibility retried once and then failed on
    `ablation_report`.

This confirms WPR106-24 resolved the prior discovery `blocked_candidates`
handoff blocker. The next stale path surfaced from the historical-cycle
manifest.

## Root Cause

The shared read-time path normalizer originally covered active catalog/spec
paths and then discovery manifest keys such as `blocked_candidates`,
`interesting_candidates`, `filter_blockers`, `run_state`, `trials`, and
`snapshots`. Historical-cycle manifests contain many evidence outputs whose
keys are stable artifact names rather than generic path-field names, including
`ablation_report`, `candidate_rankings`, `candidate_gate_report`,
`metrics_by_split`, `metrics_by_cost_stress`, `metrics_by_regime`,
`metrics_by_side`, `metrics_by_holding_window`, `stability_regions`,
`trial_budget_report`, and `overfit_adjustment_report`.

The operator root guard correctly rejected the old absolute path. The missing
piece was applying the same mirrored-checkout rebasing to any absolute local
operator-run path string when it matches the current artifact's mirrored run
anchor.

## Changes Made

- `src/tradingbotsuite/data/historical_data_catalog.py`
  - Broadens `normalize_operator_run_artifact_paths()` so any absolute local
    path string can be rebased when it matches a mirrored operator-run anchor
    and the mirrored path or parent exists.
  - Keeps non-path strings unchanged.
  - Keeps genuinely outside paths fail-closed because they do not match a
    mirrored local run anchor.
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
  - Reads candidate-pack gate JSON manifests through the shared normalizer
    before resolving `required_outputs`.
- `tests/research_artifacts/test_candidate_pack.py`
  - Adds a regression proving candidate-pack gate evaluation reads rebased
    historical-cycle evidence and does not report required output path missing
    reasons for mirrored old-root paths.
- `tests/tradingbotsuite/test_operator_ui.py`
  - Extends the migrated manifest regression to include a cycle manifest with
    stale `required_outputs.ablation_report`.
- `docs/KNOWN_ISSUES.md`
  - Adds and resolves `ISSUE-R106-005`.

No generated historical-cycle manifests, discovery manifests, ledgers, Parquet
files, trial JSONs, specs, fixture packs, live config, runtime mode, order
placement code, sizing behavior, candidate packs, or promotion artifacts were
rewritten or introduced.

## Artifact Checks

The two current BTC candidate-depth historical-cycle manifests that still carry
old-root `required_outputs` were checked through the patched normalizer:

```text
run-historical-research-cycle-3f12dcdc483945cfa753e4eb00d42280 bad [] missing []
run-historical-research-cycle-33e215b0229a466bbdea91e47924621c bad [] missing []
```

Candidate-pack gate evaluation on the latest BTC cycle manifest no longer
reports `required_output_path_missing` after read-time normalization:

```text
blocked
candidate_missing_from_rankings
required_output_path_missing? False
```

The `candidate_missing_from_rankings` result is expected for the probe because
the probe used a deliberately nonexistent candidate id. It proves the evaluator
got through cycle `required_outputs` path resolution.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py::test_research_candidate_gate_rebases_migrated_cycle_required_outputs -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_candidate_eligibility_service_rebases_migrated_manifest_outputs tests\tradingbotsuite\test_operator_ui.py::test_operator_candidate_eligibility_service_rejects_manifest_outputs_outside_root -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Observed results:

- targeted candidate-pack regression: `1 passed`;
- targeted operator regressions: `2 passed`;
- `tests/research_artifacts/test_candidate_pack.py`: `37 passed`;
- `tests/tradingbotsuite/test_operator_ui.py`: `76 passed`;
- `tests/research_artifacts`: `37 passed`;
- `tests/contracts`: `427 passed`.

## Remaining Work

The immediate P1 cycle-manifest handoff bug is resolved. Restart the operator
UI/server with `PYTHONPATH=src` so it imports the current checkout, then rerun
autopilot. The next run should get past both known migrated path blockers:
discovery `blocked_candidates` and cycle `ablation_report`.

Remaining gates are empirical research gates. Candidate eligibility may still
block on legitimate evidence reasons such as missing/failed exit-lab,
multiple-testing, validation-floor, split/cost stress, stability, or candidate
ranking evidence. Those should be treated as research results, not as this
portability failure.
