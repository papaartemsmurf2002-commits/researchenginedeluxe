# WPR106-86 Lorentzian KNN Feature Filter Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Continue the 2024-forward broad search after WPR106-85 by testing scoped
Lorentzian/KNN variants that are not tied to defending the rejected sparse BTC
side-veto lead. Use 2024-01-01 through 2026-04-30 as the optimization/search
window by default. Keep May 2026 fully out of tuning and reserve it only as a
benchmark holdout for a promising pre-May lead.

The packet may change KNN feature construction, distance/filter parameters,
variant specs, and compute behavior when the change is needed to run a broader
search honestly. Active entry rates around 1 to 5 trades per day are allowed
when cost, overlap, and monthly-stability evidence is recorded.

## Scope

- Inspect current no-RSI four-bar Lorentzian/KNN datasets and matrix runner
  extension points.
- Add or configure a small set of logically motivated KNN feature/filter
  variants over BTCUSDT and ETHUSDT using the pre-May archive-backed data.
- Prefer multiprocessing/vectorized/cache reuse where the current runner
  supports it; make truthful CUDA statements only from backend evidence.
- Summarize monthly stability, trade activity, costs, and benchmark-holdout
  eligibility.
- Preserve research-only, observe-only, promotion-ready-false metadata.

## Allowed paths

- `docs/work_packets/WPR106-86-lorentzian-knn-feature-filter-search.md`
- `docs/stage_reports/STAGE_R106_LORENTZIAN_KNN_FEATURE_FILTER_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/*wpr106_86*.json`
- `configs/research/*lorentzian*knn*.json`
- `src/tradingbotsuite/research/**`
- `src/tradingbotsuite/strategies/hmm_knn/**`
- `src/tradingbotsuite/strategies/**`
- `src/tradingbotsuite/features/**`
- `src/tradingbotsuite/optimization/**`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_archive_sources.py`
- `tests/contracts/**`
- `tests/features/**`
- `tests/optimization/**`
- `data/research/wpr106_86*/**`
- `data/research/hmm_knn_wpr106_86*/**`

## Out of scope

- No live, paper, shadow, order-placement, position-sizing, runtime-mode, or
  live-configuration changes.
- No candidate-pack, paper/live, or promotion-ready claim.
- No use of May 2026 for tuning, parameter selection, or ranking.
- No broad provider-intake rewrite. If May 2026 or new venue/context data is
  needed, record the blocker or open a later scoped packet.

## Exit evidence

- Variant specs or configs for the KNN search.
- Generated pre-May matrix outputs and stability summary, or a documented
  fail-closed blocker if the current runner/data cannot execute the variants.
- Stage report with decisions, monthly-stability evidence, compute notes, and
  May 2026 holdout status.
- Ledger update and validation baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```
