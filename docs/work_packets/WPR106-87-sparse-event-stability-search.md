# WPR106-87 Sparse Event Stability Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Continue the 2024-forward broad strategy search by revisiting sparse/event
filters without defending the rejected BTC side-veto lead. Use the WPR106-85
archive-backed BTCUSDT and ETHUSDT fixture packs from 2024-01 through
2026-04. Keep May 2026 fully excluded from tuning and reserve it only as a
benchmark holdout for a promising pre-May lead.

The packet should allow active entry rates around 1 to 5 trades per active day
when costs, overlap, and monthly stability are recorded. The target is
month-to-month stability, not one concentrated profitable window.

## Scope

- Build BTCUSDT and ETHUSDT historical-cycle configs for sparse/event filters
  over the pre-May archive-backed fixture manifests.
- Include transparent/no-trade comparators and both price-only and aggTrade
  proxy feature sets.
- Test multiple sparse/event variants: both-sided controls, one-sided
  post-selection controls, aligned/contrarian flow confirmation, looser
  active-rate settings, and longer fixed holds where appropriate.
- If the aggTrade-proxy flow path becomes compute-bound, make a scoped
  behavior-preserving sparse-filter optimization so the same candidate family
  can complete without repeated per-row feature extraction.
- Run pre-May cycles and summarize costed returns, activity, split/cost/stress
  evidence, and month-level stability.
- Do not use May 2026 for tuning or selection.

## Allowed paths

- `docs/work_packets/WPR106-87-sparse-event-stability-search.md`
- `docs/stage_reports/STAGE_R106_SPARSE_EVENT_STABILITY_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/*wpr106_87*.json`
- `data/research/historical_cycles/wpr106_87*/**`
- `data/research/wpr106_87*/**`
- `src/tradingbotsuite/strategies/sparse_event_filter.py`
- `tests/contracts/**`
- `tests/historical/**`
- `tests/tradingbotsuite/test_sparse_event_filter.py`

## Out of scope

- No live, paper, shadow, order-placement, position-sizing, runtime-mode, or
  live-configuration changes.
- No candidate-pack, paper/live, or promotion-ready claim.
- No use of May 2026 for tuning, parameter selection, ranking, or optimizer
  feedback.
- No provider-intake rewrite. If a promising lead appears, May 2026 remains
  blocked by `ISSUE-R106-025` until a later holdout-intake packet resolves it.

## Exit evidence

- BTCUSDT and ETHUSDT sparse-event historical-cycle configs.
- Generated pre-May cycle outputs and monthly stability summary.
- Stage report with decisions, active-rate evidence, May 2026 status, and
  validation.
- Ledger update.
- Validation baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```
