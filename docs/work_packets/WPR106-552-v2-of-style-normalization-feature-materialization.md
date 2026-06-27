# WPR106-552 V2 OF-Style Normalization Feature Materialization

Status: complete
Owner: Codex Research Agent
Date opened: 2026-06-27

## Goal

Add and run a fast, research-only materialization pass for the authoritative
strict-free OF-style archive. The pass must turn the WPR106-549 validated raw
archive into audit-digestible normalized feature metadata and compact feature
outputs where local runtime permits, without expanding the full external raw
archive into central row-level storage.

The intended result is pragmatic: final audit agents get exact pointers to the
validated raw archive, normalized project bar baseline, materialized feature
outputs, and any remaining compute-only follow-up. Legacy uncollectable
Hyperliquid-native history is not a blocker for this packet.

## Allowed paths

- `docs/work_packets/WPR106-552-v2-of-style-normalization-feature-materialization.md`
- `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_of_style_materialization_phase78.py`
- `data/research/of_style_feature_materialization/wpr106_552/**`
- `docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md`
- `docs/v2_visibility_snapshot_wpr106_552.json`
- `docs/index.html`
- `README.md`
- `START_HERE.md`
- `docs/ACTIVE_INDEX.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`

## Out of scope

- No paid/requester-pays provider work and no mutation of the external
  `M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw`
  archive.
- No strategy execution, candidate-pack writes, paper/live/order/sizing/runtime
  behavior, or promotion claims.
- No claim that derived features are trading signals. All generated feature
  artifacts remain `research_only`, `observe_only`, and
  `promotion_ready: false`.

## Plan

1. Inspect validated archive manifests, sample source schemas, and existing
   feature reconstruction contracts.
2. Add a deterministic OF-style materializer that streams ZIP/CSV sources into
   compact normalized feature rows and an audit report.
3. Cover the materializer with focused synthetic ZIP tests for orderflow,
   top-of-book, depth, derivatives context, and kline-context handling.
4. Run the materializer against the WPR106-549 archive in a fast bounded pass,
   preserving full archive authority by linking back to the validation report.
5. Update the data catalog, roadmap, audit index, stage ledger, static page, and
   packet validation notes.

## Boundary

Every generated report preserves:

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

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_of_style_materialization_phase78.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_ui_visibility_phase22.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomous_readiness_audit_phase29.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_central_market_history_store_phase76.py tests\v2\test_central_market_history_collection_phase77.py -q
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main ui render --input-root docs --snapshot-json v2_visibility_snapshot_wpr106_552.json --output-root docs --output-html index.html
git diff --check
```

Results:

- compile passed;
- OF-style materialization tests: 2 passed;
- UI visibility tests: 13 passed;
- autonomous readiness regression tests: 8 passed;
- contracts baseline: 463 passed;
- central market-history focused tests: 21 passed;
- WPR106-552 snapshot validates through `snapshot_from_json`;
- `docs/index.html` rendered from `docs/v2_visibility_snapshot_wpr106_552.json`;
- rendered HTML contains no `<script`, `<form`, `<button`, `onclick`, or
  `href=` controls;
- generated materialization report validates as
  `OFStyleMaterializationReport`;
- generated materialization report SHA sidecar matches;
- WPR106-552 output `.part` scan: 0;
- `git diff --check` passed with only existing LF-to-CRLF warnings.

Materialization run:

- report:
  `data/research/of_style_feature_materialization/wpr106_552/manifests/wpr106-552-of-style-feature-materialization-report.json`;
- archive linked:
  `M:\additional_archive\researchenginedeluxe\wpr106_549_of_style_raw\manifests\wpr106-549-heavy-raw-archive-validation-report.json`;
- archive sources linked: 1,159,478 complete / 1,159,478 total;
- materialized source files: 251;
- blocked source files: 0;
- parsed input rows: 81,093,159;
- materialized feature rows: 256,523;
- emitted feature JSONL files: 251;
- emitted feature SHA-256 sidecars: 251;
- report `final_audit_data_ready`: true.

## Completion summary

- Added `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`,
  exported it from the v2 data-source package, and covered it with synthetic
  ZIP/CSV tests for all nine official Binance USD-M OF-style family shapes.
- Materialized compact research-only feature rows for orderflow, BBO spread,
  L2 depth, derivatives context, and kline-context inputs from the validated
  WPR106-549 external raw archive.
- Updated the data catalog, roadmap, product scope, audit index, known issues,
  active handoff, stage ledger, README, START_HERE, visibility snapshot, and
  rendered static page.
- The strict-free/free-venue data and OF-style materialization proof lane is
  ready for final audit. Full all-file feature-panel expansion is a compute
  decision for later packets, not a data-source blocker.
- No candidate pack, accepted autonomous-readiness report, paper/live signal,
  order placement, sizing instruction, runtime-mode change, promotion behavior,
  or production-trading readiness was created.
