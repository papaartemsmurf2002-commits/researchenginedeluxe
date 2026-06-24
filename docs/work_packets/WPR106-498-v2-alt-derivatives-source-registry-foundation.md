# WPR106-498 - V2 Alt Derivatives Source Registry Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-026`

## Objective

Start `DATA-011` by adding source-registry entries for MEXC, Bitget, Gate,
KuCoin, and HTX public derivatives market data before any external gap-filler
collector or probe is added.

This packet does not add collectors, run API probes, download market data,
write archive rows, create availability matrices, run backtests, create
accepted historical coverage proof, create candidate evidence, create
candidate packs, add paper/live behavior, place orders, emit sizing
instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-498-v2-alt-derivatives-source-registry-foundation.md`
- `configs/data_sources/samples/source_registry_bitget_public_mix_market.json`
- `configs/data_sources/samples/source_registry_mexc_contract_public.json`
- `configs/data_sources/samples/source_registry_gate_futures_public.json`
- `configs/data_sources/samples/source_registry_kucoin_futures_public.json`
- `configs/data_sources/samples/source_registry_htx_swap_public.json`
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
- No MEXC/Bitget/Gate/KuCoin/HTX network probes or generated external
  market-data evidence.
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

- Add strict-free-allowed `public_rate_limited` source samples for the five
  DATA-011 complementary derivative venues.
- Keep every entry `native_to_hyperliquid=false`,
  `research_role=external_comparison`, and
  `accepted_historical_coverage_proof=false`.
- Record symbol-map, endpoint-limit, pagination, availability-matrix, and raw
  request/response prerequisites for later collectors.

## Acceptance Criteria

- The five source entries validate as `SourceRegistryEntry` objects and pass
  `require_strict_zero_dollar_source()`.
- Tests prove they remain external comparison sources and cannot be used as
  Hyperliquid-native or accepted historical coverage proof.

## Changed Files

- `configs/data_sources/samples/source_registry_bitget_public_mix_market.json`
- `configs/data_sources/samples/source_registry_mexc_contract_public.json`
- `configs/data_sources/samples/source_registry_gate_futures_public.json`
- `configs/data_sources/samples/source_registry_kucoin_futures_public.json`
- `configs/data_sources/samples/source_registry_htx_swap_public.json`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_data_source_registry_phase37.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_source_registry_phase37.py -q
```

Result: 15 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 432 passed; `tests/contracts` 463 passed;
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds registry foundation only. It does not add MEXC, Bitget, Gate,
KuCoin, or HTX collectors, API probes, downloads, generated market-data
evidence, archive writes, availability matrices, accepted historical coverage
proof, candidate evidence, candidate packs, paper/live behavior, order
placement, sizing instructions, runtime-mode changes, or promotion claims.
