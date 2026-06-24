# WPR106-499 - V2 Alt Derivatives Availability Matrix

Status: closed
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-027`

## Objective

Continue `DATA-011` by adding deterministic public REST request builders and a
metadata-only availability-matrix writer for MEXC, Bitget, Gate, KuCoin, and
HTX public derivatives market data.

This packet does not add heavy backfill, durable worker routing, download
caches, raw/bronze/silver archive writes, normalization, feature generation,
accepted historical coverage proof, candidate evidence, candidate packs,
paper/live behavior, order placement, sizing instructions, runtime-mode
changes, or promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-499-v2-alt-derivatives-availability-matrix.md`
- `src/tradingbotsuite/v2/data_sources/alt_derivatives.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_alt_derivatives_availability_phase57.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector scheduling, archive writes, or generated external market-data
  evidence.
- No real network probes in tests; all availability checks must use injected
  clients.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_alt_derivatives_availability_phase57.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add per-venue candle availability endpoint specs first, with source ID,
  venue key, URL shape, timestamp unit, rate-limit hint, and page cap metadata.
- Use verified symbol-map rows before building availability rows.
- Keep availability rows metadata-only: request URL, endpoint, family, source
  ID, venue symbol, date/window, status, response row count, and blocker
  reasons.
- Require source-registry entries to pass strict-zero-dollar validation and to
  remain external comparison/non-native sources.

## Acceptance Criteria

- Request builders produce stable public REST URLs for one candle endpoint per
  DATA-011 venue.
- Availability rows fail closed for missing or unverified symbol mappings,
  wrong source IDs, non-strict-free sources, and probe errors.
- Availability matrices preserve source ID, external-comparison role,
  endpoint-rate metadata, and non-accepted coverage status.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/alt_derivatives.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_alt_derivatives_availability_phase57.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_alt_derivatives_availability_phase57.py -q
```

Result: 4 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 436 passed; `tests/contracts` 463 passed;
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds request-builder and metadata-only availability-matrix
foundation only. It does not add alt-venue collectors, run real network probes
in tests, download market data, write raw/bronze/silver archive rows,
normalize venue data, create accepted historical coverage proof, create
candidate evidence, create candidate packs, add paper/live behavior, place
orders, emit sizing instructions, change runtime mode, or make promotion
claims.
