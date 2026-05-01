# Work Packet: WP3-01-data-manifest-consolidation

Stage: Stage 3 - Data architecture and normalized research store
Owner agent: Data Agent
Reviewer agent: QA Agent
Branch: `research/v3-experimental-engine`
Allowed paths:

- `src/tradingbotsuite/data/**`
- `tests/contracts/test_data_contracts.py`
- `tests/contracts/test_import_boundaries.py`
- `tests/integration/test_provider_intake_smoke.py`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/work_packets/WP3-01-data-manifest-consolidation.md`
- `docs/stage_reports/STAGE_3_EXIT_REPORT.md`

Forbidden paths:

- live runtime execution behavior
- strategy, feature, optimizer, and backtest implementation outside data-facing compatibility imports
- generated data, secrets, databases, logs, caches, and local artifacts

## Objective

Promote existing provider/archive contracts into `tradingbotsuite.data`, add a canonical data manifest validator, add partitioned Parquet storage, and prove one deterministic Binance kline intake path writes data plus quality evidence.

## Required source files to read first

- `docs/contracts/data_contract.md`
- `docs/repo_cartography/REPO_INVENTORY.md`
- `src/tradingbotsuite/research/archive_sources.py`
- `src/tradingbotsuite/research/data_quality.py`
- `src/tradingbotsuite/research/market_data.py`
- `tests/tradingbotsuite/test_archive_sources.py`
- `tests/tradingbotsuite/test_data_quality.py`
- `tests/tradingbotsuite/test_market_data_collection.py`

## Implementation tasks

- Add `src/tradingbotsuite/data/contracts.py`.
- Add provider wrappers under `src/tradingbotsuite/data/providers/`.
- Add `src/tradingbotsuite/data/storage/parquet_store.py`.
- Add data quality compatibility wrapper under `src/tradingbotsuite/data/quality.py`.
- Add contract tests for canonical data families, manifests, missingness, and registered-only providers.
- Add integration smoke for deterministic Binance REST kline intake.
- Update stage ledger and exit report.

## Tests and validation commands

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main collect-binance-bars --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main fetch-binance-vision --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main fetch-crypto-lake --help
$env:PYTHONPATH='src'; python -m tradingbotsuite.main prepare-hmm-knn-research-data --help
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_data_contracts.py tests/integration/test_provider_intake_smoke.py tests/contracts/test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_archive_sources.py tests/tradingbotsuite/test_data_quality.py tests/tradingbotsuite/test_data_pipeline.py tests/tradingbotsuite/test_market_data_collection.py tests/tradingbotsuite/test_research.py -q
```

## Acceptance evidence

- `src/tradingbotsuite/data/contracts.py`
- `src/tradingbotsuite/data/storage/parquet_store.py`
- `tests/contracts/test_data_contracts.py`
- `tests/integration/test_provider_intake_smoke.py`
- `docs/stage_reports/STAGE_3_EXIT_REPORT.md`

## Handoff notes

Stage 4 should build point-in-time feature manifests on top of these data manifests and must preserve explicit missingness.
