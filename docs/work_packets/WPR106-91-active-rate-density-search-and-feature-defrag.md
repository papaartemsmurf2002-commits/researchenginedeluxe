# WPR106-91 Active-Rate Density Search And Feature Defrag

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Continue the 2024-forward broad research search after WPR106-90 by testing
whether higher active entry rates are unfairly underexplored, while also
reducing the known wide-feature fragmentation overhead that slows sparse
aggTrade cycles.

Use 2024-01-01 through 2026-04-30 only for tuning, selection, ranking, and
summaries. Keep May 2026 fully out of this packet except as a future benchmark
holdout dependency for any later promising lead.

## Scope

- Make `build_feature_frame` construct registered feature and missingness
  columns in a less fragmented way without changing column names, values,
  hashes, completed-bar semantics, or availability reports.
- Add focused feature-builder coverage proving wide feature construction does
  not emit pandas fragmentation warnings and preserves missingness columns.
- Build BTCUSDT and ETHUSDT active-rate search configs that deliberately test
  sparse-event and transparent families with more frequent entry settings,
  including 1 to 5 entries per active day when costs and overlap are recorded.
- Prefer CPU-vector fixed-holding paths for cheap broad screening, and include
  a small number of primary-bar runner/trailing exits where useful. CUDA remains
  disabled unless a later packet truthfully exercises a CUDA path.
- Summarize net return, expectancy, active days, trades per active day, active
  months, losing months, inactive months, monthly concentration, overlap, split
  and cost-stress evidence, and May-holdout eligibility.

## Allowed paths

- `docs/work_packets/WPR106-91-active-rate-density-search-and-feature-defrag.md`
- `docs/stage_reports/STAGE_R106_ACTIVE_RATE_DENSITY_SEARCH_AND_FEATURE_DEFRAG_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/features/packs.py`
- `tests/features/test_feature_builders.py`
- `configs/research/wpr106_91_*.json`
- `data/research/historical_cycles/wpr106_91*/**`
- `data/research/wpr106_91*/**`

## Out of scope

- No live, paper, shadow, order-placement, position-sizing, runtime-mode, or
  live-configuration changes.
- No candidate pack, promotion artifact, or promotion-ready claim.
- No May 2026 tuning, selection, ranking, or optimizer feedback.
- No CUDA speedup claim unless a real CUDA-backed path runs and writes evidence.
- No broad data contract, feature registry, strategy registry, or live-boundary
  rewrites.

## Exit evidence

- `build_feature_frame` now batches missing manifest feature columns and
  missingness indicators with `pd.concat`, then copies once to defragment the
  final feature frame.
- Focused feature-builder regression:
  `tests/features/test_feature_builders.py::test_price_perp_aggflow_no_wt_builds_wide_missingness_without_fragmentation_warning`.
- BTCUSDT and ETHUSDT WPR106-91 pre-May cycle configs:
  `configs/research/wpr106_91_active_rate_density_search_btcusdt_v1.json`
  and
  `configs/research/wpr106_91_active_rate_density_search_ethusdt_v1.json`.
- Generated research-only cycle artifacts:
  `data/research/historical_cycles/wpr106_91_active_rate_density_search_btcusdt_v1/`
  and
  `data/research/historical_cycles/wpr106_91_active_rate_density_search_ethusdt_v1/`.
- Combined summary artifacts:
  `data/research/wpr106_91_active_rate_density_search/wpr106_91_active_rate_density_search_summary.json`,
  `data/research/wpr106_91_active_rate_density_search/wpr106_91_candidate_summary.csv`,
  `data/research/wpr106_91_active_rate_density_search/wpr106_91_candidate_summary.parquet`,
  and
  `data/research/wpr106_91_active_rate_density_search/wpr106_91_candidate_monthly_returns.csv`.
- Result: 268 candidate rows, 14 positive net/expectancy rows, 254 rows inside
  the 1 to 5 trades-per-active-day density band, 1 loose monthly-stability row,
  0 strict monthly-stability rows, and 0 May-holdout eligible rows. May 2026
  remains unused.
- Stage report:
  `docs/stage_reports/STAGE_R106_ACTIVE_RATE_DENSITY_SEARCH_AND_FEATURE_DEFRAG_REPORT.md`.
- Ledger update and `ISSUE-R106-022` resolution note.
- Validation:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Validation passed on 2026-06-11: focused feature-builder slice reported
2 passed, compileall succeeded, and contracts reported 454 passed.
