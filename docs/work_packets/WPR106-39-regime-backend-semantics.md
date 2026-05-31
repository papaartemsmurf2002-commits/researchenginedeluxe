# WPR106-39 Regime Backend Semantics

## Goal

Normalize active discovery regime backend evidence so GMM-backed regime logic is
stamped with the true backend wherever trial payloads, ledgers, manifests, KNN
specs, and artifact identity carry regime metadata.

This packet must not add new regime models, strategies, filters, live/paper
behavior, promotion logic, or candidate-pack eligibility changes.

## Current Repo Facts

- Split-safe regime materialization uses
  `sklearn.mixture.GaussianMixture`, stamps `regime_detector_type: gmm`,
  `regime_model_backend: sklearn.mixture.GaussianMixture`, and
  `true_hmm_backend_used: false`.
- Discovery spec/trial templates stamp `regime_detector_type` and
  `true_hmm_backend_used`, but do not carry `regime_model_backend`.
- KNN study specs/manifests carry `regime_detector_type` and
  `true_hmm_backend_used`, but do not carry `regime_model_backend`.
- Discovery ledgers and candidate-pack bridge columns preserve
  `regime_detector_type`, but not `regime_model_backend`.
- Compatibility field names such as `hmm_state_count`, `hmm_fit_end_row`, and
  `hmm_model_id` still exist for downstream HMM/KNN strategy contracts. This
  packet should not rename those compatibility columns.

## Conflicts And Stale Docs Found

- Older docs and command names still use HMM/KNN as a historical subsystem name.
  WPR94 already made operator-facing GMM/no-regime wording explicit, so this
  packet should focus on active machine-readable backend evidence, not broad
  historical text rewrites.

## Allowed Edit Paths

- `docs/work_packets/WPR106-39-regime-backend-semantics.md`
- `docs/work_packets/WPR106-39-progress.jsonl`
- `src/tradingbotsuite/research_discovery/hmm_materialization.py`
- `src/tradingbotsuite/research_discovery/spec.py`
- `src/tradingbotsuite/research_discovery/knn_study.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/manifests.py`
- `src/tradingbotsuite/research_discovery/artifact_keys.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- focused tests under `tests/research_discovery/**`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_REGIME_BACKEND_SEMANTICS_REPORT.md`

## Forbidden Edit Paths

- model-fitting behavior and search-space dimensions beyond metadata stamping
- strategy plugins or signal logic
- live/paper/runtime/promotion behavior
- generated data, checked fixture packs, or candidate-pack writing logic
- broad historical docs rewrites outside the active index, ledger, and report
- `.pytest_cache/**`

## Subagents Used

- Regime Backend Semantics Engineer: audit active GMM/HMM naming and backend
  evidence paths.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_spec.py tests\research_discovery\test_knn_study.py tests\research_discovery\test_discovery_runner.py tests\research_discovery\test_artifact_keys.py tests\research_discovery\test_candidate_pack_bridge.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Artifacts Expected

- Active discovery trial payloads and ledgers carry `regime_model_backend`.
- KNN study spec/manifests validate `regime_model_backend` against
  `regime_mode`.
- Discovery run manifests summarize configured and observed backend values.
- Artifact identity includes backend evidence for regime-active trials and drops
  it for no-regime trials as an inactive dimension.
- Updated stage report.

No generated research artifacts, candidate packs, promotion claims, or live
runtime behavior are expected.

## Definition Of Done

- GMM-backed active discovery evidence is stamped as
  `sklearn.mixture.GaussianMixture`.
- No-regime evidence is stamped as `none`.
- `true_hmm_backend_used` remains false unless a future true-HMM backend exists.
- Compatibility HMM/KNN field names remain where required, but backend evidence
  is explicit enough to prevent GMM being treated as true HMM.
- Focused discovery and contract validation passes.

## Rollback Plan

Revert only files in the allowed edit paths. Do not touch generated artifacts,
candidate packs, strategy logic, runtime/live paths, or unrelated cache state.
