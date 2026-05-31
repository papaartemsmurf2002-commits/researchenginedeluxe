# Work Packet: WPR106-45 replay overlay preflight contract

## Goal

Codify the WPR106-44 replay-overlay exactness preflight as reusable
research-only code and contract tests. The preflight must prove whether
materialized WPR106-31 replay leads are exactly representable by the current
historical-cycle candidate contract before any candidate-scoped overlay cycle
spec is emitted.

## Current Repo Facts

- Current checkout is `main`, documented as the migrated mirror of the
  research/experimental branch.
- P0 blockers are closed; one P1 data-depth issue remains open.
- WPR106-42 added candidate-scoped materialized prediction overlay routing in
  `research_cycle`.
- WPR106-43 restored `discovery-lead-replay-spec-v1` schema compatibility.
- WPR106-44 preflighted 48 replay leads and found zero exact representable
  candidates because the replayed KNN leads use `label_horizon: 1h`,
  `event_spacing_bars: 4`, and several threshold values outside the current
  `hmm_knn_local_analog_filter_v2` historical-cycle domain.
- The existing `hmm_knn_local_analog_filter_v2` strategy explicitly supports
  `features_perp_context_v2` and holding windows `4h`, `12h`, `24h`, and
  `72h`; `1h` remains rejected.

## Conflicts / Stale Docs Found

- Older branch references still mention `research/v3-experimental-engine`, but
  `START_HERE.md` clarifies the active checkout is `main`.
- The WPR106-44 artifact is a valid local preflight result but the reusable
  source contract is not yet codified.

## Allowed Edit Paths

- `src/tradingbotsuite/research_discovery/replay_overlay_preflight.py`
- `src/tradingbotsuite/research_discovery/__init__.py`
- `tests/research_discovery/test_replay_overlay_preflight.py`
- `docs/work_packets/WPR106-45-*`
- `docs/stage_reports/STAGE_R106_REPLAY_OVERLAY_PREFLIGHT_CONTRACT_REPORT.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

## Forbidden Edit Paths

- Live, paper, runtime, order-placement, adapter, and promotion execution
  behavior.
- Strategy implementations and strategy parameter domains.
- Historical fixture data, WPR106-31 replay artifacts, and WPR106-44 generated
  artifact files.
- Candidate gate thresholds, promotion logic, and candidate-pack eligibility
  criteria.

## Subagents To Use

- Repo Cartographer: map source/test seams for replay preflight.
- Validation Engineer: recommend fail-closed exactness tests.
- Artifact Gatekeeper: audit research-only and candidate-pack boundary fields.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_replay_overlay_preflight.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

Broaden to contracts if shared contract surfaces change.

## Artifacts Expected

- Reusable preflight result and artifact writer with JSON manifest plus Parquet
  rows.
- Focused tests for representable, unrepresentable, missing prediction
  artifact, missing manifest, and manifest boundary validation.
- Stage report and JSONL progress ledger.

## Definition Of Done

- Preflight rows explain every checked replay lead with explicit reasons.
- Missing KNN prediction or manifest paths fail closed as unrepresentable, not
  silently skipped.
- Valid exact candidates get a generated historical-cycle candidate cache key
  and candidate-scoped overlay spec draft only when current strategy support and
  allowed parameter domains match exactly.
- Manifests stamp `research_only: true`, `observe_only: true`,
  `promotion_ready: false`, no live/runtime/order side effects, and
  `candidate_pack_written: false`.
- Zero representable candidates remains a successful preflight result.

## Rollback Plan

Revert only the WPR106-45 files listed in allowed paths. The packet does not
rewrite existing WPR106-31/WPR106-44 artifacts or alter runtime behavior, so
rollback is limited to removing the reusable preflight module, tests, and docs.
