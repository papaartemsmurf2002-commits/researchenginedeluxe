# WPR106-512 - V2 BBO Spread Feature Reconstruction Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-040`

## Objective

Continue `DATA-015` by adding a research-only BBO spread feature reconstruction
foundation. The helper consumes already-normalized best-bid/offer event rows,
preserves source registry and symbol-map refs, and emits deterministic spread,
mid-price, and top-of-book size imbalance features.

This packet does not add collectors, download market data, write archive rows,
create accepted coverage, build gold panels, run backtests, create candidate
evidence, create candidate packs, add paper/live behavior, place orders, emit
sizing instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-512-v2-bbo-spread-feature-reconstruction-foundation.md`
- `src/tradingbotsuite/v2/data_sources/feature_reconstruction.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_feature_reconstruction_phase66.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_feature_reconstruction_phase66.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse already-normalized BBO event rows rather than opening streams or
  touching archive collectors.
- Keep native Hyperliquid and external-comparison BBO rows separated.
- Treat empty input, missing timestamps, missing top-of-book sizes, crossed
  books, zero/negative prices, and mixed provenance as fail-closed blockers.
- Output rows are feature candidates for later gold panels, not gold panel rows
  themselves.

## Acceptance Criteria

- BBO feature rows compute mid price, absolute spread, spread bps, and optional
  top-of-book size imbalance deterministically.
- Native and external rows carry the correct coverage label and remain
  non-promotable.
- Empty input, malformed BBO rows, missing timestamps, missing sizes, and mixed
  provenance fail closed.
- Feature reports remain research-only, observe-only, non-promotable, and not
  accepted historical coverage proof.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/feature_reconstruction.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_feature_reconstruction_phase66.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-512-v2-bbo-spread-feature-reconstruction-foundation.md`

## Validation Evidence

Focused:

```text
tests/v2/test_feature_reconstruction_phase64.py + tests/v2/test_feature_reconstruction_phase65.py + tests/v2/test_feature_reconstruction_phase66.py: 20 passed
```

Baseline:

```text
compile src/tradingbotsuite: passed
tests/v2: 489 passed
tests/contracts: first attempt hit known Windows socketpair setup error after 462 passed; sequential rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- Added deterministic `BBOFeatureInputRow`, `BBOFeatureRow`, and
  `BBOFeatureReport` models for already-normalized BBO rows.
- Added mid price, absolute spread, spread-bps, and top-of-book size imbalance
  reconstruction with source, timestamp, sequence, source registry, and
  symbol-map metadata preserved.
- Empty inputs, missing timestamps, missing top-of-book sizes, crossed books,
  bad prices, and mixed provenance fail closed.
- No collectors, downloads, archive writes, accepted coverage, gold panels,
  candidate-ready claims, paper/live/order/sizing/runtime, or promotion
  behavior were added.
