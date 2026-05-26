# WPR106-03 Historical Refresh Transient Network Continuation

Stage: R106 centralized historical data catalog
Owner: Codex Research Agent
Status: closed

## Problem

The R106 historical data catalog refresh can run for hours and then fail on a
transient Binance Vision TLS/URL open timeout after preserving already verified
archive downloads. The current downloader has cache reuse but no bounded retry
around individual ZIP or checksum requests, so one temporary network failure
still fails the entire catalog job. The operator console can also emit
websocket disconnect callback tracebacks while the user is only running
research/catalog workflows, which makes the real failure harder to see.

## Scope

Allowed paths:

- `src/tradingbotsuite/research/market_data.py`
- `src/tradingbotsuite/data/durable_public_archive.py`
- `src/tradingbotsuite/data/historical_data_catalog.py`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/core/engine.py`
- `src/tradingbotsuite/web/app.py`
- `src/tradingbotsuite/config.py`
- `tests/tradingbotsuite/test_market_data_collection.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR106-03-historical-refresh-transient-network-continuation.md`
- `docs/stage_reports/STAGE_R106_HISTORICAL_REFRESH_TRANSIENT_NETWORK_CONTINUATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Plan

1. Add bounded retry/backoff around Binance Vision archive and checksum fetches
   without retrying deterministic validation failures such as checksum mismatch.
2. Preserve retry evidence in download manifests so long catalog refreshes are
   auditable after transient network recovery.
3. Add an operator-server control for research-only runs to suppress live market
   websocket startup noise while leaving the existing default behavior intact.
4. Add focused regressions for transient download retry and operator-server
   market-stream suppression.
5. Validate with compile, affected tests, contracts, and full pytest if time
   permits.
