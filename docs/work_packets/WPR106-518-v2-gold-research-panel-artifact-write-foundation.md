# WPR106-518 - V2 Gold Research Panel Artifact Write Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-046`

## Objective

Continue `DATA-017` by adding a local artifact-write foundation for completed
gold research panel assemblies. The helper writes flattened in-memory gold
panel rows to the archive `gold` layer through the existing Parquet writer,
records file-manifest evidence, and writes the assembly result JSON under
`manifests/gold_panels/`.

This packet does not add collectors, download market data, run backtests,
create candidate evidence, create candidate packs, add paper/live behavior,
place orders, emit sizing instructions, change runtime mode, or make promotion
claims.

## Allowed Paths

- `docs/work_packets/WPR106-518-v2-gold-research-panel-artifact-write-foundation.md`
- `src/tradingbotsuite/v2/data_sources/gold_panels.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/gold_research_panel_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_gold_research_panel_phase72.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No provider/API downloads, no real generated market-data artifacts, and no
  accepted historical coverage proof creation.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_gold_research_panel_phase72.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse `ArchiveLayout`, `ArchiveManifestStore`, and `write_parquet_rows`.
- Require a ready `GoldResearchPanelAssemblyResult`; blocked or empty assembly
  results must fail before writes.
- Flatten row values to top-level panel columns and emit coverage flags as
  `coverage_flag_<family>` columns.
- Write only under the supplied archive root using existing path policy.
- The write result is metadata/evidence only and remains research-only,
  observe-only, non-promotable, and not candidate or coverage evidence.

## Acceptance Criteria

- A ready assembly result writes one gold Parquet artifact plus one assembly
  JSON manifest under the archive root and returns deterministic refs/hashes.
- Blocked assembly results, empty row sets, and unsafe archive roots/paths fail
  closed.
- The write result remains research-only, observe-only, non-promotable, and not
  candidate or coverage evidence.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/gold_panels.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_gold_research_panel_phase72.py`
- `docs/contracts/gold_research_panel_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-518-v2-gold-research-panel-artifact-write-foundation.md`

## Validation Evidence

Focused:

```text
tests/v2/test_gold_research_panel_phase72.py: 5 passed
```

Baseline:

```text
compile src/tradingbotsuite: passed
tests/v2: 531 passed
tests/contracts: first attempt hit Windows socketpair WinError 10055 after 462 passed; rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- Added deterministic `GoldResearchPanelWriteResult` and
  `write_gold_research_panel_artifacts()`.
- Ready assemblies write flattened rows to the archive `gold` layer through the
  existing Parquet writer, update the file-manifest store, and write assembly
  JSON under `manifests/gold_panels/`.
- Blocked or empty assemblies, unsafe dataset/venue partitions, and duplicate
  writes fail closed.
- The packet performs no provider downloads and creates no accepted coverage
  evidence, candidate-ready claim, paper/live/order/sizing/runtime behavior, or
  promotion behavior.
