# Data Agent Artifact: Deterministic Sweep Datasets

## Agent Name
Data Agent

## Task Received
Provide deterministic datasets for repeatable HMM/KNN sweeps.

## Files Read
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/main.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_research.py`
- `configs/v2_btc_hmm_multi_knn_research.json`
- `configs/experiments/v2_btc_hmm_knn_current_artifact_experiments.json`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`

## Files Changed
- `src/tradingbotsuite/research/deterministic_datasets.py`
- `src/tradingbotsuite/main.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `configs/experiments/v2_btc_hmm_knn_deterministic_sweep_experiments.json`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_deterministic_sweep_datasets.md`

Generated local dataset outputs:

- `data/research/deterministic_sweeps/btcusdt_hmm_knn_sweep_balanced.parquet`
- `data/research/deterministic_sweeps/btcusdt_hmm_knn_sweep_balanced.csv`
- `data/research/deterministic_sweeps/btcusdt_hmm_knn_sweep_balanced_manifest.json`
- `data/research/deterministic_sweeps/btcusdt_hmm_knn_sweep_sparse_context.parquet`
- `data/research/deterministic_sweeps/btcusdt_hmm_knn_sweep_sparse_context.csv`
- `data/research/deterministic_sweeps/btcusdt_hmm_knn_sweep_sparse_context_manifest.json`

Generated validation sweep outputs:

- `data/research/hmm_knn_deterministic_sweep_experiments/experiment_manifest.json`
- `data/research/hmm_knn_deterministic_sweep_experiments/experiment_summary.csv`
- cached HMM/KNN artifacts under `data/research/hmm_knn_deterministic_sweep_experiments/cache/`

## Commands/Tests Run
- `$env:PYTHONPATH='src'; python -m tradingbotsuite.main write-hmm-knn-sweep-datasets --output-dir data/research/deterministic_sweeps`
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q`
- `$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-hmm-knn-experiments --spec configs/experiments/v2_btc_hmm_knn_deterministic_sweep_experiments.json --output-dir data/research/hmm_knn_deterministic_sweep_experiments --skip-monitor`
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q`

Test result:

- `47 passed in 16.51s`

## Decisions Made
- Added a reusable deterministic fixture writer instead of leaving synthetic datasets embedded only in tests.
- Kept fixtures BTC-only, research-only, observe-only, and non-promotable.
- Added two variants:
  - `balanced`: all modeled exchange context populated with deterministic non-random values.
  - `sparse_context`: raw unavailable exchange context remains null while normalized fields are zeroed with matching `missing_*` flags.
- Wrote both parquet and CSV outputs. The CSV bytes are the canonical logical hash basis; parquet hashes are still recorded for experiment-cache identity.
- Added a CLI command: `write-hmm-knn-sweep-datasets`.
- Added a deterministic experiment spec that points at the balanced fixture for repeatable CLI sweep plumbing.
- Documented the fixture command, paths, and non-promotable scope in the model spec.

## Dataset Outputs
Balanced fixture:

- Rows: `240`
- Columns: `122`
- Parquet SHA-256: `d83ba2b45ce29202670b9ec6866ac3abc3a04e5684fb0f5f05bd6652eaa204ea`
- CSV/logical SHA-256: `441d52c570a1b976a59f019beec9cf6369bd6d61aff77cc45e3220f2ddbb6956`
- Missingness: all listed exchange-context `missing_*` rates are `0.0`

Sparse-context fixture:

- Rows: `240`
- Columns: `122`
- Parquet SHA-256: `845dbe7d13169b32a9853e4e75f9bebeb818e8226c9023d25fb4468718af6ccb`
- CSV/logical SHA-256: `1b3b6a8061d4909fe8d9a792c3248dc831d5b5c066f363ebf7f2b0fb70e88f94`
- Missingness: OI, basis, premium, spread, queue, top-of-book, and signed-flow fields are `1.0`; funding fields remain available.

Both fixture manifests include:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `symbol: BTCUSDT`
- `asset_scope: ["BTCUSDT"]`
- row count, column count, parquet hash, CSV hash, logical hash, source counts, source mode counts, time span, missing feature rates, and determinism metadata.
- raw context availability counts and per-family exchange context summaries with `live_fetch_used: false` and `current_only_fallback_count: 0`.

## Assumptions
- The user wanted reusable deterministic sweep inputs, not live data regeneration.
- Synthetic deterministic fixtures are acceptable for sweep plumbing, cache validation, and schema regression tests, but not for model edge claims.
- The existing modified experiment-runner files in the worktree are owned by earlier work; this task did not revert or rewrite them.

## Open Issues Or Blockers
No open issue was added. The new fixtures deliberately do not address real BTC missing-context quality; that remains a separate real-data regeneration problem.

## Handoff Notes For Other Agents
- Backtest/KNN agents can use `configs/experiments/v2_btc_hmm_knn_deterministic_sweep_experiments.json` for repeatable local matrix plumbing checks.
- Data/Testing agents can regenerate fixtures with `python -m tradingbotsuite.main write-hmm-knn-sweep-datasets --output-dir data/research/deterministic_sweeps`.
- Do not cite fixture metrics as real market performance. The fixtures are only deterministic contract inputs.
