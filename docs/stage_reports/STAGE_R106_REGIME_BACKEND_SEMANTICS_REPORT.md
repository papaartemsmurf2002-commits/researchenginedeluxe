# Stage R106 Regime Backend Semantics Report

Date: 2026-05-31

Work packet: `docs/work_packets/WPR106-39-regime-backend-semantics.md`

## Scope

Normalized active discovery regime backend evidence so GMM-backed regime logic
is stamped with the true backend. This was metadata and compatibility hardening
only.

This packet did not add a true HMM backend, new strategies, filters, models,
paper/live behavior, promotion logic, candidate-pack writing, or generated
research artifacts.

## Changes

- Added `regime_model_backend` to discovery regime-mode settings.
- Discovery trial templates, KNN specs/manifests, ledgers, run-manifest regime
  truthfulness, artifact identity, and candidate-pack bridge ledgers now carry
  `regime_model_backend`.
- GMM-backed evidence is stamped as `sklearn.mixture.GaussianMixture`;
  no-regime evidence is stamped as `none`.
- HMM compatibility fields remain where downstream strategy/artifact contracts
  still require them, but materialized regime output now also includes
  canonical aliases: `regime_fit_end_row`, `regime_model_id`,
  `regime_feature_pack_id`, and `regime_split_id`.
- Trial payloads now include canonical aliases for regime state count,
  posterior threshold, entropy threshold, cache hit, and artifact paths.
- A stale cross-horizon cache expectation was corrected: event-end-aware purge
  makes regime materialization horizon-specific, while same-horizon reuse still
  works.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_hmm_materialization.py tests\research_discovery\test_discovery_spec.py tests\research_discovery\test_knn_study.py tests\research_discovery\test_artifact_keys.py -q` passed: 51 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_runner.py tests\research_discovery\test_candidate_pack_bridge.py -q` passed: 61 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 430 tests.
- `git diff --check` passed with only existing CRLF warnings.

## Boundary Statement

Active discovery GMM evidence is now machine-readable as GMM evidence, not true
HMM evidence. Legacy `hmm_*` names are compatibility fields only. Research
outputs remain non-live, observe-only, and non-promotable.

## Remaining Work

The P0 blocker queue is closed. The next empirical packet should route the
WPR106-31 replayed KNN prediction artifacts through historical-cycle overlay,
ranking, exit lab, multiple-testing, validation floors, and candidate-pack
eligibility without weakening gates.
