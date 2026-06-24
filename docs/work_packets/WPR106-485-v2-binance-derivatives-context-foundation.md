# WPR106-485 - V2 Binance Derivatives Context Foundation

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-013`

## Objective

Start `DATA-006` by adding a schema-first Binance USD-M public derivatives
context source entry plus deterministic endpoint/request builders for the
roadmap context families: funding-rate history, open interest, open-interest
statistics, mark/index/premium klines, taker buy/sell volume, long/short
ratios, and basis.

This packet does not fetch public endpoints, page historical windows, write
archive rows, create coverage reports, backtest, create accepted
Hyperliquid-native evidence, create candidate evidence, create candidate packs,
add paper/live behavior, place orders, emit sizing instructions, change runtime
mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-485-v2-binance-derivatives-context-foundation.md`
- `configs/data_sources/v2_source_registry.schema.json`
- `configs/data_sources/samples/source_registry_binance_usdm_public_derivatives_context.json`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_derivatives_context_phase48.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_context_phase48.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Register `binance_usdm_public_derivatives_context` as a strict-free,
  public-rate-limited, non-Hyperliquid-native source.
- Extend source-registry data-family validation with the granular `DATA-006`
  family names from the roadmap.
- Add deterministic request builders with endpoint-specific parameter rules
  and documented per-endpoint limit caps.
- Preserve research-only boundary flags on all request builder artifacts.

## Acceptance Criteria

- The new source-registry sample validates through `SourceRegistryEntry` and
  `require_strict_zero_dollar_source()`.
- Request builders produce deterministic URLs/params for all `DATA-006`
  endpoint families without network I/O.
- Invalid family names, missing required interval/period fields, and excessive
  limits fail closed.
- Boundary flags remain research-only and non-promotional.

## Changed Files

- `docs/work_packets/WPR106-485-v2-binance-derivatives-context-foundation.md`
- `configs/data_sources/v2_source_registry.schema.json`
- `configs/data_sources/samples/source_registry_binance_usdm_public_derivatives_context.json`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_derivatives.py`
- `src/tradingbotsuite/v2/data_sources/schemas.py`
- `tests/v2/test_binance_derivatives_context_phase48.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_context_phase48.py -q
# 5 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_context_phase48.py tests/v2/test_data_source_registry_phase37.py -q
# 15 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 384 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added `binance_usdm_public_derivatives_context` as a strict-free,
  public-rate-limited, non-Hyperliquid-native source fixture.
- Added granular `DATA-006` family names to the source-registry schema and
  Pydantic family gate.
- Added offline deterministic request builders for Binance USD-M public
  derivatives context families, including endpoint-specific interval, period,
  pair/symbol, contract-type, time-range, and limit validation.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-006` still needs fetching, pagination, raw/bronze/silver
  normalization, funding/OI/context coverage reports, and durable worker
  integration before unattended use.
