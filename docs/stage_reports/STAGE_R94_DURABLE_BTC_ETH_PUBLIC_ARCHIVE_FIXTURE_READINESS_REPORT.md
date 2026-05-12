# Stage R94 Durable BTC/ETH Public Archive Fixture Readiness Report

Date: 2026-05-12
Owner: Codex Research Agent

## Summary

WPR94-07 added an executable fixture-readiness contract for future BTCUSDT and
ETHUSDT public archive fixture packs. The contract is stricter than normal
fixture validation: latest-window REST context and free-sample context can stay
valid for diagnostics, but they cannot satisfy durable public archive readiness.

## Changes

- Added `PublicArchiveFixtureReadiness`,
  `validate_public_archive_fixture_readiness`, and
  `assert_public_archive_fixture_ready`.
- Required readiness evidence:
  - BTCUSDT or ETHUSDT symbol
  - 15m primary bars from Binance Vision public archive provenance
  - lower-timeframe bars for exit sequencing
  - aggTrade context as a trade-flow proxy, not OFI or order-book imbalance
  - source hashes/checksum evidence
  - gap and duplicate evidence
  - trend/bull, drawdown/bear, range/chop, and high-vol shock windows
  - explicit omitted optional family reasons
  - visible non-promotion limitations
- Added BTC/ETH readiness config templates under `configs/research`.
- Exported the readiness helpers from `tradingbotsuite.data`.

## Boundary

All outputs remain research-only and observe-only with
`promotion_ready: false`. No archive downloads, live fetches, candidate-pack
writes, promotion claims, order placement, runtime mode changes, or sizing
logic were added.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py -q
# 37 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_data_contracts.py -q
# 13 passed

$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 140 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 377 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with line-ending warnings only
```

## Next

Continue the roadmap order with perp context source/version audit.
