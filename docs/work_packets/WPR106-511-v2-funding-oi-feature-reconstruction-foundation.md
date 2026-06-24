# WPR106-511 - V2 Funding/OI Feature Reconstruction Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-039`

## Objective

Continue `DATA-015` by adding a research-only funding/open-interest context
feature reconstruction foundation. The helper consumes already-normalized
derivatives context rows, preserves source registry and symbol-map refs, and
emits deterministic feature rows for funding, open-interest, open-interest
statistics, and basis context.

This packet does not add collectors, download market data, write archive rows,
create accepted coverage, build gold panels, run backtests, create candidate
evidence, create candidate packs, add paper/live behavior, place orders, emit
sizing instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-511-v2-funding-oi-feature-reconstruction-foundation.md`
- `src/tradingbotsuite/v2/data_sources/feature_reconstruction.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_feature_reconstruction_phase65.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_feature_reconstruction_phase65.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse already-normalized derivatives context rows rather than fetching or
  parsing provider payloads.
- Keep native Hyperliquid and external-comparison context rows separated.
- Treat empty input, unsupported families, missing timestamps, missing numeric
  fields, non-finite numeric values, and mixed provenance as fail-closed
  blockers.
- Output rows are feature candidates for later gold panels, not gold panel rows
  themselves.

## Acceptance Criteria

- Funding/OI context feature rows preserve family, timestamp, numeric feature,
  unit, source, registry, and symbol-map metadata deterministically.
- Native and external rows carry the correct coverage label and remain
  non-promotable.
- Empty input, unsupported families, missing timestamps/numerics, non-finite
  numerics, and mixed provenance fail closed.
- Feature reports remain research-only, observe-only, non-promotable, and not
  accepted historical coverage proof.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/feature_reconstruction.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_feature_reconstruction_phase65.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-511-v2-funding-oi-feature-reconstruction-foundation.md`

## Validation Evidence

Focused:

```text
tests/v2/test_feature_reconstruction_phase64.py + tests/v2/test_feature_reconstruction_phase65.py: 13 passed
```

Baseline:

```text
compile src/tradingbotsuite: passed
tests/v2: 482 passed
tests/contracts: first attempt hit known Windows socketpair setup error after 462 passed; sequential rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- Added deterministic `DerivativesContextFeatureInputRow`,
  `DerivativesContextFeatureRow`, and `DerivativesContextFeatureReport` models
  for already-normalized derivatives context rows.
- Added funding, open-interest, open-interest-statistics, and basis feature
  reconstruction with family, timestamp, numeric feature, unit, source, source
  registry, and symbol-map metadata preserved.
- Empty inputs, unsupported families, missing timestamps, missing numeric
  fields, non-finite numeric values, and mixed provenance fail closed.
- No collectors, downloads, archive writes, accepted coverage, gold panels,
  candidate-ready claims, paper/live/order/sizing/runtime, or promotion
  behavior were added.
