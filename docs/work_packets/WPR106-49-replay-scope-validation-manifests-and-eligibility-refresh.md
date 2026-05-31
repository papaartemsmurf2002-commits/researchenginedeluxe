# Work Packet: WPR106-49 replay-scope validation manifests and eligibility refresh

## Goal

Close the remaining WPR106-48 evidence materialization gap by generating
replay-scope multiple-testing and validation-floor manifests for the 48
WPR106-31 exact replay leads, then refresh the WPR106 replay eligibility audit
with those manifests wired into the bridge.

This packet is evidence materialization only. It must not weaken gates, emit a
candidate pack, or turn blocked replay evidence into a candidate-ready claim.

## Current Repo Facts

- Current implementation branch:
  `codex/wpr106-47-full-replay-exit-lab-controls`.
- WPR106-48 made negative controls first-class artifacts and hardened the
  bridge, but BTC/ETH replay eligibility still reports missing
  multiple-testing and validation-floor manifests for the replay evidence
  scope.
- WPR106-31 replay manifests contain 24 BTCUSDT and 24 ETHUSDT exact replay
  leads.
- WPR106-47/WPR106-48 full frozen-entry exit-lab evidence remains blocked for
  all 48 replay leads because `simple_runner_v1` did not improve over fixed
  holding.
- WPR106-48 negative controls remain blocked by missing replay profile
  provenance, validation manifest, modern-window evidence, and selected source
  label/timestamp inputs.
- `ISSUE-R104-001` remains open. There is no candidate-ready, paper-ready,
  live-ready, or promotion-ready claim.

## Allowed Edit Paths

- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_*.md`
- `docs/work_packets/WPR106-*.md`
- `docs/work_packets/WPR106-*-progress.jsonl`
- `src/tradingbotsuite/research_discovery/multiple_testing.py`
- `src/tradingbotsuite/research_discovery/validation_floors.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `tests/research_discovery/test_multiple_testing.py`
- `tests/research_discovery/test_validation_floors.py`
- `tests/research_discovery/test_candidate_pack_bridge.py`

Generated empirical artifacts under `data/research/operator_runs/` are local
research evidence outputs and remain ignored by git.

## Research Boundary

- Research outputs are not live signals.
- Artifacts must remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- This packet must not add live signals, paper signals, order placement, sizing
  behavior, runtime-mode changes, live configuration writes, promotion-ready
  claims, candidate-ready claims, or candidate-pack writes.
- Multiple-testing and validation-floor manifests are gate evidence only. A
  passing or missing row must not bypass exit-lab, cycle-ranking, bridge,
  negative-control, modern-window, or candidate-pack validation gates.

## Implementation Plan

1. Inspect the WPR106-31 replay discovery manifests and existing builders for
   manifest-based multiple-testing and validation-floor reports.
2. Generate isolated WPR106-49 BTC/ETH multiple-testing and validation-floor
   artifacts from the replay discovery manifests.
3. Refresh BTC/ETH replay candidate-pack eligibility with the new manifests,
   the WPR106-31 full exit-lab manifests, and available WPR106-46 bounded
   cycle-smoke candidate maps.
4. Record actual row counts, pass/block summaries, and residual blockers in a
   stage report and active docs.
5. Run focused validation, baseline contracts, and broaden only if source code
   changes are required.

## Acceptance Criteria

- BTC/ETH replay-scope multiple-testing manifests are materialized for all 48
  WPR106-31 replay leads.
- BTC/ETH replay-scope validation-floor manifests are materialized for all 48
  WPR106-31 replay leads.
- Refreshed eligibility manifests no longer block on
  `multiple_testing_manifest_required` or `validation_floor_manifest_required`
  for this evidence scope.
- Refreshed eligibility remains fail-closed where exit-lab, cycle-ranking,
  modern-window, control, or validation blockers remain.
- No candidate pack is written.
- Docs state whether any source-code changes were needed and list validation
  commands/results.

## Implementation Summary

- No source-code changes were required for WPR106-49. The existing
  manifest-based multiple-testing and validation-floor builders covered the
  replay evidence scope.
- Generated isolated BTCUSDT and ETHUSDT multiple-testing artifacts from the
  WPR106-31 replay discovery manifests.
- Generated isolated BTCUSDT and ETHUSDT validation-floor artifacts from the
  WPR106-31 replay discovery manifests.
- Refreshed BTCUSDT and ETHUSDT candidate-pack eligibility audits using the
  new gate manifests, WPR106-31 full frozen-entry exit-lab manifests, WPR106-46
  bounded cycle-smoke manifests, and the existing one-row-per-symbol candidate
  maps from WPR106-48.
- Verified that `multiple_testing_manifest_required` and
  `validation_floor_manifest_required` are no longer present in refreshed
  WPR106-49 eligibility blockers.

## Empirical Artifact Evidence

Local output root:
`data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh`

Summary manifest:
`data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/wpr10649_replay_scope_validation_summary.json`

BTCUSDT artifacts:

- Multiple-testing manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/btcusdt/multiple_testing/discovery_multiple_testing_manifest.json`
- Validation-floor manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/btcusdt/validation_floors/discovery_validation_floors_manifest.json`
- Eligibility manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/eligibility/btcusdt/candidate_pack_eligibility_manifest.json`

ETHUSDT artifacts:

- Multiple-testing manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/ethusdt/multiple_testing/discovery_multiple_testing_manifest.json`
- Validation-floor manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/ethusdt/validation_floors/discovery_validation_floors_manifest.json`
- Eligibility manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/eligibility/ethusdt/candidate_pack_eligibility_manifest.json`

| Artifact or count | BTCUSDT | ETHUSDT |
| --- | ---: | ---: |
| Replay leads | 24 | 24 |
| Multiple-testing gate rows | 24 | 24 |
| Multiple-testing passed rows | 0 | 0 |
| Multiple-testing blocked rows | 24 | 24 |
| Validation-floor gate rows | 24 | 24 |
| Validation-floor candidate-ready rows | 0 | 0 |
| Validation-floor diagnostic rows | 24 | 24 |
| Eligibility rows | 24 | 24 |
| Eligible rows | 0 | 0 |
| Candidate packs emitted | 0 | 0 |
| `multiple_testing_manifest_required` blockers | 0 | 0 |
| `validation_floor_manifest_required` blockers | 0 | 0 |

Dominant residual blockers for both symbols:

- `exit_lab_gate:simple_runner_did_not_beat_fixed_holding`: 24 rows.
- `exit_lab_gate:exit_lab_no_improving_exit_over_fixed_holding`: 24 rows.
- `multiple_testing_gate:split_window_concentration_required`: 24 rows.
- `multiple_testing_gate:latest_window_only_evidence`: 24 rows.
- `validation_floor_gate:candidate_ready_validation_required`: 24 rows.
- `validation_floor_gate:exit_lab_gate_status_not_passed`: 24 rows.
- `validation_floor_gate:overlap_ratio_above_ceiling`: 24 rows.
- `validation_floor_gate:split_pass_ratio_required`: 24 rows.
- `validation_floor_gate:cost_stress_survival_below_floor`: 24 rows.
- `validation_floor_gate:stability_neighborhood_size_below_floor`: 24 rows.
- `validation_floor_gate:source_provider_capability_missing`: 24 rows.
- `validation_floor_gate:durable_public_archive_readiness_missing`: 24 rows.
- `research_candidate_gate:candidate_missing_from_rankings`: 23 rows.

The result is a narrower, more accurate fail-closed audit: missing-manifest
blockers are gone, but no candidate is eligible and no candidate pack is
written.

## Validation Plan

Focused validation:

```powershell
python -m compileall -q src\tradingbotsuite\research_discovery
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_multiple_testing.py tests\research_discovery\test_validation_floors.py tests\research_discovery\test_candidate_pack_bridge.py -q
```

Baseline validation:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Broaden if shared behavior changes:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery tests\research_artifacts -q
git diff --check
```

Validation completed:

```powershell
python -m compileall -q src\tradingbotsuite\research_discovery
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_multiple_testing.py tests\research_discovery\test_validation_floors.py tests\research_discovery\test_candidate_pack_bridge.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Results:

- Focused research-discovery tests: 53 passed.
- Contracts: 441 passed.
- Both compile commands passed.
- `git diff --check` passed with line-ending warnings only.
