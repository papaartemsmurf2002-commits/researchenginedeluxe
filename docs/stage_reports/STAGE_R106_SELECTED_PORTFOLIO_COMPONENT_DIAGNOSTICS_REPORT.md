# Stage R106 Selected Portfolio Component Diagnostics Report

Date: 2026-06-11
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-99-selected-portfolio-component-diagnostics.md`

## Scope

WPR106-99 diagnoses the two WPR106-98 selected pre-May robustness leads at
component level. The diagnostic window remains 2024-01-01 through
2026-04-30. May 2026 is joined only after fixed pre-May diagnostics and is
used only as a benchmark holdout view.

No May 2026 row was used for strategy choice, feature choice, filter choice,
threshold choice, parameter changes, optimizer feedback, subset selection, or
portfolio selection.

## Method

The runner reads the fixed WPR106-98 selected leads, expands their
packet-qualified WPR106-95 sleeve membership, reloads original pre-May trade
parquets from the WPR106-95 sleeve universe, and computes equal-sleeve
component attribution.

Pre-May diagnostics include:

- member sleeve totals and monthly contributions;
- combo monthly and annual attribution;
- combo-level side, regime, volatility-bucket, symbol, and family rollups;
- all subset ablations with at least two sleeves;
- active-day, trade-rate, and overlap diagnostics.

After those diagnostics are written, the same fixed sleeve/subset definitions
are benchmarked against WPR106-97 May 2026 member trades.

Primary artifacts:

- Summary:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/wpr106_99_component_diagnostics_summary.json`
- Runner:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/scripts/run_wpr106_99_component_diagnostics.py`
- Pre-May member trades:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/pre_may/wpr106_99_selected_member_pre_may_trades.parquet`
- Sleeve and monthly attribution:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/pre_may/wpr106_99_selected_member_sleeve_summary.csv`
  and
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/pre_may/wpr106_99_selected_combo_monthly_attribution.csv`
- Factor rollups:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/pre_may/wpr106_99_selected_combo_factor_contributions.csv`
- Subset diagnostics:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/pre_may/wpr106_99_selected_subset_ablation.csv`
- May benchmark:
  `data/research/wpr106_99_selected_portfolio_component_diagnostics/may_benchmark/wpr106_99_selected_subset_may_benchmark.csv`

## Results

Generated counts:

- Selected combos: 2
- Selected membership rows: 7
- Unique selected sleeves: 6
- Pre-May selected-member trade rows: 1,372
- Diagnostic subsets: 15
- May selected-member trade rows: 49

Original selected leads:

| Selected rank | WPR106-95 rank | Combo | Pre-May return | Losing months | 2024 losing months | 2025 losing months | May return |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | `combo-d1ccbd91dc5325e5` | +0.983789 | 5 | 4 | 1 | +0.031402 |
| 2 | 3 | `combo-40bfb3546b9707ac` | +0.927046 | 5 | 3 | 2 | -0.014460 |

The dominant pre-May weak month for both selected leads is September 2024:

| Combo | Worst month | Month return | Main negative sleeve |
| --- | ---: | ---: | --- |
| `combo-d1ccbd91dc5325e5` | 2024-09 | -0.118627 | WPR106-91 BTCUSDT volatility breakout, -0.062864 weighted |
| `combo-40bfb3546b9707ac` | 2024-09 | -0.106637 | WPR106-88 BTCUSDT volatility breakout `fbbe`, -0.065816 weighted |

Sleeve totals are all positive pre-May, so the instability is not explained by
a single sleeve with negative aggregate contribution. The weakest total
pre-May sleeve in lead 1 is the WPR106-90 ETHUSDT sparse-event sleeve at
+0.195251 weighted contribution. The weakest total pre-May sleeve in lead 2 is
the WPR106-88 BTCUSDT sparse-event sleeve at +0.129049 weighted contribution.

The factor rollup does not show a simple side, regime, or volatility bucket
that can be removed safely:

- Lead 1 long and short sides are both positive pre-May: +0.802715 long,
  +0.181075 short.
- Lead 2 long and short sides are both positive pre-May: +0.797256 long,
  +0.129790 short.
- All lead-level regime buckets are positive pre-May.
- Lead 2 has a small high-volatility loss, -0.041774, but it comes from only
  two trades and is not enough to explain the annual instability.

Subset diagnostics are useful as research hypotheses but do not satisfy the
target profile. For lead 1, the original three-sleeve combination is still the
best monthly-stability row; its two-sleeve subsets increase losing months to
7, 8, and 9. For lead 2, the best pre-May subset by full-year loss balance is
`WPR106-94 BTCUSDT c66b21e8 + WPR106-94 ETHUSDT 3c982905 + WPR106-88 BTCUSDT
fbbe4e1c`, with +1.063996 return and max full-year losing months of 2, but it
has 6 total losing months over the 28-month pre-May window. It is diagnostic
only and requires a new pre-May-only packet before any follow-up benchmark use.

May 2026 benchmark behavior for the original selected leads:

| Combo | May return | Trades | Active days | Trades/active day | Overlap-day share | Positive days | Losing days |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `combo-d1ccbd91dc5325e5` | +0.031402 | 20 | 19 | 1.053 | 0.053 | 8 | 11 |
| `combo-40bfb3546b9707ac` | -0.014460 | 29 | 20 | 1.450 | 0.450 | 7 | 13 |

Lead 1's May benchmark is positive because the two BTCUSDT volatility sleeves
contribute +0.019140 and +0.019010 weighted, offsetting the WPR106-90 ETHUSDT
sparse sleeve's -0.006748 weighted contribution. Lead 2's May benchmark is
negative because the WPR106-88 BTCUSDT `fbbe` volatility sleeve contributes
-0.026100 weighted and the WPR106-94 ETHUSDT sparse sleeve contributes
-0.006407 weighted.

## Interpretation

WPR106-99 does not rescue either selected lead as candidate-ready. Both still
miss the month-to-month stability objective, and both have a visible 2024
losing-month cluster. The remaining instability is better described as
calendar-month clustering across otherwise positive sleeves than as one simple
side, regime, volatility bucket, or total-loss component.

The next research step should be a new pre-May-only construction packet that
uses annual losing-month caps, month-cluster penalties, and overlap penalties
as first-class ranking terms before any May benchmark join. The WPR106-99
subset rows can seed hypotheses, but they are not selected portfolios and are
not promotion evidence.

## Boundary

All outputs are research-only, observe-only, and promotion-ready false. No
candidate pack, paper/live artifact, order placement, position sizing,
runtime-mode change, live-configuration write, CUDA speedup claim, or
promotion claim was created.

## Validation

Passed:

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed
