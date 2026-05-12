# WPR94-01 Regime Baseline And Naming Truthfulness

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Implement the first Stage R94 truthfulness packet by making discovery regime
usage explicit, adding a real no-regime baseline mode, and recording the current
regime backend as GMM rather than true HMM.

## Allowed Paths

- `docs/work_packets/WPR94-01-regime-baseline-naming-truthfulness.md`
- `docs/stage_reports/STAGE_R94_REGIME_BASELINE_NAMING_TRUTHFULNESS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/OPERATOR_GUIDE.md`
- `docs/OPERATOR_QUICKSTART.md`
- `docs/runbooks/research_ui_runbook.md`
- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/web/templates/research.html`
- `configs/discovery/*.json`
- `tests/research_discovery/**`
- `tests/tradingbotsuite/test_operator_ui.py`

## Scope

- Add a discovery `regime_mode` axis with:
  - `none`
  - `gmm_gate_only`
  - `gmm_same_regime_neighbors`
  - `gmm_all_regime_neighbors_with_gate`
- Keep existing split-safe GaussianMixture materialization but label manifests
  with `regime_detector_type: gmm` and `true_hmm_backend_used: false`.
- Add a no-regime materialization path that preserves split and label safety
  without applying `regime_no_trade` or same-regime neighbor filtering.
- Add trial/run/KNN payload fields for regime mode, detector type, gate use,
  same-regime neighbor-pool use, and true-HMM backend use.
- Update focused UI/docs strings that describe current V4 discovery as HMM when
  the implementation is GMM plus KNN local analog evidence.
- Add focused regression tests for no-regime behavior and GMM metadata.

## Non-Goals

- No true HMM backend.
- No independent-event scoring changes.
- No exit-lab gate changes.
- No feature, filter, strategy, or candidate-pack behavior changes.
- No live trading behavior, live config writes, order placement, promotion
  readiness, or sizing logic changes.
- No generated research artifact mutation.

## Validation Plan

Minimum required:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

Focused additions:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_spec.py tests\research_discovery\test_hmm_materialization.py tests\research_discovery\test_knn_study.py tests\research_discovery\test_discovery_runner.py -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
```

## Validation Result

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_spec.py tests\research_discovery\test_hmm_materialization.py tests\research_discovery\test_knn_study.py tests\research_discovery\test_discovery_runner.py -q
# 44 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_candidate_pack_bridge.py -q
# 13 passed

$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
# 35 passed

python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 86 passed

git diff --check
# passed
```

## Exit Evidence

- `src/tradingbotsuite/research_discovery/spec.py`
- `src/tradingbotsuite/research_discovery/hmm_materialization.py`
- `src/tradingbotsuite/research_discovery/knn_study.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/manifests.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `configs/discovery/standard_entry_discovery_btcusdt_v4.json`
- `configs/discovery/deep_candidate_harvest_btcusdt_v4.json`
- `configs/discovery/hmm_materialization_v4.json`
- `configs/discovery/knn_study_v4.json`
- `tests/research_discovery/**`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/stage_reports/STAGE_R94_REGIME_BASELINE_NAMING_TRUTHFULNESS_REPORT.md`
