# WPR106-520 - V2 Multi-Symbol Coverage Gold-Panel Preflight

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-048`

## Objective

Add the narrow operational bridge recommended by the WPR106-516 through
WPR106-519 handoff: aggregate existing `DataFamilyCoverageReport` objects across
declared symbols, evaluate per-symbol required-family gates with
`evaluate_data_family_coverage_gate()`, and map accepted feature reconstruction
reports into `GoldResearchPanelFeatureRef` objects before building
`GoldResearchPanelManifest` preflight results.

This packet does not add collectors, download market data, write archive rows,
write gold panel row files, run backtests, create candidate evidence, create
candidate packs, add paper/live behavior, place orders, emit sizing
instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-520-v2-multi-symbol-coverage-gold-panel-preflight.md`
- `src/tradingbotsuite/v2/data_sources/gold_panel_preflight.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/contracts/gold_research_panel_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_gold_research_panel_preflight_phase73.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No provider/API downloads, no generated market-data artifacts, no accepted
  historical coverage proof creation, and no gold panel file writes.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_gold_research_panel_preflight_phase73.py -q
```

Baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Consume already-built `DataFamilyCoverageReport` objects only.
- Require a declared, sorted, unique symbol set and explicit required-family
  set.
- Call `evaluate_data_family_coverage_gate()` independently for each symbol.
- Treat feature reconstruction reports as usable only when they have rows,
  carry no blocker reasons, match the declared source-registry and symbol-map
  refs, and match the target symbol.
- Map feature report outputs into deterministic `GoldResearchPanelFeatureRef`
  records without claiming accepted coverage proof.
- Build one `GoldResearchPanelManifest` per declared symbol and retain blocker
  reasons when coverage or feature refs are incomplete.

## Acceptance Criteria

- Multi-symbol coverage aggregation returns deterministic per-symbol summaries.
- Per-symbol summaries expose gate IDs, report IDs, accepted family report IDs,
  missing families, rejected families, and blocker reasons.
- Accepted feature reconstruction reports are converted into feature refs with
  stable column names, family labels, source refs, row counts, row-manifest
  hashes, and coverage-flag columns.
- Symbols missing required coverage or accepted feature reports produce blocked
  preflight manifests rather than hidden gaps.
- All outputs preserve the canonical v2 research-only invariant and remain
  non-promotable, not candidate evidence, not candidate-pack eligible, not
  paper/live signals, not sizing/order instructions, and not runtime changes.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/gold_panel_preflight.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_gold_research_panel_preflight_phase73.py`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/contracts/gold_research_panel_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/work_packets/WPR106-520-v2-multi-symbol-coverage-gold-panel-preflight.md`

## Validation Evidence

Focused:

```text
tests/v2/test_gold_research_panel_preflight_phase73.py: 5 passed
```

Baseline:

```text
python -m compileall -q src/tradingbotsuite: passed
PYTHONPATH=src python -m pytest tests/v2 -q: 536 passed
PYTHONPATH=src python -m pytest tests/contracts -q: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

## Closeout Notes

- The packet implements the WPR106-520 bridge only: multi-symbol coverage
  summaries, per-symbol gate summaries, feature-report-to-feature-ref mapping,
  and per-symbol gold-panel manifest preflight results.
- No row-value materializer, provider fetch, archive write, gold panel file
  write, accepted coverage proof, bounded agent cycle wiring, candidate
  evidence, paper/live signal, sizing/order instruction, runtime change, or
  promotion behavior was added.
- The next packet should decide whether complete row-value inputs and accepted
  gates are available for an end-to-end materializer, or emit blocker manifests
  naming the missing row-value and accepted-coverage evidence.
