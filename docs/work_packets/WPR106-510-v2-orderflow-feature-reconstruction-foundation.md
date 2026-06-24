# WPR106-510 - V2 Orderflow Feature Reconstruction Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-038`

## Objective

Start `DATA-015` by adding a research-only orderflow feature reconstruction
foundation. The helper consumes already-normalized trade-like rows, buckets
them by interval, and emits VWAP, buy/sell/unknown volume, quote-volume, trade
count, and flow-imbalance features with source registry and symbol-map refs.

This packet does not add collectors, download market data, write archive rows,
create accepted coverage, build gold panels, run backtests, create candidate
evidence, create candidate packs, add paper/live behavior, place orders, emit
sizing instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-510-v2-orderflow-feature-reconstruction-foundation.md`
- `src/tradingbotsuite/v2/data_sources/feature_reconstruction.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_feature_reconstruction_phase64.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_feature_reconstruction_phase64.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse the generic `TradeBarInputRow` shape from DATA-014 rather than adding a
  second trade input contract.
- Keep native Hyperliquid and external-comparison orderflow separated.
- Treat empty input and missing side information as explicit blocker metadata.
- Output rows are feature candidates for later gold panels, not gold panel
  rows themselves.

## Acceptance Criteria

- Bucketed orderflow features compute VWAP, buy/sell/unknown volume, quote
  volume, trade count, and imbalance deterministically.
- Native and external rows carry the correct coverage label and remain
  non-promotable.
- Empty inputs and mixed native/external provenance fail closed.
- Feature reports remain research-only, observe-only, non-promotable, and not
  accepted historical coverage proof.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/feature_reconstruction.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_feature_reconstruction_phase64.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-510-v2-orderflow-feature-reconstruction-foundation.md`

## Validation Evidence

Focused:

```text
tests/v2/test_feature_reconstruction_phase64.py: 6 passed
```

Baseline:

```text
compile src/tradingbotsuite: passed
tests/v2: 475 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- Added deterministic `OrderflowFeatureRow` and `OrderflowFeatureReport`
  models for already-normalized trade rows.
- Added bucketed VWAP, buy/sell/unknown volume, quote volume, trade count,
  imbalance, missing-side blocker, and zero-volume fail-closed behavior.
- Native Hyperliquid and external-comparison rows remain separated.
- No collectors, downloads, archive writes, accepted coverage, gold panels,
  candidate-ready claims, paper/live/order/sizing/runtime, or promotion
  behavior were added.
