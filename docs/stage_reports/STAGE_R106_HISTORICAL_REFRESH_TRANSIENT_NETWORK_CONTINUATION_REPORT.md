# Stage R106 Historical Refresh Transient Network Continuation Report

Date: 2026-05-21
Work packet: `docs/work_packets/WPR106-03-historical-refresh-transient-network-continuation.md`

## Summary

Investigated the follow-up historical-data refresh job
`refresh-historical-data-catalog-500f7d78e7fa458eb3b7077ecbb7e242`. The job
failed after `241/456` archive steps with a transient Binance Vision TLS
handshake timeout while starting the ETHUSDT `1m` archive for `2020-05`. The
failed archive was not written, and the central cache remains valid.

The refresh path now:

- Retries transient Binance Vision ZIP and checksum fetch errors with bounded
  exponential backoff.
- Records archive/checksum fetch attempts and retry counts in download
  manifests.
- Reuses completed prior symbol fixture packs from interrupted catalog jobs, so
  a retry can skip rebuilding finished BTC/ETH fixture packs instead of only
  reusing raw ZIP files.
- Advances the progress journal for reused symbol packs, making the operator
  progress bar start at the real completed work instead of `0%`.
- Allows operator/research server runs to disable Binance market websocket
  startup through `TBS_BINANCE_MARKET_STREAMS_ENABLED=false`, reducing unrelated
  websocket disconnect noise during long catalog refreshes.

## Recovery State

The latest failed run completed BTCUSDT fixture generation and cached the first
ETHUSDT archives. The next refresh can reuse:

- BTCUSDT completed fixture pack from the failed job.
- All checksum-verified central archive cache entries.
- ETHUSDT archives already completed before the timeout.

No cache or generated fixture data was discarded.

## Boundaries

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. This change does not write candidate packs, claim
performance, touch live runtime configuration, place orders, or change sizing.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_market_data_collection.py::test_download_binance_vision_archive_retries_transient_fetch_errors tests\tradingbotsuite\test_market_data_collection.py::test_collect_candidate_depth_public_archive_fixtures_reuses_completed_symbol_fixture_pack tests\tradingbotsuite\test_operator_ui.py::test_operator_server_can_disable_binance_market_stream_startup -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_server_can_disable_binance_market_stream_startup tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_reports_historical_data_refresh_journal tests\tradingbotsuite\test_operator_ui.py::test_sqlite_operator_job_log_append_is_concurrency_safe -q`
- `PYTHONPATH=src python -m pytest tests\contracts -q`
- `PYTHONPATH=src python -m pytest -q`
- `git diff --check`
