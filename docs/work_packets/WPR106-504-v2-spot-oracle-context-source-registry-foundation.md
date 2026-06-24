# WPR106-504 - V2 Spot Oracle Context Source Registry Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-032`

## Objective

Start `DATA-013` by adding source-registry entries for spot, oracle, and
on-chain context sources before any context availability matrix, collector,
download, archive ingest, or coverage report is added.

This packet covers Coinbase spot, Kraken spot, Pyth Hermes, DefiLlama,
DexScreener, and GeckoTerminal source entries. It does not add collectors, run
network probes, download market data, write archive rows, create accepted
historical coverage proof, normalize venue data, run backtests, create
candidate evidence, create candidate packs, add paper/live behavior, place
orders, emit sizing instructions, change runtime mode, or make promotion
claims.

## Allowed Paths

- `docs/work_packets/WPR106-504-v2-spot-oracle-context-source-registry-foundation.md`
- `configs/data_sources/samples/source_registry_coinbase_spot_public.json`
- `configs/data_sources/samples/source_registry_kraken_spot_public.json`
- `configs/data_sources/samples/source_registry_pyth_hermes_public.json`
- `configs/data_sources/samples/source_registry_defillama_public.json`
- `configs/data_sources/samples/source_registry_dexscreener_public.json`
- `configs/data_sources/samples/source_registry_geckoterminal_public.json`
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
- No spot/oracle/on-chain network probes or generated market-data evidence.
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

- Add strict-free source samples for `coinbase_spot_public`,
  `kraken_spot_public`, `pyth_hermes_public`, `defillama_public`,
  `dexscreener_public`, and `geckoterminal_public`.
- Keep every entry `native_to_hyperliquid=false` and
  `accepted_historical_coverage_proof=false`.
- Label spot sources as external comparison and oracle/on-chain sources as
  spot/oracle context only.
- Require symbol-map or context-map refs, raw request/response refs, endpoint
  params, row counts, and rate-limit metadata before later collectors.

## Acceptance Criteria

- All six source entries validate as `SourceRegistryEntry` objects and pass
  `require_strict_zero_dollar_source()`.
- Tests prove they remain non-native and cannot be used as accepted historical
  coverage proof in this packet.

## Changed Files

- `configs/data_sources/samples/source_registry_coinbase_spot_public.json`
- `configs/data_sources/samples/source_registry_kraken_spot_public.json`
- `configs/data_sources/samples/source_registry_pyth_hermes_public.json`
- `configs/data_sources/samples/source_registry_defillama_public.json`
- `configs/data_sources/samples/source_registry_dexscreener_public.json`
- `configs/data_sources/samples/source_registry_geckoterminal_public.json`
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

Result: 17 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 451 passed; first `tests/contracts` attempt
hit the known Windows socketpair setup error after 462 passed; sequential
contract rerun passed with 463 passed. `git diff --check` passed with expected
LF-to-CRLF warnings only.

## Closeout Notes

This packet adds source registry foundation only. It does not add
spot/oracle/on-chain context availability matrices, collectors, API probes,
downloads, generated market-data evidence, archive writes, accepted historical
coverage proof, candidate evidence, candidate packs, paper/live behavior, order
placement, sizing instructions, runtime-mode changes, or promotion claims.
