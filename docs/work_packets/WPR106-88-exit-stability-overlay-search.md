# WPR106-88 Exit Stability Overlay Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Continue the 2024-forward broad research search by testing whether alternative
exit policies and tighter exit/filter combinations can improve the
month-to-month stability of pre-May strategy families. Use the WPR106-85
archive-backed BTCUSDT and ETHUSDT fixture packs from 2024-01 through 2026-04.
Keep May 2026 fully excluded from tuning and reserve it only as a benchmark
holdout for a promising pre-May lead.

This packet is not a defense of the rejected sparse side-veto lead. It should
use sparse/event positives as one input family, but also include transparent
trend, range, and volatility comparators where the same exit policies are
supported. Active entry rates around 1 to 5 trades per active day remain
acceptable when costs, overlap, and monthly stability are recorded.

## Scope

- Build BTCUSDT and ETHUSDT historical-cycle configs that test exit-policy
  overlays on 2024-forward pre-May archive-backed fixtures.
- Include no-trade and transparent comparators.
- Include sparse/event configurations that were positive but unstable in
  WPR106-87, plus broader price-only and volatility/range/trend controls where
  supported.
- Test fixed holding, lower-timeframe triple barriers, primary-bar
  volatility-scaled barriers, trailing ATR after profit, max-MAE stops, and
  simple runner exits where the strategy/feature combination supports them.
- Summarize pre-May costed returns, split/cost evidence, activity, active
  trades per day, and month-level stability.
- Do not use May 2026 for tuning, selection, optimizer feedback, or ranking.

## Allowed paths

- `docs/work_packets/WPR106-88-exit-stability-overlay-search.md`
- `docs/stage_reports/STAGE_R106_EXIT_STABILITY_OVERLAY_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/*wpr106_88*.json`
- `data/research/historical_cycles/wpr106_88*/**`
- `data/research/wpr106_88*/**`
- `tests/contracts/**`
- `tests/historical/**`

## Out of scope

- No live, paper, shadow, order-placement, position-sizing, runtime-mode, or
  live-configuration changes.
- No candidate-pack, paper/live, or promotion-ready claim.
- No use of May 2026 for tuning, parameter selection, ranking, or optimizer
  feedback.
- No provider-intake rewrite. If a promising pre-May lead appears, May 2026
  remains blocked by `ISSUE-R106-025` until a later holdout-intake packet
  resolves it.

## Exit evidence

- BTCUSDT and ETHUSDT exit-stability historical-cycle configs:
  `configs/research/wpr106_88_exit_stability_overlay_btcusdt_v1.json`,
  `configs/research/wpr106_88_exit_stability_overlay_ethusdt_v1.json`, and
  `configs/research/wpr106_88_exit_stability_overlay_ethusdt_v2.json`.
- Completed BTCUSDT and ETHUSDT historical-cycle archives:
  `data/research/historical_cycles/wpr106_88_exit_stability_overlay_btcusdt_v1/`
  and
  `data/research/historical_cycles/wpr106_88_exit_stability_overlay_ethusdt_v2/`.
  ETHUSDT v1 is retained as an aborted audit artifact because that background
  process imported a sibling package without `PYTHONPATH=src`.
- Combined pre-May monthly stability summary:
  `data/research/wpr106_88_exit_stability_overlay/summary/wpr106_88_exit_stability_overlay_summary.json`.
- Stage report:
  `docs/stage_reports/STAGE_R106_EXIT_STABILITY_OVERLAY_SEARCH_REPORT.md`.
- Ledger update.
- Validation baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Validation passed on 2026-06-11: compileall succeeded and contracts reported
451 passed.
