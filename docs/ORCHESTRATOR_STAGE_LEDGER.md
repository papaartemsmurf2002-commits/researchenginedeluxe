# Orchestrator Stage Ledger

Current stage: Stage 12 - Later-stage research expansion and institutional tuning
Current stage owner: Orchestrator Agent
Stage status: partial - empirical acceptance blocked
Last updated: 2026-05-03

## Stage entry decision

- Prior stage completed: yes
- Evidence links:
  - `docs/stage_reports/STAGE_12_1_EXIT_REPORT.md`
  - `docs/stage_reports/STAGE_12_EXIT_REPORT.md`
  - `docs/stage_reports/STAGE_12_COMPLETION_LIMITATIONS.md`
  - `src/tradingbotsuite/research/feature_ablation.py`
  - `src/tradingbotsuite/research/stage12_research.py`
  - `configs/features/features_microstructure_filter_only.json`
  - `configs/features/features_cross_asset_context.json`
  - `tests/tradingbotsuite/test_feature_ablation.py`
  - `tests/tradingbotsuite/test_stage12_research_plan.py`
  - `tests/contracts/test_feature_contracts.py`
- Known blockers accepted into this stage:
  - None.

## Open work packets

| Packet | Owner | Status | Paths | Exit evidence |
| --- | --- | --- | --- | --- |
| WP0-01-branch-and-ledger-setup | Orchestrator Agent | closed | `docs/ORCHESTRATOR_STAGE_LEDGER.md`, `docs/KNOWN_ISSUES.md`, `docs/BRANCH_PURPOSE.md`, `docs/work_packets/WP0-01-branch-and-ledger-setup.md`, `docs/stage_reports/STAGE_0_EXIT_REPORT.md` | Branch exists; governance files created; validation recorded in Stage 0 exit report. |
| WP1-01-repo-inventory | Repo Cartographer Agent | closed | `docs/repo_cartography/REPO_INVENTORY.md`, `docs/stage_reports/STAGE_1_EXIT_REPORT.md` | File-family inventory, import map, root launchers, live order paths, research commands, and tests listed. |
| WP1-02-tradingview-archive-map | Documentation Agent | closed | `docs/repo_cartography/TRADINGVIEW_ARCHIVE_MAP.md`, `docs/stage_reports/STAGE_1_EXIT_REPORT.md` | TradingView/Pine/parity files classified as removed, legacy reference, or candidate archive material. |
| WP2-01-contract-docs | Documentation Agent | closed | `AGENTS.md`, `START_HERE.md`, `docs/contracts/**`, `tests/contracts/**`, `docs/stage_reports/STAGE_2_EXIT_REPORT.md` | Contract docs and import-boundary tests created; validation recorded in Stage 2 exit report. |
| WP3-01-data-manifest-consolidation | Data Agent | closed | `src/tradingbotsuite/data/**`, `tests/contracts/test_data_contracts.py`, `tests/integration/test_provider_intake_smoke.py`, `docs/stage_reports/STAGE_3_EXIT_REPORT.md` | Normalized data package, data manifest validator, partitioned Parquet store, Binance REST intake smoke, and registered-only provider manifests created. |
| WP4-01-feature-registry | Feature Agent | closed | `src/tradingbotsuite/features/**`, `configs/features/**`, `tests/contracts/test_feature_contracts.py`, `docs/stage_reports/STAGE_4_EXIT_REPORT.md` | Point-in-time alignment package, feature registry, feature packs, preset manifests, and train-only preprocessing tests created. |
| WP5-01-backtesting-engine | Backtest Agent | closed | `src/tradingbotsuite/backtesting/**`, `tests/contracts/test_backtest_contracts.py`, `tests/unit/test_execution_simulator.py`, `tests/integration/test_backtest_engine_fixture.py`, `docs/stage_reports/STAGE_5_EXIT_REPORT.md` | Modular research backtest engine, execution simulator, cost model, metrics, deterministic outputs, and benchmark baselines created. |
| WP6-01-strategy-plugin-library | Strategy Agent | closed | `src/tradingbotsuite/strategies/**`, `configs/strategies/**`, `tests/contracts/test_strategy_contracts.py`, `tests/integration/test_backtest_engine_fixture.py`, `docs/stage_reports/STAGE_6_EXIT_REPORT.md` | Strategy plugin contract, registry, configs, four baseline plugins, LC reference, HMM/KNN diagnostic plugin, and engine integration created. |
| WP7-01-hmm-knn-refactor | Orchestrator Agent | closed | `src/tradingbotsuite/strategies/hmm_knn/**`, `src/tradingbotsuite/research/hmm_knn.py`, `tests/tradingbotsuite/test_hmm_knn.py`, `docs/stage_reports/STAGE_7_EXIT_REPORT.md` | HMM/KNN split into modules, feature packs and distances are configurable, deterministic regime baseline added, artifact diagnostics added, and Stage 6 baseline benchmark recorded. |
| WP8-01-generic-experiment-runner | Orchestrator Agent | closed | `src/tradingbotsuite/research/experiment_runner.py`, `tests/tradingbotsuite/test_experiment_runner.py`, `tests/tradingbotsuite/test_research.py`, `docs/stage_reports/STAGE_8_EXIT_REPORT.md` | Generic experiment specs, deterministic cache keys, search expansion, split/regime/side/cost stress outputs, and explicit rejection reasons added. |
| WP9-01-research-ui-command-layer | Orchestrator Agent | closed | `src/tradingbotsuite/ui/**`, `docs/runbooks/research_ui_runbook.md`, `tests/integration/test_research_ui.py`, `docs/stage_reports/STAGE_9_EXIT_REPORT.md` | Research UI pages, manifest-linked metrics, visible queued research jobs, and live-adapter import boundary tests added. |
| WP10-01-live-preflight-hardening | Orchestrator Agent | closed | `src/tradingbotsuite/live/preflight.py`, `src/tradingbotsuite/promotion/artifact_validator.py`, `tests/live/**`, `docs/stage_reports/STAGE_10_EXIT_REPORT.md` | Live mode fails closed on unsafe config, research commands and research artifacts are rejected, root launchers delegate through canonical preflight, and testnet smoke remains documented. |
| WP11-01-promotion-shadow-bridge | Orchestrator Agent | closed | `src/tradingbotsuite/promotion/artifact_validator.py`, `src/tradingbotsuite/live/shadow_loader.py`, `src/tradingbotsuite/runtime.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/**`, `tests/live/**`, `tests/tradingbotsuite/test_operator_ui.py`, `docs/stage_reports/STAGE_11_EXIT_REPORT.md` | Promotion candidates validate against Stage 11 evidence floors, load only in shadow mode without execution changes, are rejected as live order inputs, and display read-only shadow diagnostics in the operator UI. |
| WP12-01-feature-ablation-and-replacement | Orchestrator Agent | closed | `src/tradingbotsuite/research/feature_ablation.py`, `configs/features/**`, `tests/tradingbotsuite/test_feature_ablation.py`, `docs/stage_reports/STAGE_12_1_EXIT_REPORT.md` | Stage 12.1 feature ablation tracks produce reproducible manifests, pending/rejected hypothesis records, per-hypothesis experiment specs, and OOS/stress-only acceptance rules. |
| WP12-02-research-track-gates-and-limitations | Orchestrator Agent | closed with empirical limitations | `src/tradingbotsuite/research/stage12_research.py`, `tests/tradingbotsuite/test_stage12_research_plan.py`, `docs/stage_reports/STAGE_12_EXIT_REPORT.md`, `docs/stage_reports/STAGE_12_COMPLETION_LIMITATIONS.md` | Substages 12.2-12.7 produce reproducible manifests/specs and documented blocked/pending hypotheses; empirical acceptance remains blocked until real OOS/stress evidence exists. |

## Gate checklist

| Requirement | Evidence | Passed |
| --- | --- | --- |
| Stage 12.1 completed | `docs/stage_reports/STAGE_12_1_EXIT_REPORT.md` | yes |
| Required feature ablation tracks represented | `tests/tradingbotsuite/test_feature_ablation.py` | yes |
| Reproducible ablation manifests and experiment specs are written | `src/tradingbotsuite/research/feature_ablation.py` | yes |
| Rejected/pending hypotheses are documented | `tests/tradingbotsuite/test_feature_ablation.py` | yes |
| In-sample-only acceptance is rejected | `tests/tradingbotsuite/test_feature_ablation.py` | yes |
| Substages 12.2-12.7 have reproducible manifests/specs | `src/tradingbotsuite/research/stage12_research.py`, `tests/tradingbotsuite/test_stage12_research_plan.py` | yes |
| Empirical Stage 12 acceptance limitation documented | `docs/stage_reports/STAGE_12_COMPLETION_LIMITATIONS.md` | yes |
| Live mode rejects Stage 12 planning commands | `tests/live/test_preflight.py` | yes |
| No P0 issues open | `docs/KNOWN_ISSUES.md` | yes |
| Fewer than four unresolved P1 issues | `docs/KNOWN_ISSUES.md` | yes |

## Orchestrator decision

Decision: hold before Stage 13
Reason: Stage 12 reproducible planning, manifest generation, and evidence gates are complete for substages 12.1-12.7. Full empirical Stage 12 completion is blocked because the repository does not contain sufficient new OOS/stress evidence, accepted optional dependency decisions, single-strategy evidence for portfolio allocation, or ETH-specific data artifacts. Do not advance to Stage 13 until the empirical evidence limitation is resolved or explicitly accepted.
