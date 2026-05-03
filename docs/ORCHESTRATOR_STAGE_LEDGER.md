# Orchestrator Stage Ledger

Current stage: Stage 11 - Promotion pipeline and shadow-only integration
Current stage owner: Orchestrator Agent
Stage status: complete
Last updated: 2026-05-03

## Stage entry decision

- Prior stage completed: yes
- Evidence links:
  - `docs/stage_reports/STAGE_11_EXIT_REPORT.md`
  - `src/tradingbotsuite/promotion/artifact_validator.py`
  - `src/tradingbotsuite/live/shadow_loader.py`
  - `src/tradingbotsuite/runtime.py`
  - `tests/live/test_promotion_candidate_validator.py`
  - `tests/live/test_shadow_loader.py`
  - `tests/tradingbotsuite/test_operator_ui.py`
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

## Gate checklist

| Requirement | Evidence | Passed |
| --- | --- | --- |
| Stage 11 completed | `docs/stage_reports/STAGE_11_EXIT_REPORT.md` | yes |
| Promotion candidate manifest validator exists | `src/tradingbotsuite/promotion/artifact_validator.py` | yes |
| Development-plan evidence floors are enforced | `tests/live/test_promotion_candidate_validator.py` | yes |
| Candidate can be accepted/rejected for shadow-only use | `tests/live/test_promotion_candidate_validator.py` | yes |
| Live branch loads shadow-only candidate without execution changes | `src/tradingbotsuite/live/shadow_loader.py`, `src/tradingbotsuite/runtime.py`, `tests/live/test_shadow_loader.py` | yes |
| Same candidate is rejected as a live order input | `tests/live/test_promotion_candidate_validator.py` | yes |
| Operator UI displays shadow diagnostics without live controls | `tests/tradingbotsuite/test_operator_ui.py` | yes |
| Stage exit report written | `docs/stage_reports/STAGE_11_EXIT_REPORT.md` | yes |
| No P0 issues open | `docs/KNOWN_ISSUES.md` | yes |
| Fewer than four unresolved P1 issues | `docs/KNOWN_ISSUES.md` | yes |

## Orchestrator decision

Decision: advance
Reason: Stage 11 Promotion pipeline and shadow-only integration is complete on the research branch. Promotion candidates now have explicit manifest validation, development-plan evidence floors, a live-branch shadow loader, runtime recognition that does not instantiate execution inputs, live-order rejection, and read-only operator diagnostics. Stage 12 Later-stage research expansion and institutional tuning may begin next.
