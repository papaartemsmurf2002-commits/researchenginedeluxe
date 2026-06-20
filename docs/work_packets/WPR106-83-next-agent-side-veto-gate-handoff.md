# WPR106-83 - Next Agent Side-Veto Gate Handoff

## Purpose

Create the next-agent handoff after WPR106-82. The handoff should turn the
optimized BTCUSDT post-selection long-only sparse lead into a broad, concrete
next task: close the remaining research-only gate evidence gaps without
weakening candidate-pack safety, promotion boundaries, or live separation.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-83-next-agent-side-veto-gate-handoff.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_82_POST_SELECTION_SIDE_VETO_OPTIMIZER.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`

Read-only evidence and reference paths:

- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/stage_reports/STAGE_R106_POST_SELECTION_SIDE_VETO_OPTIMIZER_REPORT.md`
- `docs/stage_reports/STAGE_R106_SPARSE_SIDE_VETO_VALIDATION_REPORT.md`
- `configs/research/sparse_side_veto_optimizer_btcusdt_r106_v1.json`
- `configs/research/sparse_side_veto_btcusdt_r106_v1.json`
- `data/research/historical_cycles/sparse_side_veto_optimizer_btcusdt_r106_v1/**`
- `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/**`
- `data/research/monte_carlo_exit_sizing/wpr106_82/**`
- `data/research/monte_carlo_exit_sizing/wpr106_81/**`

Out of scope:

- Source-code changes, research-cycle reruns, optimizer reruns, or generated
  artifact rewrites.
- Candidate-pack creation, paper/live artifacts, or promotion artifacts.
- Live, paper, order-placement, runtime-mode, live-configuration, or actual
  position-sizing behavior.
- New provider intake, fixture rewrites, catalog rebuilds, or venue downloads.
- Claiming the optimized one-sided row is candidate-ready before the gate,
  feature-ablation, and stability-region blockers are resolved.

## Plan

1. Write a next-agent handoff that summarizes WPR106-80 through WPR106-82.
2. Name the current optimized research lead and its critical evidence metrics.
3. Define the broad next task as research-only gate/evidence closure for
   explicit one-sided side-veto strategies.
4. Make acceptance criteria fail-closed: paired opposite-side controls,
   no-trade and transparent baselines, feature ablation, split/cost/stability
   evidence, and research-only provenance are required before any eligibility
   claim.
5. Include a copyable `/goal` prompt for the next agent.
6. Register the handoff packet in the orchestrator ledger.

## Research Boundary

This packet is documentation only. It may formulate the next research task,
but it cannot make candidates eligible, create candidate packs, size positions,
place orders, alter runtime mode, write live configuration, or claim promotion
readiness.
