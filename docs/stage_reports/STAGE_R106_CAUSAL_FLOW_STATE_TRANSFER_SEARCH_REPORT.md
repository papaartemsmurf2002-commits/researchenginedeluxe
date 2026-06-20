# Stage R106 WPR106-149 Causal Flow-State Transfer Search Report

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It does
not create a candidate pack, paper/live artifact, order-placement path, sizing
change, runtime-mode change, live configuration write, or promotion claim.

All score formulas, thresholds, ranking, transfer checks, and selected rows use
only 2024-01-01 through 2026-04-30. May 2026 remains benchmark-only and was not
run because no pre-May row passed the packet's stability and transfer screen.
CUDA was not used and no CUDA speedup claim is made.

## Method

WPR106-149 uses the WPR106-96 verified BTCUSDT and ETHUSDT 15m feature context
through 2026-05. It builds fresh causal completed-bar score families from
common OHLCV and taker buy/sell quote-volume fields, avoiding ETH-only context
columns that BTC does not share.

The tested families are:

- completed-bar flow/momentum continuation;
- compressed-range flow breakout;
- wick/sweep absorption reversal;
- price/flow divergence reversion;
- cross-symbol flow-confirmed continuation;
- cross-symbol disagreement fade;
- transparent price-only state follow control.

The reduced staged funnel evaluates 5,376 rows: 2,688 rows per symbol across
target raw signal rates of 1 and 5 per day, all/US sessions, all/flow-active
regimes, both/long/short side modes, daily caps of 1 and 5, and fixed 8/16-bar
exits. Costs, same-symbol overlap, and daily caps use the existing WPR106-115
artifact helper semantics.

An initial wider grid that included extra regimes, target rates, caps, and
exits was stopped after it timed out before completing both symbols. The final
run uses the reduced staged funnel and completed in bounded time.

## Results

- Total evaluated rows: 5,376.
- BTCUSDT rows: 2,688; positive pre-May rows: 127; max total net return
  +0.129187; median -0.377506.
- ETHUSDT rows: 2,688; positive pre-May rows: 511; max total net return
  +0.814188; median -0.332186.
- Strict pre-May rows: 0.
- Loose pre-May rows: 0.
- Transfer-strict rows: 0.
- Transfer-loose rows: 0.
- May benchmark rows: 0, because no row qualified as a promising pre-May lead.

The best diagnostic pockets were not stable enough:

- The best same-config positive-on-both-symbol row is
  `flow_state_continuation|...|all|1.0|all|all|long|1|fixed_16b`, with
  min symbol return +0.129187 and mean +0.201005, but max losing months 11.
- ETHUSDT flow-state continuation reaches +0.500993 pre-May net return with
  237 trades, 28 active months, and 1.167 trades per active day, but still has
  10 losing months and transfer minimum return -0.114014.
- ETHUSDT compression breakout reaches +0.814188 pre-May net return, but the
  family has no annual-target, strict, loose, or transfer-stable rows.

## Decision

WPR106-149 rejects this causal flow-state transfer search as a promising lead
source. The family can produce positive diagnostic rows and some configs are
positive on both symbols, but the monthly stability target is not met: every
row fails strict and loose pre-May gates, and no parameter setting survives the
symbol-transfer screen.

May 2026 was correctly left untouched because there were no promising pre-May
survivors. The result is useful negative evidence for fresh common-column
price/flow state formulas under active 1-to-5/day search rates, but it is not a
candidate-ready or May-benchmark-ready family.

## Artifacts

- `data/research/wpr106_149_causal_flow_state_transfer_search/wpr106_149_causal_flow_state_transfer_search_summary.json`
- `data/research/wpr106_149_causal_flow_state_transfer_search/pre_may/combined_ranking.parquet`
- `data/research/wpr106_149_causal_flow_state_transfer_search/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_149_causal_flow_state_transfer_search/pre_may/combined_monthly_returns.parquet`
- `data/research/wpr106_149_causal_flow_state_transfer_search/family_summary.parquet`
- `data/research/wpr106_149_causal_flow_state_transfer_search/scripts/run_wpr106_149_causal_flow_state_transfer_search.py`

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_149_causal_flow_state_transfer_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts result: 460 passed.
