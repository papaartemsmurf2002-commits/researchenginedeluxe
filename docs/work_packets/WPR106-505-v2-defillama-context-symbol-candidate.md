# WPR106-505 - V2 DefiLlama Context Symbol Candidate

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-033`

## Objective

Continue `DATA-013` by adding a deterministic, unverified DefiLlama context
candidate to the symbol-map resolver so later context availability matrices can
fail closed on explicit mapping status rather than ad hoc side mappings.

This packet does not add source entries, collectors, run network probes,
download market data, write archive rows, create accepted historical coverage
proof, normalize venue data, run backtests, create candidate evidence, create
candidate packs, add paper/live behavior, place orders, emit sizing
instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-505-v2-defillama-context-symbol-candidate.md`
- `src/tradingbotsuite/v2/data_sources/symbol_resolver.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_symbol_map_resolver_phase38.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No DefiLlama network probes or generated market-data evidence.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_symbol_map_resolver_phase38.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add `defillama_context` to deterministic candidate generation with context
  market type.
- Candidate generation remains non-verifying. Only explicit probe evidence can
  mark a DefiLlama mapping verified.

## Acceptance Criteria

- Resolver tests include `defillama_context`.
- Unprobed DefiLlama context candidates remain `not_checked` and therefore
  blocked by `require_verified_external_mapping()` until later evidence exists.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/symbol_resolver.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_symbol_map_resolver_phase38.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_symbol_map_resolver_phase38.py -q
```

Result: 7 passed.

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

This packet adds a deterministic DefiLlama context candidate only. It does not
add source entries, availability matrices, collectors, API probes, downloads,
generated market-data evidence, archive writes, accepted historical coverage
proof, candidate evidence, candidate packs, paper/live behavior, order
placement, sizing instructions, runtime-mode changes, or promotion claims.
