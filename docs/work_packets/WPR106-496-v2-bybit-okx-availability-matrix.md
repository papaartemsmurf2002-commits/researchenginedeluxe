# WPR106-496 - V2 Bybit OKX Availability Matrix Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-024`

## Objective

Continue `DATA-010` by adding deterministic Bybit/OKX public market request
builders and an injectable availability-matrix writer for small symbol/date
smoke coverage checks.

This packet does not add heavy backfill, raw archive writes, download caches,
normalization, feature generation, accepted historical coverage proof,
candidate evidence, candidate packs, paper/live behavior, order placement,
sizing instructions, runtime-mode changes, or promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-496-v2-bybit-okx-availability-matrix.md`
- `src/tradingbotsuite/v2/data_sources/bybit_okx.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_bybit_okx_availability_phase55.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No Bybit/OKX collector scheduling, archive writes, or generated external
  market-data evidence.
- No real network probes in tests; all availability checks must use injected
  clients.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_bybit_okx_availability_phase55.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add explicit endpoint specs for Bybit and OKX candles, trades, BBO/L2,
  funding, and open-interest availability probes.
- Use verified symbol-map rows before building availability rows.
- Keep availability rows metadata-only: request URL, family, source ID, venue
  symbol, date/window, status, response row count, and blocker reasons.
- Require source-registry entries to pass strict-zero-dollar validation and to
  remain external comparison/non-native sources.

## Acceptance Criteria

- Request builders produce stable public REST URLs for supported Bybit/OKX
  endpoint families.
- Availability rows fail closed for missing or unverified symbol mappings,
  wrong source IDs, non-strict-free sources, and probe errors.
- Availability matrices preserve source ID, external-comparison role, endpoint
  rate-limit metadata, and non-accepted coverage status.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/bybit_okx.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_bybit_okx_availability_phase55.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_bybit_okx_availability_phase55.py -q
```

Result: 5 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 426 passed; `tests/contracts` 463 passed;
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds request-builder and metadata-only availability-matrix
foundation only. It does not add Bybit/OKX collectors, run real network probes
in tests, download market data, write raw/bronze/silver archive rows, create
accepted historical coverage proof, create candidate evidence, create
candidate packs, add paper/live behavior, place orders, emit sizing
instructions, change runtime mode, or make promotion claims.
