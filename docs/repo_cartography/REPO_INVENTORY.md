# Repo Inventory: research/v3-experimental-engine

Date: 2026-05-01
Stage: Stage 1 - Repo cartography

## Summary

`research/v3-experimental-engine` is the stronger research base. It already contains provider/archive intake, HMM/KNN tooling, deterministic datasets, feature alignment, data-quality reports, experiment runner artifacts, and research/live boundary metadata.

Tracked file counts at Stage 1:

| Area | Count |
| --- | ---: |
| All tracked files | 253 |
| `src/**` | 74 |
| `tests/**` | 33 |
| `docs/**` | 127 |

## Package families

| Path | Classification | Notes |
| --- | --- | --- |
| `src/tradingbotsuite/research/` | Research core | Provider intake, data quality, datasets, HMM/KNN, experiment runner, replay, journals, live-readiness boundary checks. |
| `src/tradingbotsuite/core/` | Runtime core retained on branch | Engine, models, acceptance, features, math, security, microstructure. Needs boundary treatment before promotion. |
| `src/tradingbotsuite/adapters/` | Market data and execution adapters retained on branch | Binance market data and Hyperliquid execution are present; live order path must stay isolated from research jobs. |
| `src/tradingbotsuite/persistence/` | Runtime persistence | SQLite store for runtime state and operator feed. |
| `src/tradingbotsuite/web/` | Operator UI | UI exposes live/operator controls and research job queues. |
| `src/tradingbot/` | Legacy strategy/backtest package | LC strategy, backtest, optimizer, data providers, and legacy live shell. TradingView-specific source names were removed on this branch. |
| `configs/data/` | Research data specs | Provider pipeline config. |
| `configs/experiments/` | Experiment specs | HMM/KNN and Phase 1 experiment configs. |
| `docs/tradingbotsuite_runtime/agent_artifacts/` | Historical evidence | Prior agent validation and audit memos. |
| `tests/tradingbotsuite/` | Research/runtime tests | Provider, feature, HMM/KNN, experiment, live-readiness, root launcher, and engine coverage. |

## Root launchers

| Path | Entrypoint | Classification |
| --- | --- | --- |
| `run_server.py` | Runs `tradingbotsuite.main:app` with Uvicorn | Live/operator launcher retained on research branch. |
| `run_manual.py` | Loads `AppConfig`, accepts optional runtime mode, runs manual shell | Live-adjacent launcher; must be audited before live use. |
| `run_live_smoke.py` | Runs Hyperliquid live smoke check | Live execution smoke path; must remain excluded from research workflows. |
| `src/tradingbotsuite/main.py` | `python -m tradingbotsuite.main ...` | Mixed live and research command surface. |
| `src/tradingbot/__main__.py` | `python -m tradingbot` | Legacy package launcher. |
| `pyproject.toml` | `tradingbot = tradingbot.cli:main` | No `tradingbotsuite` console script currently declared. |

## Research commands

`src/tradingbotsuite/main.py` exposes:

| Command | Classification |
| --- | --- |
| `build-dataset` | Baseline research dataset build. |
| `train-model` | Baseline acceptance model training. |
| `calibrate-model` | Baseline artifact calibration. |
| `replay-eval` | Baseline replay evaluation. |
| `research-hmm-knn` | HMM/KNN research run. |
| `replay-hmm-knn` | HMM/KNN artifact summary. |
| `monitor-hmm-knn` | Observe-only monitoring report. |
| `run-hmm-knn-experiments` | Cached HMM/KNN experiment matrix. |
| `write-hmm-knn-sweep-datasets` | Deterministic sweep fixture generation. |
| `collect-binance-bars` | Research-only Binance USD-M historical bars. |
| `fetch-binance-vision` | Binance Vision archive download/ingest. |
| `fetch-crypto-lake` | Crypto Lake archive fetch/ingest. |
| `prepare-hmm-knn-research-data` | Provider pipeline orchestration. |
| `run-research-experiment` | Bundled BTC Phase 1 experiment. |
| `benchmark-research-experiment` | Repeated timing benchmark. |

`src/tradingbot/cli.py` exposes legacy commands: `init-config`, `fetch-data`, `backtest`, `optimize`, and `run-bot`.

## Provider, archive, and data quality modules

| Path | Role |
| --- | --- |
| `src/tradingbotsuite/research/archive_sources.py` | Provider contracts for Binance Vision, Crypto Lake, and Hyperliquid archive. |
| `src/tradingbotsuite/research/market_data.py` | Binance REST/vision and Crypto Lake collection/ingestion helpers. |
| `src/tradingbotsuite/research/data_pipeline.py` | Pipeline stages: `intake`, `dataset`, `evidence`, `all`. Hyperliquid archive is registered but not locally implemented for ingestion. |
| `src/tradingbotsuite/research/data_quality.py` | Manifest-level quality checks for gaps, duplicates, receive-time absence, source mismatches, zero rows, and non-promotable sources. |
| `src/tradingbotsuite/research/market_journal.py` | Research replay market event journal. |
| `src/tradingbotsuite/research/execution_journal.py` | Offline Hyperliquid execution journal validation. |

## Feature and experiment modules

| Path | Role |
| --- | --- |
| `src/tradingbotsuite/research/feature_alignment.py` | Completed-bar validation, continuity checks, incomplete-bar filtering, point-in-time feature joins. |
| `src/tradingbotsuite/research/dataset.py` | Dataset build and `dataset_manifest.json` production. |
| `src/tradingbotsuite/research/hmm_knn.py` | HMM/KNN research artifact generation. |
| `src/tradingbotsuite/research/hmm_knn_monitoring.py` | Observe-only monitoring reports. |
| `src/tradingbotsuite/research/hmm_knn_experiments.py` | Cached matrix runs and experiment summary artifacts. |
| `src/tradingbotsuite/research/deterministic_datasets.py` | Synthetic deterministic sweep datasets. |
| `src/tradingbotsuite/research/experiment_runner.py` | General experiment orchestration seed. |
| `src/tradingbotsuite/research/live_readiness.py` | Research/live boundary metadata and promotion-readiness checks. |

## Artifact-producing paths

| Module | Main outputs |
| --- | --- |
| `research/dataset.py` | `*_dataset.parquet`, `dataset_manifest.json`. |
| `research/hmm_knn.py` | `regime_posteriors.parquet`, `knn_predictions.parquet`, `meta_predictions.parquet`, `neighbor_diagnostics.csv`, `walk_forward_metrics.json`, `artifact_manifest.json`. |
| `research/hmm_knn_monitoring.py` | `monitoring_report.json`. |
| `research/hmm_knn_experiments.py` | `generated_configs/`, cache artifacts, `experiment_summary.csv`, `experiment_manifest.json`. |
| `research/data_pipeline.py` | `data_intake_manifest.json`, `data_quality_report.json`, `market_journal.jsonl`, `market_journal_manifest.json`, `pipeline_summary.json`. |
| `research/experiment_runner.py` | `specs/`, `conclusion.md`, `experiment_run_manifest.json`, benchmark reports. |

## Live order paths present

| Path | Role |
| --- | --- |
| `src/tradingbotsuite/adapters/execution.py` | Shadow, paper, and Hyperliquid live execution adapters; intent builders. |
| `src/tradingbotsuite/core/engine.py` | Signal handling, supervision, reconciliation, execution event application, protective order handling. |
| `src/tradingbotsuite/runtime.py` | Engine construction with execution adapter and optional acceptance scorer. |
| `src/tradingbotsuite/live_smoke.py` | Hyperliquid live smoke check. |
| `src/tradingbotsuite/operator_commands.py` | Manual signal, supervise, reconcile, refresh health, smoke live command wrappers. |
| `src/tradingbot/data/hyperliquid.py`, `src/tradingbot/live.py` | Legacy Hyperliquid live client and shell. |

## Import and boundary map

Research modules are internally coupled through `tradingbotsuite.research.*` and currently do not need direct live order placement to produce artifacts. However, the branch still contains live runtime modules, and several live/operator modules import research helpers:

| Importing path | Imported research path | Risk |
| --- | --- | --- |
| `src/tradingbotsuite/core/engine.py` | `tradingbotsuite.research.config`, `tradingbotsuite.research.inference` | Runtime can use research acceptance scorer. |
| `src/tradingbotsuite/runtime.py` | `tradingbotsuite.research.inference` | Runtime can load scorer when an artifact manifest path exists. |
| `src/tradingbotsuite/main.py` | multiple `tradingbotsuite.research.*` modules | Live/operator commands and research commands share one entry module. |
| `src/tradingbotsuite/operator_console.py` | `tradingbotsuite.research.*` | Operator UI can queue research jobs. |
| `src/tradingbotsuite/web/operator.py` | `tradingbotsuite.research.data_pipeline` | Operator API includes research job endpoints. |

## Test coverage map

| Area | Tests |
| --- | --- |
| Provider/archive/data quality | `tests/tradingbotsuite/test_archive_sources.py`, `test_data_quality.py`, `test_market_data_collection.py`, `test_data_pipeline.py` |
| Feature alignment and replay | `tests/tradingbotsuite/test_feature_alignment.py`, `test_market_journal.py`, `test_replay_determinism.py` |
| Execution journal and live readiness | `tests/tradingbotsuite/test_execution_journal.py`, `test_live_readiness.py` |
| HMM/KNN and experiments | `tests/tradingbotsuite/test_hmm_knn.py`, `test_experiment_runner.py` |
| Root launchers | `tests/tradingbotsuite/test_root_launchers.py` |
| Removed source boundaries | `tests/test_removed_source_boundaries.py` |

## Stage 1 conclusions

- This branch is suitable as the research development base.
- Stage 2 must turn the documented boundaries into explicit contracts and tests.
- Stage 3 can start only after Stage 2 documents the data, feature, strategy, backtest, artifact, and promotion contracts.
- Live execution paths are present and must stay out of research workflows until the live branch hardening and promotion gates exist.
