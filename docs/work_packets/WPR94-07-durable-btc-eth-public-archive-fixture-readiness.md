# WPR94-07 Durable BTC/ETH Public Archive Fixture Readiness

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Move discovery fixture evidence toward durable BTC/ETH public archive windows
without pretending latest-window REST context is candidate-ready. This packet
adds an executable readiness contract for small, intentional fixture packs that
claim public archive provenance.

## Allowed Paths

- `docs/work_packets/WPR94-07-durable-btc-eth-public-archive-fixture-readiness.md`
- `docs/stage_reports/STAGE_R94_DURABLE_BTC_ETH_PUBLIC_ARCHIVE_FIXTURE_READINESS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `src/tradingbotsuite/data/providers/binance_vision.py`
- `src/tradingbotsuite/data/__init__.py`
- `configs/research/durable_public_archive_fixture_readiness_btcusdt_v1.json`
- `configs/research/durable_public_archive_fixture_readiness_ethusdt_v1.json`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/contracts/test_data_contracts.py`

## Scope

- Add a public-archive fixture readiness validator for BTCUSDT/ETHUSDT.
- Require primary 15m bars, lower-timeframe bars for exit sequencing, and
  aggTrade trade-flow proxy context when readiness is claimed.
- Require durable archive provenance, checksums/hashes, gap/duplicate evidence,
  window/regime selection metadata, explicit omitted optional families, and
  visible fixture limitations.
- Keep REST derivatives context `latest_window_only` and diagnostic unless a
  durable archive/local export source exists.
- Add small readiness config templates for BTCUSDT and ETHUSDT.

## Non-Goals

- No large archive downloads or checked raw archives.
- No live fetching, live config writes, order placement, runtime mode changes,
  or sizing logic changes.
- No candidate-pack writing or promotion readiness.
- No change to latest-window REST context semantics.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

Passed on 2026-05-12:

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

## Exit Evidence

- Added a durable public archive fixture readiness validator for BTCUSDT and
  ETHUSDT fixture packs.
- Readiness requires primary 15m bars, lower-timeframe bars, aggTrade
  trade-flow proxy context, public archive provenance, checksum/hash evidence,
  gap/duplicate evidence, explicit regime-window selection, omitted optional
  family reasons, and visible limitations.
- Latest-window REST context and free-sample context remain valid research
  fixture inputs but fail durable readiness as diagnostic-only evidence.
- Added BTC/ETH readiness config templates that do not point at large checked
  raw archives and do not write candidate packs.
- Exposed readiness helpers through the data package.
