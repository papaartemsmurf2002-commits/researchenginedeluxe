# WPR106-123 Flow-Price Absorption Divergence Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test a fresh 2024-forward 15m flow/price absorption and divergence source
family after WPR106-121 rejected squeeze/failure logic and WPR106-122 rejected
a simple KNN complement layer. This packet focuses on whether taker-flow proxy
pressure that fails to move price, confirms pullbacks, or exhausts directional
movement can produce stable active rows without using May 2026 for tuning.

## Scope

- Use the WPR106-96 verified feature frames:
  - `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/btcusdt_features_price_trend_vol_2024_01_to_2026_05.parquet`
  - `data/research/wpr106_96_may_2026_portfolio_holdout_benchmark/features/ethusdt_features_price_perp_aggflow_no_wt_2024_01_to_2026_05.parquet`
- Build completed-bar 15m source scores from price movement, taker-buy quote
  share, signed quote imbalance, quote-volume z-score, CVD-slope proxy,
  sweep/burst proxy, trend state, path state, and volatility state.
- Evaluate flow/price absorption, flow-confirmed pullback, directional
  exhaustion, flow/price divergence fade, and transparent no-flow controls.
- Use only 2024-01-01 through 2026-04-30 for feature/filter threshold
  calibration, score choice, side/session/regime choice, exit choice, ranking,
  and fixed selection.
- Keep May 2026 fully out of tuning. Use May only after fixed pre-May strict
  or loose selections are written.
- Allow active rows around 1 to 5 trades per day when costs, overlap,
  max-trades/day caps, drawdown, and monthly stability are handled.
- Keep all artifacts `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.

## Allowed paths

- `docs/work_packets/WPR106-123-flow-price-absorption-divergence-search.md`
- `docs/stage_reports/STAGE_R106_FLOW_PRICE_ABSORPTION_DIVERGENCE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_123*/**`

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

- A deterministic WPR106-123 runner and artifacts are written under
  `data/research/wpr106_123*/`.
- The report records feature/source coverage, evaluated row count,
  strict/loose/positive counts, selected rows, monthly and annual diagnostics,
  active-rate diagnostics, overlap/day-cap effects, cost-stress behavior,
  May benchmark result when applicable, and rejected/promising archetypes.
- May benchmark artifacts are written separately and only after fixed pre-May
  strict or loose selection.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Outcome

Closed as negative research evidence. The first broader grid timed out before
final artifacts, so the final deterministic run narrowed to fixed exits,
long/short sides, two active-rate targets, all/US sessions, all/flow-active
regimes, and the main all/flow-active/absorption filters.

The final runner evaluated 2,304 pre-May rows. It found 343 positive pre-May
rows, 182 annual-target rows, 0 loose rows, and 0 strict rows. No May benchmark
was run because no strict or loose pre-May row existed.

The failure mode is explicit:

- Annual-target rows were too sparse, with positive annual-target rows maxing
  out at 8 trades and 8 active months.
- Active rows reached 28 active months and could have strong pre-May returns,
  especially ETHUSDT flow-divergence/flow-follow long fixed-32 rows, but they
  failed annual month stability with 9 to 11 losing months and typically 4 to
  6 losing months in either 2024 or 2025.
- BTCUSDT had only basic taker quote proxy context, while ETHUSDT had the
  richer aggTrade proxy, CVD-slope proxy, and burst proxy columns.

Artifacts:

- `data/research/wpr106_123_flow_price_absorption_divergence_search/wpr106_123_flow_price_absorption_divergence_summary.json`
- `data/research/wpr106_123_flow_price_absorption_divergence_search/pre_may/feature_manifest.csv`
- `data/research/wpr106_123_flow_price_absorption_divergence_search/pre_may/flow_price_ranking.parquet`
- `data/research/wpr106_123_flow_price_absorption_divergence_search/pre_may/selected_pre_may.csv`
- `data/research/wpr106_123_flow_price_absorption_divergence_search/may_benchmark/selected_may_benchmark_metrics.csv`

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_123_flow_price_absorption_divergence_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
