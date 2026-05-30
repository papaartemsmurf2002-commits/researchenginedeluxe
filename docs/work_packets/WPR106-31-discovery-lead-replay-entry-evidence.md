# WPR106-31 Discovery Lead Replay Entry Evidence

## Summary

Replay the WPR106-30 materialized BTCUSDT and ETHUSDT discovery-lead
descriptors through the real discovery artifact path, then aggregate annotated
entry-signal evidence that downstream exit-lab and cycle-overlay work can
consume. This packet must not write candidate packs, mark candidates eligible,
or claim promotion readiness.

The packet exists because WPR106-30 intentionally produced descriptor-only
artifacts. WPR106-31 should turn those descriptors into reproducible replay
specs and entry-signal evidence while preserving the boundary between:

- real replayed KNN/strategy artifacts;
- frozen-entry exit-lab evidence;
- historical-cycle ranking/gate evidence that still must come from the cycle
  runner.

## Allowed Paths

Edit scope:

- `docs/work_packets/WPR106-31-discovery-lead-replay-entry-evidence.md`
- `docs/stage_reports/STAGE_R106_DISCOVERY_LEAD_REPLAY_ENTRY_EVIDENCE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a new blocking issue is found
- `src/tradingbotsuite/research_discovery/discovery_lead_replay.py`
- `src/tradingbotsuite/research_discovery/spec.py`
- `src/tradingbotsuite/research_discovery/runner.py`
- `src/tradingbotsuite/research_discovery/__init__.py`
- `tests/research_discovery/test_discovery_lead_replay.py`
- `tests/research_discovery/test_discovery_spec.py`
- `tests/research_discovery/test_discovery_runner.py`

Generated isolated WPR106-31 operator-run outputs may be written under
`data/research/operator_runs/`. Do not rewrite source discovery runs,
historical cycles, fixture packs, or WPR106-30 materialization artifacts in
place.

## Implementation Plan

1. Add a replay-spec builder that reads a WPR106-30 materialization manifest,
   follows normalized source discovery/trial evidence, and writes an explicit
   `trial_templates` discovery spec.
2. Preserve source identity in each replay template:
   - source discovery candidate ID;
   - source trial ID and record hash;
   - materialized candidate ID;
   - prediction and entry-event signatures;
   - original KNN/HMM threshold payload.
3. Configure replay specs for isolated output directories and real
   prediction-artifact persistence:
   - `trial_templates` with real `regime_knn_entry_discovery` payloads;
   - `execution.persist_trial_artifacts: predictions_only` so replay writes
     HMM, KNN prediction, and strategy-accounting artifacts without the much
     heavier neighbor-diagnostics table;
   - `research_only: true`, `observe_only: true`,
     `promotion_ready: false` via existing discovery contracts.
4. Add an entry-signal aggregator that reads replay trial records and
   per-trial strategy-accounting outputs, annotates signals with
   `candidate_id`, `trial_id`, `record_sha256`, source IDs, and
   `decision_time_ms`, then writes:
   - `discovery_replay_entry_signals.parquet`
   - `discovery_replay_entry_signal_manifest.json`
5. Run frozen-entry exit lab where replayed entry signals exist. Keep blocked
   outcomes truthful.
6. Document why historical-cycle ranking evidence remains the next packet if
   cycle overlays are not generated here.

## Acceptance Criteria

- BTC/ETH materialized descriptors can be converted into replay specs without
  mutating source artifacts.
- Replay specs preserve source discovery/trial identity and write isolated
  output paths.
- Entry-signal aggregation writes candidate/trial/hash annotated signals that
  frozen-entry exit lab can match.
- All new manifests are research-only, observe-only, promotion-ready false,
  candidate-pack-written false, and live-boundary false.
- The stage report records replay counts, signal counts, exit-lab outcomes,
  and any remaining blockers.
- No live execution, live config, runtime mode, sizing, order placement,
  candidate-pack writing, or promotion readiness behavior is introduced.
