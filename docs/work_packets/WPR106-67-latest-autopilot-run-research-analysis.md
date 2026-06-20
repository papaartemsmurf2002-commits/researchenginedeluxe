# WPR106-67 - Latest Autopilot Run Research Analysis

## Purpose

Analyze the latest local Research Autopilot run, compare it with the previous
autopilot run, and record research-useful findings for future strategy,
feature, filter, exit-lab, and operator workflow work.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-67-latest-autopilot-run-research-analysis.md`
- `docs/stage_reports/STAGE_R106_LATEST_AUTOPILOT_RUN_RESEARCH_ANALYSIS_REPORT.md`
- `docs/KNOWN_ISSUES.md`

Read-only evidence paths:

- `data/research/operator_runs/research_autopilot/**`
- `data/research/operator_runs/historical_cycles/**`
- `data/research/operator_runs/discovery_runs/**`
- `data/research/operator_runs/analysis/**`
- `data/research/operator_runs/analysis_deltas/**`
- `data/research/operator_runs/frozen_entry_exit_lab/**`
- `data/research/operator_runs/candidate_pack_eligibility/**`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`

Out of scope:

- Source-code changes.
- Generated artifact rewrites.
- Candidate-pack creation.
- Live, paper, order-placement, sizing, runtime-mode, or promotion behavior.
- Stage advancement.

## Research Boundary

All findings are research-only interpretation of local artifacts. They are not
live signals, paper-ready evidence, candidate-ready claims, promotion-ready
claims, or performance guarantees.

## Validation Plan

- Parse and summarize the latest and previous autopilot manifests.
- Inspect linked cycle, discovery, analysis, delta, exit-lab, and eligibility
  artifacts without rewriting them.
- Record a stage-report style analysis with concrete artifact paths and next
  research angles.
- No code validation is required because this packet is documentation-only.

## Outcome

- Analysis report written:
  `docs/stage_reports/STAGE_R106_LATEST_AUTOPILOT_RUN_RESEARCH_ANALYSIS_REPORT.md`.
- Latest forced autopilot run
  `run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e` completed the
  upstream sequence that the previous forced run
  `run-research-autopilot-93c17f8f75b742ceba023cba6fea3c5b` failed before
  starting.
- Historical-cycle evidence is valid negative evidence: BTCUSDT and ETHUSDT
  each produced 63 rejected fixed-holding candidates, with zero positive net
  return and zero positive costed expectancy.
- Latest exact-discovery evidence is analytically invalid for lead selection:
  BTCUSDT and ETHUSDT each wrote 570240 blocked rows with
  `blocker_code: trial_execution_error` and sampled trial records failed with
  `regime_model_backend must match regime_mode`.
- Registered `ISSUE-R106-019` in `docs/KNOWN_ISSUES.md` as an open P1 blocking
  discovery-runtime/accounting issue.
- No generated research artifacts, source code, candidate packs, live/paper
  runtime behavior, order placement, sizing, or promotion state were changed.
