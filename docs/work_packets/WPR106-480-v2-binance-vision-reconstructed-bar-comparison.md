# WPR106-480 - V2 Binance Vision Reconstructed-Bar Comparison

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-008`
- `V2-AUD-QUAL-008`

## Objective

Continue `DATA-005` by adding a fail-closed quality gate that reconstructs 1m
bars from parsed Binance Vision trades or aggTrades and compares the result to
parsed Binance Vision 1m klines. The output is a metadata comparison report for
later coverage/acceptance gates.

This packet does not perform network downloads, mutate live/runtime state,
run backtests, create accepted research evidence, create candidate evidence,
write candidate packs, add paper/live behavior, place orders, emit sizing
instructions, or create promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-480-v2-binance-vision-reconstructed-bar-comparison.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_vision_reconstruction_phase43.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_reconstruction_phase43.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Input is already parsed `BinanceVisionParseResult` objects.
- Trades and aggTrades may reconstruct bars; kline parse results are the
  comparison target.
- Compare open/high/low/close, volume, and observed trade/aggTrade count.
- Missing reconstructed buckets and tolerance failures must become blocker
  metadata rather than hidden skips.
- Reports remain research-only metadata and not accepted coverage evidence.

## Acceptance Criteria

- Matching parsed trades/aggTrades and klines produce a passing comparison
  report.
- Missing reconstructed buckets and OHLCV tolerance mismatches fail the report
  with explicit reasons.
- The report includes stable identity/hash metadata and preserves the v2
  research boundary.

## Changed Files

- `docs/work_packets/WPR106-480-v2-binance-vision-reconstructed-bar-comparison.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_vision.py`
- `tests/v2/test_binance_vision_reconstruction_phase43.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_reconstruction_phase43.py -q
# 3 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_reconstruction_phase43.py tests/v2/test_binance_vision_archive_ingest_phase42.py tests/v2/test_binance_vision_parser_phase41.py tests/v2/test_binance_vision_availability_phase40.py tests/v2/test_universe_data_source_manifest_bridge_phase39.py tests/v2/test_data_source_registry_phase37.py tests/v2/test_symbol_map_resolver_phase38.py -q
# 37 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 367 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added deterministic reconstructed 1m bars from parsed Binance Vision
  trades/aggTrades and compared them against parsed 1m klines.
- Missing reconstructed buckets and OHLCV tolerance failures produce explicit
  blocker metadata instead of hidden skips.
- Comparison reports remain research-only, non-native-to-Hyperliquid metadata
  and do not create accepted evidence or promotion readiness claims.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-005` still needs downloader/cache integration and data-family coverage
  report wiring before Binance Vision can serve as a complete strict-free
  comparison source.
