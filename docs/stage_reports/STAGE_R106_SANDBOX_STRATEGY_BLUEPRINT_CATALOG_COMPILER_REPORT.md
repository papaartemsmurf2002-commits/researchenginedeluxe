# Stage R106 Sandbox Strategy Blueprint Catalog Compiler Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-230-sandbox-strategy-blueprint-catalog-compiler.md`
Status: closed with local contract-suite environment caveat

## Summary

WPR106-230 extends the Rapid Strategy Iteration Sandbox so it can ingest more
than precomputed signal catalogs. Existing repo strategy JSON configs and
spreadsheet-like lead/catalog rows can now compile into deterministic
sandbox-only blueprint proxy strategies.

The compiler is intentionally bounded. It supports static built-in proxy
signals for completed-bar close momentum, range reversion, and volatility
breakout. It does not import external strategy code, create production strategy
plugins, alter historical-cycle gates, write candidate packs, or produce
promotion evidence.

## Implementation

- Added `src/tradingbotsuite/research_sandbox/strategy_blueprints.py`.
- Added deterministic signal-column generation for compiled proxy strategies.
- Added repo strategy config compilation for payloads shaped like
  `configs/strategies/*.json`.
- Added strategy-family matrix compilation for existing plugin-family payloads.
- Added spreadsheet-like lead table normalization for rows with columns such as
  `Packet`, `Lead`, `Candidate`, `Family`, `Template`, or `Next Check`.
- Preserved direct catalog behavior for rows already carrying
  `hypothesis_id`, `family`, and `signal_column`.
- Updated the fixed-hold sweep to materialize blueprint signals after the
  sandbox 2024+ market-window filter.
- Added result metadata for sandbox blueprint ID and proxy-signal status.
- Added a standard-library `.xlsx` reader fallback for spreadsheet-style lead
  intake when pandas cannot import an optional Excel engine such as
  `openpyxl`.
- Updated the sandbox research contract and active index.

## Boundary

All compiled rows remain sandbox-only descriptors. Result payloads and evidence
requests continue to carry:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `sandbox_only: true`
- `candidate_evidence: false`
- `candidate_pack_eligible: false`

Blueprint output can only request later strict validation. It cannot act as a
candidate pack, paper/live signal, sizing instruction, order instruction,
runtime-mode change, live configuration write, or promotion claim.

## Validation

Planned validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox -q
# 20 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

python -m compileall -q src\tradingbotsuite
# passed
```

Real-input smoke checks:

```powershell
$env:PYTHONPATH='src'; python -c "from tradingbotsuite.research_sandbox import load_strategy_catalog; rows=load_strategy_catalog('configs/strategies'); print(len(rows)); print(sorted({r.params.get('sandbox_blueprint_id') for r in rows})[:5])"
# 30 rows; close_momentum_proxy, range_reversion_proxy, volatility_breakout_proxy

$env:PYTHONPATH='src'; python -c "from tradingbotsuite.research_sandbox import load_strategy_catalog; p=r'outputs\019ed9da-c03f-7a01-ba1a-8a28806bc270\repo_research_performance_correlation_audit.xlsx'; rows=load_strategy_catalog(p); print(len(rows)); print(rows[0].family); print(rows[0].params.get('sandbox_blueprint_id'))"
# 17 rows; Excel fallback path works without openpyxl
```

Contract baseline:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

The full contract baseline passed once before the `.xlsx` fallback edit with
461 tests. After the fallback edit, repeated contract attempts reached 460
passed tests and failed only during asyncio event-loop fixture setup for
`test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest`
with Windows `WinError 10055` socket-buffer/resource exhaustion, before that
test body executed. The same setup failure reproduced under the Windows
selector event-loop policy and after a delayed retry. No sandbox assertion or
contract assertion failed in the post-fallback runs.

## Remaining Work

This packet does not yet add richer exit blueprint grids, multi-venue manifest
normalization beyond local data files, direct strict-cycle request execution,
or analytics/query surfaces over sandbox Parquet. Those remain separate
follow-up packets under the active sandbox objective.
