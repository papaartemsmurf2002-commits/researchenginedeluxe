# WPR106-02 Historical Data Refresh Resume Hardening

Stage: R106 centralized historical data catalog
Owner: Codex Research Agent
Status: closed

## Problem

The R106 historical data catalog refresh can spend hours downloading Binance
Vision monthly archive partitions and then fail before writing a catalog. The
current implementation writes the source summary and catalog only after all
symbols complete, downloads into a per-job directory, re-downloads existing
archives on retry, and keeps large parsed row collections in memory before
writing Parquet.

## Scope

Allowed paths:

- `src/tradingbotsuite/data/durable_public_archive.py`
- `src/tradingbotsuite/data/historical_data_catalog.py`
- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/persistence/sqlite_store.py`
- `src/tradingbotsuite/web/operator.py`
- `src/tradingbotsuite/main.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR106-02-historical-data-refresh-resume-hardening.md`
- `docs/stage_reports/STAGE_R106_HISTORICAL_DATA_REFRESH_RESUME_HARDENING_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Plan

1. Add a verified archive cache path and reuse checks so retries do not
   re-download checksum-verified partitions.
2. Preserve already downloaded job-local archives by allowing the operator
   refresh to seed the central cache from prior partial historical-data runs.
3. Add a refresh progress journal with completed archive count, current
   symbol/period/family, percentage, and ETA fields.
4. Reduce memory pressure in the collector by streaming generated Parquet
   outputs instead of holding all lower-timeframe and trade-flow rows until the
   end.
5. Harden operator job-log appends against queue/worker races that can duplicate
   `(job_id, seq)` rows.
6. Add focused regressions for cache reuse/progress, aggTrade source-order
   anomaly recording, and concurrent job-log appends.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `PYTHONPATH=src python -m pytest tests\contracts -q`
