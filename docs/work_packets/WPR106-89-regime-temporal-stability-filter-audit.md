# WPR106-89 Regime Temporal Stability Filter Audit

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Continue the 2024-forward broad research search after WPR106-88 by testing
whether simple, explainable filters over completed pre-May trade evidence can
turn otherwise profitable-but-unstable rows into month-stable candidates. This
packet is an offline audit, not a promotion path: it evaluates whether the
observed instability is removable by regime, volatility-bucket, side, and
calendar/quarter seasonality filters before spending compute on another full
historical-cycle expansion.

Use 2024-01-01 through 2026-04-30 only. Keep May 2026 fully out of tuning,
selection, ranking, optimizer feedback, and reporting except as a future
holdout dependency if a later packet finds a promising pre-May lead.

## Scope

- Read completed WPR106-88 BTCUSDT/ETHUSDT cycle trade artifacts and summary
  rows.
- Evaluate deterministic post-trade filter overlays for all non-no-trade
  strategy rows with trades:
  - side subsets,
  - regime subsets,
  - volatility-bucket subsets,
  - side plus regime,
  - side plus volatility bucket,
  - regime plus volatility bucket,
  - simple calendar month-of-year and quarter exclusions.
- Preserve active-rate evidence. Rows around 1 to 5 trades per active day
  should be accepted for analysis when overlap/cost/monthly evidence is
  recorded.
- Use the already costed trade-level net returns from completed cycles; do not
  rewrite historical-cycle rankings or claim fresh execution proof.
- Summarize net return, expectancy, active days, trades per active day, active
  months, losing active months, inactive months, monthly concentration, and a
  strict month-stability flag.
- Mark any promising-looking overlay as `research_only`, `observe_only`, and
  `promotion_ready: false`; require a future full historical-cycle rerun plus
  May 2026 holdout before candidate interpretation.

## Allowed paths

- `docs/work_packets/WPR106-89-regime-temporal-stability-filter-audit.md`
- `docs/stage_reports/STAGE_R106_REGIME_TEMPORAL_STABILITY_FILTER_AUDIT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_89_regime_temporal_stability_filter_audit/**`

## Out of scope

- No live, paper, shadow, order-placement, position-sizing, runtime-mode, or
  live-configuration changes.
- No candidate pack, promotion artifact, or promotion-ready claim.
- No use of May 2026 data.
- No source-code changes in this packet. If this audit finds a promising
  pre-May filter family, a later packet must encode it in strategy or
  historical-cycle code with contract tests and full validation.

## Exit evidence

- Offline overlay audit artifacts under
  `data/research/wpr106_89_regime_temporal_stability_filter_audit/`.
- Stage report:
  `docs/stage_reports/STAGE_R106_REGIME_TEMPORAL_STABILITY_FILTER_AUDIT_REPORT.md`.
- Result: 23,389 diagnostic overlay rows over existing WPR106-88 trades, 4,765
  positive-net/expectancy rows, 206 loose monthly-stability rows, and 1 strict
  monthly-stability row. The strict row is BTCUSDT sparse simple-runner with
  May and June excluded; it remains diagnostic only because May 2026 would be
  structurally inactive and the filter is post-trade evidence, not a pre-entry
  historical-cycle rerun.
- No candidate pack, promotion artifact, paper/live artifact, order/sizing
  change, runtime-mode change, live configuration write, May 2026 use, or CUDA
  speedup claim exists.
- Stage report with accepted/rejected overlay counts, active-rate evidence, May
  2026 status, and validation.
- Ledger update.
- Validation baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Validation passed on 2026-06-11: compileall succeeded and contracts reported
451 passed.
