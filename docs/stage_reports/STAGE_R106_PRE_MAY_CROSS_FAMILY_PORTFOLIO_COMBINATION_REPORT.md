# Stage R106 Pre-May Cross-Family Portfolio Combination Report

Date: 2026-06-11
Work packet: WPR106-95-pre-may-cross-family-portfolio-combination
Status: closed

## Scope

WPR106-95 revisited old and discarded positive rows from the 2024-forward
research packets as equal-capital sleeves. The packet tested whether combining
different symbols and families improves month-to-month stability.

The analysis used only 2024-01 through 2026-04 evidence from closed WPR106
cycles. May 2026 was not used for tuning, ranking, selection, or feedback.

## Inputs

The sleeve universe came from positive-net and positive-expectancy research
rows in:

- WPR106-87 sparse/event stability cycles
- WPR106-88 exit stability overlay cycles
- WPR106-90 causal regime/volatility filter cycles
- WPR106-91 active-rate density cycles
- WPR106-94 causal session-filter cycles

Across those cycles, the analyzer loaded 120 positive sleeves. A deterministic
64-sleeve bounded pool was selected for equal-sleeve combination enumeration.

## Method

The packet enumerated 2-, 3-, and 4-sleeve equal-capital combinations with at
least symbol or family diversity. Portfolio monthly return was computed as the
mean of sleeve monthly net return sums. Trade activity was computed from the
union of sleeve entry days, and overlap was recorded as the share of active
days with at least two sleeve entries.

The packet produced deterministic combo IDs from member sleeve IDs and kept
compact top-combo member/monthly evidence. Oversized first-pass CSV exports
were removed and replaced by parquet plus top-combo CSV artifacts.

## Results

Artifacts:

- `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_portfolio_combination_summary.json`
- `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_positive_sleeve_universe.parquet`
- `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_portfolio_combinations.parquet`
- `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_top_portfolio_combinations.csv`
- `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_top_combo_members.csv`
- `data/research/wpr106_95_pre_may_cross_family_portfolio_combination/wpr106_95_top_combo_monthly_returns.csv`

Counts:

- Positive sleeve universe: 120 rows.
- Selected bounded pool: 64 sleeves.
- Equal-sleeve combinations enumerated: 650,622.
- Loose monthly-stability combinations: 1,360.
- Strict monthly-stability combinations: 0.
- May-holdout diagnostic leads: 40.

The rank-1 combination is `combo-d9edcc252c323b03`. It combines four sleeves:

- BTCUSDT WPR106-94 72h `volatility_breakout_v1`
- BTCUSDT WPR106-91 72h `volatility_breakout_v1`
- ETHUSDT WPR106-90 72h `sparse_event_filter_v1`
- BTCUSDT WPR106-94 72h `volatility_breakout_v1`

It records 690 trades, 462 active days, 1.4935 trades per active day,
0.4048 overlap-day share, +0.851653 equal-sleeve portfolio net return, average
sleeve expectancy +0.006606, 28 active months, 24 positive months, 4 losing
months, and max positive-month profit share 0.100398.

The rank-2 combination, `combo-d1ccbd91dc5325e5`, has stronger sleeve-level
split/cost context: three sleeves, 572 trades, 1.3717 trades per active day,
+0.983789 portfolio net return, 23 positive months, 5 losing months, average
sleeve cost-stress survival 0.696970, and max sleeve split PnL share 0.449076.

## Decision

WPR106-95 does not create candidate-ready evidence. The combinations are
research-only portfolio diagnostics selected on pre-May data. They do show that
cross-family and cross-symbol combinations can materially improve pre-May
monthly stability versus individual rows, but strict stability is still absent
and May 2026 has not been benchmarked.

Because the leading combinations include BTCUSDT, `ISSUE-R106-025` is now the
required holdout dependency for the next benchmark packet. BTCUSDT May 2026
archive data must be checksum-verified and mapped before any May benchmark can
be run for these combinations.

No candidate pack, paper/live artifact, order-placement path, position sizing,
runtime-mode change, live configuration write, CUDA speedup claim, or
promotion-ready claim was created.

## Validation

Final baseline validation passed:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Result: compileall passed; contracts reported 460 passed.
