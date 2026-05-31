# WPR106-44 Replay Overlay Cycle Spec Preflight

## Goal

Preflight WPR106-31 replayed BTCUSDT/ETHUSDT KNN prediction artifacts for
historical-cycle overlay execution after WPR106-42. Build the machine that can
say whether replay leads are representable by the current historical-cycle
candidate contract before launching expensive overlay/ranking/gate runs.

## Current Repo Facts

- WPR106-42 added candidate-scoped historical-cycle prediction overlay routing.
- WPR106-43 restored replay spec parser compatibility for WPR106-31 replay
  specs.
- WPR106-31 produced 24 BTCUSDT and 24 ETHUSDT replayed KNN prediction Parquets
  and manifests.
- Historical-cycle candidates are generated from current strategy metadata and
  `CandidateConfig` hashes. Candidate-scoped overlays must match generated
  `candidate_id` or `candidate_cache_key`.
- Exact replayed discovery lead parameters may not all be in the current
  historical-cycle strategy parameter domain. That mismatch must fail closed;
  do not widen strategy domains or silently substitute parameters.

## Conflicts And Stale Docs Found

- Older WPR106-31 wording says the next step is overlay/ranking/gates, but it
  predates WPR106-41/42 schema and candidate-scoped routing.
- If replayed parameters are not representable, the correct result is a
  rejection/preflight manifest, not weaker candidate gates or approximate
  replay parameters.

## Allowed Edit Paths

- `docs/work_packets/WPR106-44-replay-overlay-cycle-spec-preflight.md`
- `docs/work_packets/WPR106-44-progress.jsonl`
- `data/research/operator_runs/wpr106_44_replay_overlay_cycle_preflight/**`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_REPLAY_OVERLAY_CYCLE_SPEC_PREFLIGHT_REPORT.md`

## Forbidden Edit Paths

- source code
- strategy parameter domains
- backtesting, split, latency, cost, fill, live, paper, runtime, or promotion
  paths
- candidate gate thresholds, validation floors, or candidate-pack writing
- WPR106-31 generated replay artifacts
- `.pytest_cache/**`

## Subagents Used

- None planned. This is a bounded artifact preflight using the current source
  contracts and existing WPR106-31 artifacts.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

## Artifacts Expected

- Per-symbol preflight manifests under
  `data/research/operator_runs/wpr106_44_replay_overlay_cycle_preflight/`.
- A combined preflight summary listing replay lead counts, prediction artifact
  counts, representable candidate counts, unsupported parameter reasons, and
  whether any historical-cycle overlay spec was emitted.

No candidate packs, promotion artifacts, live signals, paper signals, runtime
changes, order-placement behavior, or gate weakening are expected.

## Definition Of Done

- Every WPR106-31 replay lead is accounted for.
- Prediction and manifest paths are verified to exist.
- Current historical-cycle parameter-domain compatibility is checked without
  changing the domain.
- Representable leads, if any, are mapped to generated candidate IDs and
  candidate-scoped overlay entries.
- Unrepresentable leads are preserved as rejection/preflight rows with explicit
  reasons.
- If zero leads are representable, no overlay cycle spec is emitted and the
  manifest records that zero as valid evidence.

## Rollback Plan

Delete only the WPR106-44 generated preflight directory and revert only docs
listed in allowed paths. Do not touch WPR106-31 artifacts, source code,
candidate packs, live/runtime paths, or unrelated cache state.
