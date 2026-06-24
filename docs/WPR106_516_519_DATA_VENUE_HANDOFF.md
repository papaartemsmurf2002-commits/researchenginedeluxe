# WPR106-516 Through WPR106-519 Data Venue Handoff

Date: 2026-06-24
Author: Codex Research Agent
Scope: v2 Hyperliquid data-venue roadmap continuation

## What Was Done

I continued from the Git-visible roadmap:

- `docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`

The work completed the next foundation slices after `WPR106-515`:

- `WPR106-516` - gold research panel manifest foundation
- `WPR106-517` - gold research panel in-memory row assembly foundation
- `WPR106-518` - gold research panel archive artifact-write foundation
- `WPR106-519` - v2 data-venue runbook and operator docs

These packets are foundation work only. They do not prove full accepted
historical coverage, do not create candidate-ready evidence, and do not add
paper/live/order/sizing/runtime/promotion behavior.

## Code Added

Primary implementation:

- `src/tradingbotsuite/v2/data_sources/gold_panels.py`

New exported models and helpers:

- `GoldResearchPanelFeatureRef`
- `GoldResearchPanelManifest`
- `build_gold_research_panel_manifest`
- `GoldResearchPanelInputValue`
- `GoldResearchPanelRow`
- `GoldResearchPanelAssemblyResult`
- `assemble_gold_research_panel_rows`
- `GoldResearchPanelWriteResult`
- `write_gold_research_panel_artifacts`

The helper flow is:

1. Build a metadata-only gold panel manifest from a passed
   `DataFamilyCoverageGateResult` and feature refs.
2. Assemble timestamped feature values into deterministic in-memory gold panel
   rows with row-level coverage flags and source row hashes.
3. Write ready assemblies to the archive `gold` layer through the existing
   Parquet writer, record file-manifest evidence, and write assembly JSON under
   `manifests/gold_panels/`.

Fail-closed behavior was added for blocked gates, missing archive refs, empty
feature refs, uncovered families, blocked feature refs, blocked assemblies,
duplicate column/timestamp pairs, missing non-nullable values, unsafe
partitions, and duplicate artifact writes.

## Tests Added

Focused tests:

- `tests/v2/test_gold_research_panel_phase70.py`
- `tests/v2/test_gold_research_panel_phase71.py`
- `tests/v2/test_gold_research_panel_phase72.py`

Coverage intent:

- Phase 70 tests manifest identity, passed/blocked coverage gates, missing
  refs, missing feature families, uncovered feature families, and boundary
  validation.
- Phase 71 tests timestamped row assembly, nullable feature values,
  non-nullable missing-value blockers, duplicate input blockers, unready
  manifests, metadata mismatches, and boundary validation.
- Phase 72 tests root-contained artifact writes to the archive `gold` layer,
  assembly JSON writes, file-manifest evidence, unsafe partition rejection,
  duplicate write rejection, blocked assembly rejection, and boundary
  validation.

## Docs Added Or Updated

New contract:

- `docs/contracts/gold_research_panel_contract.md`

New runbook:

- `docs/runbooks/v2_hyperliquid_data_venue_runbook.md`

Closed work packets:

- `docs/work_packets/WPR106-516-v2-gold-research-panel-manifest-foundation.md`
- `docs/work_packets/WPR106-517-v2-gold-research-panel-row-assembly-foundation.md`
- `docs/work_packets/WPR106-518-v2-gold-research-panel-artifact-write-foundation.md`
- `docs/work_packets/WPR106-519-v2-data-venue-runbook-and-operator-docs.md`

Control docs updated:

- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`

New audit IDs:

- `V2-AUD-DATASRC-044`
- `V2-AUD-DATASRC-045`
- `V2-AUD-DATASRC-046`
- `V2-AUD-DATASRC-047`

## Validation

Latest focused validation:

```text
tests/v2/test_gold_research_panel_phase70.py: 8 passed
tests/v2/test_gold_research_panel_phase71.py: 8 passed
tests/v2/test_gold_research_panel_phase72.py: 5 passed
```

Latest baseline validation after WPR106-519:

```text
compile src/tradingbotsuite: passed
tests/v2: 531 passed
tests/contracts: first attempt hit Windows socketpair WinError 10055 after 462 passed; rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

The Windows socketpair failure is an intermittent local resource issue already
seen in earlier packets. The rerun passed cleanly.

## Current Boundary

All new models preserve the canonical v2 boundary:

```json
{
  "research_only": true,
  "observe_only": true,
  "promotion_ready": false,
  "candidate_evidence": false,
  "candidate_pack_eligible": false,
  "live_signal": false,
  "paper_signal": false,
  "sizing_instruction": false,
  "order_placement_instruction": false,
  "runtime_mode_change": false
}
```

Gold panels are research artifacts only. They are not accepted historical
coverage proof by themselves, not candidate-pack evidence, and not promotion
evidence.

## Remaining Gaps

The roadmap foundation through `DATA-018` is now implemented, but the broader
goal is not complete as accepted operational evidence.

Important remaining gaps:

- Real historical as-of Hyperliquid universe snapshots still need to be
  produced and accepted beyond current-public diagnostic evidence.
- Full family-specific accepted coverage is still missing for the full target
  universe and window.
- The generic coverage gate exists, but broader multi-symbol/multi-family
  gate aggregation is not yet implemented.
- Feature reconstruction helpers exist, but there is not yet an end-to-end
  materializer that reads actual archive feature outputs and builds production
  research gold panels across symbols/windows.
- Hyperliquid official requester-pays archives remain quarantined under
  strict-zero-dollar mode.
- Broad unattended backfill scheduling remains out of scope.

## Recommended Next Step

I think the next agent should start `WPR106-520` as a narrow operational bridge:

**Build a multi-symbol data-family coverage aggregation and gold-panel
materializer preflight over existing archive refs.**

Concretely:

1. Consume existing `DataFamilyCoverageReport` refs for a declared universe,
   symbol set, and time window.
2. Produce a deterministic per-symbol required-family gate summary using
   `evaluate_data_family_coverage_gate()`.
3. For symbols that pass, map available feature reconstruction reports into
   `GoldResearchPanelFeatureRef` objects.
4. Build `GoldResearchPanelManifest` objects.
5. Do not write gold rows yet unless the packet explicitly proves row-value
   inputs are complete and root-contained.

This is the right next step because gold panel writing now has the mechanics,
but it still needs a disciplined bridge from real coverage reports and feature
reports. Starting with aggregation/preflight avoids pretending the archive has
accepted family coverage where it does not.

Suggested first packet name:

```text
WPR106-520-v2-multi-symbol-coverage-gold-panel-preflight.md
```

Suggested focused test:

```text
tests/v2/test_gold_research_panel_preflight_phase73.py
```

Keep the packet research-only, strict-free, no live imports, no requester-pays
official sources, no candidate-pack writes, and no promotion claims.
