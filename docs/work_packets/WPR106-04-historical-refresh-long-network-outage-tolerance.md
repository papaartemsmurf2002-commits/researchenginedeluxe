# WPR106-04 Historical Refresh Long Network Outage Tolerance

Stage: R106 centralized historical data catalog
Owner: Codex Research Agent
Status: closed

## Problem

The R106 historical data catalog refresh still failed during ETHUSDT collection
after a transient DNS outage (`getaddrinfo failed`). WPR106-03 added bounded
per-download retries, but the default retry budget is too short for unstable
VPN/internet periods during multi-hour archive collection.

## Scope

Allowed paths:

- `src/tradingbotsuite/research/market_data.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `docs/work_packets/WPR106-04-historical-refresh-long-network-outage-tolerance.md`
- `docs/stage_reports/STAGE_R106_HISTORICAL_REFRESH_LONG_NETWORK_OUTAGE_TOLERANCE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Plan

1. Increase the default Binance Vision transient-network retry budget for long
   research archive refreshes.
2. Add environment overrides for max attempts, base backoff, and max backoff so
   the operator can tune long unattended runs without code changes.
3. Preserve fail-fast behavior for deterministic validation failures such as
   checksum mismatch.
4. Add focused tests for retry environment overrides and capped backoff.
5. Validate focused tests, contracts, and full suite if feasible.

## Outcome

Implemented a longer Binance Vision transient-network retry budget for
historical-data refreshes. Defaults are now 360 attempts, 10 second base
backoff, and 60 second max backoff per archive/checksum fetch. The values are
operator-tunable through:

- `TBS_BINANCE_VISION_DOWNLOAD_MAX_ATTEMPTS`
- `TBS_BINANCE_VISION_DOWNLOAD_RETRY_BACKOFF_SECONDS`
- `TBS_BINANCE_VISION_DOWNLOAD_RETRY_MAX_BACKOFF_SECONDS`

The downloader records the resolved retry budget in each download manifest.
Transient DNS-style `URLError` failures retry; checksum mismatches still fail
without retrying validation.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_market_data_collection.py::test_download_binance_vision_archive_retries_transient_fetch_errors tests\tradingbotsuite\test_market_data_collection.py::test_download_binance_vision_archive_uses_env_retry_budget_with_capped_backoff tests\tradingbotsuite\test_market_data_collection.py::test_download_binance_vision_archive_does_not_retry_checksum_mismatch -q`
- `PYTHONPATH=src python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q`
- `PYTHONPATH=src python -m pytest tests\contracts -q`
- `PYTHONPATH=src python -m pytest -q`
