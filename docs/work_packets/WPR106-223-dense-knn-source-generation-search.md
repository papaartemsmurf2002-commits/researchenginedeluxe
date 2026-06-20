# WPR106-223 Dense KNN Source Generation Search

Status: closed
Owner: Codex Research Agent
Created: 2026-06-13
Reconstructed: 2026-06-18 by WPR106-226 from summary JSON and ledger evidence after the prior markdown file was found NUL-filled.

## Objective

Follow WPR106-222 by changing the KNN source-generation layer instead of only
post-filtering old selected KNN artifacts. Generate denser ETHUSDT KNN source
paths with packet-local feature packs and monthly gates while keeping May 2026
out of tuning.

## Window Policy

- Selection window: 2024-01-01 through 2026-04-30.
- May 2026 predictions/trades computed only after fixed selected rows.
- All outputs remain research-only, observe-only, promotion-ready false.

## Allowed Paths

- `docs/work_packets/WPR106-223-dense-knn-source-generation-search.md`
- `docs/stage_reports/STAGE_R106_DENSE_KNN_SOURCE_GENERATION_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only for blocking risks
- `data/research/wpr106_223*/**`

## Evidence Summary

- Feature packs: `flow_wick_density`, `trend_residual_density`, `cross_event_density`, `wick_reversal_pressure`.
- Evaluated 139,968 pre-May base rows.
- Base positives: 18,619; base annual-target rows: 8,089; strict rows: zero.
- Replayed 44 base rows across monthly gates, yielding 220 gated rows.
- Gated positives: 196; gated annual-target rows: 28; strict rows: zero.
- Fixed selected set: 71 rows.
- Selected pre-May median return: +0.200877.
- Selected pre-May median active months: 24.
- Selected pre-May median losing months: eight.
- May benchmark: 43 positive, zero negative, 28 flat; median May +0.001341.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. Density improved May participation, but losing-month
stability degraded. Useful evidence: `flow_wick_density` transfers best, but
the dense KNN path needs feature/label or exit changes before monthly gates.

## Validation

Passed per ledger closeout:

```powershell
python -m compileall -q data\research\wpr106_223_dense_knn_source_generation_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```
