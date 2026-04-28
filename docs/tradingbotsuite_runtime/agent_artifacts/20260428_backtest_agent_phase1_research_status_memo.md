# Phase 1 Research Status

## Agent name

Backtest Agent

## Implemented

- BTC-only HMM/KNN research config.
- `research-hmm-knn`, `replay-hmm-knn`, and `monitor-hmm-knn` CLI paths.
- Public artifacts for regimes, KNN predictions, meta predictions, neighbor diagnostics, metrics, manifest, and monitoring.
- Synthetic CLI/E2E fixture validation.
- Real local BTC diagnostic run.

## Validated synthetically

- CLI command path works.
- Expected artifact files are written.
- Monitoring report is `research_only: true`, `observe_only: true`, and `promotion_ready: false`.
- Full repo tests previously passed at `383 passed`.

## Validated on real BTC

- Real artifact generated `446` evaluation rows.
- Regime outputs include all four intended state labels.
- KNN diagnostics are populated and same-regime-only.
- Monitoring detects high no-trade and low neighbor quality.

## Failed gates

- KNN expectancy after cost is negative.
- KNN trade count is too low.
- KNN PnL concentration fails.
- Meta accepted no trades.
- Meta long/short breakout fails.
- Promotion remains false.

## Insufficient-data gates

- Exact label distribution quality from the saved dataset is limited by older manifest fields.
- Horizon stability is not proven.
- Meta-filter improvement is not proven.
- ETH is not validated.

## Next experiments

1. Regenerate the real BTC dataset with the latest hardened label/context manifest.
2. Increase historical coverage and review per-regime neighbor pool depth.
3. Run with research extra dependencies so XGBoost and hmmlearn availability can be evaluated.
4. Tune no-trade/flip-cooldown thresholds only after data quality and pool depth are adequate.

## Decision

Phase 1 is research-contract complete and real-data diagnostic complete. It is not performance-accepted and not live-ready.
