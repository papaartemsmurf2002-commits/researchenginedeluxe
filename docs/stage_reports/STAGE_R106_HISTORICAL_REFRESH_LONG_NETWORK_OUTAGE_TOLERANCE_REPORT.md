# Stage R106 Historical Refresh Long Network Outage Tolerance Report

Date: 2026-05-22
Work packet: `docs/work_packets/WPR106-04-historical-refresh-long-network-outage-tolerance.md`

## Summary

Investigated the latest historical-data refresh job
`refresh-historical-data-catalog-c209bf0dbdb04ab6be9fa9306525b423`. The job
failed after `286/456` archive steps (`62.72%`) with
`<urlopen error [Errno 11001] getaddrinfo failed>` while collecting the ETHUSDT
`1m` monthly archive for `2021-08`. Current local DNS and TCP connectivity to
`data.binance.vision:443` were healthy after the outage, and the cache state
showed BTCUSDT had been reused while ETHUSDT had progressed into the 2021
archive range. The retry/resume hardening from WPR106-03 was loaded; the
remaining failure was that the default retry window was too short for a longer
VPN/internet outage.

The Binance Vision downloader now:

- Defaults to 360 transient fetch attempts per archive/checksum request.
- Uses 10 second exponential-backoff base delay capped at 60 seconds.
- Allows operator tuning through
  `TBS_BINANCE_VISION_DOWNLOAD_MAX_ATTEMPTS`,
  `TBS_BINANCE_VISION_DOWNLOAD_RETRY_BACKOFF_SECONDS`, and
  `TBS_BINANCE_VISION_DOWNLOAD_RETRY_MAX_BACKOFF_SECONDS`.
- Records the resolved retry budget in per-archive download manifests.
- Retries DNS-shaped `URLError` failures and other transient fetch failures.
- Preserves fail-fast behavior for deterministic validation failures such as
  checksum mismatch.

## Recovery State

The failed job did not start from scratch. It reused BTCUSDT completed fixture
work and advanced beyond the previous `241/456` archive-step failure to
`286/456`. The next refresh can reuse:

- Completed BTCUSDT fixture packs from prior interrupted jobs.
- Central checksum-verified Binance Vision cache entries.
- ETHUSDT raw archives already downloaded before the DNS outage.

Partial ETHUSDT fixture output still should not be treated as a completed
catalog result until the refresh completes and writes the catalog atomically.

## Boundaries

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. This change does not write candidate packs, claim
performance, touch live runtime configuration, place orders, or change sizing.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_market_data_collection.py::test_download_binance_vision_archive_retries_transient_fetch_errors tests\tradingbotsuite\test_market_data_collection.py::test_download_binance_vision_archive_uses_env_retry_budget_with_capped_backoff tests\tradingbotsuite\test_market_data_collection.py::test_download_binance_vision_archive_does_not_retry_checksum_mismatch -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q`
- `PYTHONPATH=src python -m pytest tests\contracts -q`
- `PYTHONPATH=src python -m pytest -q`
