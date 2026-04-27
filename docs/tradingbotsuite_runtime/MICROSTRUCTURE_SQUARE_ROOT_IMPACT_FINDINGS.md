# Microstructure Square-Root Impact Findings

Source reviewed: `arXiv:2502.17906`, Sato and Kanazawa, "Why do financial prices exhibit Brownian motion despite predictable order flow?"

Source URL: https://arxiv.org/pdf/2502.17906

Review date: 2026-04-18

## Executive Conclusion

The paper is useful for this repo as a microstructure feature-design constraint, not as a standalone trading strategy.

Actionable conclusion:

- keep signed taker flow as a diagnostic and research feature
- do not treat persistent raw order flow as direct multi-bar price predictability
- transform large trade-flow pressure concavely, especially with square-root notional
- measure whether price actually responds to signed flow
- keep these additions observe-only until prospective signal-time data proves value

## Quantized Findings

| Finding | Paper Basis | Repo Decision | Confidence | Live-Gate Status |
| --- | --- | --- | --- | --- |
| Persistent order flow can coexist with diffusive prices. | The model explains Brownian-like price dynamics despite predictable order-flow signs. | Do not promote raw signed imbalance into a hard predictor for 15m entries. | High | Not a gate |
| Square-root impact is the key useful transform. | The paper's central mechanism is concave impact, approximately `I(Q) proportional to sqrt(Q)`. | Add square-root signed-notional features beside raw signed flow. | High | Observe-only |
| Raw notional overweights large trades. | If impact is concave, linear notional pressure overstates the directional value of large orders. | Add `sqrt_signed_ratio` per microstructure window. | Medium-high | Observe-only |
| Flow persistence is informative but insufficient. | Order signs can have long memory because of metaorder splitting. | Add trade-sign lag-1 autocorrelation as context, not as a rejection rule. | Medium | Observe-only |
| Price response matters more than flow alone. | Concavity/resilience means predictable flow may not move price proportionally. | Add flow/price alignment and impact-efficiency diagnostics. | Medium | Observe-only |
| The paper is theoretical and not BTC-specific. | It uses an exactly solvable model, not Binance BTCUSDT perp replay. | Require local prospective validation before using these features in acceptance or exits. | High | Blocked from live gating |

## Implemented Additive Features

These features are now produced inside each Binance microstructure trade-flow window:

- `sqrt_signed_notional`
- `sqrt_total_notional`
- `sqrt_signed_ratio`
- `trade_sign_acf_lag1`
- `trade_price_response_bps`
- `impact_efficiency_bps_per_sqrt_notional`
- `flow_price_alignment_bps`
- `impact_transform = "sqrt_notional"`

The primary-window fields are also included in the V2 feature snapshot:

- `primary_sqrt_signed_imbalance_ratio`
- `primary_trade_sign_acf_lag1`
- `primary_flow_price_alignment_bps`
- `primary_impact_efficiency_bps_per_sqrt_notional`

Because the feature vector changed, the feature version is now:

- `v2-btc-acceptance-2`

Any older model artifact built on `v2-btc-acceptance-1` should be considered stale. Shadow scoring should skip safely on feature-version mismatch.

## Formulas

For each trade in a window:

- aggressor sign is `+1` for buyer-initiated trades
- aggressor sign is `-1` for seller-initiated trades
- notional is Binance public-flow aligned notional, using `nq` when Binance provides it

Square-root signed flow:

```text
sqrt_signed_notional = sum(sign_i * sqrt(notional_i))
sqrt_total_notional = sum(sqrt(notional_i))
sqrt_signed_ratio = sqrt_signed_notional / sqrt_total_notional
```

Trade-sign lag-1 autocorrelation:

```text
acf_1 = corr(sign_t, sign_{t-1})
```

If there are fewer than 3 trades, or if all signs are constant, the value is `null`.

Price response:

```text
trade_price_response_bps = ((last_trade_price - first_trade_price) / first_trade_price) * 10000
```

Flow/price alignment:

```text
flow_price_alignment_bps = sign(signed_notional) * trade_price_response_bps
```

Positive alignment means price moved in the same direction as signed flow. Negative alignment means signed flow was absorbed or faded.

Impact efficiency:

```text
impact_efficiency_bps_per_sqrt_notional =
    trade_price_response_bps / sqrt_total_notional
```

This is not a universal coefficient. It is a local diagnostic for comparing how much short-window price response occurred per unit of concave flow pressure.

## What Changed In Operator Visibility

The Predictions tab now prefers the square-root signed-flow ratio for its observe-only pressure score.

The Overview microstructure card now displays:

- raw signed imbalance
- square-root signed imbalance
- flow/price alignment

This makes it easier to see whether aggressive flow is actually moving price or being absorbed.

## What Did Not Change

No live entry gate was added.

No existing hard safety rule was relaxed.

No Hyperliquid execution logic was changed.

No chart-export optimizer logic was changed, because TradingView chart exports do not contain tick-level Binance trade flow.

No claim is made that these features improve profitability yet.

## Validation Requirements Before Promotion

Before any of these features can become more than observe-only diagnostics:

1. Capture prospective TradingView signal times with live Binance microstructure snapshots.
2. Build a dataset where these fields are present at signal time.
3. Compare raw signed flow against square-root signed flow out of sample.
4. Test whether negative `flow_price_alignment_bps` identifies bad continuation entries.
5. Verify the effect survives walk-forward splits.
6. Verify it does not reject high-volatility trend entries.
7. Keep rejection/retention constraints consistent with the current entry-gate research standard.

Promotion rule:

- these features may become model inputs before they become hard gates
- hard gating requires stronger evidence than diagnostic usefulness
