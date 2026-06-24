# WPR106-478 - V2 Binance Vision ZIP Parser Validation

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-006`
- `V2-AUD-ARCH-027`

## Objective

Implement the first `DATA-005` parser/checksum slice from
`docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`. This packet validates
local Binance Vision daily ZIP bytes for trades, aggTrades, and 1m klines,
checks optional checksum payloads, parses CSV members into normalized
research-only rows, and reports duplicate/gap/interval diagnostics.

This packet does not perform network downloads, write raw/bronze/silver archive
files, run backtests, create accepted research evidence, create candidate
evidence, write candidate packs, add paper/live behavior, place orders, emit
sizing instructions, mutate runtime mode, or create promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-478-v2-binance-vision-zip-parser-validation.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_vision_parser_phase41.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_vision_parser_phase41.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Parse local ZIP bytes only; no downloader or HTTP fetcher in this packet.
- Support exactly one CSV member per ZIP.
- Support headered and Binance Vision headerless rows for `trades`,
  `aggTrades`, and `klines`.
- Verify checksum payloads when supplied and fail closed on mismatch.
- Preserve Binance-native IDs and fields in raw payload metadata.
- Report duplicate trade IDs, duplicate aggregate trade IDs, candle gap counts,
  and candle interval alignment status.

## Acceptance Criteria

- Valid kline ZIP bytes parse into normalized 1m candle rows with monotonic
  timestamps, gap diagnostics, and interval alignment evidence.
- Valid trades and aggTrades ZIP bytes parse into normalized trade rows with
  duplicate ID diagnostics.
- Bad checksum payloads fail before parsing.
- ZIPs with zero or multiple CSV members fail closed.
- Outputs preserve research-only boundary flags and remain non-accepted
  metadata until archive write/coverage packets consume them.

## Changed Files

- `docs/work_packets/WPR106-478-v2-binance-vision-zip-parser-validation.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_vision.py`
- `tests/v2/test_binance_vision_parser_phase41.py`

## Acceptance Evidence

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_binance_vision_parser_phase41.py -q
# 5 passed
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_binance_vision_parser_phase41.py tests\v2\test_binance_vision_availability_phase40.py tests\v2\test_universe_data_source_manifest_bridge_phase39.py tests\v2\test_data_source_registry_phase37.py tests\v2\test_symbol_map_resolver_phase38.py -q
# 32 passed
```

Baseline validation:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 362 passed
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
- The packet parses in-memory/local ZIP bytes only and performs no network
  download or archive write.
- The packet creates no accepted research, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion claim.

## Follow-Up

- A later `DATA-005` packet should integrate availability manifests with an
  actual downloader/cache, then write raw archive files and bronze/silver
  tables from parser output.
- Reconstructed kline-vs-trade/aggTrade comparison and coverage reports remain
  pending quality gates.
