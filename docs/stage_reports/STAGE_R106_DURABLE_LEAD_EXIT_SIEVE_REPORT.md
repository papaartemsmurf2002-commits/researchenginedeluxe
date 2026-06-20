# Stage R106 Durable Lead Exit Sieve Report

Date: 2026-06-08

Work packet: `docs/work_packets/WPR106-73-durable-lead-exit-sieve.md`

Status: Completed as a research-only, observe-only, promotion-disabled
durable sieve. No candidate pack, paper/live readiness artifact, live config,
runtime mode, order-placement, sizing, or promotion claim was created.

## Question

WPR106-73 tested whether the WPR106-72 latest-window BTC/ETH leads could be
rescued by exit design on the durable 2020-2026 candidate-depth public-archive
fixtures, or whether the next research phase should move away from exit
tweaking and toward sparse-entry/filter invention.

## Configs And Matrix

Completed configs:

- `configs/research/durable_lead_exit_sieve_btcusdt_r106_v1.json`
- `configs/research/durable_lead_exit_sieve_ethusdt_r106_v1.json`

The specs were JSON-validated, loaded through
`HistoricalResearchCycleSpec.from_path(...)`, and expanded before running:

- BTCUSDT: 14 explicit optimizer rows, expanded to 28 rows with injected
  no-trade/default comparators. The target matrix is two 72h
  `volatility_breakout_v1` entries times seven exits.
- ETHUSDT: 21 explicit optimizer rows, expanded to 35 rows with injected
  no-trade/default comparators. The target matrix is three
  `trend_following_v1` entries times seven exits.

Entry groups:

- BTC WPR106-72 loose 72h volatility breakout:
  `{"atr_percentile_threshold":0.25,"shock_threshold":0.7,"spacing_bars":8}`.
- BTC strict adjacent 72h volatility breakout:
  `{"atr_percentile_threshold":0.45,"shock_threshold":1.3,"spacing_bars":18}`.
- ETH WPR106-72 24h trend:
  `{"funding_penalty_threshold":0.00025,"max_choppiness":58.0,"slope_threshold":0.12,"spacing_bars":12}`.
- ETH WPR106-72 72h trend:
  `{"funding_penalty_threshold":0.00025,"max_choppiness":58.0,"slope_threshold":0.16,"spacing_bars":18}`.
- ETH strongest R105 durable fixed-hold trend contrast:
  `{"funding_penalty_threshold":0.00025,"max_choppiness":52.0,"slope_threshold":0.08,"spacing_bars":16}`.

Exit rows per entry:

- Fixed holding window.
- `simple_runner_v1` at 0.003/0.003, 0.005/0.004, and 0.008/0.004.
- `trailing_atr_after_profit` at 0.006 activation / 0.004 trail.
- `max_mae_stop` at 0.005.
- `volatility_scaled_barrier` at 0.012 target / 0.006 stop, treated only as
  the current static primary-close barrier caveat row.

## Data Coverage

The active candidate-depth catalog is:

`data/research/operator_runs/historical_data/refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb/historical_data_catalog.json`

Subagent source checks confirmed BTCUSDT and ETHUSDT candidate-depth fixture
manifests exist under the Binance Vision public-archive source. Both symbols
cover 2020-01-01 through 2026-04-30 with 221,952 15m bars and 3,329,280 1m
lower-timeframe rows. Both include an aggTrade-derived 1m flow proxy.

Durable funding rate, premium-index, open-interest, and liquidation context are
absent. ETH/BTC trend rows therefore act as price-trend rows with neutral
missing funding, not durable funding-aware rows.

## Cycle Outputs

Historical cycles completed:

- BTCUSDT:
  `data/research/historical_cycles/durable_lead_exit_sieve_btcusdt_r106_v1`
- ETHUSDT:
  `data/research/historical_cycles/durable_lead_exit_sieve_ethusdt_r106_v1`

Run-output JSONs:

- `data/research/historical_cycles/durable_lead_exit_sieve_btcusdt_r106_v1_run_output.json`
- `data/research/historical_cycles/durable_lead_exit_sieve_ethusdt_r106_v1_run_output.json`

Cycle duration was about 15.7 minutes for BTC and 21.2 minutes for ETH.

Standard research-cycle rows compare the same strategy parameters. They do not
guarantee identical executed entry events across exits because early exits can
admit later overlapping signals. To judge exit quality separately, WPR106-73
also wrote a frozen-entry audit that replays each exit policy over the fixed
holding row's executed entries:

- `data/research/historical_cycles/durable_lead_exit_sieve_btcusdt_r106_v1/same_entry_exit_audit.parquet`
- `data/research/historical_cycles/durable_lead_exit_sieve_btcusdt_r106_v1/same_entry_exit_audit_summary.json`
- `data/research/historical_cycles/durable_lead_exit_sieve_ethusdt_r106_v1/same_entry_exit_audit.parquet`
- `data/research/historical_cycles/durable_lead_exit_sieve_ethusdt_r106_v1/same_entry_exit_audit_summary.json`

The audit preserved the fixed entry set for every comparison.

## BTCUSDT Result

Cycle ranking: all 28 BTC rows were rejected. No optimizer-search row had
positive net return. The best overall net return was the no-trade comparator at
0.0.

Best standard-cycle target rows:

- Strict 72h `max_mae_stop`: 1,497 trades, net -0.876583, expectancy
  -0.001187, PF 0.810542.
- Loose 72h fixed hold: 734 trades, net -0.892458, expectancy -0.001542,
  PF 0.921465.
- Strict static barrier caveat: 1,920 trades, net -0.953864, expectancy
  -0.001526, PF 0.767364.

Frozen-entry exit audit:

- Loose WPR106-72 entry, 734 fixed entries:
  - Best exit was `max_mae_stop`, net -0.683654, delta versus fixed +0.208804,
    expectancy -0.001384, PF 0.778771.
  - Static barrier caveat also improved damage control, net -0.753077, delta
    +0.139381.
  - Runner and trailing variants were worse than fixed on the same entries.
- Strict adjacent entry, 622 fixed entries:
  - Best exit was `max_mae_stop`, net -0.603455, delta versus fixed +0.389852,
    expectancy -0.001286, PF 0.795218.
  - Static barrier caveat was second, net -0.680436, delta +0.312870.
  - Runner/trailing rows beat fixed in this stricter entry group but remained
    strongly negative.

BTC verdict: exit choice can reduce losses, especially hard-stop and static
barrier caveat rows, but entry quality is not durable. No BTC exit row beat
fixed holding and no-trade with positive expectancy/PF evidence.

## ETHUSDT Result

Cycle ranking: all 35 ETH rows were rejected. No optimizer-search row had
positive net return. The best overall net return was the no-trade comparator at
0.0.

Best standard-cycle target rows:

- WPR106-72 72h fixed hold: 754 trades, net -0.699357, expectancy +0.001173,
  PF 1.046081, but still rejected with low signal density and no completed
  split/cost/stability evidence.
- R105 24h fixed-hold contrast: 2,053 trades, net -0.918704, expectancy
  -0.000368, PF 0.974897.
- WPR106-72 72h runner 0.008/0.004: 2,325 trades, net -0.983361, expectancy
  -0.001002, PF 0.903826.

Frozen-entry exit audit:

- R105 24h contrast, 2,053 fixed entries:
  - Fixed hold was best, net -0.918704, expectancy -0.000368, PF 0.974897.
  - Every alternate exit was worse.
- WPR106-72 24h entry, 2,233 fixed entries:
  - `max_mae_stop` was best, net -0.976629, delta versus fixed +0.021895,
    expectancy -0.001529, PF 0.745356.
  - Other alternate exits only slightly improved or worsened an already
    negative entry.
- WPR106-72 72h entry, 754 fixed entries:
  - Fixed hold was best, net -0.699357, expectancy +0.001173, PF 1.046081.
  - All runner, trailing, max-MAE, and barrier exits were worse on the same
    entries.

ETH verdict: the 72h fixed-hold trend row has a weak isolated hint because
same-entry expectancy and PF are above break-even, but it still compounds to a
large negative net result, does not beat no-trade, has only 754 trades over the
full durable window, and fails the gate. Exit design did not rescue ETH; for
the only mildly interesting row, exit changes damaged the evidence.

## Gate And Cost Evidence

Pack eligibility was zero for both symbols:

- BTC: 28 gate rows, 0 pack-eligible.
- ETH: 35 gate rows, 0 pack-eligible.

The common blockers were no-trade baseline not beaten, split evidence required,
cost-stress scenario set incomplete, cost-stress survival below floor, and
stability-region enrichment/accepted-decision requirements. ETH 72h fixed hold
also carried low-signal-density risk.

Because `top_regions_to_refine` was intentionally set to 1, split and
cost-stress refinement was reserved for the top aggregate row. The no-trade
baseline outranked all negative target rows, so cost-stress artifacts were
produced only for the baseline no-trade comparator. This is consistent with
the compact sieve design and is itself evidence that no target row earned a
larger validation pass.

The results-analyst subagent independently confirmed the target rows had
`split_evaluated=false` and `cost_stress_evaluated=false`, with 0/4 required
split evaluations and 0/11 required cost-stress scenarios on candidate rows.

## Subagent Cross-Checks

Data/source explorer findings were used to confirm durable fixture coverage,
manifest availability, active-schema context, and the absence of funding/OI/
premium context.

Strategy/exit auditor findings were used to label horizon and exit semantics:

- Historical-cycle rows are same-parameter comparisons, not necessarily
  same-entry comparisons.
- `simple_runner_v1` is a profit-activated close-based trailing gap with no
  initial stop.
- Explicit `trailing_atr_after_profit` rows are close-return activation/trail
  rows in this matrix, not true ATR-derived trails.
- `max_mae_stop` uses primary-bar high/low approximation.
- `volatility_scaled_barrier` is treated as static primary-close barrier
  evidence only.

Results-analyst findings matched the local audit: BTC's best same-entry exit
was strict-entry `max_mae_stop` but still had net -0.603455, expectancy
-0.001286, and PF 0.795218; ETH's only caveat was the 72h fixed-hold row with
expectancy +0.001173 and PF 1.046081 but net -0.699357, severe drawdown, and no
gate support.

## Decision

Exit design did not rescue any WPR106-72/R105 BTC or ETH lead on durable
candidate-depth evidence. Some exits reduced losses on the same entries, but
no row beat both fixed holding and no-trade with enough coherent durable,
split, cost-stress, and gate evidence.

The next phase should not be more runner-exit tweaking. Open the next packet
around a novel sparse-entry/filter layer. The strongest direction is sparse
event selection that freezes entry quality before exit optimization:

- cooldown/top-score event selection over the existing transparent entry
  signals;
- side-balance controls so one side does not dominate durable PnL;
- optional aggTrade flow gating using the existing 1m proxy; and
- sparse KNN/event gating as a later overlay only after transparent sparse
  filters show evidence.

This remains research-only. The ETH 72h fixed-hold row can be kept as a
diagnostic seed for sparse-entry selection, not as a durable lead ready for
validation scale.

## Validation

Fresh WPR106-73 validation was run after config and report edits:

- `python -m json.tool configs/research/durable_lead_exit_sieve_btcusdt_r106_v1.json`
- `python -m json.tool configs/research/durable_lead_exit_sieve_ethusdt_r106_v1.json`
- Spec load and candidate expansion checks for both configs.
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  443 tests in 6.69 seconds.
