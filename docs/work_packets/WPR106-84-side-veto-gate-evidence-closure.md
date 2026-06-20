# WPR106-84 - Side-Veto Gate Evidence Closure

## Purpose

Close `ISSUE-R106-024` without weakening candidate-pack safety. The packet
teaches the research gates how to represent explicit one-sided side-veto
contracts, then tests the optimized BTCUSDT aggTrade sparse lead with paired
opposite-side controls, no-trade and transparent baselines, feature ablation,
split/cost/stability evidence, and research-only provenance.

The starting lead is:

`941c7d1a1a3b8669c66e816ee465dc30cf18b1fba56c54b95555a027cdf046d6`

from WPR106-82. It remains research-only unless every gate passes.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-84-side-veto-gate-evidence-closure.md`
- `docs/stage_reports/STAGE_R106_SIDE_VETO_GATE_EVIDENCE_CLOSURE_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/sparse_side_veto_gate_evidence_btcusdt_r106_v1.json`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research_artifacts/candidate_pack.py`
- `src/tradingbotsuite/optimization/stability.py`
- `tests/historical/test_full_cycle_synthetic.py`
- `tests/optimization/test_region_of_stability.py`
- `tests/research_artifacts/test_candidate_pack.py`

Allowed generated research-output paths:

- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/**`

Read-only evidence and reference paths:

- `AGENTS.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_82_POST_SELECTION_SIDE_VETO_OPTIMIZER.md`
- `docs/stage_reports/STAGE_R106_SPARSE_SIDE_VETO_VALIDATION_REPORT.md`
- `docs/stage_reports/STAGE_R106_POST_SELECTION_SIDE_VETO_OPTIMIZER_REPORT.md`
- `configs/research/sparse_side_veto_btcusdt_r106_v1.json`
- `configs/research/sparse_side_veto_optimizer_btcusdt_r106_v1.json`
- `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/**`
- `data/research/historical_cycles/sparse_side_veto_optimizer_btcusdt_r106_v1/**`
- `data/research/monte_carlo_exit_sizing/wpr106_81/**`
- `data/research/monte_carlo_exit_sizing/wpr106_82/**`

Out of scope:

- Candidate-pack creation unless all research gates pass and existing
  candidate-pack contracts allow it.
- Paper/live artifacts, order placement, position sizing, runtime-mode changes,
  live configuration writes, or promotion artifacts.
- New provider downloads, fixture rewrites, catalog rebuilds, or venue intake.
- Lower-timeframe TP/SL or Martingale claims.
- Treating a one-sided PnL result as candidate-ready when paired controls,
  ablation, stability, split, cost, and provenance evidence are incomplete.

## Plan

1. Audit the WPR106-82 artifact math and gate reasons before code changes.
2. Add explicit one-sided side-veto gate semantics:
   - only accepted for a strategy contract that declares one allowed side;
   - actual trade evidence must contain the allowed side only;
   - a paired opposite-side control with matching non-side parameters must be
     present and fail versus no-trade;
   - no-trade and transparent baselines must be present and beaten;
   - artifacts remain `research_only`, `observe_only`, and
     `promotion_ready: false`.
3. Fix feature-ablation matching for sparse aggTrade features so flow-only
   parameters do not prevent matching a price-only comparator with the same
   core entry/exit contract.
4. Keep opposite-side controls out of same-side stability neighborhoods.
5. Make grouped side metrics either mathematically match their metric name or
   expose the summed-return interpretation explicitly.
6. Add focused tests for the gate, pack validation, and stability family logic.
7. Run a focused BTCUSDT side-veto evidence cycle with the optimized lead,
   price-only ablation comparator, exact short controls, no-trade/transparent
   baselines, and a small validated long-side stability neighborhood.
8. Document the result fail-closed if any evidence is still missing or failing.

## Research Boundary

All outputs remain `research_only: true`, `observe_only: true`, and
`promotion_ready: false`. This packet cannot place orders, size positions,
alter runtime mode, write live configuration, create paper/live artifacts, or
claim promotion readiness.
