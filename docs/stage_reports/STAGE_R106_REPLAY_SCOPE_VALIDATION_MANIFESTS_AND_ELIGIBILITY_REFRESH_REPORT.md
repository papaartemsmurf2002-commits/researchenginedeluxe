# Stage R106 Replay-Scope Validation Manifests And Eligibility Refresh Report

Work packet:
`docs/work_packets/WPR106-49-replay-scope-validation-manifests-and-eligibility-refresh.md`

Date: 2026-05-31

## Summary

WPR106-49 materializes the replay-scope multiple-testing and validation-floor
manifests that WPR106-48 identified as missing from the exact replay evidence
audit. No source-code changes were needed. Existing manifest-based builders
generated gate evidence directly from the WPR106-31 BTCUSDT and ETHUSDT replay
discovery manifests.

Refreshed BTC/ETH candidate-pack eligibility audits no longer block on
`multiple_testing_manifest_required` or `validation_floor_manifest_required`.
They still correctly block every row on exit-lab, multiple-testing,
validation-floor, and cycle-ranking evidence. No candidate pack was written,
and no candidate-ready, paper-ready, live-ready, or promotion-ready claim
exists.

## Artifact Evidence

Local output root:
`data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh`

Summary manifest:
`data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/wpr10649_replay_scope_validation_summary.json`

BTCUSDT:

- Multiple-testing manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/btcusdt/multiple_testing/discovery_multiple_testing_manifest.json`
- Validation-floor manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/btcusdt/validation_floors/discovery_validation_floors_manifest.json`
- Eligibility manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/eligibility/btcusdt/candidate_pack_eligibility_manifest.json`

ETHUSDT:

- Multiple-testing manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/ethusdt/multiple_testing/discovery_multiple_testing_manifest.json`
- Validation-floor manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/ethusdt/validation_floors/discovery_validation_floors_manifest.json`
- Eligibility manifest:
  `data/research/operator_runs/wpr106_49_replay_scope_validation_manifests_and_eligibility_refresh/eligibility/ethusdt/candidate_pack_eligibility_manifest.json`

| Artifact or count | BTCUSDT | ETHUSDT |
| --- | ---: | ---: |
| Replay leads | 24 | 24 |
| Multiple-testing rows | 24 | 24 |
| Multiple-testing passed rows | 0 | 0 |
| Multiple-testing blocked rows | 24 | 24 |
| Validation-floor rows | 24 | 24 |
| Validation-floor candidate-ready rows | 0 | 0 |
| Validation-floor diagnostic rows | 24 | 24 |
| Eligibility rows | 24 | 24 |
| Eligible rows | 0 | 0 |
| Candidate packs emitted | 0 | 0 |
| `multiple_testing_manifest_required` blockers | 0 | 0 |
| `validation_floor_manifest_required` blockers | 0 | 0 |

## Findings

The missing-manifest blockers are resolved for this replay evidence scope.
Both refreshed bridge manifests include source hashes for the multiple-testing
and validation-floor manifests, and both eligibility Parquets contain matched
gate rows for all 24 replay leads per symbol.

The actual gates remain blocked. For both symbols, all 24 rows block on
`simple_runner_v1` failing to beat fixed holding, missing split/window
concentration evidence, latest-window-only evidence, diagnostic validation
floors, missing provider-capability fields in replay lead rows, missing
ablation/baseline evidence, and partial bounded-cycle ranking overlap. Each
symbol still maps only one replay lead into the WPR106-46 bounded cycle-smoke
ranking evidence; the other 23 replay leads remain missing from rankings.

This packet narrows the evidence gap but does not change candidate status:
48/48 replay rows are blocked, 0/48 are eligible, and no candidate pack exists.

## Research Boundary

- Research outputs are not live signals.
- WPR106-49 artifacts remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- The generated manifests are gate evidence only and do not bypass exit-lab,
  cycle-ranking, bridge, modern-window, negative-control, or candidate-pack
  validation gates.
- No paper/live execution, order placement, sizing behavior, runtime-mode
  change, live configuration write, promotion authorization, or
  candidate-ready claim is introduced.

## Issue State

`ISSUE-R104-001` remains open. WPR106-49 removes one evidence-materialization
gap from the replay audit, but it does not provide a passing exit lab,
candidate-ready validation floors, passing multiple-testing evidence, full
cycle-ranking coverage for all replay leads, modern-window replay profiles,
available negative controls, deep-cycle evidence, or eligible candidate rows.

## Validation

Completed:

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
