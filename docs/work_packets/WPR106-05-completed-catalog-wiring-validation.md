# WPR106-05 Completed Catalog Wiring Validation

Stage: R106 centralized historical data catalog
Owner: Codex Research Agent
Status: closed

## Problem

The completed R106 historical-data catalog is present and candidate-depth ready
for BTCUSDT and ETHUSDT, but final validation found stale operator wiring that
still treats only R104 hard-coded cycle/discovery IDs as required evidence.
Generated catalog active specs use candidate-depth IDs, so progress and
required-artifact gates can incorrectly report current catalog artifacts as
missing or stale.

## Scope

Allowed paths:

- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/web/templates/research.html`
- `src/tradingbotsuite/persistence/sqlite_store.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR106-05-completed-catalog-wiring-validation.md`
- `docs/stage_reports/STAGE_R106_COMPLETED_CATALOG_WIRING_VALIDATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Plan

1. Validate the completed local catalog, fixture manifests, Parquet row counts,
   checksum-backed archive references, readiness files, and generated active
   cycle/discovery specs.
2. Patch operator progress gates to derive expected cycle/discovery IDs from
   the active catalog readiness instead of R104 literals.
3. Patch stable exact-discovery detection to include generated candidate-depth
   exact specs.
4. Update UI artifact filters so current catalog-required artifacts are not
   hidden as legacy/non-required.
5. Recover interrupted DB `running` jobs on operator-service startup so stale
   pre-restart jobs do not mask the completed catalog.
6. Add tests that simulate a completed catalog with generated active specs and
   prove progress/readiness routing follows it.
7. Validate focused tests, contracts, and full suite if feasible.

## Outcome

The completed local catalog
`data/research/operator_runs/historical_data/refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb/historical_data_catalog.json`
was validated as the centralized source of truth for the current research data
path. BTCUSDT and ETHUSDT are both candidate-depth fixture ready with 76 monthly
periods (`2020-01` through `2026-04`), 228 checksum-verified archives per
symbol, generated active readiness files, generated active cycle specs, and
generated active exact-discovery specs.

Patched stale R104-only UI/API wiring:

- Operator progress gates now derive expected cycle and discovery IDs from the
  active catalog readiness.
- The operator API treats generated `*_candidate_depth_v1` exact-discovery
  specs as stable resumable required sweeps.
- The Research UI recognizes generated candidate-depth cycle/discovery
  artifacts as required evidence and primes BTC controls from the active
  catalog when no local override is saved.
- Operator startup now recovers interrupted DB jobs left in `running` state so
  stale jobs do not mask current catalog progress.

Provider-quality review kept Binance Vision as the implemented active source:
official Binance public data provides daily/monthly files with per-ZIP checksum
sidecars and USD-M futures klines/aggTrades matching exchange API schemas.
Crypto Lake, Bybit, and Hyperliquid remain useful expansion sources but are not
current active catalog inputs until credentials/parser/checksum/gap-validation
contracts are implemented.

## Validation

- Completed-catalog validation script: `VALIDATION_OK`
- Central cache count check: BTCUSDT and ETHUSDT each have 76 `15m`, 76 `1m`,
  and 76 `aggTrades` ZIP/checksum/manifest triplets.
- Current operator DB cleanup: stale running jobs recovered; no `running` jobs
  remain.
- `python -m compileall -q src\tradingbotsuite`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q`
- `PYTHONPATH=src python -m pytest tests\contracts -q`
- `PYTHONPATH=src python -m pytest -q`
