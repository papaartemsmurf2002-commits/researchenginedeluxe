# BTC ETH Perpetual Strategy Knowledge Base

Date cataloged: 2026-05-28
Work packet: `WPR106-23-btc-eth-perp-strategy-knowledge-ingest`
Source file: `C:/Users/papaa/Downloads/btc_eth_perp_strategies_master_report.md`
Imported full source:
`docs/research_knowledge/source_reports/btc_eth_perp_strategies_master_report.md`
Source status: external research synthesis, not standalone proof

## Use Policy

This document catalogs strategy knowledge for future falsification work. It is
not an implementation plan, work queue, candidate-ready claim, paper/live
readiness claim, or investment advice.

Agents may use it to frame hypotheses, choose feature groups, design ablations,
or define simulator requirements. Agents must not cite it as empirical evidence
that a strategy works. Any strategy idea still needs repo-native data
provenance, point-in-time feature construction, cost/funding/slippage
accounting, split-safe validation, stability evidence, and gate artifacts.

The source report includes inherited citation markers from prior research runs,
but not a complete standalone bibliography. Treat those markers as provenance
clues, not verified source references.

The full source report is stored in this directory so future agents can inspect
details that are intentionally not repeated here. This knowledge-base file is a
curated map for fast use; the imported source is the longer reference.

## Core Thesis

The report argues that a rational BTC/ETH perpetual futures research program
should be a medium-frequency, execution-honest, risk-engineered research stack,
not a small imitation of an HFT firm.

The strongest near-term research base is:

- simple strategy mechanisms with an identifiable payer of PnL;
- separate alpha, execution, and risk layers;
- realistic fee, funding, spread, slippage, latency, and liquidation modeling;
- microstructure and ML only when they improve a transparent baseline under
  realistic costs;
- carry treated as balance-sheet and collateral engineering, not as free yield;
- market making treated as inventory plus adverse-selection management, not
  passive spread capture.

The report's strongest architectural warning is to keep three layers separate:

| Layer | Role | Why separation matters |
| --- | --- | --- |
| Alpha | Trend, breakout, carry, relative value, OFI, liquidation/OI states | Keeps the market hypothesis testable and ablatable. |
| Execution | Venue adapter, maker/taker choice, order type, queue/fill/latency model | Prevents mid-price or passive-fill assumptions from masquerading as edge. |
| Risk | Vol targeting, liquidation distance, funding exposure, event throttles, collateral constraints, drawdown limits | Identifies which PnL survives realistic leverage, margin, and venue stress. |

If these layers are blended too early, a backtest may show profit without
revealing whether the alpha, the execution assumption, or the risk sizing is
responsible.

## Project Fit

The report fits this repo's current direction well. The project is already a
modular backtest and research machine with provider manifests, fixture packs,
feature registries, strategy plugins, backtest engines, candidate gates,
research-only artifacts, and operator visibility.

Useful alignment:

- The repo already supports transparent trend, volatility breakout, range,
  funding/basis, OI, KNN/local-analog, exit, cost-stress, ablation, and
  candidate-gate surfaces.
- R106 candidate-depth BTCUSDT/ETHUSDT catalog data supports medium-frequency
  bar and aggTrade-backed testing better than unsupported live claims.
- The report reinforces existing branch discipline: do not promote outputs,
  do not trade research artifacts, and do not accept a candidate without
  falsification.

Important gaps the report highlights as knowledge, not immediate tasks:

- true L2/order-book replay is required before OFI, depth-pressure, queue, and
  market-making claims can be trusted;
- Deribit options, macro/ETF flow, richer OI/positioning, and Hyperliquid fill
  telemetry are useful context only after provider provenance is available;
- carry and cross-venue funding need pathwise collateral, margin, funding-flip,
  transfer, and forced-exit simulation;
- liquidation streams are state triggers, not complete liquidation maps.

## Venue And Market-Structure Notes

BTC/ETH perpetuals are structurally different from dated futures. There is no
calendar convergence; funding, mark/index rules, margin tiers, and liquidation
waterfalls anchor the contract. That creates multiple PnL channels:

- price movement;
- funding paid/received;
- mark/index divergence;
- liquidation-distance changes;
- execution spread and slippage;
- collateral and venue constraints.

Knowledge to preserve:

- Funding and basis are state variables, not just costs. They can identify
  leveraged demand, crowding, and stress, but they can remain extreme during
  persistent trends.
- Post-ETF BTC market structure may have compressed simple carry and changed
  older regime behavior. Backtests should include a post-ETF split.
- Weekend and session effects matter because liquidity, spreads, funding
  pressure, and event risk are not uniform through time.
- Binance is a strong signal/data venue because of depth and public historical
  surfaces. Hyperliquid may be an execution research venue later, but only with
  its own book/fill/latency telemetry.
- CEX-to-CEX public-API latency arbitrage is treated as avoid-first; the likely
  edge belongs to lower-latency and better-capitalized participants.

## Strategy Priority Map

The report's combined priority ranking should be read as an order-of-testing
hint, not as expected profitability.

| Priority | Strategy family | Knowledge classification | Main reason to test or defer |
| ---: | --- | --- | --- |
| 1 | Adaptive trend plus volatility targeting | Strong first baseline | Clear mechanism, low subsecond-latency dependence, clean risk normalization. |
| 2 | BTC/ETH dynamic relative value | Strong first baseline | Simple enough to test honestly; rich enough for beta, funding, vol, and event ablations. |
| 3 | Intraday compression-to-expansion breakout | Strong first baseline | Tests regime transitions rather than generic breakouts. |
| 4 | Funding/OI crowding unwind | Useful overlay | Funding alone is weak; funding plus OI, extension, flow exhaustion, and trend filters may identify crowded unwinds. |
| 5 | Delta-neutral spot-perp carry | Research after risk simulator | Mechanism is real, but margin, collateral, transfer, venue, and funding-flip risk dominate naive backtests. |
| 6 | Deribit options regime overlay | Risk overlay | More useful for sizing, stop width, and strategy activation than direct direction prediction. |
| 7 | OFI/depth/spread classifier | Defer until replay | Strong microstructure mechanism, but realized-fill PnL can disappear after bid/ask, latency, and fill probability. |
| 8 | Open-interest shock classifier | Useful context | OI only matters jointly with price, funding, ratios, and flow. |
| 9 | VWAP-to-mid micro-reversion | Entry/exit overlay | Better as an execution-quality filter than standalone alpha. |
| 10 | Liquidation-flow tactics | State overlay | Liquidation prints can split continuation/exhaustion states but are incomplete ground truth. |
| 11 | Cross-venue funding spread arbitrage | Later research | Requires survival/half-life, execution skew, margin, stablecoin, bridge, and venue-risk modeling. |
| 12 | Hyperliquid inventory-aware market making | Later only | Needs local book, fill logs, stale-quote controls, queue model, toxicity filters, and mature OMS. |
| 13 | Generic deep learning directional model | Low first value | Complexity without a payer story is likely curve fitting unless it improves baselines in OOS ablation. |
| 14 | Public-API latency arbitrage | Avoid | Public setup is unlikely to compete where latency is the edge. |

High-level order-of-testing logic:

```text
medium-frequency bar/flow systems
-> richer perp context and relative value
-> event replay for microstructure overlays
-> collateral/margin simulator for carry
-> OMS/fill telemetry before market making
```

Do not invert that order. OFI, carry, and market making may be promising, but
their simulator requirements are materially harder than trend/RV/breakout.

## Strategy Cards

### Adaptive Trend Plus Volatility Targeting

Mechanism:
Leveraged flow, reflexivity, liquidations, slow information diffusion, and
cross-venue participation can create directional persistence.

Testable feature families:
multi-horizon returns, Donchian or rolling high/low position, EMA or regression
slope, realized volatility regime, funding/basis/OI throttle, time-of-week,
macro/event filters, optional options-vol/skew leverage gate.

Backtest cautions:
trend systems must survive chop, crowded funding, post-ETF splits, event
periods, false starts, and conservative fees/slippage. Vol targeting must not
hide tail loss or liquidation distance.

### Intraday Compression-To-Expansion Breakout

Mechanism:
Low realized volatility and narrow range can represent temporary balance; a
flow-confirmed break can mark transition into directional expansion.

Testable feature families:
range percentile, local realized-vol percentile, spread/depth normality,
breakout beyond compression range, aggressive flow confirmation, session/event
context, OI/funding crowding.

Backtest cautions:
separate acceptance breakouts from failure breakouts. Falsify by session,
weekend, event windows, and post-ETF regime. Add slippage uplift around news.

### Funding/OI Crowding Unwind

Mechanism:
Funding is self-correcting only in context. Extreme funding plus OI
acceleration, price extension, basis, ratios, and tape exhaustion may indicate
crowded leverage vulnerable to unwind.

Testable feature families:
funding z-score, mark-index gap, OI z-score/acceleration, long-short ratios,
taker imbalance, price extension, settlement window, liquidation pressure.

Backtest cautions:
funding-only must be a baseline. If the conditioned model does not beat
funding-only after costs and splits, the added structure is not useful.

### Delta-Neutral Carry

Mechanism:
Carry monetizes demand for leveraged exposure and constrained arbitrage
capital.

Required simulator scope:
spot/perp mids, funding schedule, projected funding, maker/taker costs,
borrow/stablecoin yield, collateral haircut, margin rules, liquidation
thresholds, transfer latency, venue risk, basis half-life, and forced exits.

Backtest cautions:
this is a balance-sheet strategy. Do not treat delta-neutral as risk-free, and
do not trust a carry result without pathwise margin/collateral accounting.

### BTC/ETH Dynamic Relative Value

Mechanism:
BTC and ETH are linked but regime-dependent. Beta-adjusted residuals can revert
in calm regimes or express BTC leadership and ETH catch-up in volatile regimes.

Testable feature families:
rolling or Kalman beta, ETH residual versus beta-adjusted BTC return, spread
z-score, half-life, funding differential, volatility regime, BTC impulse/lead,
BTC/ETH options-vol gap.

Backtest cautions:
hedge ratio stability and half-life must survive walk-forward. Funding
differential must not eat the spread PnL.

### Open-Interest Shock Classifier

Mechanism:
OI change is a state variable, not a standalone direction signal. It must be
interpreted with price, funding, taker flow, and liquidation context.

State examples:
healthy build-up, exhausted crowding, forced unwind, short squeeze, long
squeeze.

Backtest cautions:
add OI to a price plus flow baseline and keep it only if it improves expectancy,
drawdown, or trade selection.

### OFI / Depth / Spread Classifier

Mechanism:
Signed flow, top-of-book pressure, OFI, depth slope, and spread regime can
predict very short-horizon moves.

Required simulator scope:
trades, L2 depth or reconstructed book, sequence integrity, latency, bid/ask,
fill probability, cancel behavior, and realized-fill PnL.

Backtest cautions:
mid-price forecast accuracy is insufficient. Measure realized-fill PnL,
decision-to-fill drift, adverse selection after fill, fill ratio, cancel ratio,
and alpha half-life.

### VWAP-To-Mid Micro-Reversion

Mechanism:
Aggressive flow can push transaction VWAP away from mid. If intensity decays
and spread normalizes, some pressure may revert.

Best use:
entry/exit overlay for parent trend, RV, or funding systems.

Backtest cautions:
do not fade when spread widens or OFI continues. Keep it only if it improves
MAE/MFE, entry price, or net hit rate for the parent strategy.

### Liquidation-Flow Tactics

Mechanism:
Forced flows can create short-lived nonlinear continuation or exhaustion.

Best use:
state trigger or risk overlay.

Backtest cautions:
Binance liquidation streams are incomplete snapshots, not a complete
liquidation map. Test only after a flow/depth baseline exists.

### Deribit Options Regime Overlay

Mechanism:
Options surfaces can identify volatility and crash-risk regimes better than
they predict immediate direction.

Testable features:
DVOL, implied term structure, skew, realized versus implied volatility,
BTC/ETH vol gap, options OI.

Backtest cautions:
must improve drawdown, tail loss, sizing, or conditional expectancy without
destroying the parent strategy's return profile.

### Macro / ETF / News Event Overlay

Mechanism:
Events change volatility and execution quality more reliably than direction.

Best use:
risk throttle, mean-reversion freeze, slippage uplift, breakout permission
after post-event expansion.

Backtest cautions:
do not make it first alpha. It should reduce event-window damage or improve
conditional activation.

### Inventory-Aware Market Making

Mechanism:
Spread capture plus rebates plus inventory skew plus short-horizon alpha.

Required simulator scope:
local book, fill/cancel logs, post-only/reduce-only semantics, queue
approximation, stale quote cancellation, toxicity filters, reconnect/rate-limit
handling, and inventory penalty.

Backtest cautions:
passive fills are often toxic. A market-making backtest that earns spread
without adverse-selection penalty is likely false.

## Feature Knowledge Map

| Feature group | Examples | Likely role |
| --- | --- | --- |
| Returns/trend | 1m/5m/1h/4h returns, EMA slope, breakout position | Directional baseline and trend context. |
| Volatility | realized vol, vol-of-vol, range compression, jump flags | Regime detection and sizing. |
| Funding/basis | funding z-score, mark-index gap, basis slope, funding interval | Carry, crowding, and risk accounting. |
| OI/positioning | OI delta, OI acceleration, long-short ratios, top-trader ratios | Crowding/unwind state. |
| Flow | signed volume, taker imbalance, trade intensity | Short-horizon alpha or confirmation. |
| Book | spread, top-N imbalance, OFI, depth slope, cancel/add intensity | Execution realism and short-horizon alpha after replay exists. |
| Liquidations | liquidation bursts, direction, context | State trigger and risk overlay. |
| Options | DVOL, skew, term structure, BTC/ETH vol gap | Risk/regime overlay. |
| Events | CPI/FOMC/NFP, ETF flows, weekend/US-hours, news sentiment | Risk throttle and conditional activation. |
| On-chain | selected stablecoin and exchange flows | Secondary overlay only. |

## High-Value Experiment Backlog From Source Report

This table preserves the report's promising research ideas as hypotheses, not
implementation commitments.

| Hypothesis | Required data | Complexity | Research value | Pass/fail criterion |
| --- | --- | ---: | ---: | --- |
| Vol-targeted 4h trend survives fees on BTC/ETH | OHLCV plus funding | Low | High | Positive OOS costed expectancy across both assets and regimes. |
| Intraday breakout only works in expansion regimes | 1m/5m bars plus flow/session context | Low | High | Conditioned expansion model beats unconditional breakout. |
| Funding extreme needs OI plus extension | Funding, OI, price extension, taker flow | Low | High | Full conditioned model beats funding-only baseline. |
| BTC/ETH beta spread is stable in calm regimes | Synchronized BTC/ETH returns | Low | High | Stable hedge ratio, half-life, and OOS spread exits. |
| Deribit vol overlay reduces trend drawdown | DVOL/skew plus base trend system | Medium | High | Lower tail loss without destroying CAGR/expectancy. |
| Binance OFI survives taker simulation | Trades plus L2 depth | Medium | High | Realized-fill edge remains after latency and bid/ask. |
| VWAP-to-mid improves entry quality | Trades, mid, spread | Medium | Medium | Better MAE/MFE and net hit rate for parent strategy. |
| OI shock classifier beats raw OI delta | OI, price, funding, ratios | Low | Medium | Improves trade selection and max drawdown versus raw OI. |
| Liquidation bursts split continuation/exhaustion | Liquidation prints, L2, trades | Medium | Medium | Edge survives incomplete liquidation data treatment. |
| Cross-venue carry needs survival model | Multi-venue funding, fees, margin | Medium | Medium | Spread magnitude alone fails; survival model improves OOS. |
| Macro-event throttle reduces event drawdowns | Calendar plus base strategies | Low | Medium | Tail event loss is materially smaller. |
| Simple GBDT beats deep net on same LOB features | L2 plus trades | Medium | Medium | Deep model gives no stable OOS lift unless proven. |
| Hyperliquid maker needs alpha skew | Hyperliquid book, fills, local alpha | High | Medium | PnL remains after toxicity, queue, stale-quote penalties. |

## Strategy-Specific Falsification Notes

Use these notes when creating future work packets. They are intended to prevent
weak tests from looking stronger than they are.

| Strategy family | Baseline to beat | Must ablate | Main false-positive risk |
| --- | --- | --- | --- |
| Adaptive trend | Simple vol-targeted momentum/trend with funding as cost | Trend horizons, vol target, funding/OI throttle, event/weekend filters | Profit concentrated in a small number of crisis/trend days. |
| Compression breakout | Unconditional breakout and no-trade baseline | Compression definition, flow confirmation, session/event gate | Range formula overfit and news whipsaw. |
| Funding/OI unwind | Funding-only fade and trend-following baseline | OI, price extension, taker flow, liquidation context, trend veto | Fading persistent leveraged demand too early. |
| BTC/ETH RV | Static beta spread and outright BTC/ETH trend | Dynamic beta, calm/volatile regime split, funding differential, vol gap | Nonstationary hedge ratio and regime break. |
| OI shock | Price plus flow baseline | OI delta, OI acceleration, long/short ratios, funding state | OI visually explains moves but adds no OOS value. |
| OFI/depth | Trade imbalance and no-L2 baseline | OFI windows, top-N imbalance, spread, depth slope, latency | Predicts mid-price but not executable fills. |
| VWAP reversion | Parent strategy without overlay | VWAP deviation, intensity decay, OFI reversal, spread filter | Reversion only exists at mid, not bid/ask. |
| Liquidation tactics | Flow/depth baseline without liquidation prints | Liquidation burst threshold, support/reclaim, spread/depth states | Treating incomplete liquidation stream as complete map. |
| Options overlay | Parent strategy without options | DVOL, skew, term structure, vol gap, crash-risk throttle | Explanatory overlay that does not improve decisions. |
| Carry | Static carry threshold with conservative costs | Funding projection, basis decay buffer, margin headroom, forced exits | Delta-neutral paper PnL hides pathwise margin failure. |
| Market making | No-quote and taker/mid baselines | Inventory penalty, alpha skew, toxicity filter, stale quote cancel | Spread capture without adverse selection. |

## Overestimated Or Avoid-First Ideas

The report repeatedly warns against treating these as starting points:

- pure funding arbitrage marketed as risk-free yield;
- generic LSTM/Transformer/RL on OHLCV without a payer story;
- public-L2 spoofing or iceberg detection without L3/order IDs;
- liquidation heatmap trading without tape/book context;
- maker-only rebate farming without alpha and toxicity controls;
- CEX-to-CEX public-API latency arbitrage;
- pure social/news/whale-alert signals;
- one model that claims to trade all regimes;
- any strategy tested on mid-price fills only.

These ideas can still contain feature inspiration. They should not be used as a
production basis until the repo can falsify the execution, cost, regime, and
data-quality assumptions behind them.

## Data And Simulator Standards

The report treats the first production-grade artifact as the data lake, not a
strategy. Data and simulator requirements that matter for this repo:

- raw immutable events plus normalized Parquet tables;
- replayable event bus for anything below bar horizon;
- Binance futures trades, book/depth, mark/index/funding, liquidations, OI,
  taker volume, and long-short ratios;
- synchronized BTC/ETH cross-venue mids;
- Hyperliquid book/funding/fill metadata if it becomes an execution research
  venue;
- Deribit options snapshots, skew, term structure, and DVOL if options overlays
  are tested;
- venue metadata for fees, funding schedules, liquidation rules, margin tiers,
  rate limits, and mark/index logic;
- live or shadow order logs with decision, submit, ack, fill, cancel, error,
  partial-fill, and stale-book timestamps.

Simulator requirements by strategy family:

| Family | Minimum honest simulator |
| --- | --- |
| Trend / breakout / RV | Bar engine with bid/ask-aware costs, funding, conservative slippage, and regime splits. |
| Funding/OI overlays | Bar engine plus funding schedule, mark/index gap, OI provenance, and funding as both cost and signal. |
| Carry / cross-venue spread | Pathwise collateral, margin, transfer, funding flip, forced exit, and venue-risk simulator. |
| OFI / VWAP / liquidation tactics | Event replay with trades, L2/book state, latency, bid/ask, fill probability, and adverse-selection metrics. |
| Market making | Full order-state, queue/fill, stale-quote, inventory, toxicity, cancel, reconnect, and rate-limit simulation. |

## Validation Standards

Before any idea graduates from hypothesis to candidate evidence, it should
survive:

- strict chronological split;
- rolling or expanding walk-forward;
- post-cost fee, funding, borrow, collateral, spread, and slippage accounting;
- post-ETF split;
- weekend/session split;
- high-vol, low-vol, bull, bear, and chop splits;
- event-window stress;
- parameter stability;
- feature-group ablation;
- parent-baseline comparison;
- latency/fill sensitivity grid for execution-sensitive systems;
- outlier-day contribution analysis;
- regime-separated OOS reporting.

Metrics worth tracking:

- costed expectancy, Sharpe, Sortino, Calmar, max drawdown, time under water;
- turnover, holding period, exposure time, gross/net leverage;
- fee-to-gross-PnL ratio and funding PnL share;
- slippage, decision-to-fill drift, adverse selection after fill;
- fill ratio, cancel ratio, liquidation distance, margin stress;
- regime-bucket performance and live-vs-paper divergence;
- orderbook participation or capacity proxy for short-horizon systems.

## ML And Microstructure Guidance

The report's ML stance is conservative: use ML as a filter, meta-labeler,
regime classifier, sizing helper, or short-horizon microstructure model only
after transparent baselines exist.

Useful ML roles:

- classify whether a primary signal is worth taking;
- estimate expected net edge after fees, funding, spread, and slippage;
- separate volatility, trend, chop, squeeze, and crash-risk regimes;
- detect local order-flow imbalance if L2 replay and latency are modeled;
- improve exit timing or position sizing for an already profitable baseline.

Labels to prefer over naive next-bar direction:

- volatility-aware horizon labels;
- triple-barrier labels with stop, target, and timeout;
- meta-labels on top of primary strategy signals;
- purged and embargoed labels for overlapping outcomes;
- strictly chronological train/validation/test splits;
- rolling or expanding walk-forward reporting;
- regime-separated OOS reports.

ML outputs to distrust:

- accuracy improvements that do not improve net expectancy;
- models that only work on mid-price;
- models whose alpha disappears after maker/taker distinction;
- models that improve with complexity but fail across regimes;
- public-L2 spoofing/iceberg claims without order IDs;
- social sentiment as a standalone intraday predictor;
- performance concentrated in a few outlier days.

Preferred framing:

```text
not "will price go up?"
but "is expected edge greater than cost, funding, slippage, and risk now?"
```

## Red-Team Cautions

Common false positives:

- mid-price PnL treated as tradable PnL;
- passive spread capture without adverse-selection penalty;
- OFI accuracy that does not survive realized-fill PnL;
- funding or carry treated as risk-free;
- spread magnitude used without spread survival/reversal model;
- liquidation heatmaps treated as complete ground truth;
- ML accuracy optimized without fee/slippage/funding objective;
- cross-venue edge without measured latency and execution skew;
- performance concentrated in a tiny number of outlier days;
- features that improve in-sample complexity but fail OOS or across regimes.

Likely crowded or overemphasized:

- obvious BTC/ETH funding capture;
- simple high-funding contrarian shorts;
- liquidation wick fades from public heatmaps;
- public CEX latency dislocations;
- maker rebate farming without alpha;
- generic sentiment/news signals;
- OHLCV deep learning demos.

Negative discipline the report emphasizes:

- max daily and intraday drawdown halts;
- volatility spike throttle;
- spread/depth deterioration halt;
- macro-event freeze for mean reversion;
- funding flip exit;
- OI/funding squeeze warning;
- stale data and sequence-gap halt;
- venue status or rate-limit halt;
- live-vs-paper divergence halt;
- liquidation-distance minimum;
- strategy-specific parameter-instability deactivation.

## How Future Agents Should Use This

Use this document as a knowledge base when designing a future research packet.
Do not copy its ranked list into the stage roadmap. Instead:

- pick one hypothesis family;
- state the market mechanism and expected payer of PnL;
- map required data to existing or missing repo provider contracts;
- define the minimum honest simulator for that horizon;
- define baseline and ablation comparisons;
- define the exact falsification criteria before running experiments;
- preserve research-only and promotion-false artifact metadata.

If a proposed packet cannot meet the data and simulator standard for the
strategy family, keep the idea as knowledge only.
