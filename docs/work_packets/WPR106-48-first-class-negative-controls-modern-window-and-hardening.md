# Work Packet: WPR106-48 first-class negative controls modern window and hardening

## Goal

Continue the post-WPR106-47 research-only replay evidence lane by making
negative controls first-class artifacts, hardening the discovery-to-candidate
bridge against control or incomplete replay evidence, and documenting the
modern-window blocker without relabeling full-window evidence.

## Current Repo Facts

- Current implementation branch:
  `codex/wpr106-47-full-replay-exit-lab-controls`.
- WPR106-47 wrote separated audit rows for full replay exit-lab evidence,
  window-scope evidence, negative-control status, and eligibility review.
- WPR106-47 negative controls were audit rows only; no normalized control
  artifact manifest family existed.
- WPR106-47 eligibility found zero eligible rows and no candidate packs.
- `ISSUE-R104-001` remains open because there is no validated positive edge and
  no durable candidate-ready evidence.

## Allowed Edit Paths

- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_*.md`
- `docs/work_packets/WPR106-*.md`
- `docs/work_packets/WPR106-*-progress.jsonl`
- `src/tradingbotsuite/research_discovery/replay_evidence_controls.py`
- `src/tradingbotsuite/research_discovery/candidate_pack_bridge.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `tests/research_discovery/test_replay_evidence_controls.py`
- `tests/research_discovery/test_candidate_pack_bridge.py`
- `tests/research_artifacts/test_candidate_pack.py`

Generated empirical artifacts under `data/research/operator_runs/` are local
research evidence outputs and remain ignored by git.

## Research Boundary

- Research outputs are not live signals.
- Artifacts must remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- Control artifacts must be marked `artifact_family: negative_control`,
  `control_only: true`, `candidate_evidence: false`, and
  `promotion_ready: false`.
- This packet must not add live signals, paper signals, order placement, sizing
  behavior, runtime-mode changes, live configuration writes, promotion-ready
  claims, candidate-ready claims, or candidate-pack writes.

## Implementation Plan

1. Add a normalized WPR106-48 negative-control artifact builder/writer and
   validator with four families: shuffled labels, shifted context, no KNN
   overlay, and no regime backend.
2. Preserve WPR106-47 audit behavior while allowing it to verify first-class
   control artifacts before marking control rows available.
3. Harden the discovery candidate-pack bridge so `control_only` and
   `artifact_family: negative_control` inputs are structurally rejected, and
   replay-scoped inputs can require replay profile, validation manifest, exact
   replay lineage, and modern-window evidence.
4. Add read-side replay-ledger compatibility normalization for old rows without
   rewriting immutable generated evidence.
5. Generate WPR106-48 local audit artifacts from existing WPR106-46/WPR106-47
   evidence. Preserve fail-closed modern-window status if no modern profile is
   present.
6. Update active docs, the ledger, the stage report, and the known issue notes
   with actual counts, validation, and residual blockers.

## Implementation Summary

- Added WPR106-48 first-class negative-control artifact support in
  `tradingbotsuite.research_discovery.replay_evidence_controls`.
- Added a WPR106-48 control manifest validator requiring
  `artifact_family: negative_control`, `control_only: true`,
  `candidate_evidence: false`, `candidate_pack_eligible: false`,
  `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- Added first-class rows for `shuffled_labels`, `shifted_context`,
  `no_knn_overlay`, and `no_regime_backend`, including deterministic seed,
  source hashes, replay/validation/modern-window provenance fields, shuffled
  label hashes, shifted-context hashes, explicit `overlay_used: false`, and
  `regime_model_backend: none` where applicable.
- Preserved the WPR106-47 audit schema while making it validate first-class
  WPR106-48 control manifests before treating a control as available.
- Hardened discovery candidate-pack bridge input checks so control-only and
  negative-control manifests are rejected before pack assembly.
- Hardened replay-scoped bridge manifests to require replay profile,
  validation manifest, exact replay lineage, and modern-window evidence when
  the manifest declares those bridge requirements.
- Added read-side ledger compatibility normalization for historical replay
  ledgers missing newer columns such as `regime_model_backend`; immutable
  generated evidence is not rewritten.
- Hardened the research candidate-pack validator and evidence-reader boundary
  so negative-control manifests are rejected even outside the discovery bridge.

## Empirical Artifact Evidence

Local output root:
`data/research/operator_runs/wpr106_48_first_class_negative_controls_modern_window_and_hardening`

Primary first-class negative-control manifest:
`data/research/operator_runs/wpr106_48_first_class_negative_controls_modern_window_and_hardening/negative_controls/wpr10648_negative_control_manifest.json`

Compatibility audit manifest:
`data/research/operator_runs/wpr106_48_first_class_negative_controls_modern_window_and_hardening/audit/wpr10647_replay_evidence_manifest.json`

Eligibility manifests:

- BTC:
  `data/research/operator_runs/wpr106_48_first_class_negative_controls_modern_window_and_hardening/eligibility/btcusdt/candidate_pack_eligibility_manifest.json`
- ETH:
  `data/research/operator_runs/wpr106_48_first_class_negative_controls_modern_window_and_hardening/eligibility/ethusdt/candidate_pack_eligibility_manifest.json`

| Artifact or count | Value |
| --- | ---: |
| First-class negative-control rows | 192 |
| First-class negative-control blocked rows | 192 |
| Control families | 4 |
| Full replay leads audited | 48 |
| WPR106-48 compatibility audit control rows | 192 |
| WPR106-48 compatibility audit control blocked rows | 192 |
| Full-window scope rows available | 2 |
| Modern-window scope rows blocked | 2 |
| Candidate eligibility rows | 48 |
| Candidate eligible rows | 0 |
| Candidate packs emitted | 0 |
| Replay-ledger schema mismatch after normalization | 0 |

The first-class negative-control artifacts are blocked by
`replay_profile_provenance_missing`, `validation_manifest_missing`, and
`modern_window_evidence_required` on all 192 rows. `shuffled_labels` also
records `source_label_column_missing` for 48 rows, and `shifted_context`
records `source_timestamp_column_missing` for 48 rows. The compatibility audit
links those first-class blockers back into the WPR106-47 audit shape without
claiming candidate evidence.

## Validation Plan

Focused validation:

```powershell
python -m compileall -q src\tradingbotsuite\research_discovery
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_replay_evidence_controls.py tests\research_discovery\test_candidate_pack_bridge.py -q
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

Review completed after implementation and validation:

- Control artifact helpers preserve research-only boundaries and deterministic
  hashes, and missing replay/validation/modern-window evidence fails closed.
- WPR106-47 compatibility audit validates first-class controls before marking
  control rows available.
- Candidate bridge rejects negative-control inputs and handles replay-scoped
  missing evidence with named blockers.
- Replay-ledger compatibility is read-side only; historical artifacts are not
  rewritten.
- Candidate-pack validation rejects negative-control evidence outside the
  bridge path.
- Tests cover available controls, fail-closed controls, bridge rejection,
  replay requirement blockers, old ledger normalization, and pack-level
  rejection.
- Stage docs keep `ISSUE-R104-001` open and make no candidate-ready,
  paper-ready, live-ready, or promotion-ready claim.

## Definition Of Done

- New negative-control artifacts are generated or explicitly blocked with
  first-class provenance.
- Candidate bridge rejects every negative-control family before pack assembly.
- Modern-window evidence remains blocked by a named missing-profile blocker
  unless a real modern-window profile is available.
- Replay ledger compatibility is read-side only and tested against old and new
  rows.
- No candidate pack is emitted and no live/paper/promotion behavior changes.
- Focused validation, baseline validation, diff check, and bottom-to-top review
  complete.

## Rollback Plan

Revert the WPR106-48 source, test, generated local audit artifacts, and
documentation paths from this packet. Do not revert unrelated local dirty
cache files or handoff prompts.
