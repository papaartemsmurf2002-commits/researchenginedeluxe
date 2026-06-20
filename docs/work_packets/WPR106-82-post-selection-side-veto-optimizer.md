# WPR106-82 - Post-Selection Side Veto Optimizer

## Purpose

Run a bounded expensive optimizer sweep around the WPR106-81 BTCUSDT
post-selection long-only sparse rows. The aggTrade-contrarian sparse row is the
lead because it ranked first, survived split and cost-stress evidence, and had
the strongest Monte Carlo profile under the user-requested 0.0432% taker fee
per side with funding ignored.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-82-post-selection-side-veto-optimizer.md`
- `docs/stage_reports/STAGE_R106_POST_SELECTION_SIDE_VETO_OPTIMIZER_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/sparse_side_veto_optimizer_btcusdt_r106_v1.json`

Allowed generated research-output paths:

- `data/research/historical_cycles/sparse_side_veto_optimizer_btcusdt_r106_v1/**`
- `data/research/monte_carlo_exit_sizing/wpr106_82/**`

Read-only evidence and reference paths:

- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/stage_reports/STAGE_R106_SPARSE_SIDE_VETO_VALIDATION_REPORT.md`
- `configs/research/sparse_side_veto_btcusdt_r106_v1.json`
- `data/research/historical_cycles/sparse_side_veto_btcusdt_r106_v1/**`
- `data/research/monte_carlo_exit_sizing/wpr106_81/**`

Out of scope:

- Candidate-pack creation, paper/live artifacts, or promotion artifacts.
- Live, paper, order-placement, runtime-mode, live-configuration, or actual
  position-sizing behavior.
- Provider downloads, fixture rewrites, catalog rebuilds, or new venue intake.
- KNN/exact-discovery reruns, Martingale overlays, or fixed TP/SL claims.
- Treating optimizer output as candidate-ready before one-sided gate,
  feature-ablation, and stability-region blockers are resolved.

## Plan

1. Add a BTCUSDT historical-cycle optimizer spec using parameter-grid search
   spaces for post-selection long-only sparse rows:
   - aggTrade-contrarian sparse variants;
   - price-only sparse variants;
   - short post-selection controls;
   - no-trade and transparent volatility controls.
2. Use bounded `latin_hypercube` sampling with a larger candidate budget than
   WPR106-81 and refine only the strongest rows through split and cost stress.
3. Run the historical cycle on the durable public archive fixture.
4. Run Monte Carlo on the optimized top rows with 0.0432% taker fee per side,
   funding ignored, and slippage ignored for the offline analysis.
5. Document whether an optimized row improves the WPR106-81 lead and what gate
   blockers remain.

## Research Boundary

All outputs remain `research_only: true`, `observe_only: true`, and
`promotion_ready: false`. This packet may identify optimizer follow-up
directions, but it cannot size positions, place orders, alter runtime mode,
write live configuration, create candidate packs, or claim promotion readiness.
