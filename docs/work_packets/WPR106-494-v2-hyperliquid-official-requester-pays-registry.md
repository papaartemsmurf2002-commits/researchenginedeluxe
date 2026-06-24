# WPR106-494 - V2 Hyperliquid Official Requester-Pays Registry

Status: closed
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-022`

## Objective

Close the `DATA-009` requester-pays official archive source-registry gate by
registering the missing quarantined Hyperliquid official S3/source families and
proving strict-zero-dollar validation rejects every official requester-pays
source before download or archive intake.

This packet does not enable S3 downloads, relax strict-zero-dollar mode,
request operator transfer acknowledgement, ingest official files, run coverage
audits, run backtests, create accepted historical coverage proof, create
candidate evidence, create candidate packs, add paper/live behavior, place
orders, emit sizing instructions, change runtime mode, or make promotion
claims.

## Allowed Paths

- `docs/work_packets/WPR106-494-v2-hyperliquid-official-requester-pays-registry.md`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_l2_book.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_asset_ctxs.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_node_fills.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_node_trades.json`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_data_source_registry_phase37.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No S3/network download implementation or generated official archive evidence.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_source_registry_phase37.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add missing requester-pays source entries for:
  - `hyperliquid_official_s3_l2_book`;
  - `hyperliquid_official_s3_asset_ctxs`;
  - `hyperliquid_official_s3_node_fills`;
  - `hyperliquid_official_s3_node_trades`.
- Keep the existing `hyperliquid_official_s3_node_fills_by_block` entry
  quarantined.
- Require `public_requester_pays_transfer`, `strict_zero_dollar_allowed=false`,
  `accepted_under_strict_free=false`, and explicit operator gates.

## Acceptance Criteria

- All five official requester-pays source IDs validate as `SourceRegistryEntry`
  objects.
- All five fail `require_strict_zero_dollar_source()` with a strict-free
  rejection.
- Tests prove none can claim accepted historical coverage proof or strict-free
  acceptance.

## Changed Files

- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_l2_book.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_asset_ctxs.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_node_fills.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_s3_node_trades.json`
- `tests/v2/test_data_source_registry_phase37.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`

## Validation Evidence

```text
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_source_registry_phase37.py -q
13 passed

$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
passed

$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
420 passed

$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
463 passed

git diff --check
passed with existing LF-to-CRLF warnings only
```

## Closeout Notes

WPR106-494 registers the complete quarantined Hyperliquid official
requester-pays source set for L2 book, asset contexts, node fills by block,
node fills, and node trades. All five official source IDs validate as native
Hyperliquid requester-pays sources, fail strict-zero-dollar mode, require
operator gates, and cannot claim accepted historical coverage proof. No S3
download, strict-free relaxation, official-file ingest, coverage audit,
accepted evidence, candidate evidence, paper/live behavior, order placement,
sizing, runtime-mode change, or promotion claim was added.
