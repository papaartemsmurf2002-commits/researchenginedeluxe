# WPR106-95 Pre-May Cross-Family Portfolio Combination

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Continue the 2024-forward broad research search by revisiting old and
discarded positive rows as equal-capital research sleeves. Test whether
combining weakly different families, symbols, and filters produces better
month-to-month stability than any single row.

Use 2024-01-01 through 2026-04-30 only for tuning, selection, ranking, and
summaries. Keep May 2026 fully out of tuning. Any promising pre-May
combination must still receive a separate May 2026 benchmark before it can be
treated as more than a research lead.

## Scope

- Read existing pre-May WPR106 research cycle artifacts from selected closed
  packets, including sparse/event, exit-overlay, causal regime/volatility,
  active-rate density, and causal session-filter packets.
- Extract positive-net and positive-expectancy research rows with their
  monthly returns, trade counts, active days, strategy family, symbol, and
  rejection reasons.
- Deterministically enumerate equal-sleeve combinations across symbols and
  families after bounded prefilters to avoid an unbounded combinatorial search.
- Treat 1 to 5 aggregate trades per active day as acceptable when costs and
  overlap/activity evidence are recorded.
- Summarize portfolio net return, average sleeve expectancy, active months,
  losing months, positive months, concentration, aggregate trades per active
  day, family/symbol diversity, and May-holdout eligibility.
- Keep all artifacts research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-95-pre-may-cross-family-portfolio-combination.md`
- `docs/stage_reports/STAGE_R106_PRE_MAY_CROSS_FAMILY_PORTFOLIO_COMBINATION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_95*/**`

## Out of scope

- No live, paper, shadow, order-placement, position-sizing, runtime-mode, or
  live-configuration changes.
- No candidate pack, promotion artifact, or promotion-ready claim.
- No May 2026 tuning, ranking, selection, optimizer feedback, feature
  selection, or threshold selection.
- No strategy, feature, backtest-engine, research-cycle, or live-boundary code
  changes in this packet.
- No post-May data, no synthetic fallback, and no CUDA speedup claim.

## Exit evidence

- Loaded positive-net and positive-expectancy research rows from WPR106-87,
  WPR106-88, WPR106-90, WPR106-91, and WPR106-94 pre-May historical-cycle
  artifacts.
- Positive sleeve universe:
  `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_positive_sleeve_universe.parquet`
  and
  `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_positive_sleeve_universe.csv`.
- Full deterministic combination parquet:
  `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_portfolio_combinations.parquet`.
- Compact top-combo artifacts:
  `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_top_portfolio_combinations.csv`,
  `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_top_combo_members.csv`,
  and
  `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_top_combo_monthly_returns.csv`.
- Summary:
  `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_portfolio_combination_summary.json`.
- Result: 120 positive sleeves loaded, 64 sleeves selected into the bounded
  deterministic pool, 650,622 equal-sleeve combinations enumerated, 1,360 loose
  monthly-stability combinations, 0 strict monthly-stability combinations, and
  40 pre-May May-holdout diagnostic leads. May 2026 remained unused.
- Stage report:
  `docs/stage_reports/STAGE_R106_PRE_MAY_CROSS_FAMILY_PORTFOLIO_COMBINATION_REPORT.md`.
- Validation:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Validation passed on 2026-06-11:

- Compileall: passed.
- Contracts: 460 passed.
