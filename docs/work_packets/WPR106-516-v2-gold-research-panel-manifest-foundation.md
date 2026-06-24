# WPR106-516 - V2 Gold Research Panel Manifest Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-044`

## Objective

Start `DATA-017` by adding a research-only gold research panel manifest
foundation. The helper consumes a passed `DataFamilyCoverageGateResult` plus
feature report references and emits deterministic metadata for a future gold
panel without writing panel rows or creating accepted coverage evidence.

This packet does not add collectors, download market data, write archive rows,
write gold panel data files, run backtests, create candidate evidence, create
candidate packs, add paper/live behavior, place orders, emit sizing
instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-516-v2-gold-research-panel-manifest-foundation.md`
- `src/tradingbotsuite/v2/data_sources/gold_panels.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/gold_research_panel_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_gold_research_panel_phase70.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No archive data downloads, generated market-data rows, accepted historical
  coverage proof creation, data mutation, or gold panel row writes.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_gold_research_panel_phase70.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse `DataFamilyCoverageGateResult` instead of inventing a separate
  coverage acceptance path.
- Emit manifest metadata only: refs, feature refs, row counts, hashes, required
  families, and blocker reasons.
- Fail closed when the coverage gate is blocked, when required refs are missing,
  when feature refs are empty, when feature families are not covered by the gate,
  or when any supplied metadata violates the v2 research boundary.
- Preserve nullable/missing-family visibility through explicit feature coverage
  flags rather than hiding absent data.

## Acceptance Criteria

- A passed coverage gate plus valid refs and feature refs produces a
  deterministic `GoldResearchPanelManifest` with source, universe, symbol-map,
  archive, coverage-gate, and feature refs.
- Blocked coverage gates, missing refs, empty feature refs, uncovered feature
  families, and boundary flag violations fail closed.
- The manifest remains research-only, observe-only, non-promotable, and not
  candidate or coverage evidence.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/gold_panels.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_gold_research_panel_phase70.py`
- `docs/contracts/gold_research_panel_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-516-v2-gold-research-panel-manifest-foundation.md`

## Validation Evidence

Focused:

```text
tests/v2/test_gold_research_panel_phase70.py: 8 passed
```

Baseline:

```text
compile src/tradingbotsuite: passed
tests/v2: 518 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- Added deterministic `GoldResearchPanelFeatureRef`,
  `GoldResearchPanelManifest`, and `build_gold_research_panel_manifest()`.
- Ready manifests require a passed data-family coverage gate, archive ref,
  coverage report refs, and valid feature refs for every required family.
- Blocked gates, missing archive refs, empty feature refs, missing required
  feature families, uncovered feature families, blocked or empty feature refs,
  and mismatched ref context fail closed.
- The packet writes no gold panel rows and creates no accepted coverage
  evidence, candidate-ready claim, paper/live/order/sizing/runtime behavior, or
  promotion behavior.
