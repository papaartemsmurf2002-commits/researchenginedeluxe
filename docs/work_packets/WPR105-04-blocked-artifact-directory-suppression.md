# WPR105-04 Blocked Artifact Directory Suppression

Owner: Codex Research Agent
Stage: R105 candidate factory component falsification
Status: closed
Created: 2026-05-19

## Goal

Reduce discovery filesystem pressure for large `interesting_only` sweeps by
avoiding empty per-trial artifact attempt directories when blocked trials do
not persist HMM/KNN/accounting artifacts.

The R104 exact sweep completed with zero interesting candidates and hundreds
of thousands of blocked trials. Under `interesting_only` persistence, blocked
trials still need durable JSON trial records for resume and audit, but they do
not need empty `trial_artifacts/<trial>/<attempt>` directories.

## Allowed paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/**`
- `docs/stage_reports/**`
- `src/tradingbotsuite/research_discovery/runner.py`
- `tests/research_discovery/**`
- `tests/contracts/**`

## Constraints

- Do not change discovery scoring, KNN/HMM logic, candidate gates, ledgers,
  trial JSON records, live execution, runtime mode, order placement, live
  config, promotion behavior, or sizing behavior.
- Keep outputs research-only, observe-only, and `promotion_ready: false`.
- Preserve persisted artifact behavior for `persist_trial_artifacts: all` and
  for interesting trials under `interesting_only`.
- Do not claim processor-parallel speedup; this packet only reduces redundant
  filesystem directory materialization for blocked compacted trials.

## Planned implementation

1. Stop eagerly creating the real-discovery trial attempt directory before
   trial evaluation.
2. Rely on existing artifact writers to create parent directories only when
   HMM/KNN/accounting artifacts are actually persisted.
3. Extend the blocked-compaction regression test to assert that blocked
   `interesting_only` runs leave no empty trial artifact root.
4. Run focused discovery tests plus compile/contract validation.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py::test_discovery_runner_compacts_blocked_real_trial_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Exit evidence

- Removed eager creation of
  `trial_artifacts/<trial_id>/<attempt_id>` directories before real-discovery
  trial evaluation.
- Existing HMM, KNN, and strategy-accounting artifact writers still create
  parent directories when artifacts are persisted, so `persist_trial_artifacts:
  all` and interesting-trial persistence semantics are preserved.
- Extended the blocked compacted-trial regression to assert that a blocked
  `interesting_only` trial does not leave an empty `trial_artifacts` root.
- This reduces filesystem pressure for no-candidate exact sweeps like R104. It
  does not change scoring, candidate gates, trial records, ledgers, or claim a
  processor-parallel speedup.
- Validation passed:
  `python -m compileall -q src\tradingbotsuite`;
  `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py::test_discovery_runner_compacts_blocked_real_trial_artifacts -q`
  (`1 passed`);
  `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  (`180 passed`);
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  (`427 passed`);
  targeted performance-surface validation:
  `$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider tests\research_discovery\test_compute_telemetry.py tests\research_discovery\test_discovery_runner.py::test_discovery_runner_writes_manifest_state_ledgers_and_snapshots tests\research_discovery\test_discovery_runner.py::test_discovery_runner_compacts_blocked_real_trial_artifacts tests\research_discovery\test_discovery_benchmark.py::test_discovery_benchmark_report_contains_research_only_gate_metrics tests\historical\test_full_cycle_synthetic.py::test_cycle_auto_backend_default_uses_fastest_exact_vector_route tests\historical\test_full_cycle_synthetic.py::test_full_cycle_expands_optimizer_search_spaces_and_writes_stability_regions tests\historical\test_research_cycle_benchmark.py::test_research_cycle_benchmark_report_contains_research_only_gate_metrics`
  (`7 passed`);
  `git diff --check` passed with CRLF normalization warnings only.
