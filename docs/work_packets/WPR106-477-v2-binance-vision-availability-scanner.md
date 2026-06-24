# WPR106-477 - V2 Binance Vision Availability Scanner

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-005`
- `V2-AUD-XVENUE-016`

## Objective

Implement the `DATA-004` availability-scanner slice from
`docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`. The scanner probes
Binance Vision daily ZIP and checksum paths for verified Binance mappings from
the symbol-map snapshot and writes a local availability manifest for downstream
downloader/parser work.

This packet does not download ZIP contents, parse market data, normalize
bronze/silver tables, reconstruct bars, run backtests, create accepted
research evidence, create candidate evidence, write candidate packs, add
paper/live behavior, place orders, emit sizing instructions, mutate runtime
mode, or create promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-477-v2-binance-vision-availability-scanner.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `configs/data_sources/samples/**`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_vision_availability_phase40.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked legacy evidence under `data/research/fixtures/**`,
  `data/research/historical_cycles/**`, or existing WPR evidence directories.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_availability_phase40.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Probe metadata only: use injectable HEAD-style probe functions in tests.
- Require strict-free Binance Vision source entries before probing.
- Require verified `binance_usdm` or `binance_spot` symbol-map refs before
  building URLs.
- Record missing ZIPs, missing checksums, mapping blockers, and probe errors as
  manifest rows instead of silently skipping them.
- Mark Binance Vision as `native_to_hyperliquid=false` in source entries and
  availability rows.

## Acceptance Criteria

- Daily URL builders match the roadmap paths for USD-M trades, aggTrades,
  klines, and spot trades, aggTrades, klines.
- Availability manifests contain one row per requested symbol/date/source when
  mapping is verified.
- Unverified mappings produce blocker rows without URL probes.
- Missing ZIPs and missing checksums are explicit statuses.
- Source entries that are requester-pays, paid/keyed, or not accepted under
  strict-free mode fail before probing.

## Changed Files

- `docs/work_packets/WPR106-477-v2-binance-vision-availability-scanner.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `configs/data_sources/samples/source_registry_binance_vision_usdm_agg_trades.json`
- `configs/data_sources/samples/source_registry_binance_vision_usdm_klines.json`
- `configs/data_sources/samples/source_registry_binance_vision_spot_trades.json`
- `configs/data_sources/samples/source_registry_binance_vision_spot_agg_trades.json`
- `configs/data_sources/samples/source_registry_binance_vision_spot_klines.json`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_vision.py`
- `tests/v2/test_binance_vision_availability_phase40.py`

## Acceptance Evidence

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_binance_vision_availability_phase40.py -q
# 5 passed
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_binance_vision_availability_phase40.py tests\v2\test_universe_data_source_manifest_bridge_phase39.py tests\v2\test_data_source_registry_phase37.py tests\v2\test_symbol_map_resolver_phase38.py -q
# 27 passed
```

Baseline validation:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 357 passed
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF warnings only
```

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer path was changed.
- No legacy GUI path was changed.
- No checked legacy evidence under `data/research/fixtures/**` or
  `data/research/historical_cycles/**` was rewritten.
- The packet writes no generated market/research evidence during tests outside
  temporary pytest archives and performs no ZIP/archive download.
- The packet creates no accepted research, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion claim.

## Follow-Up

- `DATA-005` should use availability manifests to download available Binance
  Vision daily archives, verify checksums where present, parse trades,
  aggTrades, and 1m klines, and write raw/bronze/silver evidence.
- Reconstructed-bar validation from trades/aggTrades should remain a separate
  fail-closed quality gate after parser intake exists.
