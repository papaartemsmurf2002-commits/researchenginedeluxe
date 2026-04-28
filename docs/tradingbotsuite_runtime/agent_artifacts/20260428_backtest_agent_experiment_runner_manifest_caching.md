# Backtest Agent Experiment Runner Manifest Caching

## Agent name

Backtest Agent

## Task received

Design and implement an HMM/KNN experiment runner with manifest and caching support.

## Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_next_experiment_matrix.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_next_experiment_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_next_experiment_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_meta_model_agent_next_experiment_spec.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_monitoring_agent_next_experiment_thresholds.md`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- `tests/tradingbotsuite/test_hmm_knn.py`

## Files changed

- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/main.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `configs/experiments/v2_btc_hmm_knn_current_artifact_experiments.json`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_experiment_runner_manifest_caching.md`

## Implementation summary

Added `run_hmm_knn_experiment_matrix`, a research-only experiment runner that:

- Reads a JSON experiment spec.
- Applies nested config mutations to the base HMM/KNN config.
- Writes generated per-experiment config files.
- Computes deterministic cache keys from the dataset hash and final config payload hash.
- Reuses complete cached artifacts when `artifact_manifest.json` and referenced outputs are present and match the generated config.
- Supports `--force` cache refresh.
- Optionally writes `monitor-hmm-knn` observe-only reports for each experiment.
- Writes a top-level `experiment_manifest.json`.
- Writes an `experiment_summary.csv` with key metrics.
- Preserves `research_only: true`, `observe_only: true`, and `promotion_ready: false` at the experiment-runner manifest level.

Added CLI:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-hmm-knn-experiments --spec configs/experiments/v2_btc_hmm_knn_current_artifact_experiments.json --output-dir data/research/hmm_knn_experiments
```

Useful options:

- `--dataset <path>` overrides the spec dataset.
- `--cache-dir <path>` overrides the default cache under the output directory.
- `--force` refreshes cached runs.
- `--skip-monitor` skips observe-only monitoring reports.
- `--fail-fast` stops on the first failed experiment.

Added starter spec:

```text
configs/experiments/v2_btc_hmm_knn_current_artifact_experiments.json
```

The starter spec includes current-artifact diagnostic experiments for:

- Regime cooldown zero.
- KNN small-K softmax.
- KNN observed-core feature subset.
- KNN price-trend-WT3D feature subset.

## Commands/tests run

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

First run failed due to a cache-check hash mismatch and then a test snapshot issue. Both were fixed.

Final exact output:

```text
.........................                                                [100%]
25 passed in 12.98s
```

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-hmm-knn-experiments --help
```

Exact output:

```text
usage: python.exe -m tradingbotsuite.main run-hmm-knn-experiments
       [-h] --spec SPEC [--dataset DATASET] [--output-dir OUTPUT_DIR]
       [--cache-dir CACHE_DIR] [--force] [--skip-monitor] [--fail-fast]

options:
  -h, --help            show this help message and exit
  --spec SPEC
  --dataset DATASET     Override the dataset path in the experiment spec
  --output-dir OUTPUT_DIR
  --cache-dir CACHE_DIR
  --force               Refresh cached experiment artifacts
  --skip-monitor        Do not write monitor-hmm-knn reports for experiment
                        artifacts
  --fail-fast           Stop on the first failed experiment
```

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_operator_ui.py -q
```

Exact output:

```text
.................................................................        [100%]
65 passed in 21.94s
```

```powershell
$env:PYTHONPATH='src'; python -m pytest -q
```

Exact output:

```text
........................................................................ [ 16%]
........................................................................ [ 32%]
........................................................................ [ 49%]
........................................................................ [ 65%]
........................................................................ [ 82%]
........................................................................ [ 98%]
.....                                                                    [100%]
437 passed in 133.29s (0:02:13)
```

```powershell
git diff --check
```

Exact output:

```text
warning: in the working copy of 'docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/tradingbotsuite/main.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/tradingbotsuite/research/hmm_knn.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/tradingbotsuite/test_hmm_knn.py', LF will be replaced by CRLF the next time Git touches it
```

Exit code: `0`.

Result: PASS. Git reported line-ending normalization warnings only; no whitespace errors were reported.

## Decisions made

- Implemented a spec-driven runner instead of hardcoding the next-experiment matrix in Python.
- Used generated config files for every experiment so each child HMM/KNN artifact remains replayable through the existing `research-hmm-knn` contract.
- Chose cache identity based on dataset hash plus final config payload hash, not just experiment name, so renames do not invalidate identical experiments and mutation changes do.
- Kept monitoring optional but enabled by default for programmatic and CLI runs.
- Kept all experiment-runner outputs research-only and non-promotional.
- Continued on individual experiment failures by default and recorded the failure in the top-level manifest; `--fail-fast` is available for strict runs.
- Orchestrator follow-up changed experiment JSON reads to `utf-8-sig` after a CLI smoke found that PowerShell-created specs may include a UTF-8 BOM. Added regression coverage for BOM-prefixed specs.

## Assumptions

- Experiment specs are JSON objects with `base_config_path`, `dataset_path`, and an `experiments` list.
- Mutations use dotted keys such as `knn.primary_k`, or nested JSON objects such as `{ "knn": { "primary_k": 16 } }`.
- The runner is for Phase 1 BTC HMM/KNN research only and does not alter live gates, sizing, execution, safety, Hyperliquid behavior, or operator live controls.
- The checked-in starter spec is diagnostic only and depends on the repo-local BTC dataset unless `--dataset` is supplied.

## Open issues or blockers

- No blocker was added.
- The current starter spec can run on the current repo-local BTC dataset, but the resulting metrics remain diagnostic until Data and Labeling regeneration produce promotion-quality context and label manifests.
- Existing unrelated working-tree changes are present in the HMM/KNN area; they were not reverted.

## Handoff notes for other agents

- Regime and KNN agents can add new config-only variants by appending to `configs/experiments/v2_btc_hmm_knn_current_artifact_experiments.json`.
- Data and Labeling agents should provide a regenerated dataset path; Backtest can run the same spec with `--dataset <new_dataset_path>` without editing the spec.
- Monitoring can consume each child artifact's `monitoring_report.json` or the top-level `experiment_summary.csv`.
- Execution/Risk should continue treating all runner outputs as research-only and non-promotional.
