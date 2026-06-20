# WPR106-90 Causal Stability Filter Rerun

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Move the WPR106-89 regime/volatility-bucket stability audit from diagnostic
post-trade overlays into causal pre-entry sparse-event filters, then rerun
focused 2024-forward historical-cycle evidence without calendar exclusions.

Use 2024-01-01 through 2026-04-30 only for tuning, selection, ranking, and
research summaries. Keep May 2026 fully out of this packet except as a future
benchmark holdout dependency for any later promising lead.

## Scope

- Add scoped sparse-event filter parameters for causal pre-entry regime and
  volatility-bucket admission checks using completed-bar columns already used by
  the research cycle/backtest evidence.
- Keep defaults behavior-compatible: existing sparse configurations must remain
  unchanged unless the new filters are explicitly set.
- Fail closed for invalid filter values or missing columns when a non-default
  filter is requested.
- Cover the new parameters and behavior with focused strategy contract tests.
- Build focused WPR106-90 BTCUSDT and ETHUSDT historical-cycle configs that
  rerun the strongest WPR106-88/WPR106-89 sparse leads plus causal non-calendar
  regime/volatility variants.
- Preserve active-rate evidence. Leads around 1 to 5 trades per active day may
  remain under consideration when costs, overlap, and month-to-month stability
  are recorded.
- Summarize pre-May net return, expectancy, trade counts, active days, trades
  per active day, active months, losing active months, inactive months, cost
  stress, side/regime/volatility exposure, and May-holdout eligibility status.

## Allowed paths

- `docs/work_packets/WPR106-90-causal-stability-filter-rerun.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_STABILITY_FILTER_RERUN_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/strategies/sparse_event_filter.py`
- `src/tradingbotsuite/strategies/parameters.py`
- `tests/contracts/test_strategy_contracts.py`
- `tests/tradingbotsuite/test_sparse_event_filter.py`
- `configs/research/wpr106_90_*.json`
- `data/research/historical_cycles/wpr106_90*/**`
- `data/research/wpr106_90*/**`

## Out of scope

- No live, paper, shadow, order-placement, position-sizing, runtime-mode, or
  live-configuration changes.
- No candidate pack, promotion artifact, or promotion-ready claim.
- No May 2026 tuning, selection, ranking, or optimizer feedback.
- No CUDA speedup claim unless a run truthfully uses CUDA-backed code and writes
  evidence for it. CPU multiprocessing/vectorization/caching improvements may
  be used when scoped to this packet.
- No broad strategy registry rewrites or live-boundary imports.

## Exit evidence

- Added default-off causal sparse filters:
  `allowed_regimes` and `allowed_volatility_buckets`.
- Added focused sparse contract coverage for regime filters,
  volatility-bucket filters, invalid values, and fail-closed missing context.
- WPR106-90 historical-cycle configs:
  `configs/research/wpr106_90_causal_stability_filter_btcusdt_v1.json` and
  `configs/research/wpr106_90_causal_stability_filter_ethusdt_v1.json`.
- Generated research-only cycle artifacts:
  `data/research/historical_cycles/wpr106_90_causal_stability_filter_btcusdt_v1/`
  and
  `data/research/historical_cycles/wpr106_90_causal_stability_filter_ethusdt_v1/`.
- Combined summary artifacts:
  `data/research/wpr106_90_causal_stability_filter/wpr106_90_causal_stability_filter_summary.json`,
  `data/research/wpr106_90_causal_stability_filter/wpr106_90_candidate_summary.csv`,
  `data/research/wpr106_90_causal_stability_filter/wpr106_90_candidate_summary.parquet`,
  and
  `data/research/wpr106_90_causal_stability_filter/wpr106_90_candidate_monthly_returns.csv`.
- Result: 150 candidate rows, 58 positive net/expectancy rows, 4 loose
  monthly-stability rows, 0 strict monthly-stability rows, and 0 May-holdout
  eligible rows. May 2026 remains unused.
- Stage report:
  `docs/stage_reports/STAGE_R106_CAUSAL_STABILITY_FILTER_RERUN_REPORT.md`.
- Ledger update.
- Validation baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Validation passed on 2026-06-11: compileall succeeded and contracts reported
454 passed.
