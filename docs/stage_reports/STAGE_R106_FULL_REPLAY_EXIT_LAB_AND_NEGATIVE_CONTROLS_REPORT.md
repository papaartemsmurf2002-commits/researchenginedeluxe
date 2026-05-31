# Stage R106 Full Replay Exit Lab And Negative Controls Report

Work packet:
`docs/work_packets/WPR106-47-full-replay-exit-lab-and-negative-controls.md`

Date: 2026-05-31

## Summary

WPR106-47 adds a research-only audit artifact for the post-WPR106-46 evidence
queue. It keeps full frozen-entry exit-lab evidence, full-window versus
modern-window evidence, negative-control status, and eligibility review in
separate sections so no single performance claim is implied.

Full WPR106-31 frozen-entry exit-lab artifacts were verified for all 48 replay
leads. A fresh WPR106-47 full rerun was attempted but exceeded a 10-minute local
timeout on BTC, so the packet uses the already-completed WPR106-31 full-lab
artifacts as source evidence and records the rerun limitation explicitly.

## Artifact Evidence

Local output root:
`data/research/operator_runs/wpr106_47_full_replay_exit_lab_and_negative_controls`

Primary audit manifest:
`data/research/operator_runs/wpr106_47_full_replay_exit_lab_and_negative_controls/audit/wpr10647_replay_evidence_manifest.json`

| Artifact or count | Value |
| --- | ---: |
| Full replay leads audited | 48 |
| BTC full exit-lab leads | 24 |
| ETH full exit-lab leads | 24 |
| Exit-lab matrix rows | 96 |
| Exit-lab gate rows | 48 |
| Exit-lab blocked rows | 48 |
| BTC frozen-entry trades | 1,046,531 |
| ETH frozen-entry trades | 1,039,774 |
| Full-window scope rows available | 2 |
| Modern-window scope rows blocked | 2 |
| Negative-control rows | 192 |
| Negative-control blocked rows | 192 |
| Candidate eligibility rows | 48 |
| Candidate eligible rows | 0 |
| Candidate packs emitted | 0 |

Source full exit-lab manifests:

- BTC:
  `data/research/operator_runs/wpr106_31_discovery_lead_replay/btcusdt/frozen_entry_exit_lab/discovery_exit_lab_manifest.json`
- ETH:
  `data/research/operator_runs/wpr106_31_discovery_lead_replay/ethusdt/frozen_entry_exit_lab/discovery_exit_lab_manifest.json`

Eligibility manifests:

- BTC:
  `data/research/operator_runs/wpr106_47_full_replay_exit_lab_and_negative_controls/eligibility/btcusdt/candidate_pack_eligibility_manifest.json`
- ETH:
  `data/research/operator_runs/wpr106_47_full_replay_exit_lab_and_negative_controls/eligibility/ethusdt/candidate_pack_eligibility_manifest.json`

## Findings

The full frozen-entry exit-lab gate remains blocked for all 48 replay leads.
Every lead failed because `simple_runner_v1` did not improve over fixed holding.
This is negative research evidence, not a candidate-ready claim.

The full-window side is available from WPR106-46 exact replay-overlay
preflight/spec-draft evidence. The modern-window side is blocked because no
local `modern_window_profile.json` artifacts exist under the active historical
data catalog. The audit records this as `modern_window_profile_artifact_missing`
rather than slicing full-window evidence and relabeling it.

Negative controls are fail-closed. No first-class shuffled-label,
shifted-context, no-KNN baseline, or no-regime baseline control artifacts exist
for the exact replay overlay lane, so WPR106-47 emits 192 blocked control rows
with `control_only: true` and `candidate_pack_eligible: false`.

Eligibility review after the audit evidence produced 48 blocked rows and zero
eligible rows. The bounded WPR106-46 cycle smokes cover one replay lead per
symbol, so bridge alignment is partial: one mapped overlap and 23 unmapped
discovery rows per symbol. Multiple-testing and validation-floor manifests are
also absent for the WPR106-47 evidence scope. The bridge additionally reports
WPR106-31 replay-ledger schema mismatch against the current eligibility schema,
which is recorded as a fail-closed blocker rather than normalized away.

## Research Boundary

- Research outputs are not live signals.
- WPR106-47 artifacts remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- No paper/live execution, order placement, sizing behavior, runtime-mode
  change, live configuration write, promotion authorization, or candidate-ready
  claim is introduced.
- No candidate packs were written.

## Issue State

`ISSUE-R104-001` remains open. WPR106-47 adds full replay exit-lab audit,
window-scope separation, blocked negative controls, and eligibility review, but
it does not provide the deep cycles, exact sweeps, complete negative-control
artifacts, passing validation floors, or eligible candidate rows required to
close the blocker.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\historical tests\research_artifacts -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\features tests\historical tests\research_artifacts tests\live -q
python -m compileall -q src\tradingbot src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
python -m compileall -q src\tradingbotsuite\research_discovery
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_replay_evidence_controls.py tests\research_discovery\test_frozen_entry_exit_lab.py -q
```

Results:

- Focused replay-evidence and frozen-entry exit-lab tests: 12 passed.
- Focused package compile: passed.
- `python -m compileall -q src\tradingbotsuite`: passed.
- `tests\research_discovery tests\contracts`: 678 passed.
- `tests\historical tests\research_artifacts`: 82 passed.
- High-risk backtesting/features/historical/research-artifacts/live suite:
  280 passed, 1 skipped.
- `python -m compileall -q src\tradingbot src\tradingbotsuite`: passed.
- Full `pytest -q`: 1530 passed, 1 skipped.
- `git diff --check`: passed with line-ending warnings only.
