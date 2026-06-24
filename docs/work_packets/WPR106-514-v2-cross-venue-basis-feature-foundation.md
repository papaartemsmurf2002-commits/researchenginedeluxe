# WPR106-514 - V2 Cross-Venue Basis Feature Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-042`

## Objective

Finish the `DATA-015` feature reconstruction foundation by adding a
research-only cross-venue price/basis feature helper. The helper consumes
already-normalized price observation rows, requires a primary venue row, and
emits deterministic comparison rows with absolute and bps differences while
preserving source registry and symbol-map refs.

This packet does not add collectors, download market data, write archive rows,
create accepted coverage, build gold panels, run backtests, create candidate
evidence, create candidate packs, add paper/live behavior, place orders, emit
sizing instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-514-v2-cross-venue-basis-feature-foundation.md`
- `src/tradingbotsuite/v2/data_sources/feature_reconstruction.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_feature_reconstruction_phase68.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No archive data downloads, generated market-data rows, accepted historical
  coverage proof, data-family coverage acceptance, or gold panel writes.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_feature_reconstruction_phase68.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Consume already-normalized price observations rather than fetching or
  normalizing provider payloads.
- Keep primary venue and comparison venue provenance explicit; never relabel
  external venue prices as Hyperliquid-native observations.
- Treat empty input, insufficient venue coverage, missing/duplicate primary
  rows, mixed coin/market/price-kind provenance, non-positive prices, and
  missing timestamps as fail-closed blockers.
- Output rows are feature candidates for later gold panels, not gold panel rows
  themselves.

## Acceptance Criteria

- Cross-venue feature rows compute absolute and bps price differences
  deterministically against the requested primary venue.
- Rows preserve primary and comparison venue/source metadata and remain
  non-promotable.
- Empty input, insufficient venues, missing/duplicate primary rows, malformed
  prices/timestamps, and mixed provenance fail closed.
- Feature reports remain research-only, observe-only, non-promotable, and not
  accepted historical coverage proof.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/feature_reconstruction.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_feature_reconstruction_phase68.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-514-v2-cross-venue-basis-feature-foundation.md`

## Validation Evidence

Focused:

```text
tests/v2/test_feature_reconstruction_phase64.py + tests/v2/test_feature_reconstruction_phase65.py + tests/v2/test_feature_reconstruction_phase66.py + tests/v2/test_feature_reconstruction_phase67.py + tests/v2/test_feature_reconstruction_phase68.py: 34 passed
```

Baseline:

```text
compile src/tradingbotsuite: passed
tests/v2: 503 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- Added deterministic `CrossVenuePriceInputRow`,
  `CrossVenueBasisFeatureRow`, and `CrossVenueBasisFeatureReport` models for
  already-normalized price observations.
- Added cross-venue absolute and bps price-basis reconstruction against a
  requested primary venue while preserving primary/comparison venue, source,
  timestamp, source registry, and symbol-map metadata.
- Empty inputs, insufficient venue coverage, missing or duplicate primary
  prices, missing comparison prices, missing timestamps, mixed context, and bad
  prices fail closed.
- Cross-venue rows remain `external_comparison` only and never become
  Hyperliquid-native evidence.
- No collectors, downloads, archive writes, accepted coverage, gold panels,
  candidate-ready claims, paper/live/order/sizing/runtime, or promotion
  behavior were added.
