# Stage R105 Bybit And Hyperliquid Provider Surface Audit Report

Date: 2026-05-20
Work packet: `docs/work_packets/WPR105-107-bybit-hyperliquid-provider-surface-audit.md`
Status: closed

## Summary

WPR105-107 clarifies that Binance Vision Step 0 is the default implemented
public-archive collection path, not the full universe of possible data
providers. Bybit is now represented as a conservative registered-only archive
surface, and Hyperliquid archive remains explicitly registered-only until local
archive ingestion and account-journal reconciliation are implemented.

Official source notes:

- Bybit documents historical market-data downloads for public OHLCV/trade CSVs
  and V5 market endpoints for recent trades, funding, open interest, orderbook,
  and klines.
- Hyperliquid documents requester-pays S3 archives for L2 book snapshots,
  asset contexts, node fills/trades, and historical node data, with warnings
  about missing or untimely data.

## Implementation Notes

- Added `bybit_archive` to archive-source descriptors with BTC/ETH scope,
  durable-relevant market-data families, source caveats, and diagnostic-only
  defaults.
- Added `bybit_archive` to provider capability metadata as `registered_only`,
  `implemented_for_ingestion: false`, `candidate_ready_default: false`.
- Added a registered-only Bybit provider manifest helper.
- Updated provider pipeline diagnostics and runtime docs to show Bybit and
  Hyperliquid as registered-only diagnostics, while Binance Vision and Crypto
  Lake remain the currently implemented local ingestion paths.
- Updated the Research UI wording so Step 0 is clearly the default Binance
  Vision route, not a statement that other providers are impossible.

## Boundary

No Bybit downloader/parser, Hyperliquid downloader/parser, live execution,
order placement, runtime-mode mutation, live configuration write, promotion
behavior, candidate-pack write, or sizing behavior was added. Registered-only
provider manifests remain `research_only`, `observe_only`, diagnostic, and
`promotion_ready: false`.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_data_contracts.py tests\tradingbotsuite\test_archive_sources.py tests\tradingbotsuite\test_data_pipeline.py::test_archive_provider_descriptors_cover_expected_contract_sources tests\tradingbotsuite\test_data_pipeline.py::test_prepare_hmm_knn_research_data_intake_writes_provider_journal_and_quality_manifests tests\tradingbotsuite\test_operator_ui.py::test_operator_research_page_keeps_hmm_knn_monitoring_observe_only -q
git diff --check
```

Result: compile passed; focused provider and UI validation passed with
`34 passed`; `git diff --check` passed.
