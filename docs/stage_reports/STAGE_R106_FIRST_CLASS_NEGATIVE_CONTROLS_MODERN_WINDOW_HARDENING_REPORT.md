# Stage R106 First Class Negative Controls Modern Window Hardening Report

Work packet:
`docs/work_packets/WPR106-48-first-class-negative-controls-modern-window-and-hardening.md`

Date: 2026-05-31

## Summary

WPR106-48 turns WPR106-47 negative-control audit rows into first-class
research artifacts and hardens the candidate bridge around them. Control
artifacts are explicitly `negative_control`, `control_only`, not candidate
evidence, research-only, observe-only, and non-promotable. They can be used as
fail-closed audit evidence, but they cannot be packaged as candidate evidence.

Modern-window evidence remains blocked. No local modern-window replay profile
exists, so the packet records `modern_window_evidence_required` instead of
relabeling full-window evidence.

## Artifact Evidence

Local output root:
`data/research/operator_runs/wpr106_48_first_class_negative_controls_modern_window_and_hardening`

Primary negative-control manifest:
`data/research/operator_runs/wpr106_48_first_class_negative_controls_modern_window_and_hardening/negative_controls/wpr10648_negative_control_manifest.json`

Compatibility audit manifest:
`data/research/operator_runs/wpr106_48_first_class_negative_controls_modern_window_and_hardening/audit/wpr10647_replay_evidence_manifest.json`

| Artifact or count | Value |
| --- | ---: |
| First-class negative-control rows | 192 |
| First-class negative-control blocked rows | 192 |
| Control families | 4 |
| Full replay leads audited | 48 |
| Full-window scope rows available | 2 |
| Modern-window scope rows blocked | 2 |
| Candidate eligibility rows | 48 |
| Candidate eligible rows | 0 |
| Candidate packs emitted | 0 |
| Replay-ledger schema mismatch after normalization | 0 |

## Findings

All 192 first-class control rows are blocked by missing replay profile
provenance, missing validation manifest, and missing modern-window evidence.
This is expected fail-closed evidence. `shuffled_labels` also lacks source
label columns for the WPR106-46 preflight rows, and `shifted_context` lacks a
source timestamp column.

The discovery bridge now rejects `control_only: true` and
`artifact_family: negative_control` manifests. Replay-scoped bridge inputs can
also declare required replay profile, validation manifest, exact replay
lineage, and modern-window evidence, and missing fields block eligibility.

Historical replay ledgers are normalized at read time for newer compatibility
columns such as `regime_model_backend`. WPR106-48 refreshed BTC/ETH eligibility
audits with zero replay-ledger schema mismatch blockers and without rewriting
immutable WPR106-31 evidence.

Eligibility remains blocked for all 48 rows. The dominant blockers remain
exit-lab no-improvement over fixed holding, missing multiple-testing and
validation-floor manifests for this evidence scope, and partial bounded-cycle
ranking overlap from the WPR106-46 singleton cycle smokes.

## Research Boundary

- Research outputs are not live signals.
- WPR106-48 artifacts remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- Control artifacts are `control_only: true`, `candidate_evidence: false`, and
  `candidate_pack_eligible: false`.
- No paper/live execution, order placement, sizing behavior, runtime-mode
  change, live configuration write, promotion authorization, or
  candidate-ready claim is introduced.
- No candidate packs were written.

## Issue State

`ISSUE-R104-001` remains open. WPR106-48 improves control provenance,
candidate-bridge rejection, and replay-ledger compatibility, but it does not
provide a passing exit lab, modern-window replay profile, multiple-testing
manifest, validation-floor manifest, deep-cycle evidence, or eligible
candidate rows.

## Validation

Completed:

```powershell
python -m compileall -q src\tradingbotsuite\research_discovery src\tradingbotsuite\research_artifacts
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_replay_evidence_controls.py tests\research_discovery\test_candidate_pack_bridge.py tests\research_artifacts\test_candidate_pack.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery tests\research_artifacts -q
python -m compileall -q src\tradingbot src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
```

Results:

- Focused replay evidence, bridge, and candidate-pack boundary tests:
  79 passed.
- Focused package compile: passed.
- `python -m compileall -q src\tradingbotsuite`: passed.
- `tests\contracts`: 441 passed.
- `tests\research_discovery tests\research_artifacts`: 282 passed.
- `python -m compileall -q src\tradingbot src\tradingbotsuite`: passed.
- Full `pytest -q`: 1538 passed, 1 skipped.
- `git diff --check`: passed with line-ending warnings only.

## Bottom-To-Top Review

Review completed from helper code through docs. The reviewed layers preserve
research-only boundaries, keep controls structurally separate from candidate
evidence, fail closed on missing replay/validation/modern-window provenance,
normalize replay ledgers only at read time, avoid live/paper/order/sizing
paths, and leave `ISSUE-R104-001` open.
