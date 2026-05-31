# WPR106-43 Discovery Replay Spec Schema Compatibility

## Goal

Restore fail-closed parser compatibility for discovery lead replay specs after
the WPR106-41 discovery-run schema guard, without changing discovery behavior,
candidate gates, live/paper behavior, order placement, promotion logic, or
generated artifacts.

## Current Repo Facts

- `DiscoveryRunSpec.from_payload()` now rejects unknown active fields and wrong
  `spec_version` values.
- WPR106-31 replay specs intentionally use
  `spec_version: discovery-lead-replay-spec-v1` while otherwise conforming to
  the active discovery-run execution contract.
- `build_discovery_lead_replay_spec()` validates its generated payload through
  `DiscoveryRunSpec.from_payload()`, so the stricter schema now rejects replay
  specs.
- `tests\research_discovery\test_discovery_lead_replay.py` fails on that
  compatibility path.

## Conflicts And Stale Docs Found

- The active discovery-run schema guard is correct for ordinary discovery specs
  but did not account for the replay specialization already present in
  WPR106-31 artifacts.
- Replay specs are research-only execution specs, not candidate readiness or
  promotion evidence.

## Allowed Edit Paths

- `docs/work_packets/WPR106-43-discovery-replay-spec-schema-compatibility.md`
- `docs/work_packets/WPR106-43-progress.jsonl`
- `src/tradingbotsuite/research_discovery/spec.py`
- `tests/research_discovery/test_discovery_spec.py`
- `tests/research_discovery/test_discovery_lead_replay.py`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_DISCOVERY_REPLAY_SPEC_SCHEMA_COMPATIBILITY_REPORT.md`

## Forbidden Edit Paths

- historical-cycle runner/spec behavior
- backtesting, split, cost, fill, latency, or strategy behavior
- live/paper/runtime/order-placement/promotion paths
- generated replay artifacts under `data/research/**`
- candidate gates, validation floors, or candidate-pack writing
- `.pytest_cache/**`

## Subagents Used

- None. This was discovered by the default research-discovery validation suite.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_spec.py tests\research_discovery\test_discovery_lead_replay.py -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
git diff --check
```

## Artifacts Expected

- Parser allowlist for the replay spec version as a known discovery-run
  specialization.
- Regression test proving replay spec version is accepted while unrelated wrong
  versions still fail closed.
- Stage report.

No generated research artifacts, candidate packs, promotion claims, or live
runtime behavior are expected.

## Definition Of Done

- Ordinary wrong discovery `spec_version` values still fail closed.
- `discovery-lead-replay-spec-v1` is accepted as a known replay specialization.
- Replay spec builder tests pass.
- Full research-discovery validation passes.

## Rollback Plan

Revert only files listed in allowed edit paths. Do not alter generated replay
artifacts, candidate packs, historical-cycle outputs, live/runtime paths, or
unrelated cache state.
