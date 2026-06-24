# WPR106-521 - V2 Gold Panel Materializer

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-049`

## Objective

Add a narrow all-or-nothing gold research panel materializer over the
WPR106-520 preflight output. The helper consumes a ready
`GoldPanelPreflightResult` plus explicit per-symbol
`GoldResearchPanelInputValue` rows, assembles each symbol with the existing
row assembler, and writes gold-layer archive artifacts only when every declared
symbol is ready and every row-value set assembles cleanly.

This packet does not add collectors, download market data, infer row values
from provider files, create backtest data manifests, run backtests, enqueue or
run bounded agent cycles, create candidate evidence, create candidate packs,
add paper/live behavior, place orders, emit sizing instructions, change
runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-521-v2-gold-panel-materializer.md`
- `src/tradingbotsuite/v2/data_sources/gold_panel_materializer.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/gold_research_panel_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_gold_research_panel_materializer_phase74.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior, provider/API downloads, or source archive intake.
- No backtest data service, bounded-cycle planner, durable worker runner, CLI,
  ledger, Lead Book, validation gate, or audit worker changes in this packet.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_gold_research_panel_materializer_phase74.py -q
```

Baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Consume `GoldPanelPreflightResult` objects already accepted by the
  WPR106-520 preflight; do not rebuild coverage or feature reports.
- Require explicit per-symbol row-value inputs keyed by declared symbol.
- Use `assemble_gold_research_panel_rows()` for row construction and
  `write_gold_research_panel_artifacts()` for archive writes.
- Do not write any symbol if any declared symbol has a blocked preflight
  result, missing row values, assembly blockers, or missing source row hashes.
- Return deterministic materializer result objects with assembly IDs, optional
  write IDs, row counts, artifact refs, and explicit blockers.

## Acceptance Criteria

- Ready multi-symbol preflight plus complete row-value inputs writes one
  gold-layer artifact per declared symbol and records write results.
- Blocked preflight, missing symbol inputs, incomplete row values, duplicate
  column/timestamp values, unknown input symbols, and missing source row hashes
  fail closed before any gold archive write.
- Materializer outputs preserve canonical v2 research-only invariants and
  remain non-promotable, not candidate evidence, not candidate-pack eligible,
  not paper/live signals, not sizing/order instructions, and not runtime
  changes.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/gold_panel_materializer.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_gold_research_panel_materializer_phase74.py`
- `docs/contracts/gold_research_panel_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-521-v2-gold-panel-materializer.md`

## Validation Evidence

Focused:

```text
tests/v2/test_gold_research_panel_materializer_phase74.py: 5 passed
```

Baseline:

```text
python -m compileall -q src/tradingbotsuite: passed
PYTHONPATH=src python -m pytest tests/v2 -q: 541 passed
PYTHONPATH=src python -m pytest tests/contracts -q: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- The packet implements the gold-panel materializer bridge only: ready
  preflight output plus explicit per-symbol row-value inputs can produce
  gold-layer archive artifacts through the existing writer.
- The materializer is all-or-nothing across declared symbols. Blocked
  preflights, missing inputs, incomplete values, duplicate column/timestamp
  values, unknown input symbols, and missing source row hashes produce blocker
  metadata and no gold writes.
- No backtest-data consumption of gold refs, bounded-cycle wiring, provider
  fetch, accepted coverage proof, candidate evidence, paper/live signal,
  sizing/order instruction, runtime change, or promotion behavior was added.
