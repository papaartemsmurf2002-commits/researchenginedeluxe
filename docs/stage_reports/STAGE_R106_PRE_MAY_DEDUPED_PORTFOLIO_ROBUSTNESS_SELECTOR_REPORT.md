# Stage R106 Pre-May Deduped Portfolio Robustness Selector Report

Date: 2026-06-11
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-98-pre-may-deduped-portfolio-robustness-selector.md`

## Scope

WPR106-98 revisits the WPR106-95 pre-May portfolio-combination evidence with a
stricter robustness selector. The selector uses only 2024-01 through
2026-04 data for ranking and then joins May 2026 benchmark rows from WPR106-97
only after selected leads are fixed.

May 2026 was not used for strategy choice, feature choice, filter choice,
threshold choice, parameter changes, optimizer feedback, or selection changes.

## Method

The selector reads the WPR106-95 full 650,622-row combination parquet and the
120-row positive sleeve universe. It reconstructs each sleeve's monthly return
vector from the original pre-May backtest trades, then fingerprints exact
monthly-return behavior. This detects packet-qualified sleeves that are
different by id but identical by pre-May monthly return path.

Hard pre-May filters require:

- unique candidate hashes inside a combination;
- unique parameter/core signatures inside a combination;
- unique monthly-behavior fingerprints inside a combination;
- positive pre-May portfolio return after costs;
- 1 to 5 trades per active day;
- at least 24 active months;
- no more than 5 losing months across the 28-month pre-May window;
- max positive-month profit share at or below 0.15;
- average sleeve cost-stress survival at or above 0.50;
- max sleeve single-split PnL share at or below 0.75;
- overlap-day share at or below 0.55;
- symbol or family diversity.

The final selected lead set is also de-duplicated by sorted monthly-behavior
combo signature. May benchmark rows are joined only after this selection.

Primary artifacts:

- Summary:
  `data/research/wpr106_98_pre_may_deduped_portfolio_robustness_selector/wpr106_98_selector_summary.json`
- Full ranking:
  `data/research/wpr106_98_pre_may_deduped_portfolio_robustness_selector/pre_may/wpr106_98_pre_may_deduped_robustness_ranking.parquet`
- Top ranking CSV:
  `data/research/wpr106_98_pre_may_deduped_portfolio_robustness_selector/pre_may/wpr106_98_pre_may_deduped_robustness_top200.csv`
- Selected leads:
  `data/research/wpr106_98_pre_may_deduped_portfolio_robustness_selector/pre_may/wpr106_98_selected_pre_may_robustness_leads.csv`
- Selected monthly returns:
  `data/research/wpr106_98_pre_may_deduped_portfolio_robustness_selector/pre_may/wpr106_98_selected_lead_monthly_returns.csv`
- Annual stability:
  `data/research/wpr106_98_pre_may_deduped_portfolio_robustness_selector/pre_may/wpr106_98_selected_lead_annual_stability.csv`
- May benchmark join:
  `data/research/wpr106_98_pre_may_deduped_portfolio_robustness_selector/benchmark/wpr106_98_selected_lead_may_benchmark_join.csv`

## Results

Pre-May selector counts:

- Total WPR106-95 combinations evaluated: 650,622
- Duplicate monthly-return fingerprint groups: 20
- Sleeve rows inside duplicate monthly-return groups: 52
- Strict hard-filter rows: 3
- Behavior-signature unique selected leads: 2
- May benchmark rows available after selection: 2

Selected leads:

| Selected rank | WPR106-95 rank | Combo | Pre-May return | Trades | Trades/active day | Losing months | Max full-year losing months | May return |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | `combo-d1ccbd91dc5325e5` | +0.983789 | 572 | 1.372 | 5 | 4 | +0.031402 |
| 2 | 3 | `combo-40bfb3546b9707ac` | +0.927046 | 800 | 1.515 | 5 | 3 | -0.014460 |

Annual pre-May stability:

| Combo | 2024 losing months | 2025 losing months | 2026 Jan-Apr losing months |
| --- | ---: | ---: | ---: |
| `combo-d1ccbd91dc5325e5` | 4 | 1 | 0 |
| `combo-40bfb3546b9707ac` | 3 | 2 | 0 |

The first selected lead benchmarks positive in May and keeps active frequency
inside the requested 1 to 5 trades-per-active-day range. It is still not
candidate-ready because 2024 has four losing months, and May daily behavior is
uneven: the WPR106-97 joined row has 8 positive active days and 11 losing
active days.

The second selected lead has better 2025 annual stability but fails the May
benchmark at -0.014460. It remains rejected as a holdout diagnostic lead.

## Interpretation

WPR106-98 narrows the portfolio direction materially. The best remaining
pre-May robustness lead is WPR106-95 rank 2, not rank 1. That result is
pre-May-only: rank 2 survives because it has better sleeve split balance,
higher cost-stress survival, lower overlap, and no duplicate monthly behavior
inside the combination.

The evidence does not prove the requested ideal profile. No selected lead has
zero to two losing months in both full pre-May years. The positive May lead is
worth future research-only follow-up, but it needs fresh pre-May-only
strategy/portfolio construction and full gate evidence, including split,
monthly, cost-stress, ablation, side/control, no-trade, transparent baseline,
and candidate-pack rejection checks.

The clearest next research implication is to design new pre-May searches that
make duplicate behavior, annual losing-month clustering, and overlap penalties
first-class ranking terms before May benchmark evaluation.

## Boundary

All outputs are research-only, observe-only, and promotion-ready false. No
candidate pack, paper/live artifact, order placement, position sizing,
runtime-mode change, live-configuration write, CUDA speedup claim, or
promotion claim was created.

## Validation

Passed:

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460 passed
