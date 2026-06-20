# WPR106-94 Causal Session Filter Broad Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Continue the 2024-forward broad research search after the WPR106-93 May
holdout rejection by testing whether causal intraday and weekday session
structure can improve month-to-month stability for old and discarded
transparent and sparse/event families.

Use 2024-01-01 through 2026-04-30 only for tuning, selection, ranking, and
summaries. Keep May 2026 fully out of tuning. Use May 2026 only as a benchmark
holdout for a genuinely promising pre-May lead, and only where the required
source data has already been verified or is verified in a separate scoped
intake.

## Scope

- Inspect existing transparent trend, range, volatility-breakout, and
  sparse/event strategy contracts for any existing causal time/session filter
  support.
- If needed, add default-off causal UTC hour and weekday entry filters to the
  scoped strategy families without changing behavior for existing configs.
- Add focused strategy-contract coverage for default-off behavior, explicit
  allowed-hour/weekday behavior, and fail-closed invalid filter values.
- Build BTCUSDT and ETHUSDT WPR106-94 pre-May cycle configs that revisit
  transparent and sparse/event families with session-filter variants, including
  active 1 to 5 trades-per-active-day behavior when costs and overlap evidence
  are recorded.
- Prefer CPU-vector aggregate screening plus existing split/cost-stress
  refinement for shortlist rows. Use multiprocessing where the current runner
  supports it. Do not claim CUDA speedup unless a real measured CUDA-backed
  path writes evidence.
- Summarize net return, expectancy, active days, trades per active day, active
  months, losing months, inactive months, month concentration, split
  concentration, cost-stress survival, overlap/activity evidence, and
  May-holdout eligibility.

## Allowed paths

- `docs/work_packets/WPR106-94-causal-session-filter-broad-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_SESSION_FILTER_BROAD_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/strategies/_helpers.py`
- `src/tradingbotsuite/strategies/parameters.py`
- `src/tradingbotsuite/strategies/sparse_event_filter.py`
- `src/tradingbotsuite/strategies/trend.py`
- `src/tradingbotsuite/strategies/range_reversion.py`
- `src/tradingbotsuite/strategies/volatility_breakout.py`
- `tests/contracts/test_strategy_contracts.py`
- `configs/research/wpr106_94_*.json`
- `data/research/historical_cycles/wpr106_94*/**`
- `data/research/wpr106_94*/**`

## Out of scope

- No live, paper, shadow, order-placement, position-sizing, runtime-mode, or
  live-configuration changes.
- No candidate pack, promotion artifact, or promotion-ready claim.
- No May 2026 tuning, ranking, selection, optimizer feedback, feature
  selection, or threshold selection.
- No new provider/source intake in this packet unless a pre-May lead first
  justifies a separate holdout dependency.
- No broad research-cycle, data-contract, feature-registry, operator UI, or
  live-boundary rewrite.
- No post-trade calendar exclusion as candidate evidence; any time/session
  filter tested here must be computable before entry.

## Exit evidence

- Added default-off causal UTC session filters for the scoped strategy
  families:
  - `src/tradingbotsuite/strategies/_helpers.py`
  - `src/tradingbotsuite/strategies/trend.py`
  - `src/tradingbotsuite/strategies/volatility_breakout.py`
  - `src/tradingbotsuite/strategies/range_reversion.py`
  - `src/tradingbotsuite/strategies/sparse_event_filter.py`
- Extended strategy metadata for `allowed_hours_utc`,
  `allowed_weekdays_utc`, and scoped 4-bar transparent active-rate spacing in
  `src/tradingbotsuite/strategies/parameters.py`.
- Added focused strategy-contract coverage in
  `tests/contracts/test_strategy_contracts.py`.
- Oversized BTCUSDT v1 audit artifact retained as stopped compute:
  `data/research/historical_cycles/wpr106_94_causal_session_filter_broad_search_btcusdt_v1/`.
- Completed BTCUSDT and ETHUSDT v2 cycle configs:
  `configs/research/wpr106_94_causal_session_filter_broad_search_btcusdt_v2.json`
  and
  `configs/research/wpr106_94_causal_session_filter_broad_search_ethusdt_v2.json`.
- Completed v2 research-only cycle artifacts:
  `data/research/historical_cycles/wpr106_94_causal_session_filter_broad_search_btcusdt_v2/`
  and
  `data/research/historical_cycles/wpr106_94_causal_session_filter_broad_search_ethusdt_v2/`.
- Summary artifacts:
  `data/research/wpr106_94_causal_session_filter_broad_search/summary/wpr106_94_causal_session_filter_summary.json`,
  `data/research/wpr106_94_causal_session_filter_broad_search/summary/wpr106_94_symbol_summary.csv`,
  `data/research/wpr106_94_causal_session_filter_broad_search/summary/wpr106_94_candidate_summary.csv`,
  `data/research/wpr106_94_causal_session_filter_broad_search/summary/wpr106_94_candidate_summary.parquet`,
  and
  `data/research/wpr106_94_causal_session_filter_broad_search/summary/wpr106_94_monthly_returns.csv`.
- Result: each symbol produced 119 total rows, 115 research candidates, 11
  positive net/expectancy rows, 115 rows inside the 1 to 5
  trades-per-active-day band, 0 loose monthly-stability rows, 0 strict
  monthly-stability rows, and 0 May-holdout candidates. May 2026 remained
  unused.
- Stage report:
  `docs/stage_reports/STAGE_R106_CAUSAL_SESSION_FILTER_BROAD_SEARCH_REPORT.md`.
- Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_strategy_contracts.py -q
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Validation passed on 2026-06-11:

- Focused strategy contracts: 295 passed.
- Compileall: passed.
- Contracts: 460 passed.
