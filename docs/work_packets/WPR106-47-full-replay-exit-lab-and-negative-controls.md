# Work Packet: WPR106-47 full replay exit lab and negative controls

## Goal

Run the next research-only evidence packet after WPR106-46 exact replay-overlay
representability. The packet tests four separate theories without mixing claims:

1. Full frozen-entry exit-lab coverage for all 48 exact replay leads.
2. Modern-window versus full-window replay comparison, with scope labels kept
   separate.
3. Negative-control and leakage stress artifacts for shuffled labels, shifted
   context, no-KNN baseline, and no-regime baseline where honest data and
   existing simulators support them.
4. Candidate eligibility and gate review after the new evidence exists.

## Current Repo Facts

- Current implementation branch: `codex/wpr106-46-exact-replay-overlay`.
- WPR106-46 made all 48 WPR106-31 replay leads exactly representable and
  generated 48 singleton replay-overlay historical-cycle specs locally.
- WPR106-46 bounded BTC/ETH cycle smokes proved candidate-scoped overlay
  provenance reaches rankings, backtest indexes, and gate reports.
- No candidate pack was written by WPR106-46; zero eligible rows remains a valid
  research outcome.
- `ISSUE-R104-001` remains open until durable candidate-depth data, deep cycles,
  exact sweeps, full exit labs, negative controls, and eligibility evidence
  justify closure.

## Allowed Edit Paths

- `docs/ACTIVE_INDEX.md`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_*.md`
- `docs/work_packets/WPR106-*.md`
- `docs/work_packets/WPR106-*-progress.jsonl`
- `configs/discovery/**`
- `configs/research/**`
- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/research_artifacts/**`
- `tests/research_discovery/**`
- `tests/historical/**`
- `tests/research_artifacts/**`
- `tests/contracts/**`

Generated empirical artifacts under `data/research/operator_runs/` are local
research evidence outputs and remain ignored by git.

## Research Boundary

- Research outputs are not live signals.
- Artifacts must remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- This packet must not add live signals, paper signals, order placement, sizing
  behavior, runtime-mode changes, live configuration writes, promotion-ready
  claims, or candidate-ready claims.
- Candidate packs must not be written unless the existing gate stack passes.
- Negative controls must be clearly labeled as controls and must not be
  consumable as production candidate evidence.

## Implementation Plan

1. Inspect WPR106-46 replay-overlay specs, WPR106-31 replay artifacts, and
   existing frozen-entry exit-lab contracts.
2. Add or run a batch path that covers all 48 replay leads, preserving
   per-lead blocked reasons when an exit-lab input cannot be trusted.
3. Build modern-window/full-window comparison artifacts with explicit
   `evidence_scope` labels, source hashes, and non-comparability reasons when
   one side is missing.
4. Build negative-control artifacts only where provenance is honest:
   shuffled-label, shifted-context, no-KNN, and no-regime controls must be
   labeled `control_only` and fail closed when required provenance is missing.
5. Run candidate eligibility/gate review only after exit-lab and control
   evidence exists.
6. Update active docs and stage report with artifact counts, validation, known
   issue impact, and research-only boundary language.

## Implementation Summary

- Added `tradingbotsuite.research_discovery.replay_evidence_controls`, a
  WPR106-47 audit artifact writer that keeps full replay exit-lab evidence,
  window-scope evidence, and negative-control evidence in separate Parquet
  tables under one research-only manifest.
- Added contract tests proving the WPR106-47 audit manifest stays
  `research_only`, `observe_only`, `promotion_ready: false`, and cannot carry
  candidate-pack or live-adjacent flags.
- Verified the existing full WPR106-31 frozen-entry exit-lab artifacts cover all
  48 replay leads: 24 BTC and 24 ETH.
- Attempted a fresh WPR106-47 full exit-lab rerun; the BTC run exceeded a
  10-minute local timeout and was stopped. The packet therefore uses the
  already-completed WPR106-31 full exit-lab artifacts as source evidence and
  records the rerun as blocked by runtime cost rather than overwriting local
  evidence.
- Wrote WPR106-47 local audit artifacts under
  `data/research/operator_runs/wpr106_47_full_replay_exit_lab_and_negative_controls`.
- Ran candidate eligibility bridge audits for BTC and ETH after the audit
  evidence existed, using the bounded WPR106-46 cycle-smoke manifests and a
  one-row candidate-ID map per symbol.

## Empirical Artifact Evidence

Local output root:
`data/research/operator_runs/wpr106_47_full_replay_exit_lab_and_negative_controls`

| Artifact or count | Value |
| --- | ---: |
| Full replay leads audited | 48 |
| BTC full exit-lab leads | 24 |
| ETH full exit-lab leads | 24 |
| Exit-lab comparison rows | 96 |
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

Primary WPR106-47 audit manifest:

`data/research/operator_runs/wpr106_47_full_replay_exit_lab_and_negative_controls/audit/wpr10647_replay_evidence_manifest.json`

Eligibility manifests:

- BTC:
  `data/research/operator_runs/wpr106_47_full_replay_exit_lab_and_negative_controls/eligibility/btcusdt/candidate_pack_eligibility_manifest.json`
- ETH:
  `data/research/operator_runs/wpr106_47_full_replay_exit_lab_and_negative_controls/eligibility/ethusdt/candidate_pack_eligibility_manifest.json`

The modern-window rows are explicitly blocked with
`modern_window_profile_artifact_missing`. Negative-control rows are explicitly
blocked for missing first-class `shuffled_labels`, `shifted_context`,
`no_knn_baseline`, and `no_regime_baseline` control artifacts.

Candidate eligibility produced zero eligible rows for both symbols. The bridge
reported partial discovery-to-cycle ranking overlap because only the bounded
WPR106-46 singleton cycle smokes exist for one replay lead per symbol. The top
blocking reasons include replay-ledger schema mismatch against the current
bridge schema, missing multiple-testing and validation-floor manifests, exit-lab
no-improvement over fixed holding, and 23 of 24 discovery rows per symbol
missing from the bounded cycle-smoke rankings.

## Validation Plan

Focused validation:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\historical tests\research_artifacts -q
```

Broaden when shared contracts change:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\backtesting tests\features tests\historical tests\research_artifacts tests\live -q
python -m compileall -q src\tradingbot src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
```

Validation completed:

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
- `tests\research_discovery tests\contracts`: 678 passed.
- `tests\historical tests\research_artifacts`: 82 passed.
- High-risk backtesting/features/historical/research-artifacts/live suite:
  280 passed, 1 skipped.
- Full `pytest -q`: 1530 passed, 1 skipped.
- Full compile for `src\tradingbot src\tradingbotsuite`: passed.
- `git diff --check`: passed with line-ending warnings only.

## Definition Of Done

- All 48 replay leads are processed by full exit-lab evidence or blocked with
  explicit fail-closed reasons.
- Modern-window and full-window evidence remain separately labeled.
- Negative controls are generated or blocked with explicit provenance reasons.
- Gate reports show whether any rows are eligible.
- Candidate packs are absent unless existing gates pass.
- `ISSUE-R104-001` remains open unless durable candidate-depth data, deep
  cycles, exact sweeps, exit labs, negative controls, and eligibility evidence
  are sufficient to close it.
- No live/paper/order/sizing/runtime/promotion behavior is introduced.

## Rollback Plan

Revert the WPR106-47 code, test, and documentation paths from this packet. Do
not revert unrelated local dirty files or pytest cache state unless explicitly
requested.
