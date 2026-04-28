# Agent name

Backtest Agent

# Task received

Score the real-data result against acceptance gates.

Tasks:

- Evaluate positive expectancy after fees/slippage/funding.
- Report split concentration, positive split ratio, long/short breakout, and horizon stability.
- Mark each acceptance gate as pass/fail/insufficient-data.

# Files read

- `configs/v2_btc_hmm_multi_knn_research.json`
- `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- `data/research/v2-btc-hmm-multi-knn-1/artifact_manifest.json`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_real_btc_contract_run.md`

# Files changed

- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_real_btc_acceptance_triage.md`

# Commands/tests run

No new validation command was required for this triage. This artifact evaluates the metrics produced by the real local BTC contract run documented in `20260428_backtest_agent_real_btc_contract_run.md`.

# Input artifact summary

- Dataset: `data\research\v2-btc-research-1\btcusdt_dataset.parquet`
- Output directory: `data/research/v2-btc-hmm-multi-knn-1`
- Metrics: `data/research/v2-btc-hmm-multi-knn-1/walk_forward_metrics.json`
- Rows evaluated: `446`
- `research_only`: `true`
- `promotion_ready`: `false`
- PnL source: `realized_label_return_after_fee_slippage_funding`
- Fee: `5.0` bps
- Slippage: `5.0` bps
- Funding included: `true`
- HMM backend: `gaussian_mixture_fallback`
- Meta backend: `random_forest_fallback`

# Acceptance thresholds

From `configs/v2_btc_hmm_multi_knn_research.json`:

- Minimum trade count: `25`
- Minimum expectancy after cost: `0.0`
- Maximum single split PnL share: `0.6`
- Long/short breakout required: `true`
- Research-only phase: `true`

# Result summary

Pure KNN:

- Trade count: `5`
- Long count: `3`
- Short count: `2`
- Accepted rate: `0.011210762331838564`
- No-trade rate: `0.9887892376681614`
- Expectancy after cost: `-1.0008811453163364`
- Realized PnL total: `-5.004405726581682`
- Profit factor: `0.0`
- Positive split ratio: `0.0`
- Max single split PnL share: `0.8000705017118063`

Meta-filter:

- Trade count: `0`
- Long count: `0`
- Short count: `0`
- Accepted rate: `0.0`
- No-trade rate: `1.0`
- Expectancy after cost: `0.0`
- Realized PnL total: `0.0`
- Profit factor: `null`
- Positive split ratio: `0.0`
- Max single split PnL share: `0.0`

Promotion failures already emitted by metrics:

- `knn_expectancy_after_cost_below_threshold`
- `knn_insufficient_trade_count`
- `knn_single_split_dominates_pnl`
- `meta_insufficient_trade_count`
- `meta_missing_long_short_breakout`
- `research_only_not_live_promotable`

# Gate triage

| Gate | Status | Evidence |
| --- | --- | --- |
| Research-only flag present | Pass | Metrics and manifest report `research_only: true`. |
| Promotion remains false | Pass | Metrics report `promotion_ready: false`. |
| Positive expectancy after fees/slippage/funding | Fail | Pure KNN expectancy after cost is `-1.0008811453163364`. Meta accepted no trades, so it provides no positive expectancy evidence. |
| Minimum trade count | Fail | Pure KNN has `5` trades versus required `25`; meta has `0` trades versus required `25`. |
| Split concentration | Fail for KNN; insufficient-data for meta | KNN max single split PnL share is `0.8000705017118063`, above the `0.6` limit. Meta has no trades, so split concentration cannot be meaningfully evaluated. |
| Positive split ratio | Fail | Both KNN and meta positive split ratio are `0.0`. |
| Long/short breakout | Pass for KNN shape only; fail for meta; overall fail | KNN has both sides represented (`3` long, `2` short) but with insufficient trade count. Meta has `0` long and `0` short and metrics emit `meta_missing_long_short_breakout`. |
| Horizon stability across 6h, 24h, 72h | Insufficient-data | Metrics only report configured horizons and primary label horizon `24h`; there are no separate realized metrics for 6h, 24h, and 72h. |
| 7d exploratory horizon | Insufficient-data | `7d` is configured but no separate 7d realized metrics were produced in this artifact. |
| Pure KNN versus meta both reported | Pass | Metrics include `comparison.hmm_regime_lorentzian_knn` and `comparison.hmm_knn_meta_model`. |
| Funding/fees/slippage included | Pass | Evaluation basis is `realized_label_return_after_fee_slippage_funding`, with `fee_bps: 5.0`, `slippage_bps: 5.0`, and `funding_cost_enabled: true`. |

# Split detail

Pure KNN by split:

- Split `0`: `0` trades, expectancy `0.0`, realized PnL `0.0`.
- Split `1`: `1` trade, expectancy `-1.0005283261460394`, realized PnL `-1.0005283261460394`.
- Split `2`: `4` trades, expectancy `-1.0009693501089107`, realized PnL `-4.003877400435643`.

Meta by split:

- Split `0`: `0` trades.
- Split `1`: `0` trades.
- Split `2`: `0` trades.

Interpretation:

- KNN losses are concentrated mostly in split `2`, causing the split concentration failure.
- Meta-filter rejected every candidate, so meta split-level performance is not evaluable.

# Horizon stability

Current metrics include:

```json
{
  "6h": "configured",
  "24h": "configured",
  "72h": "configured",
  "7d": "configured"
}
```

This is not enough to assess horizon stability. The artifact does not contain separate realized walk-forward metrics for 6h, 24h, 72h, or 7d. The only primary horizon in the manifest is `24h`.

# Acceptance conclusion

Overall status: fail / not accepted.

The real local BTC result does not pass acceptance gates. It has negative pure-KNN expectancy after costs, insufficient trade count, zero positive split ratio, KNN split concentration above threshold, and no meta-filter trades. Horizon stability is insufficient-data because per-horizon realized metrics are not present.

No positive expectancy claim exists.

No live-readiness claim exists.

This remains a research-only, non-promotional result.

# Decisions made

- Scored KNN and meta separately where the metrics provide separate evidence.
- Marked meta split concentration as insufficient-data rather than pass because zero accepted trades cannot validate concentration.
- Marked KNN long/short breakout as shape-only pass but not acceptance pass because total KNN trade count is below threshold.
- Did not infer horizon stability from configured horizon names.

# Assumptions

- Acceptance gates should be applied to realized costed returns, not expected KNN EV.
- Meta-filter is the stricter deployment candidate, but pure KNN must still be reported because the prompt explicitly forbids hiding poor KNN behavior.

# Open issues or blockers

No implementation blocker. Acceptance is blocked by current real-data results and insufficient per-horizon evidence.

# Handoff notes for other agents

- Backtest should not promote this run.
- Data/Labeling should regenerate a current-contract BTC dataset before deeper performance work.
- Backtest/Labeling should add per-horizon realized metrics if horizon stability across 6h, 24h, and 72h is required as an explicit acceptance gate.
