# Stage R106 Complete Empirical Development And Stage Decision Report

Work packet:
`docs/work_packets/WPR106-56-complete-empirical-development-and-stage-decision.md`

Date: 2026-06-01

## Summary

WPR106-56 completes the empirical development decision from cleaned `main`
after the WPR106-46 through WPR106-54 merge. The current R106 Historical Data
Catalog is candidate-depth ready for BTCUSDT and ETHUSDT, and the active
cycle, discovery, exit-lab, multiple-testing, validation-floor, replay, and
eligibility evidence has enough coverage to make a final stage decision.

The decision is fail-closed: no candidate-pack gate stack passes, zero eligible
candidate rows exist, and no candidate pack is written. This closes
`ISSUE-R104-001` as a resolved no-candidate empirical outcome, not as a
candidate-ready or promotion-ready result.

## Catalog Evidence

Source catalog:
`data/research/operator_runs/historical_data/refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb/historical_data_catalog.json`

| Evidence | BTCUSDT | ETHUSDT |
| --- | ---: | ---: |
| Candidate-depth ready | true | true |
| Candidate-depth blockers | 0 | 0 |
| Effective coverage hours | 55,488 | 55,488 |
| 15m primary bars | 221,952 | 221,952 |
| 1m lower-timeframe bars | 3,329,280 | 3,329,280 |
| AggTrade proxy rows | 3,291,128 | 3,317,494 |
| Checksum-verified archives | 228 | 228 |
| Fixture manifest valid | true | true |

The catalog, readiness manifests, active cycle specs, and active discovery
specs remain `research_only: true`, `observe_only: true`, and
`promotion_ready: false`.

## Active Empirical Evidence

Current active historical cycles:

- BTCUSDT:
  `data/research/operator_runs/historical_cycles/r105-btcusdt-durable-public-archive-candidate-depth-v1/run-historical-research-cycle-3f12dcdc483945cfa753e4eb00d42280/research_cycle_manifest.json`
- ETHUSDT:
  `data/research/operator_runs/historical_cycles/r105-ethusdt-durable-public-archive-candidate-depth-v1/run-research-autopilot-52719942d4604874a51a67489bbbe98a-ethusdt-cycle/research_cycle_manifest.json`

Both active cycles produced 63 ranked research candidates. All 63 per symbol
remain rejected in `candidate_rankings.parquet` and blocked in
`candidate_gate_report.parquet`; `candidate_pack_written` is false and
`promotion_ready` is false.

Current active exact discovery manifests:

- BTCUSDT:
  `data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-candidate-depth-v1/discovery_run_manifest.json`
- ETHUSDT:
  `data/research/operator_runs/discovery_runs/exact-entry-sweep-ethusdt-candidate-depth-v1/discovery_run_manifest.json`

| Evidence | BTCUSDT | ETHUSDT |
| --- | ---: | ---: |
| Completed exact-discovery trials | 570,240 | 570,240 |
| Interesting discovery rows | 22,560 | 23,040 |
| Blocked discovery rows | 547,680 | 547,200 |
| Candidate-pack paths | 0 | 0 |

WPR106-29 materialized the active multiple-testing and validation-floor gate
evidence and refreshed capped eligibility:

- BTCUSDT:
  `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause_capped/btcusdt/candidate_pack_eligibility/candidate_pack_eligibility_manifest.json`
- ETHUSDT:
  `data/research/operator_runs/wpr106_29_candidate_rejection_root_cause_capped/ethusdt/candidate_pack_eligibility/candidate_pack_eligibility_manifest.json`

| Gate evidence | BTCUSDT | ETHUSDT |
| --- | ---: | ---: |
| Multiple-testing rows | 22,560 | 23,040 |
| Multiple-testing passed rows | 0 | 0 |
| Validation-floor candidate-ready rows | 0 | 0 |
| Validation-floor diagnostic rows | 22,560 | 23,040 |
| Candidate-pack bridge rows | 22,560 | 23,040 |
| Candidate-pack eligible rows | 0 | 0 |
| Discovery-to-cycle ranking overlap | 0 | 0 |
| Candidate packs written | 0 | 0 |

Dominant active blockers include
`research_candidate_gate:candidate_missing_from_rankings`,
`multiple_testing_gate:split_window_concentration_required`,
`validation_floor_gate:candidate_ready_validation_required`,
`validation_floor_gate:exit_lab_gate_status_not_passed`, baseline/no-trade
comparator gaps, ablation gaps, and stability/cost-stress validation floors.

## Replay And Control Evidence

WPR106-46 through WPR106-49 add exact replay-overlay and replay-scope gate
evidence without changing the final candidate status:

- WPR106-46 made all 48 WPR106-31 replay leads exactly representable and ran
  bounded BTC/ETH overlay cycle smokes with candidate-scoped overlay
  provenance. The smokes produced zero pack-eligible rows and no packs.
- WPR106-47 verified full frozen-entry exit-lab evidence for all 48 replay
  leads. All 48 remain blocked because `simple_runner_v1` does not improve
  over fixed holding.
- WPR106-48 generated 192 first-class negative-control rows across shuffled
  labels, shifted context, no-KNN overlay, and no-regime backend controls. All
  controls are blocked, `control_only: true`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- WPR106-49 materialized replay-scope multiple-testing and validation-floor
  manifests. All 48 replay rows remain blocked, 0 are eligible, and no replay
  candidate pack exists.

Replay/control artifacts remain research-only, observe-only, and
promotion-disabled.

## Decision

`ISSUE-R104-001` is resolved by final empirical decision rather than by a
positive candidate. The original compact-fixture blocker has been superseded by
the expanded R106 catalog and the active BTC/ETH candidate-depth run evidence.
The existing gate stack rejects every active and replay-scoped row, so the only
defensible outcome is:

- zero eligible candidates;
- no candidate pack;
- no candidate-ready claim;
- no paper-ready or live-ready claim;
- no promotion-ready claim;
- no order-placement, sizing, runtime-mode, or live-configuration behavior.

Future research may open new packets for new data, new candidate
materialization, or stronger controls, but that would be new research work, not
unfinished WPR106 development.

## Validation

Completed WPR106-56 baseline validation:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- `python -m compileall -q src\tradingbotsuite`: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`: 441 passed.
