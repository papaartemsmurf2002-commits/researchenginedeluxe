# Orchestrator Stage Ledger

Current stage: Stage 4 - Point-in-time feature store and feature registry
Current stage owner: Orchestrator Agent
Stage status: complete
Last updated: 2026-05-01

## Stage entry decision

- Prior stage completed: yes
- Evidence links:
  - `docs/stage_reports/STAGE_3_EXIT_REPORT.md`
  - `src/tradingbotsuite/features/alignment.py`
  - `src/tradingbotsuite/features/registry.py`
  - `src/tradingbotsuite/features/packs.py`
  - `src/tradingbotsuite/features/preprocessing.py`
  - `configs/features/features_full_context_wt3d.json`
  - `configs/features/features_full_context_no_wt.json`
  - `tests/contracts/test_feature_contracts.py`
  - `docs/work_packets/WP4-01-feature-registry.md`
  - `docs/stage_reports/STAGE_4_EXIT_REPORT.md`
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

## Gate checklist

| Requirement | Evidence | Passed |
| --- | --- | --- |
| Stage 3 completed | `docs/stage_reports/STAGE_3_EXIT_REPORT.md` | yes |
| Completed-bar alignment moved to feature package | `src/tradingbotsuite/features/alignment.py` | yes |
| Feature registry dataclasses added | `src/tradingbotsuite/features/registry.py` | yes |
| Initial feature packs implemented | `src/tradingbotsuite/features/packs.py` | yes |
| Required preset manifests and hashes added | `configs/features/*.json` | yes |
| WT3D optional and no-WT presets registered | `tests/contracts/test_feature_contracts.py` | yes |
| No-lookahead feature behavior tested | `tests/contracts/test_feature_contracts.py` | yes |
| Train-only preprocessing tested | `tests/contracts/test_feature_contracts.py` | yes |
| Feature package boundary tested | `tests/contracts/test_import_boundaries.py` | yes |
| Stage exit report written | `docs/stage_reports/STAGE_4_EXIT_REPORT.md` | yes |
| No P0 issues open | `docs/KNOWN_ISSUES.md` | yes |
| Fewer than four unresolved P1 issues | `docs/KNOWN_ISSUES.md` | yes |

## Orchestrator decision

Decision: advance
Reason: Stage 4 point-in-time feature registry is complete on the research branch. Stage 5 fast modular backtesting engine may begin; unresolved live-boundary enforcement risks remain assigned to Stage 10 and Stage 11.
