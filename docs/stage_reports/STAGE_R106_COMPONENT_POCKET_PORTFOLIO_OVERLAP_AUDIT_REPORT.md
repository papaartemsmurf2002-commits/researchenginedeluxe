# Stage R106 Component Pocket Portfolio Overlap Audit Report

Date: 2026-06-12
Work packet: WPR106-162-component-pocket-portfolio-overlap-audit
Status: rejected as candidate-ready, portfolio-ready, and promotion-ready evidence

## Scope

WPR106-162 tested whether the WPR106-161 pre-May component pockets could become
more stable as small equal-sleeve portfolios once overlap, active trade rates,
costs, and source reuse were handled explicitly.

All portfolio generation, ranking, caps, scoring, and selection used only
2024-01-01 through 2026-04-30. May 2026 was excluded from all tuning and was
used only after selected portfolios were fixed.

The packet is research-only and observe-only. It writes no candidate pack, no
paper/live artifact, no live configuration, no sizing change, no order path,
and no promotion claim.

## Inputs

- WPR106-161 selected component-pocket rows:
  `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/selected_component_pocket_rows.parquet`
- WPR106-161 matched-control rows:
  `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/matched_control_rows.parquet`
- WPR106-161 selected/control pre-May trade details:
  `data/research/wpr106_161_pre_may_component_pocket_control_audit/pre_may/selected_and_control_pre_may_trades.parquet`
- WPR106-161 selected/control May benchmark trade details:
  `data/research/wpr106_161_pre_may_component_pocket_control_audit/may_benchmark/selected_and_control_may_trades.parquet`

## Method

The runner built daily net, gross, cost, and trade-count matrices for 162 source
rows: 81 component-pocket rows and 81 matched-control rows. It generated
deterministic 2-, 3-, 4-, 6-, and 8-sleeve equal-weight portfolios separately
for component pockets and matched controls.

Construction templates included quality rank, component diversity,
low-correlation greedy selection, low same-day-overlap greedy selection, packet
diversity, family diversity, balanced diversity, and rank-window variants.

Pre-May scoring included total return, 2024-2025 search return, 2026 Jan-Apr
validation return, losing-month counts, best-month concentration, drop-best
month robustness, cost stress, drawdown, mean pairwise absolute correlation,
same-day overlap, packet/family diversity, and sleeve-average active trade
rates.

The selected portfolios were then replayed on May 2026 after selection was
frozen.

## Pre-May Results

- Source rows: 162.
- Generated portfolios: 660.
- Component-pocket generated portfolios: 338.
- Matched-control generated portfolios: 322.
- Strict pre-May portfolios: 415.
- Robust pre-May portfolios: 637.
- Selected fixed portfolios: 72.
- Selected component-pocket portfolios: 39.
- Selected matched-control portfolios: 33.

Selected component-pocket portfolios were mostly strict: 36 strict and 3
robust. Their pre-May median total net return was +2.121019, median
drop-best-three-month return was +1.451363, median 2026 Jan-Apr validation
return was +0.388685, median losing months was 3, median max drawdown was
-0.136307, and median sleeve-average trades per active day was 0.813184.

Selected matched-control portfolios were all strict. Their pre-May median total
net return was +1.334584, median drop-best-three-month return was +0.987136,
median 2026 Jan-Apr validation return was +0.199268, median losing months was
2, median max drawdown was -0.076577, and median sleeve-average trades per
active day was 0.625300.

All selected portfolios survived the configured cost-stress grid. The failure
was not caused by a high active-rate overflow in the selected portfolios.

## May 2026 Benchmark

May rejected every fixed selected portfolio:

| Group | Rows | Positive | Negative | Flat | Best | Worst | Median | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Component pocket | 39 | 0 | 39 | 0 | -0.005600 | -0.069842 | -0.029799 | -0.030960 |
| Matched control | 33 | 0 | 33 | 0 | -0.009271 | -0.103368 | -0.054215 | -0.048921 |
| All selected | 72 | 0 | 72 | 0 | -0.005600 | -0.103368 | -0.032745 | -0.039192 |

Component-pocket portfolios remained less bad than matched controls on May,
but the entire fixed set was negative. The best component-pocket portfolio was
a 3-sleeve rank-window row at -0.005600. The best matched-control portfolio was
a 2-sleeve rank-window row at -0.009271.

The May median sleeve-average trades per active day was 0.703704 for
component-pocket portfolios and 0.575000 for matched controls. Median same-day
overlap remained high at 0.714286 and 0.689655 respectively, but low-overlap
and low-correlation constructions did not produce positive May transfer.

## Interpretation

The WPR106-161 row-level finding survived directionally: component pockets were
less bad than matched controls. WPR106-162 also shows that simple fixed
equal-sleeve portfolio construction, diversity templates, cost stress, and
overlap-aware diagnostics do not turn those pockets into May-stable evidence.

This is a stronger rejection than WPR106-161 because the selected portfolios
had strong pre-May total returns, positive 2026 Jan-Apr validation, positive
drop-best-three-month returns, manageable active rates, and full cost-stress
survival before the May benchmark.

WPR106-139 calendar/session exposure and WPR106-137 KNN-veto ensemble exposure
remain suspect in this component-pocket context. WPR106-146 relative-strength
and WPR106-119/WPR106-120 wick-fade pockets are not promoted by this packet;
they remain research-only clues requiring materially different, May-blind
follow-up if revisited.

## Artifacts

- Runner:
  `data/research/wpr106_162_component_pocket_portfolio_overlap_audit/scripts/run_wpr106_162_component_pocket_portfolio_overlap_audit.py`
- Summary:
  `data/research/wpr106_162_component_pocket_portfolio_overlap_audit/wpr106_162_component_pocket_portfolio_overlap_audit_summary.json`
- Generated portfolio ranking:
  `data/research/wpr106_162_component_pocket_portfolio_overlap_audit/pre_may/portfolio_pre_may_ranking.parquet`
- Selected pre-May portfolios:
  `data/research/wpr106_162_component_pocket_portfolio_overlap_audit/pre_may/selected_pre_may_portfolios.parquet`
- Selected portfolio members:
  `data/research/wpr106_162_component_pocket_portfolio_overlap_audit/pre_may/selected_portfolio_members.parquet`
- May benchmark metrics:
  `data/research/wpr106_162_component_pocket_portfolio_overlap_audit/may_benchmark/selected_may_portfolio_metrics.parquet`

## Validation

Passed:

- `python -m compileall -q data/research/wpr106_162_component_pocket_portfolio_overlap_audit/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

Contract result: 460 passed.
