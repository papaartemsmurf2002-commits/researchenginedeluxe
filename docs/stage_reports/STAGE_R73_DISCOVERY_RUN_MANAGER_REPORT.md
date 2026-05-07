# Stage R73 Discovery Run Manager Report

Date: 2026-05-07
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR73-01-discovery-run-manager.md`

## Scope

WPR73 implemented the V4 discovery run manager foundation only. It does not add
feature math, HMM materialization, KNN search, optimizer changes, UI changes,
promotion behavior, live execution, sizing, or order placement.

## Changes

- Added `src/tradingbotsuite/research_discovery/`:
  - `spec.py` parses bounded discovery specs, validates safe run IDs, resolves
    paths from the repo root, and enforces output isolation under the configured
    research output directory.
  - `runner.py` creates discovery output trees, writes resolved specs, run
    manifests, run state, placeholder immutable trial records, Parquet candidate
    ledgers, and snapshots.
  - `state.py` validates completed-trial immutability with per-record hashes and
    merges already-written records back into resumable state.
  - `snapshots.py` writes readable snapshot JSON files by temp-file then rename.
  - `manifests.py` records research-only, observe-only, promotion-not-ready run
    evidence.
- Added `configs/discovery/quick_smoke_btcusdt_v4.json` as a plumbing-only
  smoke discovery spec.
- Added `tests/research_discovery/` coverage for spec validation, path safety,
  state immutability, atomic snapshots, resume behavior, completed-run overwrite
  refusal, and placeholder ledgers.
- Extended `tests/contracts/test_import_boundaries.py` so
  `tradingbotsuite.research_discovery` is scanned for forbidden order-placement
  imports.

## Evidence

Generated discovery artifacts remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `candidate_pack_written: false`
- `order_placement_used: false`
- `runtime_mode_changed: false`

Completed trial records are immutable. Existing incomplete runs require
`resume=True`, changed specs require a new run ID, and completed runs refuse
overwrite.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

Results:

- Compile passed.
- Contracts passed: 368 passed.
- Discovery tests passed: 13 passed.
- `git diff --check` passed.

## Limitations

The run manager currently executes deterministic placeholder trials only. That
is intentional for WPR73. Later packets must add feature-column-set discovery,
split-safe HMM materialization, regime-local KNN studies, filter ablations,
exit labs, operator UI surfaces, and candidate-pack bridge behavior without
bypassing the existing research-only gates.
