# Stage R94 Mandatory Exit-Lab Gate Report

Date: 2026-05-12
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR94-03-mandatory-exit-lab-gate.md`

## Summary

WPR94-03 made completed exit-lab evidence mandatory before the discovery
candidate-pack bridge can mark a discovery lead eligible for the existing
historical-cycle candidate-pack validator.

Implemented:

- Extended discovery exit-lab artifacts with
  `discovery_exit_lab_candidate_gates.parquet`.
- Added candidate-tied gate fields:
  `exit_lab_status`, `exit_lab_gate_status`, `exit_lab_best_family`,
  `best_comparison_id`, fixed-holding score delta, cost-stress status,
  no-improvement reason, and entry-lead evidence hashes.
- Added deterministic `discovery_entry_lead_evidence_sha256()` hashing for the
  discovery lead fields that matter to bridge eligibility.
- Updated the bridge API and CLI with `exit_lab_manifest_path` /
  `--exit-lab-manifest`.
- Added bridge fail-closed reasons for missing exit lab artifacts, candidate
  gate row absence, hash mismatch, fixed-holding-only evidence, and no
  executable exit improvement over fixed holding.
- Kept the existing historical-cycle `evaluate_research_candidate_gate(...)`
  requirement after an exit-lab pass.
- Updated discovery exit-lab and bridge configs to declare the mandatory gate.

## Boundary Notes

- Research outputs remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- The bridge still writes eligibility/rejection audit artifacts only and never
  writes candidate packs.
- No live order placement, live config writes, runtime mode changes, candidate
  promotion, or sizing behavior was added.
- No new exit execution model was added; this packet gates on existing
  discovery exit-lab comparison evidence.

## Validation

Passed:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_exit_lab.py tests\research_discovery\test_candidate_pack_bridge.py -q
# 28 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 102 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 372 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with line-ending warnings only
```

## Next Packet

Continue the R94 roadmap with WPR94-04 matched filter ablation v2. The bridge
still remains locked behind exit-lab and historical-cycle gate evidence; later
packets should add matched filter, multiple-testing/stability, validation-floor,
and blocker-registry requirements before any candidate-ready wording.
