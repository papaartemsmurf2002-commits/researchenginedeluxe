# WPR106-121 Volatility Squeeze Failed-Breakout Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test a genuinely new 2024-forward source family after WPR106-120 rejected
reranking the WPR106-119 portfolio universe. This packet searches 15m
volatility-squeeze, breakout-confirmation, and failed-breakout/fade variants
over the WPR106-96 verified BTCUSDT/ETHUSDT completed-bar feature frames. The
goal is to see whether compression-to-expansion and failed-expansion logic can
produce month-to-month stability without depending on the already rejected ETH
lead-lag/dense ensemble archetype.

## Scope

- Use the WPR106-96 verified feature frames:
  - `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/btcusdt_features_price_trend_vol_2024_01_to_2026_05.parquet`
  - `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/ethusdt_features_price_perp_aggflow_no_wt_2024_01_to_2026_05.parquet`
- Use only 2024-01-01 through 2026-04-30 for score construction choices,
  feature/filter threshold calibration, side choice, session/regime choice,
  exit choice, ranking, and fixed selection.
- Keep May 2026 fully out of tuning. Use May only after fixed pre-May
  selections are written.
- Evaluate completed-bar 15m source variants, including:
  - low-volatility squeeze breakout follow;
  - squeeze fakeout/fade;
  - failed range expansion fade;
  - volatility expansion pullback follow;
  - flow-confirmed squeeze breakout where ETH/BTC aggTrade proxy features are
    available;
  - transparent no-flow controls for the same score families.
- Calibrate thresholds on pre-May only to target roughly 1, 2.5, or 5 raw
  signals per active day, with max accepted trades/day caps and no-overlap
  handling.
- Use realistic taker/slippage/spread costs and stress them.
- Keep all artifacts `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.

## Allowed paths

- `docs/work_packets/WPR106-121-volatility-squeeze-failed-breakout-search.md`
- `docs/stage_reports/STAGE_R106_VOLATILITY_SQUEEZE_FAILED_BREAKOUT_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_121*/**`

## Out of scope

- No May 2026 tuning, feedback, feature choice, threshold choice, side choice,
  exit choice, ranking choice, cost-policy choice, or selection choice.
- No shared `src/tradingbotsuite` package, strategy registry, feature registry,
  backtest engine, optimizer, research-cycle, candidate-pack, live, runtime,
  config, or test changes.
- No candidate pack, paper/live artifact, order placement, position sizing,
  live runtime change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data and no silent use of unavailable context as zero.

## Exit evidence

- A deterministic WPR106-121 runner and artifacts are written under
  `data/research/wpr106_121*/`.
- The report records source feature coverage, evaluated row count,
  strict/loose/positive counts, selected rows, monthly and annual diagnostics,
  active-rate diagnostics, overlap/day-cap effects, cost-stress behavior,
  May benchmark result, and rejected/promising archetypes.
- May benchmark artifacts are written separately and only after fixed pre-May
  selection.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Outcome

Closed as negative research evidence. The final fixed run evaluated 18,432
pre-May rows across BTCUSDT/ETHUSDT volatility squeeze, breakout-follow,
failed-expansion fade, expansion-pullback, range-compression, flow-confirmed,
and no-flow control variants. Thresholds, filters, side/session/regime choices,
exit choices, ranking, and selection used only 2024-01-01 through 2026-04-30.
May 2026 remained benchmark-only after fixed loose selection.

The search found 1,998 positive pre-May rows, 9 loose rows, and 0 strict rows.
The loose rows were concentrated in ETHUSDT long US/high-vol squeeze-follow,
flow-confirmed squeeze, and no-flow control variants plus one BTCUSDT choppy
failed-expansion fade; all selected rows used fixed 32-bar exits and traded
about one time per active day. They still had 6 to 7 losing pre-May months,
missed the strict month-stability bar, and showed max drawdowns from -10.1% to
-21.6%.

The fixed May benchmark rejected the family as candidate-ready evidence:
1 selected row was May-positive, 8 were May-negative, and 0 were flat. Best May
return was +0.030321 from the lowest-ranked BTCUSDT failed-expansion fade, while
the ETHUSDT selected rows returned -0.036954 to -0.051256. Median selected May
return was -0.036954 and worst selected May return was -0.051256.

Artifacts:

- `data/research/wpr106_121_volatility_squeeze_failed_breakout_search/wpr106_121_volatility_squeeze_failed_breakout_summary.json`
- `data/research/wpr106_121_volatility_squeeze_failed_breakout_search/pre_may/vol_squeeze_ranking.parquet`
- `data/research/wpr106_121_volatility_squeeze_failed_breakout_search/pre_may/selected_pre_may.csv`
- `data/research/wpr106_121_volatility_squeeze_failed_breakout_search/may_benchmark/selected_may_benchmark_metrics.csv`

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_121_volatility_squeeze_failed_breakout_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
