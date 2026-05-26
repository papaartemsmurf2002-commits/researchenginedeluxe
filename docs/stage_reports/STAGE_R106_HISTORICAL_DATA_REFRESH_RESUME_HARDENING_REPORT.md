# Stage R106 Historical Data Refresh Resume Hardening Report

Date: 2026-05-21
Work packet: `docs/work_packets/WPR106-02-historical-data-refresh-resume-hardening.md`

## Summary

Investigated the failed R106 historical data catalog refresh. The local partial
run under `data/research/operator_runs/historical_data/refresh-historical-data-catalog-379ba340ee4a4ed18197a2237e339dea`
contains 228 checksum-verified BTCUSDT monthly archives through `2026-04`,
about 42 GB, but no fixture summary or `historical_data_catalog.json`. That
matches an all-or-nothing failure after archive download and before final
catalog writing.

The refresh path now:

- Uses a central verified Binance Vision download cache under the configured
  research output root.
- Seeds that cache from older partial historical-data or durable-data runs
  instead of discarding already downloaded archives.
- Reuses existing checksum-verified archives without network fetches.
- Writes `collection_progress.json` during collection with archive-step
  progress, current symbol/period/family, rate, elapsed time, and ETA.
- Streams generated Parquet files by archive partition instead of holding all
  lower-timeframe and trade-flow fixture rows in Python lists until the end.
- Exposes active historical-data refresh progress through the operator progress
  API and Research UI progress panel.
- Hardens operator job-log appends with an immediate SQLite write lock and
  retry so a fast background worker cannot race the queue request and crash the
  API with a duplicate `(job_id, seq)` insert.
- Records Binance aggTrade aggregate-ID source-order anomalies as quality
  evidence instead of treating them as fatal duplicate corruption. The generated
  trade-flow fixture is bucketed by event time, so non-monotonic aggregate IDs
  should not discard already checksum-verified archive data.

## Local recovery

The interrupted follow-up job
`refresh-historical-data-catalog-cf4a810eeaca466bbf83379847182248` had no live
Python worker and was marked failed with
`stale_running_job_recovered_after_network_or_operator_restart`. Its progress
journal was also marked failed so the operator console no longer reports a dead
run as active.

The central cache remains usable for retry:

- `data/research/historical_data_cache/binance_vision_public_archive/downloads`
- 228 BTCUSDT ZIP archives with checksum/manifests, about 39.3 GB
- ETHUSDT archive partitions were not downloaded yet and remain the next
  network-heavy leg.

## Boundaries

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. This change does not write candidate packs, claim
performance, touch live runtime configuration, place orders, or change sizing.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_api_reports_r104_milestones tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_reports_historical_data_refresh_journal tests\tradingbotsuite\test_operator_ui.py::test_operator_research_job_routes_default_to_r104_deep_and_exact_specs -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_sqlite_operator_job_log_append_is_concurrency_safe -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
- `PYTHONPATH=src python -m pytest tests\contracts -q`
- `PYTHONPATH=src python -m pytest -q`
