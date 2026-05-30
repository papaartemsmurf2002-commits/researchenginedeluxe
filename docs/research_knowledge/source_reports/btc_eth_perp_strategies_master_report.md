# Master report: автоматизируемые стратегии для BTC и ETH perpetual futures

**Скомпоновано из двух исследовательских документов:** `deep-research-report (7).md` и `deep-research-report (8).md`.

**Статус:** исследовательский документ, не инвестиционный совет.
**Назначение:** дать единую, более цельную версию без потери глубины: сохранить venue mechanics, strategy atlas, deep dives, ML/microstructure layer, validation roadmap, backlog and red-team critique, но убрать повторения и добавить синтетический слой практического мышления.

> Примечание о ссылках: исходные файлы содержали inline source markers вида `cite...`. В этом объединённом документе они сохранены как inherited research markers, потому что сами библиографические карточки/URL не были приложены отдельно. Их следует читать как карту источников из первоначального research run, а не как полноценный standalone bibliography.

---

## 1. Исполнительное резюме

Это исследование рассматривает «перспективную» стратегию не как обещание доходности, а как подход, у которого есть правдоподобное положительное математическое ожидание **после** комиссий, проскальзывания, funding, borrow/collateral drag, задержек, path-dependent liquidation risk, venue failures и смены режимов. Для BTC и ETH perpetual futures ключевая реальность такова: рынок достаточно ликвиден, чтобы простые идеи быстро арбитражировались, но всё ещё достаточно фрагментирован по venue, funding mechanics, ликвидациям, API, latency и custody/collateral constraints, чтобы disciplined independent quant мог найти edge в правильно ограниченном пространстве.

Главный вывод двух документов совпадает и после объединения становится ещё жёстче: **лучшие стартовые направления для solo-quant — не “магический ИИ”, не универсальный RL-бот и не псевдо-HFT latency arbitrage, а mid-frequency systematic stack**, где сначала строятся data, simulation and execution layers, затем тестируются несколько механистически понятных стратегий, и только после этого добавляются ML, order-flow and market-making components.

Самая рациональная opportunity set выглядит так:

1. **Adaptive trend following with volatility targeting and regime filters** на BTC/ETH perps. Это самая чистая стартовая линия: понятный механизм, низкая зависимость от subsecond latency, высокая автоматизируемость, хорошая совместимость с risk throttling.
2. **Intraday compression → volatility expansion breakout.** Эта идея сильна не как “каждый breakout надо покупать”, а как regime-change detector: рынок переходит из узкого, тихого баланса в направленное расширение диапазона.
3. **Funding/basis/carry strategies with pathwise risk engine.** Carry — структурная премия, но не free lunch. Без separate-leg collateral accounting, funding flip logic, margin stress simulation and forced-exit rules такие стратегии выглядят намного лучше на бумаге, чем в live.
4. **BTC/ETH relative value with dynamic beta hedge.** Это хороший middle ground между outright directional и fragile stat-arb: data requirements умеренные, комиссии терпимые, а BTC→ETH spillover/leadership можно проверить честно.
5. **Short-horizon order-flow imbalance / VWAP-to-mid / depth-pressure overlays.** Механизм реален, но execution-fragile. Эти сигналы не стоит превращать в production alpha до L2 replay, latency model and realized fill diagnostics.
6. **Liquidation-flow and open-interest shock classifiers.** Полезны как state variables, но опасны как standalone strategy. Ликвидации надо использовать как trigger/context, а не как полную карту forced flows.
7. **Deribit options-informed overlays.** Options data лучше всего использовать для regime/risk/leverage gating, а не для прямого “buy/sell perp now” predictor.
8. **Inventory-aware market making on Hyperliquid or similar venues.** Это может быть интересно позже, но only after validated short-term alpha, robust OMS, stale-quote protection and adverse-selection accounting.

Самые переоценённые идеи тоже устойчивы в обоих отчётах: pure funding arbitrage as “risk-free yield”; generic deep learning по OHLCV; public-L2 spoofing/iceberg detection; liquidation heatmap trading без book/tape context; maker-only rebate farming; CEX-to-CEX public-API latency arbitrage; and “one model to trade all regimes”. Эти подходы могут содержать зерно идеи, но в чистом виде они обычно не переживают fees, fills, regime shifts or adverse selection. citeturn36view0turn38view0turn35view2turn36view4turn39view0

**Интеграционный тезис, добавленный поверх двух документов:** проект стоит проектировать как три отдельных, но связанных слоя:

- **Alpha layer:** trend, breakout, carry, RV, OFI, liquidation/OI states.
- **Execution layer:** venue adapter, order type selection, maker/taker choice, queue/fill model, latency and stale-book protection.
- **Risk layer:** volatility targeting, liquidation distance, funding exposure, event throttles, collateral/cross-margin constraints, drawdown governors and kill switches.

Если эти слои смешать, backtest почти неизбежно начнёт лгать. Если разделить, можно понять, что именно приносит PnL, кто за него платит, и какая часть edge исчезает при реалистичном исполнении.

---

## 2. Карта источников и метод исследования

Два исходных документа опирались на четыре класса источников:

1. **Official venue docs and APIs.** Binance, Hyperliquid, Coinbase International, Bybit, OKX, dYdX, Aevo, Drift, GMX, Deribit. Эти документы важны для funding, fee schedules, market-data streams, liquidation rules, order flags, rate limits, mark/index logic, portfolio margin, historical data availability and execution semantics.
2. **Academic papers and working papers.** Perpetual pricing, crypto carry, funding market fragmentation, cross-impact, price discovery, market quality, options-implied risk premia, microstructure feature stability, LOB ML, sentiment/news spillovers, and regime models.
3. **Engineering/data stack sources.** Tardis, NautilusTrader, hftbacktest, Hummingbot and related bot/replay infrastructure.
4. **Multilingual practitioner sources.** Chinese, Japanese, Korean, Russian, Spanish and Turkish materials were used mostly as hypothesis generators and as evidence of what retail communities over-emphasize or under-estimate. They were not treated as proof of edge.

The strongest sources are the first two classes. Official docs define the feasible trading space; academic/working papers explain why certain premia exist and why they can disappear. Engineering sources define whether the backtest can be made honest. Community content is useful for finding popular heuristics — funding arbitrage, liquidation maps, OI/funding contrarian trades, market making, order-flow scalping — but it repeatedly underestimates transfer risk, collateral fragmentation, spread reversal, toxic fills and liquidation path dependency. citeturn21view0turn21view7turn22view4turn23view0turn23view5turn27view6turn27view7turn35view2turn35view3turn36view2turn36view4

A useful conservative taxonomy for evaluating strategy claims:

| Evidence class | Meaning | How to treat it |
|---|---|---|
| Proven mechanism | Economic/microstructural mechanism is clear and supported by multiple strong sources | Worth building baseline tests first |
| Plausible mechanism | Logic is strong, but live net-of-cost evidence is incomplete | Worth testing with strict falsification |
| Anecdotal edge | Common practitioner heuristic, limited formal proof | Use only as feature/context until proven |
| Backtest-only / marketing edge | Edge depends on unrealistic mid fills, no cost model, or opaque assumptions | Avoid as production basis |

This lens explains why simple-sounding ideas can rank higher than sophisticated ones. Trend/carry/RV/order-flow have identifiable payers: trend-chasers, leveraged demand, fragmented margin, liquidity takers, forced liquidations, or informed/uninformed order-flow imbalance. Generic deep learning or RL often lacks such a payer story; it starts from model complexity rather than market mechanism.

---

## 3. Market structure: why BTC/ETH perpetuals are special

### 3.1 Perpetuals are not ordinary futures

BTC/ETH perpetual futures dominate crypto derivatives because they give leverage without expiry or roll. But this makes them structurally different from fixed-maturity futures. A perpetual does not converge to spot on a calendar date. Its anchor is the **funding mechanism**, plus mark/index price rules and liquidation waterfall.

That has three consequences:

- **Funding and basis are state variables**, not just carry costs. They describe leveraged demand, crowding, venue stress and arbitrage-capital constraints.
- **PnL has multiple channels:** price move, funding, mark/index dynamics, liquidation distance and execution slippage.
- **No-arbitrage bounds are looser and more path-dependent** than in simple spot/futures convergence. Perpetual pricing involves random maturity, funding feedback and trading-cost bounds. citeturn38view0turn20search13turn15search1turn15search0

The BIS-style carry literature and related perpetual pricing work matter because they show both sides of the opportunity. Crypto carry can be large because of leveraged trend-chasing demand and limited arbitrage capital; however, that does not mean cash-and-carry is risk-free. The launch of US spot BTC ETFs structurally compressed some carry opportunities and made the market more institutionally arbitraged. Older backtests of simple basis/carry therefore need stronger discounting than tests of trend or execution-based systems. citeturn36view0turn16search12

### 3.2 Funding mechanics are venue-specific

One of the most important merged conclusions: **any carry/funding strategy without a venue-specific engine almost certainly overstates edge.** Funding interval, formula, clamp/cap behavior, settlement timing and margin rules differ materially across venues.

Examples from the source reports:

- Binance USDⓈ-M defaults to 8-hour funding, but the interval can shift under cap/floor conditions.
- OKX also uses 8-hour default logic but can support 1/2/4-hour variants.
- Coinbase International uses hourly funding and differs from the typical base-interest-plus-clamp design.
- Hyperliquid pays hourly as one eighth of an 8-hour formula and allows very high caps under stress.
- dYdX, Aevo and Drift also use hourly-style logic, but with governance, TWAP, oracle or lazy-update differences.
- GMX is not a normal LOB venue: borrowing fees, price impact and pool imbalance are first-class costs, so LOB carry models do not transfer cleanly.

| Venue | Market model | Funding / margin note | Automation implication |
|---|---|---|---|
| Binance USDⓈ-M | CEX LOB | Default 8h funding; rich futures data; L2 public book | Best baseline data source for BTC/ETH research |
| Bybit | CEX LOB | Mature perps; post-only/reduce-only; taker costs matter | Viable execution venue but needs cost discipline |
| OKX | CEX LOB | Strong venue for carry/RV; varied funding intervals possible | Needs exact venue adapter |
| Coinbase International | CEX LOB | Hourly funding; clear institutional docs | Useful cross-venue and basis venue |
| Deribit | Options + futures/perps | Perps useful, but options data is the main signal value | Critical vol/skew source |
| Hyperliquid | On-chain CLOB/HyperCore | Hourly funding, on-chain state, no special DMM latency advantage | Good for slower systematic alpha, not public-internet latency arb |
| dYdX | On-chain orderbook-style | Hourly/governance funding; node infra matters | Useful for fragmentation/carry studies |
| Aevo / Drift | On-chain/hybrid | Hourly; idiosyncratic mechanics | Secondary venues for carry/frag tests |
| GMX | Oracle/pool | Funding + borrowing + price impact | Do not port LOB strategies directly |

The merged conclusion is not “avoid DEX” or “use CEX only”. It is: **CEX and DEX differ strategically, not just in custody.** CEX venues tend to lead price discovery and offer deeper immediate liquidity. DEX/on-chain venues may offer different funding/collateral conditions and maker incentives, but their latency, node-state requirements and execution semantics change which strategies are realistic. citeturn36view4turn29view1turn29view2

### 3.3 Binance as signal venue; Hyperliquid as possible execution venue

A recurring architecture in the two reports is `Binance data → Hyperliquid execution`. The refined version is:

- **Works plausibly** for minute-bar trend, funding/carry overlays, BTC/ETH RV, event-driven state machines, and some seconds-to-minutes order-flow features.
- **Does not work plausibly** for true subsecond latency arb, queue-jump market making, public-L2 spoofing detection or aggressive maker queue warfare.

Binance provides rich public futures streams: trades, diff-depth, book ticker, mark/index, liquidation snapshots, open interest, taker buy/sell volume and long/short ratios. But it is still L2-by-price-level, not full L3-by-order. RPI orders are not visible. Local book reconstruction requires snapshot + diff protocol and strict sequence checks. That is enough for OFI, depth slope, spread, trade intensity and pressure features; it is not enough for precise queue position, hidden liquidity or reliable iceberg/spoof labels. citeturn32view0turn22search0turn21search7turn11search2turn11search4turn11search0turn11search1

Hyperliquid is attractive because it has clear APIs, maker rebates, on-chain transparency, portfolio/collateral features and no special designated market-maker latency privileges. But the execution game is different. Its median end-to-end latency is on the order of tenths of seconds for geographically close clients, and serious latency-sensitive users are encouraged to run node/local-state infrastructure. That is workable for slower systematic alpha; it is not a substitute for CEX colocation. citeturn24search4turn24search6turn23search1turn19search1

### 3.4 Post-ETF regime and time-of-week liquidity

The ETF era changes how to treat historical data. Spot BTC ETFs have affected returns/volatility, institutional flow timing and liquidity concentration. One practical implication from the source reports is that weekend/weekday liquidity asymmetry matters more than before: US-hours and weekday flows can dominate, while weekends may have thinner liquidity and larger stress moves. This makes time-of-week and macro/event filters part of the risk engine, not a cosmetic overlay. citeturn19search1turn19search5turn19search8

**Added synthesis:** when splitting backtests, use at least these regime partitions:

- pre-ETF vs ETF-era;
- weekday US-hours vs non-US-hours vs weekend;
- high funding vs normal funding;
- high OI acceleration vs neutral OI;
- narrow-spread normal depth vs stressed/wide-spread depth;
- macro-event windows vs ordinary hours;
- CEX-led vs DEX-lagging cross-venue episodes.

A strategy that only survives the aggregate sample but dies in these partitions is not ready for live deployment.

---

## 4. Strategy atlas and priority ranking

### 4.1 Broad strategy map

| Strategy family | Core alpha hypothesis | Evidence class | Horizon | Data needed | Automation | Solo fit | Overall viability |
|---|---|---|---|---|---|---|---|
| Adaptive trend following | Trend-chasing and behavioral inertia persist in leveraged futures flow | Strong/plausible | Hours–days | OHLCV, volume, funding, OI | High | High | Very high |
| Intraday compression breakout | Low-vol balance often resolves into directional expansion | Plausible | Minutes–hours | 1m/5m bars, realized vol, sessions, flow | High | High | Very high |
| Funding/basis extreme reversion | Extreme funding/basis plus OI crowding can unwind | Mixed but plausible | Hours–days | Funding, basis, OI, taker flow, ratios | High | High | High |
| Delta-neutral carry | Funding/basis compensates arbitrage capital and leverage supply | Strong mechanism | Hours–weeks | Spot/perp mids, fees, borrow, margin, funding | Medium | Medium | High if risk-engineered |
| BTC/ETH relative value | BTC and ETH are linked but regime-dependent; residuals can revert or follow leadership | Plausible | Hours–days | Synchronized returns, beta, funding, vol | High | High | High |
| OFI / depth / spread alpha | Signed flow and L2 pressure predict short-horizon moves | Strong but fragile | Seconds–minutes | Trades + L2 + latency/fill replay | Medium | Medium | High only with replay |
| VWAP/micro reversion | Short pressure overshoots and partially mean-reverts | Plausible | Seconds–minutes | Trades, mid, spread, VWAP | High | High as overlay | Medium-high |
| Open-interest shock classifier | OI changes classify build-up, trend confirmation or unwind | Plausible | Minutes–hours | OI, funding, ratios, price response | High | High | Medium-high |
| Liquidation cascade tactics | Forced flows create nonlinear short-lived dislocations | Plausible/anecdotal | Seconds–minutes | Liquidation stream, depth, taker flow | Medium | Medium | Medium-high as overlay |
| Deribit options overlay | IV/skew/term structure improves risk regime identification | Moderate/strong for risk | Hours–days | DVOL, skew, options OI, perps | Medium | Medium | Medium-high |
| Macro/ETF/news overlay | Events change vol/execution regimes more than they give clean direction | Plausible | Hours–days | Calendar, ETF flows, news sentiment | High | High | Medium |
| Hyperliquid market making | Spread + rebates + inventory skew + micro-alpha | Mechanism strong, execution-sensitive | Seconds–minutes | Local book, fills, alpha, inventory | High | Medium-low first | Medium/later |
| Generic deep learning/RL | Complex model discovers hidden nonlinear alpha | Mostly backtest-only | Any | Everything | Formal high | Low | Low as first project |
| Cross-exchange latency arb | Fast venue lead/lag can be captured | Real for institutions, weak for public setup | Milliseconds | Colocated feeds/execution | Low | Very low | Avoid |

The practical thesis is simple: **mid-frequency first, microstructure second, market making third, public-API latency arbitrage never.**

### 4.2 Refined priority scores

The two documents had slightly different score tables. The combined ranking below blends them into an order-of-operations view rather than a claim of absolute profitability.

| Rank | Strategy | Mechanism | Evidence | Data | Feasibility | Cost robustness | Regime robustness | Solo practicality | Combined priority |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | Adaptive trend + vol targeting | 9 | 7 | 10 | 9 | 8 | 7 | 10 | 8.6 |
| 2 | BTC/ETH dynamic relative value | 7 | 6 | 10 | 8 | 8 | 7 | 9 | 7.9 |
| 3 | Intraday compression breakout | 8 | 6 | 9 | 8 | 7 | 6 | 9 | 7.7 |
| 4 | Funding/OI crowding unwind | 8 | 6 | 8 | 8 | 7 | 5 | 8 | 7.3 |
| 5 | Delta-neutral spot-perp carry | 9 | 8 | 7 | 6 | 7 | 6 | 6 | 7.2 |
| 6 | Deribit options regime overlay | 7 | 7 | 6 | 7 | 8 | 8 | 7 | 7.1 |
| 7 | OFI/depth/spread classifier | 8 | 8 | 7 | 6 | 4 | 5 | 6 | 6.9 |
| 8 | Open-interest shock classifier | 7 | 6 | 8 | 8 | 7 | 5 | 9 | 7.2 |
| 9 | VWAP-to-mid/micro reversion | 6 | 5 | 7 | 8 | 5 | 5 | 8 | 6.4 |
| 10 | Liquidation-flow tactics | 8 | 5 | 8 | 6 | 5 | 4 | 7 | 6.2 |
| 11 | Cross-venue funding spread arb | 8 | 7 | 6 | 5 | 4 | 4 | 5 | 6.0 |
| 12 | Hyperliquid inventory-aware MM | 8 | 5 | 7 | 5 | 4 | 4 | 5 | 5.7 |
| 13 | Generic deep learning directional | 4 | 4 | 7 | 4 | 5 | 3 | 4 | 4.4 |
| 14 | Public-API latency arb | 7 | 5 | 3 | 1 | 2 | 3 | 1 | 2.8 |

Why trend ranks first: it has the best combination of intuitive mechanism, data simplicity, lower micro-latency dependence and easy risk normalization. Why carry ranks below its mechanism score: because capital/margin/venue risk is a much larger engineering problem than typical yield-style backtests admit. Why OFI ranks below its evidence score: because execution and fill simulation can erase it. Why market making is not first: because maker PnL is heavily exposed to adverse selection, queue position, stale quotes and infrastructure uptime. citeturn37view0turn36view2turn39view0turn20search7

---

## 5. Deep dives: most promising directions

### 5.1 Adaptive trend following with volatility targeting

**Mechanism.** BTC and ETH perps show regimes where directional moves persist due to trend-chasing leverage demand, slow information diffusion, reflexivity, liquidations and cross-venue flow. Trend following does not require predicting every bar; it requires capturing the subset of moves that extend far enough to pay for false starts.

**Signal design.** Do not rely on a single moving-average crossover. Use an ensemble:

- sign of 4h / 1d / 3d / 7d returns;
- Donchian-style breakout or rolling high/low position;
- slope of medium EMA or regression trend;
- realized vol regime;
- funding/basis/OI crowding as a throttle;
- time-of-week and macro-event filter;
- optional Deribit vol/skew overlay for leverage scaling.

**Execution.** For 1h–1d strategies, Binance-data → Hyperliquid/CEX execution is realistic. Use maker/passive entries when spread is normal; use reduce-only exits; avoid blind market orders except for risk exits. Position size should be vol-targeted and cut when funding is extreme against the position, OI accelerates too fast or liquidity deteriorates.

```python
trend_score = ensemble(
    sign_return_4h,
    sign_return_1d,
    donchian_breakout,
    ema_slope,
)

if trend_score > entry_threshold:
    if regime_ok and funding_not_extreme and liquidity_ok:
        target_risk = base_risk * regime_multiplier
        size = vol_targeted_size(target_risk, realized_vol)
        enter_long(size, prefer_maker=True, reduce_only_exit=True)
elif trend_score < -entry_threshold:
    if regime_ok and funding_not_extreme and liquidity_ok:
        size = vol_targeted_size(base_risk * regime_multiplier, realized_vol)
        enter_short(size, prefer_maker=True, reduce_only_exit=True)
```

**Failure modes.** Long choppy regimes, funding-crowded reversals, macro shock gaps, weekend illiquidity and parameter instability. The strategy is falsified if edge appears only pre-ETF, only on BTC, only in one direction, or only before fees/funding/slippage.

**My additional implementation view.** Treat trend as the portfolio backbone, not as a lonely bot. It should allocate risk to market direction only when the risk layer allows it. It can also serve as a regime label for other strategies: contrarian funding trades should be smaller or disabled in strong trend regimes; breakout entries should be larger when trend and vol expansion agree.

### 5.2 Intraday compression-to-expansion breakout

**Mechanism.** Crypto liquidity and volatility often shift discontinuously. A narrow range and low realized vol can represent temporary balance; when aggressive flow and realized vol expand, the market can reprice quickly. This works best as a regime-change strategy rather than a generic breakout rule.

**Signal components.**

- rolling range width below historical percentile;
- realized vol below local percentile;
- spread and depth normal before the break;
- breakout beyond compression range;
- aggressive buy/sell flow confirmation;
- session/event context;
- OI or funding context for crowding.

```python
compressed = range_width(last_24_bars) < p20_range and realized_vol(last_24_bars) < p25_vol

if compressed:
    if price > upper_range and aggressive_buy_flow > flow_threshold and spread_ok:
        enter_long(stop='range_reclaim', take_profit='vol_scaled')
    elif price < lower_range and aggressive_sell_flow > flow_threshold and spread_ok:
        enter_short(stop='range_reclaim', take_profit='vol_scaled')
```

**Failure modes.** False breakouts, news whipsaws, thin weekend books, volatility expansion without directional acceptance. Falsify with walk-forward by session and era; add synthetic slippage uplift around events.

**Added synthesis.** Breakout should have two modes:

- **Acceptance breakout:** price breaks range, flow confirms, and new range holds. Trade continuation.
- **Failure breakout:** price breaks but instantly reclaims/loses level with fading intensity. Either avoid or trade reversion only with strict stop.

This split matters more than finding a perfect range formula.

### 5.3 Funding/basis extreme reversion with OI and positioning confirmation

**Mechanism.** Funding is self-correcting, but not a standalone reversal signal. High positive funding can persist during powerful uptrends; negative funding can persist in forced deleveraging. The edge appears when funding extreme, basis, OI acceleration, price extension and flow exhaustion jointly indicate crowded leverage that is vulnerable to unwind.

**Signal design.**

- funding z-score;
- mark-index premium/basis;
- OI z-score and OI acceleration;
- top-trader/all-trader long-short ratios;
- taker imbalance;
- price extension from VWAP/rolling mean;
- settlement window and liquidation pressure.

```python
crowded_long = funding_z > 2.5 and oi_z > 2.0 and price_extension_z > 2.0
crowded_short = funding_z < -2.5 and oi_z > 2.0 and price_extension_z < -2.0

if crowded_long and tape_reversal_detected() and trend_regime != 'strong_uptrend':
    enter_short_small(stop='microstructure_reclaim', max_hold='short')
elif crowded_short and tape_reversal_detected() and trend_regime != 'strong_downtrend':
    enter_long_small(stop='microstructure_reclaim', max_hold='short')
```

**Execution.** This strategy should not fire constantly. It should be an overlay that either reduces trend exposure, triggers smaller contrarian trades, or changes exit aggressiveness.

**Failure modes.** Persistent trends and squeeze continuation. If funding remains high because true demand is strong, fading it is catching a knife. The strategy is falsified if funding-only performs similarly to the full conditioned model; that means the added structure is not adding edge.

### 5.4 Delta-neutral carry: spot-perp and perp-perp basis

**Mechanism.** Carry/funding strategies monetize demand for leveraged exposure and segmentation of arbitrage capital. The clean version is delta-neutral: short rich perp / long spot when positive funding compensates costs, or long cheap perp / short spot/borrow when the reverse economics are viable. Cross-venue variants try to capture funding differentials.

**Why it is not free money.** Funding can flip. Basis can widen before convergence. Margin is path-dependent. Collateral can be fragmented across venues. Withdrawal/bridge delays matter. Stablecoin risk, exchange risk and forced liquidation of one leg can dominate nominal carry. BIS-style crypto carry evidence and funding-market fragmentation studies both point to this: high carry exists because constraints exist. citeturn37view0turn36view4

**Minimum viable model.**

- spot and perp mid prices;
- funding schedule and projected funding;
- fee tiers and maker/taker mix;
- borrow/stablecoin yield/collateral haircut;
- margin rules and liquidation thresholds;
- transfer latency and withdrawal risk;
- basis half-life and spread reversal model.

```python
net_annualized_carry = projected_funding \
    - borrow_cost \
    - expected_open_close_cost \
    - collateral_drag \
    - basis_decay_buffer \
    - venue_risk_buffer

if net_annualized_carry > entry_threshold and collateral_headroom_ok and venue_risk_ok:
    open_delta_neutral_carry()
    monitor_funding_flip_basis_widening_liquidation_distance()
```

**Added synthesis.** Carry systems should be treated as **balance-sheet strategies**, not pure alpha strategies. Their core artifact is not a signal model; it is a pathwise margin/collateral simulator. If you cannot simulate what happens when one leg widens 3–5 sigma before convergence, you do not yet have a carry strategy.

### 5.5 Cross-venue funding spread arbitrage

**Mechanism.** Long low-funding perp and short high-funding perp, collect spread. In theory delta-neutral; in practice exposed to venue, margin, transfer and reversal risk. CEX often leads DEX in price discovery, and funding spreads can revert too fast or force exits before enough funding is earned. citeturn36view4

**Signal must include expected duration.** Spread magnitude alone is insufficient. You need a survival/half-life model: will this spread persist long enough after fees and slippage?

```python
spread = funding_high - funding_low
survival = expected_survival_hours(spread_state, venue_pair, regime)

if spread > spread_entry and survival > min_hold_hours and margin_headroom_ok:
    short_high_funding_perp()
    long_low_funding_perp()
    exit_if(spread_collapses or venue_risk_trigger or execution_skew_too_large)
```

**Failure modes.** Forced exits, desynchronized margin, one leg failing to execute, stablecoin/bridge risk, weekend liquidity and funding formula changes.

**Practical ranking.** This is not a first live bot. It is worth researching after single-venue carry and collateral simulation exist.

### 5.6 BTC/ETH relative value with dynamic beta hedge

**Mechanism.** BTC and ETH are strongly linked but not identical. BTC often acts as dominant information transmitter, while ETH has different narratives, ETF/flows sensitivity, staking/DeFi linkages, beta, funding structure and options surface. A beta-adjusted spread can isolate relative dislocations better than outright directional positions.

**Two regimes.**

- Calm regime: residual mean reversion is plausible.
- Volatile regime: BTC leadership / ETH catch-up or overreaction may dominate.

**Signal design.**

- rolling/Kalman hedge ratio;
- spread z-score on ETH return minus beta-adjusted BTC return;
- half-life estimate;
- funding differential;
- volatility regime;
- BTC impulse/lead-lag features;
- Deribit BTC vs ETH vol gap.

```python
beta = rolling_beta(eth_returns, btc_returns, window='adaptive')
spread = eth_return_window - beta * btc_return_window
z = zscore(spread)

if calm_regime and z > 2 and half_life_stable:
    short_eth_long_beta_btc()
elif calm_regime and z < -2 and half_life_stable:
    long_eth_short_beta_btc()
elif volatile_regime and btc_impulse_up and eth_lagging:
    long_eth_short_beta_btc_for_catchup()
```

**Failure modes.** Regime breaks, unstable hedge ratio, nonstationary spread, event-driven divergence. The strategy is falsified if cointegration/half-life disappears in walk-forward or if funding differential eats most spread PnL.

**Added synthesis.** This is one of the best research lines because it is simple enough to test honestly but rich enough to add layers: trend filter, funding differential, options vol gap and macro/event mode can all be ablated cleanly.

### 5.7 Open-interest shock and crowded positioning unwind

**Mechanism.** OI change is not a directional signal by itself. Its meaning depends on price, funding and flow:

- price up + OI up + taker buying + positive funding: leveraged long build-up;
- price flat + OI up + funding rising: crowded pressure without acceptance;
- price down + OI down: liquidation/unwind or position reduction;
- price up + OI down: short covering rather than fresh long demand.

**State machine.**

| State | Features | Trade implication |
|---|---|---|
| Healthy build-up | OI up, price accepts new range, funding not extreme | Trend continuation possible |
| Exhausted crowding | OI up, funding extreme, price fails to advance | Reversion/unwind possible |
| Forced unwind | OI down sharply with liquidation/taker burst | Continuation or exhaustion depending on reclaim |
| Short/long squeeze | OI down with violent move and spread widening | Do not fade until flow decays |

**Falsification.** Add OI features to a price+flow baseline. If they do not improve PnL, drawdown or trade selection, remove them. OI is often visually compelling but redundant.

### 5.8 Short-horizon OFI / depth / spread classifier

**Mechanism.** Signed trade flow, OFI, top-of-book imbalance, depth slope and spread regime reflect local inventory/information imbalance. This is one of the strongest short-horizon mechanisms, but also one of the easiest to destroy with bad fills.

**Feature space.**

- signed trade imbalance over 0.5s/1s/5s/10s;
- top-N bid/ask imbalance;
- OFI at first N levels;
- spread in bps and spread changes;
- depth slope and book pressure;
- cancel/add intensity by price level;
- trade arrival intensity;
- mark-index gap;
- OI/funding context;
- liquidation prints as state triggers.

```python
features = {
    'ofi_1s': ofi(book, trades, 1.0),
    'ofi_5s': ofi(book, trades, 5.0),
    'qimb_top5': top_n_imbalance(book, n=5),
    'spread_bps': spread_bps(book),
    'depth_slope': depth_slope(book),
    'trade_intensity': trade_arrivals(trades, 1.0),
    'mark_index_gap': mark_index_gap(),
}

p_up = model.predict_proba(features)

if p_up > 0.57 and spread_ok and latency_budget_ok:
    enter_long_with_fill_model()
elif p_up < 0.43 and spread_ok and latency_budget_ok:
    enter_short_with_fill_model()
```

**Validation requirement.** Mid-price forecast accuracy is not enough. Judge by realized-fill PnL, adverse selection after fill, fill ratio and decision-to-fill slippage. If alpha half-life is 200 ms and your effective execution latency is 200+ ms, the signal may be academically real but economically unusable.

### 5.9 VWAP-to-mid and local micro-reversion

**Mechanism.** Aggressive flow can push transaction VWAP away from mid; if intensity decays and spread remains normal, some pressure may revert. If spread widens and OFI continues, the same deviation is toxic continuation, not reversion.

**Best use.** Entry/exit overlay, not core strategy. It can improve where trend/RV/funding signals enter or reduce false entries during temporary pressure.

```python
dev = signed_vwap_deviation(trades_last_n_seconds, mid)

if abs(dev) > dev_cut and spread_state == 'normal':
    if ofi_reversing() and intensity_falling():
        fade_small()
    elif ofi_continuing() or spread_widening():
        do_not_fade()
```

**Falsification.** If it does not improve MAE/MFE, realized entry price or post-cost hit rate over the parent strategy, keep it as dashboard only.

### 5.10 Liquidation-flow aware tactics

**Mechanism.** Forced liquidations create non-linear flows through thin liquidity. Cascades can produce continuation if forced flow keeps feeding itself, or exhaustion if the book reclaims and intensity decays.

**Important limitation.** Binance liquidation stream snapshots are not complete ground truth. They may show largest forced liquidation order within a snapshot window rather than a full map of all liquidations. Therefore use liquidation prints as a **state trigger**, not as a complete liquidation map. citeturn11search2

**State logic.**

```python
if long_liquidation_burst and local_support and sell_intensity_fading and spread_normalizing:
    try_reversion_long_small()
elif short_liquidation_burst and breakout_regime and buy_flow_continues:
    try_continuation_long()
elif liquidation_burst and spread_widening and depth_depleting:
    reduce_or_disable_mean_reversion()
```

**Ranking.** Useful overlay, medium priority as core. It should be tested only after OFI/VWAP/depth baseline exists.

### 5.11 Deribit options-informed volatility regime overlay

**Mechanism.** Options data is more useful for regime and risk than direct intraday direction. DVOL, implied term structure, skew, realized-vs-implied spread and BTC–ETH vol gap can improve sizing, stop width and strategy activation.

**Use cases.**

- reduce leverage when downside skew is extreme;
- allow trend/breakout more than mean reversion when vol regime is unstable;
- adjust stop width when implied vol leads realized vol;
- detect BTC vs ETH relative vol dislocations for RV sizing;
- throttle carry positions when options imply crash-risk repricing.

```python
vrp = implied_vol_30d - realized_vol_20d

if trend_signal and vrp_not_extreme and skew_not_crash_regime:
    allow_full_size()
else:
    cut_leverage_or_disable_reversion()
```

**Falsification.** Overlay must improve drawdown, tail loss or expectancy conditional on entries. If it merely explains past moves but does not improve decisions, remove it.

### 5.12 Macro / ETF / news event overlay

**Mechanism.** News and macro events often change volatility, liquidity and execution quality more reliably than they predict direction. Same-day ETF flows, CPI/FOMC/NFP and crypto-specific regulatory/news shocks can change risk regime.

**Use as risk switch.**

```python
if major_macro_event_in_next_hour():
    reduce_risk_budget()
    disable_new_mean_reversion_trades()
    widen_slippage_assumptions()
elif post_event_vol_expansion() and signal_confirms():
    allow_breakout_entry()
```

**Added synthesis.** News trading should not be the first alpha. But event-aware risk throttling should be built early because it prevents strategies from behaving identically in ordinary hours and in CPI/FOMC hours.

### 5.13 Inventory-aware market making on Hyperliquid

**Mechanism.** Market making is spread capture plus rebates plus inventory skew plus micro-alpha. It is not “always quote both sides”. Passive fills are often toxic: they occur when the market is moving against the resting order. Fresh work on negative drift after limit-order fills reinforces this warning. citeturn20search7

**Minimum viable ingredients.**

- local book state;
- fill and cancel logs;
- short-horizon alpha to skew quotes;
- inventory target and inventory penalty;
- post-only/reduce-only semantics;
- stale quote cancellation;
- rate-limit and WS reconnect handling;
- toxicity filter based on OFI/spread/depth/news.

```python
fair = mid + alpha_adjustment(short_horizon_signal)
reservation = fair - inventory_penalty(current_inventory)
spread = base_spread * volatility_multiplier * toxicity_multiplier

quote_bid = reservation - spread / 2
quote_ask = reservation + spread / 2

if toxicity_high or stale_book:
    cancel_quotes()
else:
    place_post_only_quotes(quote_bid, quote_ask, size=inventory_aware_size)
```

**Why later.** Market making should come after data, replay, OFI and OMS maturity. A maker strategy that makes money only in simulation from spread capture without adverse-selection penalty is almost certainly false.

---

## 6. ML, AI and microstructure

### 6.1 What ML is actually useful for

The realistic ML stack is not “start with Transformer/RL”. It is:

1. Simple baselines: linear/logistic models on engineered features.
2. Tree/boosting models: XGBoost/LightGBM/GBDT for nonlinear interactions.
3. Meta-labeling: base signal proposes; secondary model decides whether to trade and size.
4. Regime gating: HMM/Markov-like or simpler regime classifiers for activation/sizing.
5. Online recalibration and drift detection.

Deep sequence models may be tested later, but only if they beat baselines in walk-forward, post-cost, post-latency, regime-separated evaluation. If a complex model does not outperform GBDT on the same features, complexity is not edge.

### 6.2 Feature groups worth testing

A defensible BTC/ETH perp feature map:

| Group | Examples | Likely role |
|---|---|---|
| Returns/trend | 1m/5m/1h/4h returns, EMA slope, breakout position | Core directional/trend |
| Volatility | realized vol, vol-of-vol, range compression, jump flags | Regime and sizing |
| Funding/basis | funding z-score, mark-index gap, basis slope, funding interval | Carry/crowding/risk |
| OI/positioning | OI delta, OI acceleration, long/short ratios, top trader ratios | Crowding/unwind states |
| Flow | signed volume, taker imbalance, trade intensity | Short-horizon alpha |
| Book | spread, top-N imbalance, OFI, depth slope, cancel/add intensity | Execution/short alpha |
| Liquidations | liquidation bursts, direction, context | State trigger |
| Options | DVOL, skew, term structure, BTC/ETH vol gap | Risk/regime overlay |
| Events | CPI/FOMC/NFP, ETF flows, weekend/US-hours, news sentiment | Risk throttle |
| On-chain | selected stablecoin flows, exchange inflows/outflows | Secondary overlay only |

### 6.3 Labeling and validation for ML

Avoid naive “next bar up/down” labels. They rarely match trade lifecycle. Better:

- volatility-aware horizon;
- triple-barrier labels with stop/target/time-out;
- meta-labeling on top of primary signals;
- purging/embargo for overlapping labels;
- strictly chronological train/validation/test;
- rolling or expanding walk-forward;
- regime-separated OOS reporting.

**Added synthesis:** the ML target should be not “will price go up?” but “is expected edge greater than cost and risk at this moment?” A 51% predictor is worthless if average win is smaller than fee/slippage and adverse selection.

### 6.4 What not to trust

Be skeptical of:

- public-L2 spoofing and iceberg detectors without L3/order IDs;
- liquidation maps that cannot be reconstructed with exact timestamp logic;
- social sentiment intraday as standalone predictor;
- models that only work on mid-price;
- models whose alpha disappears after maker/taker distinction;
- models whose performance concentrates in a tiny number of outlier days;
- results that improve with more complexity but fail across regimes.

---

## 7. Data, simulation and validation standards

### 7.1 Data to collect first

The first production-grade artifact is not a strategy; it is the data lake.

**Collect immediately:**

- Binance futures raw trades;
- Binance diff-depth and book ticker;
- mark/index/funding history and live updates;
- liquidation snapshots;
- OI stats, taker buy/sell volume, long/short ratios;
- cross-venue synchronized mids for BTC/ETH;
- Hyperliquid public book/funding/fills metadata if executing there;
- Deribit DVOL/options snapshots/skew/term structure;
- venue metadata: fees, funding schedule, liquidation rules, margin tiers, rate limits;
- live order logs: decision timestamp, submit timestamp, ack timestamp, fill timestamp, cancel timestamp, errors, partial fills, stale-book flags.

**Storage pattern:** raw immutable event logs + normalized parquet tables + replayable event bus. Never overwrite raw events. Derived features can be regenerated; raw tick/depth history cannot be reconstructed later.

### 7.2 Event-driven simulator

A realistic simulator for BTC/ETH perps must include:

- maker/taker fees by venue/tier;
- bid/ask spread and slippage;
- funding accrual at correct venue interval;
- mark-price liquidation logic;
- margin tiers and liquidation distance;
- partial fills;
- queue approximation for maker orders;
- order latency and cancel latency;
- stale book resets;
- rejected orders, reconnects and rate limits;
- separate collateral buckets for cross-venue carry;
- borrow/stablecoin and transfer assumptions for spot-perp.

For LOB/maker strategies, candle backtests are not enough. Use L2 replay at minimum and L3 where available. Tools mentioned in the source reports — Tardis, NautilusTrader, hftbacktest and Hummingbot — have different roles: data, event-driven parity, latency/queue simulation and execution scaffolding. citeturn8search3turn8search7turn19search3turn19search15turn11search7turn11search20

### 7.3 Metrics that matter

Do not optimize only Sharpe. For perp systems track:

- CAGR, Sharpe, Sortino, Calmar;
- max drawdown and time under water;
- turnover and average holding period;
- exposure time and gross/net leverage;
- average win/loss, profit factor, tail percentiles;
- fee-to-gross-PnL ratio;
- funding PnL share;
- slippage and decision-to-fill drift;
- adverse selection after fill;
- fill ratio and cancel ratio;
- liquidation distance and margin stress;
- performance by regime bucket;
- capacity proxy by orderbook participation rate;
- live vs paper divergence.

A strategy where 70% of gross PnL is eaten by fees/funding and worst days coincide with margin stress is not robust even if headline Sharpe looks acceptable.

### 7.4 Backtest falsification checklist

Before paper trading, each strategy should survive:

- strict chronological split;
- walk-forward retraining/recalibration;
- post-cost model with conservative fee/slippage;
- funding and borrow/collateral accounting;
- event-window stress;
- post-ETF split;
- weekend split;
- high-vol and low-vol splits;
- bull/bear/chop splits;
- parameter stability test;
- ablation of each feature group;
- latency/fill sensitivity grid;
- outlier-day contribution analysis.

If the strategy only works in one narrow parameter island, one asset, one era or one direction, it is not production-ready.

---

## 8. Roadmap and backlog

### 8.1 Phased project roadmap

| Phase | Build | Concrete output |
|---|---|---|
| 1. Data collection | Recorder for Binance trades/depth/book ticker/liquidations/funding/OI; Deribit options intake; venue metadata | Reliable lakehouse with raw + normalized tables |
| 2. Baseline research | 4h/1d trend, intraday breakout, BTC/ETH RV, funding/OI overlays | Replicable bar/funding/OI backtests |
| 3. Event-driven engine | Same logic for backtest and live; order state machine; reduce-only/post-only semantics | Production-like simulator |
| 4. Execution simulator | Taker best bid/ask model; maker queue/latency model; venue-specific costs/funding | Realistic post-cost PnL |
| 5. Paper/shadow trading | Real-time signals without capital, then paper orders on target venue | Drift, missed-fill and slippage diagnostics |
| 6. Small live deployment | Tiny size, hard daily limits, kill switches, reconciliation | Operational validation |
| 7. Scale-out | Add Deribit overlay, OFI layer, carry/RV portfolio, later market making | Multi-strategy portfolio |

### 8.2 Backlog of high-value experiments

| Hypothesis | Data | Complexity | Research value | Priority | Pass/fail criterion |
|---|---|---:|---:|---|---|
| Vol-targeted 4h trend survives fees on BTC/ETH | OHLCV + funding | Low | High | Immediate | Positive OOS expectancy across both assets and regimes |
| Intraday breakout only works in expansion regimes | 1m/5m bars + flow/session | Low | High | Immediate | Conditional alpha > unconditional alpha |
| Funding extreme needs OI + extension | Funding + OI + price + taker flow | Low | High | Immediate | Full conditioned model beats funding-only baseline |
| BTC/ETH beta spread is stable in calm regimes | Synchronized BTC/ETH returns | Low | High | Immediate | Stable half-life and OOS spread exits |
| Deribit vol overlay reduces trend drawdown | DVOL/skew + base trend system | Medium | High | High | Lower tail loss without destroying CAGR |
| Binance OFI survives taker simulation | Trades + L2 depth | Medium | High | High | Realized-fill edge remains after latency and bid/ask |
| VWAP-to-mid improves entry quality | Trades + mid + spread | Medium | Medium | High | Better MAE/MFE and net hit rate |
| OI shock classifier beats raw OI delta | OI + price + funding + ratios | Low | Medium | High | Improves selection and max drawdown |
| Liquidation bursts split continuation/exhaustion | Liquidation + L2 + trades | Medium | Medium | Medium-high | Edge survives incomplete liquidation data |
| Cross-venue carry needs survival model | Multi-venue funding + fees | Medium | Medium | Medium | Spread magnitude alone fails; survival model improves OOS |
| Macro-event throttle reduces event drawdowns | Calendar + base strategies | Low | Medium | Medium | Tail event loss materially smaller |
| Simple GBDT beats deep net on same LOB features | L2 + trades | Medium | Medium | Medium | Complex model gives no stable OOS lift |
| Hyperliquid maker needs alpha skew | HL book + fills + local alpha | High | Medium | Later | PnL remains after toxicity/queue/stale penalties |

### 8.3 Suggested first implementation sequence

1. Build data recorder and normalized schema.
2. Implement fee/funding-aware bar backtester.
3. Test vol-targeted trend and intraday breakout.
4. Test BTC/ETH RV with dynamic beta.
5. Add funding/OI crowding overlay.
6. Add event/weekend/ETF-era regime reporting.
7. Build event-driven execution simulator.
8. Test OFI/VWAP only after replay/fill model exists.
9. Paper trade trend/RV/funding stack.
10. Consider carry and later market making only after operational stability.

**Added synthesis:** resist the temptation to build the most sophisticated strategy first. The right order is determined by which assumptions are easiest to make honest. Trend/RV/funding can be evaluated with relatively clean data. OFI requires replay. Market making requires replay plus OMS maturity. Cross-venue carry requires collateral simulation. Build in that order.

---

## 9. Red-team critique

### 9.1 Why these projects usually fail

They fail less often because “markets are perfectly efficient” and more often because the developer underestimates one of four things:

1. **Execution cost.** Mid-price PnL is not traded PnL. Passive fills are often toxic. Taker fees and slippage matter.
2. **Regime dependence.** A strategy can be real in trend regimes and bad in chop, or work pre-ETF and fail post-ETF.
3. **Collateral and liquidation engineering.** Carry and delta-neutral trades are path-dependent; margin segmentation can force exits before convergence.
4. **Operational risk.** API changes, funding interval changes, stale books, reconnects, partial fills and venue outages are strategy risks, not engineering noise.

### 9.2 Where backtests lie most

| Area | Common lie | Correct treatment |
|---|---|---|
| Market making | Spread capture assumed without adverse selection | Model queue, toxicity, stale quotes and fills |
| Micro-reversion | Entry/exit at mid | Use bid/ask, latency and fill probability |
| OFI | Predicts mid but not tradable edge | Judge realized-fill PnL |
| Carry | Delta-neutral treated as risk-free | Simulate pathwise margin and forced exits |
| Funding arb | Spread magnitude treated as enough | Add survival/reversal model |
| Liquidations | Heatmap treated as ground truth | Use stream as trigger, not full map |
| ML | Accuracy optimized without cost | Optimize expected net edge after costs |
| Cross-venue | Latency ignored | Use measured decision-to-fill timing |

### 9.3 What is likely crowded

- obvious funding capture on major BTC/ETH venues;
- simple high-funding contrarian shorts;
- liquidation wick fades from popular heatmaps;
- public CEX latency dislocations;
- maker rebate farming without alpha;
- generic sentiment/news signals;
- OHLCV deep learning demos.

Crowding does not mean impossible. It means conditioning and execution matter more than the raw signal.

### 9.4 Kill switches and negative discipline

A serious system needs rules for when not to trade:

- max daily loss and max intraday drawdown;
- volatility spike throttle;
- spread/depth deterioration halt;
- macro-event freeze for mean reversion;
- funding flip exit;
- OI/funding squeeze warning;
- stale data / sequence gap halt;
- venue status/rate-limit halt;
- live-vs-paper divergence halt;
- liquidation distance minimum;
- strategy-specific parameter instability deactivation.

**Added synthesis:** the strongest marker of a real quant project is not how many models it has, but how many bad trades it refuses to take.

---

## 10. Final recommendation

If the goal is a rational automated BTC/ETH perpetual futures project for a serious independent developer, build in this order:

**First build:**

- raw data recorder;
- normalized market-data store;
- fee/funding-aware bar backtester;
- event-driven simulator foundation;
- live order/fill logging;
- risk and kill-switch layer.

**First strategies to test:**

1. adaptive trend + volatility targeting;
2. intraday compression breakout with regime gate;
3. BTC/ETH dynamic beta relative value;
4. funding/OI crowding reversion overlay;
5. open-interest shock classifier;
6. Deribit options overlay as risk/leverage switch.

**Second wave:**

- Binance OFI to same-venue or Hyperliquid execution tests;
- VWAP-to-mid entry filters;
- liquidation-flow state machine;
- cross-venue funding survival model;
- macro/ETF event throttle.

**Later only:**

- Hyperliquid inventory-aware market making;
- multi-venue carry with transfer/collateral automation;
- deep sequence models;
- RL-style policy optimization.

**Avoid at the start:**

- pure funding arbitrage as yield;
- pure liquidation-map trading;
- pure social/news/whale alerts;
- generic LSTM/Transformer/RL on OHLCV;
- maker-only rebate farming;
- public-API latency arbitrage;
- any strategy backtested on mid-price fills.

The integrated view is: **do not try to be a tiny HFT fund. Build a medium-frequency, execution-honest, risk-engineered research platform.** Use simple strategies with clear mechanisms as the base. Add microstructure and ML only where they improve a baseline under realistic costs. Treat carry as balance-sheet engineering. Treat market making as an inventory/adverse-selection business. Treat every feature as guilty until it proves incremental value through ablation and live-like simulation.

That is the path most likely to turn the two original reports into a practical research program rather than another curve-fitted strategy notebook.

---

## Appendix A. Compact strategy decision matrix

| Question | If yes | If no |
|---|---|---|
| Can I explain who pays my PnL? | Continue research | Probably curve fitting |
| Does it survive fees, funding and slippage? | Continue | Reject or redesign |
| Does it survive bid/ask rather than mid? | Continue | Not tradable yet |
| Does it survive walk-forward and post-ETF split? | Continue | Regime-specific only |
| Does each feature improve baseline in ablation? | Keep feature | Remove feature |
| Is fill model realistic enough for horizon? | Paper trade | Build replay first |
| Is liquidation/collateral path simulated? | Carry may be tested | Carry result unreliable |
| Does live shadow match backtest assumptions? | Small live possible | Fix infra first |

## Appendix B. Minimal production module layout

```text
perp_research_stack/
  data/
    raw_recorders/
      binance_trades_depth.py
      binance_funding_oi.py
      deribit_options.py
      hyperliquid_book.py
    normalization/
      schema.py
      timestamp_alignment.py
      parquet_writer.py
  research/
    features/
      trend.py
      funding_basis.py
      orderflow.py
      btc_eth_rv.py
      options_overlay.py
    labels/
      triple_barrier.py
      meta_labels.py
    backtests/
      bar_backtester.py
      event_replay.py
  execution/
    oms.py
    venue_adapters/
      binance.py
      hyperliquid.py
    risk_checks.py
    order_state.py
  risk/
    vol_targeting.py
    liquidation_distance.py
    kill_switches.py
    event_calendar.py
  monitoring/
    live_vs_paper.py
    slippage_dashboard.py
    reconciliation.py
```

## Appendix C. One-page build order

1. Record raw data continuously.
2. Normalize timestamps and instruments.
3. Backtest trend/RV/funding baselines post-cost.
4. Add regime reports and ablations.
5. Build event-driven replay.
6. Add execution and order-state realism.
7. Shadow trade without capital.
8. Paper trade with same OMS.
9. Small live with hard limits.
10. Scale only after slippage, fills and ops match assumptions.
