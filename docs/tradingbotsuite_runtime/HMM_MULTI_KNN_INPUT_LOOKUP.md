# HMM Multi-KNN Input Lookup

This document preserves the user-provided research inputs as a lookup source for future agents. It is not a live-trading approval document.

## Source Inputs

1. `Lorentzian-space KNN в криптотрейдинге BTC и ETH perpetuals (1).docx`
   - Local source: `C:/Users/papaa/Downloads/Lorentzian-space KNN в криптотрейдинге BTC и ETH perpetuals (1).docx`
   - ASCII alias for tools that cannot render Cyrillic reliably: `Lorentzian-space KNN in crypto trading BTC and ETH perpetuals (1).docx`
   - Main use: initial research basis for Lorentzian/log-Lorentzian KNN, hyperbolic embeddings, BTC/ETH perp features, WT/WT3D, exits, cost-aware validation, and research ranking.
2. `crypto_hmm_multi_knn_production_matrix (1).xlsx`
   - Local source: `C:/Users/papaa/Downloads/crypto_hmm_multi_knn_production_matrix (1).xlsx`
   - Main use: production-oriented matrix and agent runbook for HMM-routed multi-KNN strategy research.
3. User-provided refined thesis and implementation request
   - Main use: final implementation direction and acceptance rules.

## Initial Research Thesis From DOCX

The first research document separated two meanings of Lorentzian-space KNN:

- **Log-Lorentzian KNN**: tabular nearest-neighbor search using a log-compressed distance such as `sum(log(1 + abs(x_i - y_i) / scale_i))`.
- **Hyperbolic / Lorentz embedding KNN**: learned representation in negative-curvature geometry, then neighbor search by hyperbolic distance.

Key conclusions:

- For BTC and ETH perpetuals held from 1 hour to about 1 week, pure KNN is not the most likely standalone edge.
- Stronger edge candidates are funding/carry, momentum/reversal, liquidity, on-chain/exchange-flow overlays, volatility scaling, and execution discipline.
- KNN is most useful as a local analog and explainability layer over stronger base factors.
- Log-Lorentzian distance is still worth testing because crypto has heavy tails, liquidation cascades, funding spikes, and outlier candles.
- Hyperbolic/Lorentz embeddings are conceptually attractive for regime hierarchies but should be later-stage R&D after simpler tabular models show value.

Recommended research ranking from the DOCX:

1. Baseline without KNN: carry/funding + momentum/reversal + execution/risk.
2. Tabular ML baseline: XGBoost/RF using the same features.
3. Lorentz-log KNN as robust local analog model.
4. Hyperbolic/Lorentz embedding + KNN only after simpler versions prove edge.

## Feature Guidance From DOCX

Priority feature blocks:

- Price and return path: multi-horizon log returns, return z-scores, path shape.
- Volatility: realized volatility, ATR, Parkinson/Garman-Klass, vol-of-vol, jump flags.
- Liquidity and microstructure: spread, depth imbalance, queue imbalance, signed volume, trade imbalance, Amihud-like illiquidity.
- Perp structure: funding, premium index, mark-index spread, open interest, OI change, basis slope.
- On-chain and exchange flows: BTC/ETH/USDT net flows, exchange balances, realized/unrealized value metrics.
- Technical state: WaveTrend, WT slope, WT cross, WT3D coordinates, RSI, ADX, CCI, kernel trend state.
- Embeddings: PCA as production-friendly baseline; learned metrics and hyperbolic embeddings later.

Validation rules:

- Use purged walk-forward validation with embargo.
- Fit scaling, PCA, feature selection, neighbor indices, and embeddings only on train folds.
- Backtest must include fees, slippage, funding, min-notional, latency, and execution constraints.
- Treat missing market-context features as explicit missingness, not fabricated defaults.

## WT / WT3D Guidance From DOCX

WT and WT3D should be features, not standalone strategies.

Recommended WT/WT3D roles:

- WT as feature: fast/slow values, slopes, curvature, spread, percentile extremeness.
- WT as regime gate: allow mean reversion only in exhaustion zones; allow momentum when zero-line or trend state confirms.
- WT3D as embedding-lite: three-speed or multi-scale oscillator state for nearest-neighbor search.

DOCX warning:

- WT3D can improve state similarity, but the larger edge likely comes from funding, liquidity, execution, exits, and regime conditioning.

## Workbook Summary

Workbook sheets:

- `Summary`
- `Candidate_Stacks`
- `Regime_HMM`
- `KNN_Features`
- `WT3D_Features`
- `Exit_Models`
- `Agent_Runbook`
- `Source_Log`

Workbook core decision:

```text
Build HMM regime router + regime-specific Lorentzian KNNs.
```

Workbook highest-probability stack:

```text
HMM posterior gate -> KNN vote -> LightGBM/XGBoost meta-label gate -> triple-barrier exit.
```

Workbook stance:

- WT3D is a bounded, multi-speed feature family, not a standalone entry system.
- Perp edge layer is non-negotiable: funding, basis/premium, OI change, taker imbalance, liquidation context.
- Exit model is first-class: triple-barrier labels plus state-specific volatility barriers and live-style exit triggers.
- Outside-KNN upside is likely larger than pure KNN: tree ensembles, order-flow, and perp-specific models may carry more standalone gain.

## Candidate Strategy Stacks From Workbook

1. **HMM-regime Lorentzian Multi-KNN**
   - Entry regimes: all, routed separately.
   - Core features: HMM posterior, WT3D fast/normal/slow, RSI/CCI/ADX, 1h/4h returns, vol z, funding/OI, BTC-to-ETH lead.
   - Decision logic: one KNN per regime; Lorentzian distance; inverse-distance vote on triple-barrier labels.
   - Filters: no trade on high entropy, `p_regime < 0.60`, ADX conflict, high spread/slippage.
2. **HMM + KNN + XGBoost meta-labeler**
   - KNN proposes; gradient boosting predicts take/no-take and size bucket.
   - Inputs include KNN vote, vote margin, regime probability, WT3D, realized vol, funding, OI, sentiment, order flow.
3. **WT3D range-reversion KNN**
   - Range/chop regime only.
   - Uses WT3D reversal-zone intensity, Bollinger/Keltner/VWAP stretch, RSI, funding extremes, CVD exhaustion.
4. **WT3D trend-continuation KNN**
   - Bull/bear trend regimes.
   - Uses WT3D 3-speed alignment, ADX, EMA slope, breakout retest, volume z, OI expansion.
5. **Shock/liquidation avoidance + reversal scout**
   - Mostly no-trade.
   - Optional small reversal scout only after volatility compression and order-flow absorption.
6. **Cross-asset lead-lag ETH model**
   - Phase 2.
   - BTC regime, BTC return impulse, BTC funding/OI, ETH/BTC relative strength, ETH WT3D pullback.
7. **Funding/basis carry-fade hybrid**
   - Range or high funding imbalance.
   - Classifies crowded long/short conditions; fade only when trend is weak or exhaustion appears.
8. **GMM/HMM-filtered RF/KNN baseline**
   - Benchmark against HMM-KNN.
9. **HMM generative embeddings + SVM/MKL**
   - Later-stage hybrid generative-discriminative model.
10. **Pure neural multi-asset classifier benchmark**
   - Later-stage benchmark, not Phase 1.

## Regime Design From Workbook

Phase 1 starts with four regimes:

| State | Interpretation | Preferred KNN family | Trade bias |
| --- | --- | --- | --- |
| S0 | Range / low-vol chop | WT3D range-reversion KNN | Long and short allowed |
| S1 | Bull trend / risk-on | Trend-continuation / pullback KNN | Long-biased |
| S2 | Bear trend / risk-off | Short-continuation / pullback KNN | Short-biased |
| S3 | Shock / liquidation / transition | Risk-off overlay; optional reversal scout | Flat by default |

Transition is not a state. It is posterior uncertainty:

- high entropy
- small gap between top and second posterior
- fast state flipping

Default action in transition:

- no trade, or at most half-size in future live research
- Phase 1 artifact output only

## KNN Feature Lookup From Workbook

High-priority feature families:

- WT3D multi-speed oscillator: fast, normal, slow, slopes, accelerations, spreads, cross age, reversal-zone intensity, kernel slope.
- Momentum / return path: 1, 2, 4, 8, 24 bar log returns; percentile rank; close-to-VWAP distance; EMA slope.
- Trend strength / chop: ADX, choppiness, Hurst proxy, EMA slope, Bollinger bandwidth, realized autocorrelation.
- Mean-reversion stretch: RSI2/RSI14, CCI, Bollinger z, Keltner z, VWAP z, high/low sweep flags.
- Volatility / risk: realized vol 4h/8h/24h/72h, ATR%, vol-of-vol, downside semivol, MAE proxy.
- Perp derivatives: funding, annualized funding z, premium, basis, OI pct change, OI/volume divergence.
- Order flow / microstructure: taker buy ratio, CVD, order-book imbalance, spread, impact, liquidation notional, volume imbalance.
- Cross-asset spillover: BTC returns/funding/OI as ETH features, ETH/BTC return, BTC dominance, alt breadth.
- Sentiment / macro: crypto-weighted news sentiment, Fear & Greed, DXY, Nasdaq, VIX, rates, ETF flows.
- Temporal effects: hour-of-day, day-of-week, funding-window proximity, weekend flag.

## WT3D Feature Lookup From Workbook

WT3D-derived features to implement or preserve:

- `wt3d_fast`
- `wt3d_normal`
- `wt3d_slow`
- fast-normal spread
- normal-slow spread
- slopes and accelerations
- median/zero-line cross events
- bars since cross
- reversal-zone intensity
- divergence flag later only if implemented without future pivots
- kernel estimator slope/color
- MTF WT3D agreement using completed higher-timeframe bars only

Promising WT3D setups:

- trend continuation in bull/bear regimes
- pullback continuation in bull/bear regimes
- range reversion in chop
- divergence reversal in exhaustion/shock
- ETH/BTC relative setup in Phase 2

## Exit Model Lookup From Workbook

Primary exit and label framework:

- CUSUM event sampling
- volatility-scaled triple-barrier labels
- state-specific upper/lower/time barriers
- fees, slippage, and funding included

State-specific barrier starting points:

| Regime | Upper barrier | Lower barrier | Time stop |
| --- | --- | --- | --- |
| Range | 0.8-1.5 ATR | 0.8-1.2 ATR | 6h-24h |
| Bull trend | 2-4 ATR | 1-2 ATR | 24h-72h |
| Bear trend | 2-4 ATR | 1-2 ATR | 24h-72h |
| Shock | Special only | Tight | 1h-12h |
| Weekly swing | Vol-adjusted | Vol-adjusted | 3d-7d |

Live-style exit triggers for future research:

1. upper/lower triple barrier hit
2. max holding time hit
3. HMM posterior flips against trade
4. WT3D/kernel trend reverses
5. funding becomes too expensive versus expected edge
6. OI/volume confirms squeeze exhaustion
7. trailing ATR stop activates after partial profit

Required label fields:

- `gross_return`
- `fees`
- `slippage`
- `funding_paid_or_received`
- `time_in_trade`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `barrier_hit_type`

## Final User-Provided Direction

The user requested implementation of:

- full repo runbook set
- BTC-first Phase 1
- ETH as Phase 2
- HMM regime router
- regime-specific Lorentzian KNN
- XGBoost meta-filter
- triple-barrier exit research
- all outputs research-only
- no live gate, sizing, or Hyperliquid execution changes
- issue protocol where agents write difficult unresolved problems to Markdown and stop when 4 or more unresolved issues accumulate
