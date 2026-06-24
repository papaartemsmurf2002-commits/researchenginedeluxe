# WPR106-517 - V2 Gold Research Panel Row Assembly Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-045`

## Objective

Continue `DATA-017` by adding an in-memory gold research panel row assembly
foundation. The helper consumes a ready `GoldResearchPanelManifest` plus
timestamped feature-column values and returns deterministic row/report metadata
for complete or explicitly blocked panel assembly.

This packet does not add collectors, download market data, write archive rows,
write gold panel data files, run backtests, create candidate evidence, create
candidate packs, add paper/live behavior, place orders, emit sizing
instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-517-v2-gold-research-panel-row-assembly-foundation.md`
- `src/tradingbotsuite/v2/data_sources/gold_panels.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/gold_research_panel_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_gold_research_panel_phase71.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No archive data downloads, generated market-data row writes, accepted
  historical coverage proof creation, data mutation, or gold panel file writes.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_gold_research_panel_phase71.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse ready `GoldResearchPanelManifest` output from WPR106-516.
- Assemble rows in memory only; no archive or gold file writes.
- Row identity must include panel ID, symbol, interval, timestamp, feature
  values, coverage flags, and source row hashes.
- Complete rows pass only when every non-nullable manifest feature ref has a
  value for the timestamp.
- Nullable feature refs may be absent for a timestamp, but the row must retain
  the column with a `null` value and family coverage flags must reflect that
  row-level missingness.

## Acceptance Criteria

- Complete timestamped feature values produce deterministic
  `GoldResearchPanelRow` output and a ready assembly result.
- Blocked manifests, empty input rows, duplicate column/timestamp pairs, missing
  non-nullable values, and unknown/mismatched feature metadata fail closed.
- Row and assembly result objects remain research-only, observe-only,
  non-promotable, and not candidate or coverage evidence.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/gold_panels.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_gold_research_panel_phase71.py`
- `docs/contracts/gold_research_panel_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-517-v2-gold-research-panel-row-assembly-foundation.md`

## Validation Evidence

Focused:

```text
tests/v2/test_gold_research_panel_phase71.py: 8 passed
```

Baseline:

```text
compile src/tradingbotsuite: passed
tests/v2: 526 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- Added deterministic `GoldResearchPanelInputValue`,
  `GoldResearchPanelRow`, `GoldResearchPanelAssemblyResult`, and
  `assemble_gold_research_panel_rows()`.
- Complete timestamped feature values assemble to stable in-memory panel rows
  with row-level coverage flags, source row hashes, and row hashes.
- Blocked manifests, empty inputs, duplicate column/timestamp pairs, missing
  non-nullable values, unknown columns, and feature-report mismatches fail
  closed.
- The packet writes no gold panel files and creates no accepted coverage
  evidence, candidate-ready claim, paper/live/order/sizing/runtime behavior, or
  promotion behavior.
