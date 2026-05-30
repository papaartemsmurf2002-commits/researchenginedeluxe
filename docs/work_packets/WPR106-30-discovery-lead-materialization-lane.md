# WPR106-30 Discovery Lead Materialization Lane

## Summary

Create the first bounded materialization lane from exact-discovery KNN leads to
cycle/backtest-ready candidate descriptors. This packet must not write candidate
packs, mark candidates eligible, or claim promotion readiness. It should produce
a deterministic research-only artifact that preserves the original discovery
lead evidence, assigns stable materialized candidate IDs, and records why the
next empirical packet still must run backtests, comparators, exit lab,
multiple-testing, validation floors, and candidate-pack eligibility.

## Allowed Paths

Edit scope:

- `docs/work_packets/WPR106-30-discovery-lead-materialization-lane.md`
- `docs/stage_reports/STAGE_R106_DISCOVERY_LEAD_MATERIALIZATION_LANE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a new blocking issue is found
- `src/tradingbotsuite/research_discovery/discovery_lead_materialization.py`
- `src/tradingbotsuite/research_discovery/__init__.py`
- `tests/research_discovery/test_discovery_lead_materialization.py`

Generated research artifacts may be read. Isolated WPR106-30 operator-run
outputs may be written under `data/research/operator_runs/`. Do not rewrite
historical cycle, discovery, fixture, or prior WPR106-29 artifacts in place.

## Implementation Plan

1. Define a deterministic artifact contract for bounded discovery lead
   materialization:
   - `discovery_lead_materialization_manifest.json`
   - `materialized_discovery_leads.parquet`
   - `materialization_candidate_specs.jsonl`
2. Select top leads by stable score ordering with per-signature deduplication so
   one dense parameter family cannot consume the full materialization budget.
3. Preserve source discovery identity:
   - source manifest path and hash
   - source ledger hash
   - source trial ID and record hash
   - discovery candidate ID
   - prediction and entry-event signature hashes
4. Assign stable materialized candidate IDs derived from the source discovery
   evidence and intended validation scope.
5. Emit cycle/backtest-ready descriptors, not cycle evidence:
   - strategy family: frozen KNN entry lead
   - symbol/timeframe/feature set/regime mode/label horizon/KNN thresholds
   - required next gates and missing evidence labels
6. Keep all artifacts `research_only: true`, `observe_only: true`, and
   `promotion_ready: false`.
7. Add focused tests covering deterministic IDs, bounded selection,
   deduplication, research-boundary flags, manifest hashes, and fail-closed
   no-pack/no-promotion behavior.

## Acceptance Criteria

- BTC/ETH discovery leads can be materialized into bounded descriptor artifacts
  without mutating source discovery or cycle outputs.
- The manifest explicitly states that descriptors are not backtest evidence,
  not candidate-pack evidence, and not promotion evidence.
- Materialized IDs are stable across reruns from the same inputs.
- Output records include source discovery IDs, source trial hashes, signature
  hashes, materialized candidate IDs, and required downstream gate labels.
- No live execution, live config, runtime mode, sizing, order placement,
  candidate-pack writing, or promotion readiness is introduced.
- Focused tests and the baseline compile/contracts validation pass.
