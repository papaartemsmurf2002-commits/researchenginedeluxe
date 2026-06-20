# Stage R106 Sparse Entry Filter Layer Report

Date: 2026-06-08

Work packet: `docs/work_packets/WPR106-74-sparse-entry-filter-layer.md`

Status: Completed as a research-only, observe-only, promotion-disabled sparse
entry/filter wave. No candidate pack, paper/live readiness artifact, live
config, runtime-mode change, order-placement, sizing change, or promotion claim
was created.

## Question

WPR106-73 showed that exit design did not rescue dense BTC/ETH leads on durable
candidate-depth evidence. WPR106-74 tested the next theory: sparse event
selection over transparent price entries, with cooldown/top-score admission,
side-balance control, and optional aggTrade trade-flow proxy gating.

## Implementation

Added `sparse_event_filter_v1` as a normal research strategy plugin:

- base transparent score models: `trend_following` and `volatility_breakout`;
- top-N score selection per fixed bar window;
- cooldown between accepted events;
- optional side-balance cap;
- optional `aligned` or `contrarian` aggTrade signed-flow confirmation;
- research-only signal output through the existing strategy contract.

Comparator support was extended so `baseline_no_trade`, `trend_following_v1`,
and `volatility_breakout_v1` can run on
`features_price_perp_aggflow_no_wt`. Their signal math remains unchanged; the
new feature-set support preserves no-trade/transparent comparator coverage for
aggTrade-gated sparse rows.

Focused strategy-contract validation passed with 284 tests.

## Configs And Matrix

Completed configs:

- `configs/research/sparse_entry_filter_btcusdt_r106_v1.json`
- `configs/research/sparse_entry_filter_ethusdt_r106_v1.json`

Both configs were JSON-validated and expanded before running:

- BTCUSDT: 8 explicit target rows, 14 total rows with injected comparators.
- ETHUSDT: 8 explicit target rows, 15 total rows with injected comparators.

The BTC matrix compared WPR106-73 dense 72h volatility-breakout rows against
sparse 72h volatility-breakout filters:

- price-only top-score/cooldown;
- stricter price-only top-score/cooldown/side-balance;
- aggTrade aligned flow confirmation;
- aggTrade contrarian flow confirmation;
- one max-MAE stop damage-control comparator.

The ETH matrix compared the WPR106-73/R105 dense 24h/72h trend rows against
sparse 24h/72h trend filters with price-only, aligned aggTrade, and contrarian
aggTrade variants.

## Cycle Outputs

Historical cycles completed:

- BTCUSDT:
  `data/research/historical_cycles/sparse_entry_filter_btcusdt_r106_v1`
- ETHUSDT:
  `data/research/historical_cycles/sparse_entry_filter_ethusdt_r106_v1`

Run-output JSONs:

- `data/research/historical_cycles/sparse_entry_filter_btcusdt_r106_v1_run_output.json`
- `data/research/historical_cycles/sparse_entry_filter_ethusdt_r106_v1_run_output.json`

Cycle duration was about 23.0 minutes for BTC and 48.0 minutes for ETH. Both
runs completed, with repeated pandas fragmentation warnings from wide
feature-frame missingness construction.

## BTCUSDT Result

Standard cycle: all 14 BTC rows were rejected and pack eligibility remained
zero, but sparse filtering produced the first aggregate-positive durable rows
in the recent BTC/ETH exit/filter sequence.

Best BTC target rows by aggregate net:

- AggTrade contrarian sparse volatility breakout, 72h fixed hold:
  546 trades, net +0.065930, expectancy +0.001575, PF 1.085587, max drawdown
  -0.779185.
- Price-only strict sparse volatility breakout, 72h fixed hold:
  521 trades, net +0.007351, expectancy +0.001309, PF 1.074839, max drawdown
  -0.594381.
- AggTrade aligned sparse row:
  539 trades, net -0.254400, expectancy +0.000738, PF 1.041596.

Dense WPR106-73 comparators stayed negative in the same cycle:

- strict dense `max_mae_stop`: net -0.876583, PF 0.810542;
- loose dense fixed hold: net -0.892458, PF 0.921465;
- strict dense fixed hold: net -0.993307, PF 0.714449.

Side evidence explains most of the sparse aggregate edge:

- Price-only sparse row:
  long side 258 trades, expectancy +0.006157, net +1.588513; short side
  263 trades, expectancy -0.003446, net -0.906351.
- AggTrade contrarian sparse row:
  long side 265 trades, expectancy +0.007269, net +1.926401; short side
  281 trades, expectancy -0.003794, net -1.066194.

Positive-row audit:

`data/research/historical_cycles/sparse_entry_filter_btcusdt_r106_v1/sparse_positive_validation_audit/positive_sparse_validation_summary.json`

- Price-only sparse positive row completed 4/4 split checks and 11/11 cost
  stress scenarios. Split pass rate was 2/4. Cost-stress survival was 5/11
  (45.45%), below the 70% floor.
- AggTrade contrarian sparse positive row completed 4/4 split checks, but cost
  stress was stopped after 2/11 scenarios because full-frame cost-stress
  validation exceeded the compact-run budget. Split pass rate was 2/4; partial
  cost-stress survival was 1/2 and is diagnostic only.

BTC verdict: sparse selection is a real improvement over the dense exit-tweak
rows, but it is not validation-scale durable evidence. The useful theory is
not "scale this row"; it is "test side-veto/long-only sparse BTC selection and
make cost-stress validation practical."

## ETHUSDT Result

Standard cycle: all 15 ETH rows were rejected and pack eligibility remained
zero. No sparse ETH target row had positive aggregate net return.

Best ETH target rows by aggregate net:

- Dense WPR106-73 72h trend fixed hold:
  754 trades, net -0.699357, expectancy +0.001173, PF 1.046081.
- AggTrade contrarian sparse 72h trend:
  514 trades, net -0.829658, expectancy -0.001081, PF 0.955127.
- Price-only sparse 72h trend:
  479 trades, net -0.880188, expectancy -0.002015, PF 0.920876.
- Dense R105 24h trend contrast:
  2,053 trades, net -0.918704, expectancy -0.000368, PF 0.974897.

ETH verdict: sparse top-score/cooldown and aggTrade proxy gating did not
improve the ETH durable trend lead. The WPR106-73 caveat remains the dense 72h
fixed-hold row, but it still does not beat no-trade and does not justify scale.

## Gate And Blockers

Pack eligibility remained zero:

- BTC: 14 gate rows, 0 pack-eligible.
- ETH: 15 gate rows, 0 pack-eligible.

Common blockers remained no-trade baseline not beaten by final score,
candidate split evidence required, cost-stress scenario set incomplete,
cost-stress survival below floor, stability-region accepted-decision
requirements, and feature-ablation evidence requirements for the combined
aggTrade feature rows.

WPR106-74 opened `ISSUE-R106-022` because combined price+aggTrade sparse
cost-stress validation exceeded the compact budget and wide feature material
emits fragmentation warnings. Until that is resolved, aggregate-positive
aggTrade-gated sparse rows are diagnostic only.

## Decision

Sparse entry filtering did uncover a BTC research direction worth another
focused packet, but not a row worth large validation or candidate-pack work.

Do not scale these rows yet. Open the next packet around:

- BTCUSDT long-only or side-veto sparse volatility-breakout selection;
- side-specific no-trade/short-veto controls rather than side-balance alone;
- cost-stress performance cleanup for combined price+aggTrade feature frames;
- then, only after transparent side-veto evidence holds up, sparse KNN/event
  gating as an overlay.

ETH should not receive more runner/exit or sparse-trend tuning until a novel
entry layer changes the event population.

## Validation

Validation run for WPR106-74:

- `python -m pytest tests/contracts/test_strategy_contracts.py -q` passed with
  284 tests.
- `python -m json.tool configs/research/sparse_entry_filter_btcusdt_r106_v1.json`
- `python -m json.tool configs/research/sparse_entry_filter_ethusdt_r106_v1.json`
- Spec load and candidate expansion checks passed for both sparse configs:
  BTCUSDT expanded to 14 rows and ETHUSDT expanded to 15 rows, both with
  `top_regions_to_refine=2`.
- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  449 tests.
