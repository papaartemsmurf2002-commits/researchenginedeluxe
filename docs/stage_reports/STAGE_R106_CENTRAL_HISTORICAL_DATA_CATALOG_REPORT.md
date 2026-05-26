# Stage R106 Central Historical Data Catalog Report

Date: 2026-05-20
Work packet: `docs/work_packets/WPR106-01-central-historical-data-catalog.md`

## Scope

R106 replaces the one-off durable data collection workflow with a central
historical data catalog. The catalog is the required source of truth for active
BTCUSDT/ETHUSDT historical fixture, readiness, cycle, and discovery paths.

## Implementation

- Added `src/tradingbotsuite/data/historical_data_catalog.py`.
- Added CLI and operator job support for `refresh-historical-data-catalog`.
- Added `/api/operator/research/historical-data-catalog`.
- Updated required Research UI Step 0 to `Refresh Historical Data Catalog`.
- Kept `collect-durable-data` as compatibility-only.
- Indexed `historical_data_catalog.json` in research artifacts and progress.
- Documented catalog behavior in the data and boundary contracts.

## Provider Status

- Binance Vision: active implemented source, checksum-validated public archive
  fixture path.
- Crypto Lake: local/vendor export ingestion exists elsewhere in the branch,
  but unattended catalog refresh requires configured exports or cache access.
- Bybit archive: official public historical data surface exists, but normalized
  downloader/parser/checksum validation is not implemented in this packet.
- Hyperliquid archive: official requester-pays archive exists and may be
  incomplete; ingestion requires AWS requester-pays access, LZ4 parsing, and
  local account-journal reconciliation before candidate-depth use.

## Boundary

All catalog outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. The catalog does not place orders, change runtime
mode, write live configuration, or promote research artifacts.

## Validation

Completed 2026-05-20:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\tradingbotsuite\test_operator_ui.py tests\contracts\test_data_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
```

Result: full suite passed with `1394 passed, 1 skipped`. The full run emitted
existing pandas future warnings in legacy `src/tradingbot/lorentz_lc.py` and one
XGBoost device mismatch warning during data-pipeline tests; no test failed.
