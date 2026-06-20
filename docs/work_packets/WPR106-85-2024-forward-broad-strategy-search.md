# WPR106-85 - 2024-Forward Broad Strategy Search

## Purpose

Move the research effort away from defending the rejected BTCUSDT sparse
side-veto lead and into a broader 2024-forward strategy search. The rejected
side-veto row remains useful negative evidence, but the next work should test
old, discarded, and novel strategy families for month-to-month stability after
realistic costs.

Default tuning must use 2024-01-01 through 2026-04-30 UTC. May 2026 is a hard
benchmark holdout and must not influence strategy, feature, threshold, filter,
exit, cost, model, or candidate-selection choices.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-85-2024-forward-broad-strategy-search.md`
- `docs/stage_reports/STAGE_R106_2024_FORWARD_BROAD_STRATEGY_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_85_2024_FORWARD_BROAD_STRATEGY_SEARCH.md`
- `configs/research/*wpr106_85*.json`
- `configs/research/*2024_forward*.json`
- `src/tradingbotsuite/research/**`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/strategies/**`
- `src/tradingbotsuite/features/**`
- `src/tradingbotsuite/backtesting/**`
- `src/tradingbotsuite/optimization/**`
- `tests/contracts/**`
- `tests/historical/**`
- `tests/tradingbotsuite/**`
- `tests/optimization/**`
- `tests/features/**`
- `tests/backtesting/**`

Allowed generated research-output paths:

- `data/research/historical_cycles/*wpr106_85*/**`
- `data/research/historical_cycles/*2024_forward*/**`
- `data/research/strategy_search/wpr106_85*/**`
- `data/research/wpr106_85*/**`
- `data/research/hmm_knn_four_bar_archive_mapping/wpr106_85*/**`
- `data/research/hmm_knn_four_bar_validation/wpr106_85*/**`
- `data/research/monte_carlo_exit_sizing/wpr106_85*/**`

Read-only evidence and reference paths:

- `AGENTS.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `docs/stage_reports/STAGE_R106_SIDE_VETO_GATE_EVIDENCE_CLOSURE_REPORT.md`
- `docs/stage_reports/STAGE_R106_POST_SELECTION_SIDE_VETO_OPTIMIZER_REPORT.md`
- `docs/stage_reports/STAGE_R106_SPARSE_SIDE_VETO_VALIDATION_REPORT.md`
- `docs/stage_reports/STAGE_R106_LOCAL_BINANCE_ARCHIVE_FOUR_BAR_MAPPER_REPORT.md`
- `docs/stage_reports/STAGE_R106_VENUE_FIRST_NO_RSI_KNN_FOUR_BAR_REPORT.md`
- `docs/NEXT_AGENT_HANDOFF_WPR106_82_POST_SELECTION_SIDE_VETO_OPTIMIZER.md`
- `configs/research/sparse_side_veto_gate_evidence_btcusdt_r106_v1.json`
- `configs/research/sparse_side_veto_optimizer_btcusdt_r106_v1.json`
- `configs/research/no_rsi_knn_four_bar_matrix_btcusdt_r106_v1.json`
- `configs/research/no_rsi_knn_four_bar_matrix_ethusdt_r106_v1.json`
- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/**`
- `data/research/hmm_knn_four_bar_archive_mapping/wpr106_79_full_local_archive_map/**`

Out of scope:

- Candidate-pack creation unless every existing research gate passes after
  pre-May validation and May 2026 benchmark evidence.
- Paper/live artifacts, order placement, position sizing, runtime-mode changes,
  live configuration writes, or promotion artifacts.
- New provider downloads, fixture rewrites, catalog rebuilds, or venue intake
  unless a narrower follow-up packet explicitly scopes them.
- Using May 2026 to tune or select a strategy family.
- Treating a high entry rate as either sufficient evidence or an automatic
  rejection without cost, overlap, monthly, split, and drawdown analysis.

## Plan

1. Inventory available 2024-forward data and existing strategy/spec surfaces,
   including sparse filters, transparent baselines, trend/range/volatility,
   perp-context, funding/OI/liquidation/timing, HMM/KNN, Lorentzian KNN,
   no-RSI four-bar KNN, replay-overlay, and simple ensemble/veto families.
2. Add or configure a staged research-only screening path that:
   - tunes on 2024-01-01 through 2026-04-30 UTC by default;
   - excludes 2026-05-01 through 2026-05-31 UTC from tuning;
   - ranks by post-cost return, monthly stability, drawdown, downside risk,
     split balance, trade frequency adequacy, cost stress, and ablations;
   - allows normal active rates such as 1 to 5 entries per day when costs and
     overlap are explicit.
3. Run cheap diagnostic sweeps before long runs. Use multiprocessing,
   vectorization, caching, and CUDA only when deterministic and truthfully
   represented in manifests.
4. For any promising pre-May lead, run May 2026 as a separate benchmark holdout
   with trades, post-cost net return, drawdown, downside-risk metric,
   month/day-level behavior, and contradiction notes.
5. Add focused code/tests if existing tooling cannot report the required
   monthly stability, holdout isolation, active-rate, or artifact-boundary
   evidence.
6. Document all rejected and promising families without promotion claims.

## Research Boundary

All outputs remain `research_only: true`, `observe_only: true`, and
`promotion_ready: false`. This packet cannot place orders, size positions,
alter runtime mode, write live configuration, create paper/live artifacts, or
claim candidate, paper, live, or promotion readiness.
