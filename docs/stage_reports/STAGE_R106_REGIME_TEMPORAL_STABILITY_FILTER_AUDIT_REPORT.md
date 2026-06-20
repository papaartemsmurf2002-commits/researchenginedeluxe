# Stage R106 Regime Temporal Stability Filter Audit Report

Date: 2026-06-11
Work packet: `docs/work_packets/WPR106-89-regime-temporal-stability-filter-audit.md`
Owner: Codex Research Agent

## Decision

WPR106-89 is closed as an offline diagnostic audit. It found one strict
month-stability overlay, but not an actionable pre-May lead: the only strict
hit is BTCUSDT sparse simple-runner with May and June excluded. Because the
requested benchmark holdout is May 2026, that overlay would be structurally
inactive in the holdout month and cannot satisfy the requested May benchmark.

No candidate pack, paper/live artifact, order placement, sizing change, runtime
mode change, live configuration write, CUDA speedup claim, or promotion-ready
claim exists.

## Scope

- Source evidence: completed WPR106-88 BTCUSDT and ETHUSDT trade artifacts.
- Window: 2024-01 through 2026-04 only.
- May 2026 usage: none.
- Method: deterministic post-trade overlays over already-costed trade
  `net_return` rows.
- Filter families: side subsets, regime subsets, volatility-bucket subsets,
  side/regime, side/volatility, regime/volatility, side/regime/volatility,
  one-month exclusions, two-month exclusions, and quarter exclusions.

This is not fresh execution proof. Any useful pattern must be encoded as a
pre-entry strategy/filter and rerun through the historical cycle before it can
support candidate interpretation.

## Artifacts

- Summary:
  `data/research/wpr106_89_regime_temporal_stability_filter_audit/wpr106_89_regime_temporal_stability_filter_audit_summary.json`
- Full overlay results:
  `data/research/wpr106_89_regime_temporal_stability_filter_audit/wpr106_89_overlay_filter_results.parquet`
- Top 200 overlays:
  `data/research/wpr106_89_regime_temporal_stability_filter_audit/wpr106_89_overlay_filter_top200.csv`
- Monthly returns for strict/loose overlays:
  `data/research/wpr106_89_regime_temporal_stability_filter_audit/wpr106_89_promising_overlay_monthly_returns.csv`

## Results

- Source candidates with trade artifacts: 140.
- Overlay rows evaluated: 23,389.
- Positive net and expectancy rows: 4,765.
- Loose monthly-stability rows: 206.
- Strict monthly-stability rows: 1.
- Rows with 1 to 5 trades per active day: 23,384.
- May 2026 rows observed in source trades: 0.

Strict stability rule:

- positive trade net sum and expectancy,
- at least 24 trades,
- at least 24 active months,
- no more than 4 inactive months,
- no more than 4 total losing active months,
- no more than 2 losing active months in each full year,
- no more than 1 losing active month in 2026 Jan-Apr,
- max single-month absolute PnL share at or below 0.35.

Only strict row:

| Symbol | Source candidate | Strategy | Exit | Filter | Net sum | Trades | Active months | Losing active months | Inactive months |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | `4239f08ef337` | `sparse_event_filter_v1` | `simple_runner_v1` | exclude month numbers 05 and 06 | 0.598581 | 112 | 24 | 4 | 4 |

Year stability for this diagnostic overlay:

- 2024: 10 active months, 2 inactive months, 2 losing active months, +0.127796 net.
- 2025: 10 active months, 2 inactive months, 2 losing active months, +0.275865 net.
- 2026 Jan-Apr: 4 active months, 0 losing active months, +0.194920 net.

## Interpretation

The audit confirms that the WPR106-88 BTC sparse simple-runner row has a
seasonal/monthly instability signature: excluding May and June reduces the
source row from 8 losing active months to 4 while preserving positive net and
one trade per active day. This is useful as a diagnostic pattern, but it is not
an actionable lead for the user objective because May 2026 is the required
benchmark holdout month and the overlay would take no May trades by design.

No non-calendar filter family produced a strict stability hit. Regime and
volatility subsets produced some loose rows, including ETH sparse and
trend/volatility rows, but those remained too sparse, too inactive, or too
weakly validated for a holdout trigger.

## Filter Family Counts

| Filter family | Rows | Positive rows | Loose hits | Strict hits |
| --- | ---: | ---: | ---: | ---: |
| baseline | 140 | 21 | 5 | 0 |
| calendar month exclusion 1 | 1,680 | 268 | 32 | 0 |
| calendar month exclusion 2 | 9,240 | 1,481 | 78 | 1 |
| quarter exclusion | 560 | 91 | 6 | 0 |
| regime subset | 840 | 159 | 4 | 0 |
| regime volatility subset | 2,987 | 844 | 48 | 0 |
| side regime subset | 1,344 | 213 | 5 | 0 |
| side regime volatility subset | 4,993 | 1,387 | 16 | 0 |
| side subset | 224 | 14 | 0 | 0 |
| side volatility subset | 863 | 176 | 2 | 0 |
| volatility subset | 518 | 111 | 10 | 0 |

## Next Useful Direction

The best next research step is not a May/June seasonal candidate. It is a
pre-entry implementation packet that tests whether the same instability can be
removed by causal features available before entry, such as volatility-bucket,
range/trend state, or flow-shock context, without hard-excluding the May
holdout month. That packet should encode the filter in strategy or
historical-cycle code, rerun the full pre-May cycle, and only then decide
whether May 2026 intake/holdout is warranted.

## Validation

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Result: compileall passed; contracts passed with 451 passed.
