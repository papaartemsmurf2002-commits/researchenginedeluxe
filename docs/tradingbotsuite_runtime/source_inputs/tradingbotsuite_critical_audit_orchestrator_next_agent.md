# TradingBotSuite Critical Repo Audit and Next-Agent Instructions

**Repo under audit:** `papaartemsmurf2002-commits/tradingbotsuite`
**Base:** `main @ a3cf3a5018acae2e167f1dbf373690c10acb00fe`
**Head:** `codex/hmm-knn-research-package`, ahead by 3, behind by 0
**Audit source of truth:** uploaded `tradingbotsuite_pro_audit_packet.md`; no branch/files outside that packet were assumed.
**Target system:** fully automated BTC/ETH perpetual-futures system, Binance-driven market data, Hyperliquid execution.
**Audit stance:** critical, evidence-seeking, no profitability assumptions.

---

## 0. Executive verdict

### Merge decision

**Do not merge `codex/hmm-knn-research-package` into production/live runtime as-is.**

The branch may be useful as a **research-only prototype**, but it is **not live-ready** and should not be allowed to influence autonomous BTC/ETH perp execution. The branch’s own documented BTC diagnostic is an explicit non-pass:

- `promotion_ready=false`
- `research_only=true`
- `observe_only=true`
- dataset row count only `446`
- pure KNN accepted only `5` trades
- KNN costed expectancy approximately `-1.0008811453163364`
- meta model accepted `0` trades
- monitoring reports high no-trade rate and low neighbor quality

This is not a minor tuning problem. It means the research module has **no demonstrated tradable edge** in the packet, and any attempt to wire it into live order flow would be premature.

### Production direction that can survive scrutiny

The architecture should be reorganized around this hierarchy:

```text
1. Safety / execution correctness
2. Data integrity and replayability
3. Leakage-free research protocol
4. Shadow-mode model diagnostics
5. Live promotion only after hard acceptance criteria
```

A viable production architecture is:

```text
Binance USD-M market data backbone
+ Hyperliquid execution/order-state backbone
+ append-only event journal and replay engine
+ strict live risk governor
+ venue-basis and stale-feed guards
+ leakage-free feature/label pipeline
+ HMM regime diagnostics and KNN/meta models in observe-only mode
+ promotion pipeline with walk-forward and live-shadow gates
```

The HMM/KNN work should remain a diagnostic/research layer until it proves positive out-of-sample expectancy after fees, slippage, funding, venue mismatch, and execution latency.

---

## 1. Non-negotiable production constraints

The next agent must treat the following as hard requirements, not preferences.

### 1.1 Asset and holding-window scope

```text
Assets: BTC and ETH perpetuals only
Signal data: Binance USD-M perp market data
Execution venue: Hyperliquid
Holding window: minimum 1 hour, maximum 1 week
Mode: fully automated only after live-readiness gates pass
```

No signal should be accepted if it requires sub-minute scalping assumptions or human discretionary intervention. No model should be promoted from BTC-only evidence to ETH without separate ETH validation.

### 1.2 Exchange split creates a real basis/execution problem

The system intends to **derive signals from Binance** and **execute on Hyperliquid**. That is not equivalent to trading the same venue. Every order decision must check:

```text
Binance mark/last/reference price
Hyperliquid mid/bid/ask/book depth
Binance-Hyperliquid basis
spread and expected slippage on Hyperliquid
funding state on Hyperliquid
position state on Hyperliquid
```

A Binance-only signal is insufficient for execution. Hyperliquid book and account state are the source of truth for fillability, risk, liquidation, open orders, reduce-only exits, funding, and position reconciliation.

---

## 2. P0 blockers: must fix before any production merge

These are immediate stop-ship issues.

### P0-1. Live risk defaults are unsafe because zero disables hard limits

From the audit packet:

```python
max_daily_loss_quote: Decimal = Decimal("0")
max_open_risk_notional: Decimal = Decimal("0")
```

The packet curator specifically notes these are treated as disabled. That is unacceptable for a fully automated perp system.

#### Required change

In `RuntimeMode.LIVE`, reject config startup unless all hard risk caps are explicitly positive:

```text
TBS_MAX_DAILY_LOSS_QUOTE > 0
TBS_MAX_OPEN_RISK_NOTIONAL > 0
max_position_notional_per_symbol > 0
max_order_notional > 0
max_leverage configured and bounded
max_intraday_drawdown configured
max_consecutive_losses configured
```

`0` must mean **invalid in LIVE**, not unlimited.

#### Required tests

Add tests that prove:

```text
LIVE + max_daily_loss_quote=0 => startup fails
LIVE + max_open_risk_notional=0 => startup fails
PAPER + zero risk caps => allowed only if explicitly documented as paper-only
manual/smoke-live/serve all call the same live-readiness validator
```

---

### P0-2. `run_manual.py` has a config-loss bug

From the packet:

```python
config = AppConfig(
    runtime_mode=RuntimeMode(sys.argv[1]),
    db_path=config.db_path,
    webhook=config.webhook,
    strategy=config.strategy,
    binance=config.binance,
    hyperliquid=config.hyperliquid,
)
```

This reconstructs `AppConfig` and drops fields such as `research` and `operator_ui`. The main CLI reportedly preserves `research=config.research`, but the root launcher does not.

#### Why this matters

Root launchers are exactly the kind of scripts operators accidentally use during manual/live work. Dropping config fields can silently disable safety, UI, research-gating, or future fields.

#### Required change

Do not reconstruct `AppConfig` manually. Add one of:

```python
config = config.with_runtime_mode(RuntimeMode(sys.argv[1]))
```

or, if `AppConfig` becomes a dataclass:

```python
config = dataclasses.replace(config, runtime_mode=RuntimeMode(sys.argv[1]))
```

If `AppConfig` is not a dataclass, implement a method that copies **all** fields.

#### Required tests

```text
run_manual.py preserves research config
run_manual.py preserves operator_ui config
run_manual.py preserves every current AppConfig field when overriding runtime_mode
future AppConfig field additions fail tests if not preserved
```

---

### P0-3. Research jobs are allowed in LIVE when flat

From the packet:

```python
if self.config.runtime_mode == RuntimeMode.LIVE:
    for position in await self.store.list_position_states():
        if position.status == TradeStatus.OPEN:
            raise ValueError("research jobs are blocked while a live position is open")
```

This means research jobs are blocked in LIVE only when a live position is open. They are still allowed in LIVE when flat.

#### Why this is unsafe

A research job can:

```text
consume CPU/RAM/disk/DB resources
mutate artifacts
write files used by runtime
delay order reconciliation
delay cancels/exits
race with signal generation
produce misleading operator state
```

Even when flat, a fully automated bot can transition from flat to open in milliseconds. LIVE runtime should not run build/train/calibrate/replay/research tasks.

#### Required change

Hard-ban research jobs in LIVE:

```text
build-dataset
train-model
calibrate-model
replay-eval
research-entry-gates
optimize-entry-gates
preflight-entry-gates
research-hmm-knn
replay-hmm-knn
monitor-hmm-knn, unless strictly read-only and isolated
```

The only acceptable exception is an explicit isolated worker with:

```text
separate process
separate DB connection pool or read-only replica
separate artifact directory
no ability to update live model pointers
no ability to block order/risk loops
explicit env flag, disabled by default
```

#### Required tests

```text
LIVE + queue build-dataset => reject
LIVE + queue train-model => reject
LIVE + queue replay-eval => reject
LIVE + queue research-hmm-knn => reject
LIVE + flat positions does not bypass research ban
PAPER/SIM modes can queue research jobs
```

---

### P0-4. HMM/KNN artifacts must not be live-promotable

The branch’s own docs say HMM/KNN artifacts are `research_only` and `observe_only`. Monitoring also forces `promotion_ready=false`.

#### Required change

Add explicit runtime enforcement:

```text
If artifact.manifest.research_only == true, live signal engine refuses to load it.
If artifact.manifest.observe_only == true, live signal engine refuses to trade it.
If artifact lacks a promotion manifest, live signal engine refuses to load it.
If artifact was trained on BTC only, ETH live path refuses to load it.
```

#### Required tests

```text
LIVE load research_only HMM/KNN artifact => fail
LIVE load observe_only HMM/KNN artifact => fail
LIVE load BTC-only artifact for ETH => fail
PAPER load observe_only artifact => allowed only as no-trade diagnostics
```

---

### P0-5. Hyperliquid execution must be idempotent and dead-man protected

Hyperliquid supports client order IDs (`cloid`), cancel-by-cloid, and `scheduleCancel` dead-man behavior. The official docs describe `cloid` as an optional 128-bit hex string and schedule-cancel as a future cancel-all operation; the schedule-cancel time must be at least 5 seconds ahead and the trigger count is limited per day.

#### Required change

Every order must have deterministic idempotency:

```text
cloid = deterministic 128-bit hex from strategy_id + symbol + side + timestamp bucket + sequence
all order submissions persisted before send
all exchange responses persisted after receive
all retries use same cloid unless explicitly replacing an order
all cancels use cancelByCloid when possible
```

Every LIVE session must maintain dead-man protection:

```text
on startup: scheduleCancel(now + N seconds)
while healthy: refresh scheduleCancel before expiry
on shutdown: cancel all open orders, remove scheduleCancel only after flat/reconciled
if websocket/user-state stale: do not remove scheduleCancel
```

#### Required tests

```text
network timeout after order submit => retry does not duplicate exposure
duplicate signal => same cloid or explicit dedupe rejects second order
cancel by cloid reconciles order state
bot crash simulation leaves scheduled cancel active
restart reconciles open orders before new orders
partial fill + cancel leaves correct residual state
reduce-only exit cannot increase exposure
```

---

### P0-6. Binance-driven signal does not prove Hyperliquid fillability

The branch has `HyperliquidConfig.max_basis_bps = 75`, but the audit packet does not prove that basis and Hyperliquid book depth are checked at order time.

#### Required change

Before any order, compute:

```text
binance_mark_price
binance_last_or_aggtrade_price
hyperliquid_mid
hyperliquid_best_bid
hyperliquid_best_ask
hyperliquid_spread_bps
estimated_market_impact_bps
binance_hyperliquid_basis_bps
expected_fees_slippage_funding
```

Reject if:

```text
abs(basis_bps) > max_basis_bps
Hyperliquid spread > max_spread_bps
estimated impact > max_impact_bps
book snapshot stale
Binance feed stale
Hyperliquid user/order feed stale
```

#### Required tests

```text
basis too wide => no order
Hyperliquid book stale => no order
Binance feed stale => no order
spread too wide => no order
available depth insufficient => order size reduced or rejected
```

---

### P0-7. Webhook secret default is unsafe

From config:

```python
WebhookConfig.secret: str = "change-me"
```

If the service can be network-exposed, this is a live safety risk.

#### Required change

In LIVE and any mode accepting external webhooks:

```text
secret != "change-me"
secret length >= 32 bytes or equivalent entropy
timestamp tolerance enforced
replay nonce/idempotency enforced
signature verification test-covered
```

#### Required tests

```text
LIVE + default webhook secret => startup fails
invalid signature => reject
old timestamp => reject
replayed alert => reject
```

---

## 3. P1 architecture risks

### P1-1. Current branch is BTC-only but target scope is BTC/ETH

Config says:

```json
"asset_scope": ["BTCUSDT"],
"symbol": "BTCUSDT"
```

Dataset builder explicitly raises if symbol is not BTCUSDT:

```python
if self.plan.symbol.upper() != BTC_PHASE_1_SYMBOL:
    raise ValueError("Phase 1 research dataset builds are BTCUSDT-only")
```

#### Required action

Do not describe this branch as BTC/ETH capable. Next implementation must add ETH as a first-class path:

```text
BTCUSDT Binance data pipeline
ETHUSDT Binance data pipeline
BTC Hyperliquid execution metadata
ETH Hyperliquid execution metadata
separate BTC and ETH model artifacts
cross-asset features: BTC lead/lag for ETH, ETH/BTC relative strength, funding basis divergence
separate metrics and promotion gates per asset
```

---

### P1-2. Binance feed must be event-journaled, not merely queried

Binance USD-M streams relevant for this system include aggTrade, mark price/funding, and kline streams. The official Binance futures connector documents aggregate-trade streams at 100ms, mark-price/funding streams at 1s or 3s, and kline streams for USD-M futures.

#### Required action

Create an append-only market-data journal:

```text
source = binance_um_futures
stream = aggTrade | markPrice | kline | depth | forceOrder | funding | open_interest_snapshot
symbol = BTCUSDT | ETHUSDT
event_time_ms
receive_time_ms
sequence/id fields
raw_payload_hash
normalized fields
parser_version
```

Do not let feature generation read directly from unversioned websocket callbacks. Features must be reproducible from the journal.

---

### P1-3. Hyperliquid account/order/fill state must be separately journaled

Hyperliquid websocket subscriptions include user fills, user funding, user events, BBO, and clearinghouse state. Rate limits include REST weight caps, websocket connection/subscription caps, and address-based action limits.

#### Required action

Create an append-only execution journal:

```text
order_intent
order_submitted
order_acknowledged
order_rejected
order_partially_filled
order_filled
order_cancel_requested
order_cancel_acknowledged
position_snapshot
funding_payment
liquidation_or_margin_event
schedule_cancel_set
schedule_cancel_triggered
```

Execution state must be reconstructed from the journal plus exchange reconciliation, not inferred from local assumptions.

---

### P1-4. Root launchers increase operational ambiguity

Added root launchers:

```text
run_server.py
run_manual.py
run_live_smoke.py
```

Root scripts often bypass normal CLI safety. `run_manual.py` already demonstrates this by losing config fields.

#### Required action

Either delete root launchers or make them thin wrappers around the canonical CLI, with no separate config reconstruction.

```text
run_server.py -> tradingbot serve
run_manual.py -> tradingbot manual
run_live_smoke.py -> tradingbot smoke-live
```

Each wrapper must call the same preflight/live-readiness checks as the CLI.

---

## 4. Data and research validity risks

### R1. The branch has no demonstrated edge

The branch’s own BTC diagnostic is negative and sparse. That must dominate any architectural optimism.

#### Required action

The next agent must mark the current HMM/KNN branch as:

```text
status: research prototype
live_signal_status: prohibited
promotion_status: failed
primary_failure_reasons:
  - negative KNN expectancy
  - insufficient KNN trade count
  - meta model accepted zero trades
  - BTC-only
  - insufficient sample size
  - missing live-vs-replay validation
```

---

### R2. Dataset row count is too small for multi-regime KNN

`row_count=446` across 4 regimes, multiple horizons, K values `[16,24,32,48,64]`, and same-regime-only filtering is not enough.

#### Why this matters

KNN needs dense local neighborhoods. Same-regime-only KNN with 4 HMM states fragments the sample. A 446-row dataset can easily leave fewer than the required neighbors for many regimes/horizons/sides.

#### Required action

Set minimum research thresholds before model training is even considered meaningful:

```text
minimum rows per asset: >= 10,000 event rows or justified lower via power analysis
minimum rows per HMM regime: >= 1,000
minimum labeled trades per side per asset: >= 300
minimum accepted trades per validation split: >= 50
minimum validation splits: >= 6 walk-forward splits
minimum history: includes multiple volatility regimes and at least one major stress period
```

These numbers are conservative starting gates, not proof of profitability.

---

### R3. `entry_price` fallback can create optimistic labels

Dataset excerpt:

```python
normalized_entry_price = _decimal_or_none(raw_payload.get("normalized_entry_price"))
entry_price = normalized_entry_price if normalized_entry_price is not None else latest_bar.close
entry_price_source = str(raw_payload.get("entry_price_source") or "signal_bar_close")
```

Using `signal_bar_close` as the entry price may not be executable. For live automation, the real entry is after alert generation, routing, risk checks, order submission, matching, and Hyperliquid liquidity conditions.

#### Required action

Replace label entry assumptions with a live-executable fill model:

```text
signal close time
+ configured signal delay
+ feature computation delay
+ order decision delay
+ Hyperliquid order placement delay
+ slippage model from Hyperliquid book depth
= simulated fill price
```

Allow `signal_bar_close` only as a diagnostic baseline, never as a promotion label.

#### Required tests

```text
entry_price_source=signal_bar_close marks dataset as non-promotable
promotion dataset requires executable_entry_price_source
latency stress increases slippage and can flip labels
```

---

### R4. Missing feature zero-fill is dangerous

Dataset excerpt:

```python
for column in RESEARCH_FEATURE_COLUMNS:
    if column not in frame.columns:
        frame[column] = 0.0
```

This conflates “missing” with a real zero. In perp microstructure, zero funding, zero imbalance, zero OI change, and missing values mean different things.

#### Required action

Replace silent zero-fill with:

```text
feature value = NaN or train-only imputed value
feature_available_<name> = 0/1
missing rate recorded per split and per regime
promotion fails if missingness exceeds threshold
```

Imputation must be fit on train only and applied to validation/test.

#### Required tests

```text
missing column does not silently become all-zero without availability flag
train-only imputer does not inspect validation/test values
feature outage triggers monitoring alert
high missingness makes artifact non-promotable
```

---

### R5. WT3D may be computed on sparse signal rows instead of continuous bars

The packet says research rows are built from TradingView/export signal rows. `build_wt3d_features(frame, settings)` uses:

```python
price = frame[price_column].astype(float).replace([inf,-inf], nan).ffill().fillna(0.0)
```

with config:

```json
"price_column": "entry_price"
```

If WT3D is computed on the dataset’s signal-event table rather than the full continuous bar series, the oscillator is invalid. WaveTrend/WT3D features need continuous time-series context, not a sequence of accepted/research signal events.

#### Required action

Verify immediately. If current WT3D is computed over event rows, fix it this way:

```text
1. Compute WT3D on complete Binance bar/mark-price series per symbol and timeframe.
2. Use completed bars only.
3. Store WT3D features by bar close time.
4. Join signal/event rows to the latest completed WT3D feature timestamp <= signal_time.
5. Record feature_time_ms and feature_lag_ms.
6. Reject rows where WT3D feature_time_ms > signal_time_ms.
```

#### Required tests

```text
WT3D uses continuous bars, not event rows
WT3D feature timestamp is <= signal timestamp
WT3D no future pivot/divergence leakage
missing prices are forward-filled only from prior completed bars
```

---

### R6. Purge/embargo setting may be too small for 7-day labels

Config says:

```json
"horizons": ["6h", "24h", "72h", "7d"],
"purge_embargo_bars": 8
```

If bars are hourly or event-based, an 8-bar embargo is likely insufficient for a 7-day vertical barrier.

#### Required action

Embargo must be label-end-time aware:

```text
For each test row, remove train rows whose label window overlaps test feature/label window.
Embargo duration >= max holding horizon, or dynamic by actual label exit time.
```

Do not use a fixed `8` bars unless the code proves it is always greater than the maximum label overlap.

#### Required tests

```text
7d label windows cannot overlap train/test boundary
purge removes rows by actual label_start_time and label_end_time
embargo works on irregular event-sampled data
```

---

### R7. Meta-model leakage risk must be explicitly controlled

The packet says `_fit_meta_model` fits XGBoost or RandomForest on `feature_columns`. It is unclear whether KNN diagnostics are included, and if they are, whether they are out-of-fold.

#### Required action

Define two legal modes:

```text
Mode A: raw-feature classifier
  - Do not call it a KNN meta-labeler.

Mode B: KNN meta-labeler
  - KNN predictions used as features must be generated out-of-fold on training data.
  - Validation/test KNN predictions must be generated only from prior training rows.
```

Never train a meta-model on in-sample KNN diagnostics computed using the same rows as neighbors.

#### Required tests

```text
meta training KNN features are out-of-fold
no validation/test row appears in its own neighbor pool
neighbor_min_source_index and max_source_index are < query source index for walk-forward mode
```

---

### R8. Feature units and cost units need audit

KNN expected value code excerpt:

```python
gross_expected = weighted label_pnl_multiple
expected_net = gross_expected - ((fee_bps + slippage_bps)/10000) - funding_cost
```

If `label_pnl_multiple` is a multiple of ATR/risk and fees are return fractions, the subtraction is dimensionally wrong.

#### Required action

Add a unit manifest for every label/output:

```text
label_pnl_multiple unit: return_fraction | atr_multiple | risk_multiple
fee_bps unit: bps of notional
slippage_bps unit: bps of notional
funding_cost unit: return_fraction over holding period
expected_net_return_after_costs unit: return_fraction
```

Promotion fails if units are mixed.

---

### R9. TradingView/export signals are not equivalent to Binance live data

Dataset sources include:

```python
RESEARCH_SIGNAL_SOURCES = {
  "tradingview",
  "tradingview_chart_export",
  "tradingview_strategy_export",
  "tradingview_alert_log"
}
```

This is acceptable for exploratory research but weak for live Binance-driven automation unless the alert-generation latency, candle-close semantics, exchange symbol mapping, and historical revisions are reproduced.

#### Required action

For promotion datasets, source rows must come from the same event-driven engine used live:

```text
Binance raw stream journal
feature builder
signal builder
risk filter
paper execution fill model
label builder
```

TradingView export rows can remain as legacy research data but must mark artifacts as non-promotable.

---

## 5. Execution and runtime safety risks

### E1. Need a canonical live-readiness gate

Create one function and call it everywhere:

```python
def assert_live_ready(config: AppConfig, store: Store, *, context: str) -> None:
    ...
```

It must be called by:

```text
serve
manual
smoke-live
operator_console
signal execution engine
any root launcher
```

It must check:

```text
runtime_mode == LIVE only when explicitly armed
Hyperliquid enable_live true
account address present
private key present via secure secret source
webhook secret non-default
risk caps positive
research jobs disabled
artifact promotion manifest valid
Binance feed healthy
Hyperliquid feed healthy
dead-man schedule active
exchange reconciliation complete
no stale open orders
```

---

### E2. Risk governor must be independent of strategy/model code

Do not let the model decide whether risk is acceptable. The risk engine must sit between signal and execution.

Required risk checks:

```text
max daily realized loss
max daily unrealized drawdown
max open notional
max per-symbol notional
max leverage
max order notional
max order count per minute
max cancel count per minute
max consecutive rejected orders
max funding cost per trade
max basis bps
max spread bps
max expected slippage bps
stale data no-trade
exchange state unresolved no-trade
safe mode no-trade
```

---

### E3. Position reconciliation must use Hyperliquid as source of truth

Local store positions are not enough.

Before new exposure:

```text
fetch/reconcile Hyperliquid clearinghouse/position state
fetch/reconcile open orders
consume user fills and funding events
verify local journal equals exchange state within tolerance
```

If reconciliation fails, the bot must enter safe mode and only allow reduce-only/cancel actions.

---

### E4. Exits must be exchange-safe before model-smart

The research branch discusses triple-barrier labels, but live exits need independent hard protection.

Minimum live exit stack:

```text
hard stop / reduce-only trigger or active risk-managed exit
time stop
daily loss stop
position max age <= 7d
funding-cost stop
basis dislocation stop
regime/model exit only after hard safety exits exist
```

All exits must be reduce-only. Failed exit placement must trigger cancel/retry/escalation logic.

---

## 6. Recommended production architecture

### 6.1 Services

```text
market_data_binance_service
  - subscribes to BTCUSDT/ETHUSDT aggTrade, markPrice, kline, depth, forceOrder if enabled
  - writes append-only raw events
  - emits normalized feature-ready events

execution_hyperliquid_service
  - manages orders, cancels, cloids, scheduleCancel, fills, funding, positions
  - writes append-only execution events
  - owns reconciliation

feature_service
  - computes completed-bar features only
  - computes microstructure features with explicit timestamps
  - stores feature version and availability masks

research_service
  - offline/isolated only
  - builds datasets from journals
  - trains HMM/KNN/meta artifacts
  - cannot write live model pointer

signal_service
  - in paper/live reads promoted artifact only
  - emits signal intent, not order

risk_governor
  - approves/rejects/size-adjusts signal intent
  - independent of model

execution_router
  - converts approved order intent to Hyperliquid order
  - enforces cloid, reduce-only exits, slippage, order type

monitoring_service
  - watches feed health, model drift, live-vs-replay mismatch, PnL, funding, error rates
```

### 6.2 Event flow

```text
Binance websocket event
 -> raw_market_event journal
 -> normalized_market_event
 -> feature_snapshot
 -> model_signal_intent
 -> risk_decision
 -> order_intent
 -> Hyperliquid order submit with cloid
 -> order/fill/funding/position journal
 -> reconciliation
 -> monitoring and replay dataset
```

Nothing should happen without a journaled event.

---

## 7. Research architecture that is acceptable

### 7.1 HMM regime router

HMM can be useful as a regime diagnostic, but not as proof of edge. Use it to route models and reduce trading during uncertainty.

Legal HMM usage:

```text
posterior probabilities
posterior entropy
regime duration
recent flip cooldown
no-trade if uncertain
```

Illegal/unsafe HMM usage:

```text
fit on all data then validate
use test rows to label states
trade directly because regime == bull/bear
allow HMM output to bypass risk governor
```

### 7.2 KNN role

KNN should be treated as a local similarity diagnostic:

```text
p_up_barrier
p_down_barrier
expected_net_return_after_costs
neighbor_count
neighbor_agreement
neighbor_distance_quality
```

Do not treat KNN vote as a direct live signal until it passes promotion criteria.

### 7.3 Better candidate feature families

Prioritize features with plausible perp-market mechanisms:

```text
Binance taker imbalance and signed volume
open interest change and OI/price divergence
funding rate and funding z-score
mark/index/premium basis
liquidation/force-order flow if reliable
realized volatility and volatility-of-volatility
BTC lead/lag features for ETH
ETH/BTC relative strength
Hyperliquid/Binance basis and liquidity state
WT3D only as completed-bar oscillator features, not standalone signal
```

Order-flow and cross-crypto predictability research supports focusing on flow and cross-asset spillovers more than adding more oscillators.

---

## 8. Promotion criteria for any model artifact

A model artifact must not be live-promotable unless all of the following are true.

### 8.1 Data criteria

```text
BTC and ETH evaluated separately
source data comes from Binance/Hyperliquid journals, not only TradingView export
features are completed-bar or explicitly point-in-time
missingness handled with availability flags
entry labels use executable fill model, not signal close
fees, slippage, funding, latency, basis included
```

### 8.2 Validation criteria

```text
walk-forward splits >= 6
purge/embargo based on actual label windows
no split with > 40% of total PnL
net expectancy positive after 2x fee/slippage stress
bootstrap confidence interval not obviously negative
long and short metrics shown separately
BTC and ETH metrics shown separately
all horizons 6h/24h/72h/7d shown separately
max drawdown and tail losses reported
```

### 8.3 Live shadow criteria

```text
minimum 30 days shadow mode
no live-vs-replay feature mismatch above threshold
no unexplained signal divergence
feed outage behavior verified
risk governor rejects unsafe conditions
paper fills reconciled against Hyperliquid book snapshots
```

### 8.4 Final promotion manifest

Required fields:

```json
{
  "artifact_id": "...",
  "research_only": false,
  "observe_only": false,
  "asset_scope": ["BTC", "ETH"],
  "training_period": "...",
  "validation_period": "...",
  "feature_version": "...",
  "label_version": "...",
  "execution_cost_model_version": "...",
  "promotion_tests_passed": true,
  "approved_by": "orchestrator/manual signoff id",
  "max_notional_allowed": "...",
  "expiry_time": "..."
}
```

No manifest, no live load.

---

## 9. Branch merge / no-merge matrix

| Component | Merge decision | Reason | Required before merge |
|---|---:|---|---|
| `configs/v2_btc_hmm_multi_knn_research.json` | **No production merge** | BTC-only, research-only, not live-promotable | Move under research examples; mark non-live |
| `src/tradingbotsuite/research/hmm_knn.py` | Conditional research merge | Useful prototype, but no edge and possible WT3D/meta/unit issues | Fix leakage/unit/OOF/WT3D issues; keep isolated |
| `src/tradingbotsuite/research/hmm_knn_monitoring.py` | Conditional research merge | Observe-only monitoring is useful | Ensure read-only and never promotion-ready by default |
| `src/tradingbotsuite/research/dataset.py` changes | **No merge until fixed** | Entry fallback, zero-fill, BTC-only, TradingView source limitations | Fix executable labels, missingness, ETH, continuous features |
| `src/tradingbotsuite/main.py` CLI changes | Conditional | Research commands okay if isolated | Live-readiness gate and LIVE research ban |
| `src/tradingbotsuite/operator_console.py` changes | **No live merge** | Allows research jobs in LIVE when flat | Hard-ban research jobs in LIVE |
| `run_manual.py` | **No merge** | Config-loss bug | Use canonical CLI or copy all config fields |
| `run_server.py` | Conditional | Unknown wrapper behavior | Thin wrapper only; same preflight as CLI |
| `run_live_smoke.py` | **No merge until audited** | Live smoke scripts can be dangerous | Must prove no unintended live order; strict preflight |
| `pyproject.toml` research extras | Conditional | Research deps okay as extras | Do not load heavy ML deps in live path |
| large docs/agent artifacts | Usually no merge | Can clutter repo and confuse operators | Move to `docs/research/archive`, not runtime docs |

---

## 10. Exact next-agent instructions

Copy the following into the next agent’s task prompt.

```markdown
# Next Agent Task: TradingBotSuite Live-Readiness Cleanup

You are working on `papaartemsmurf2002-commits/tradingbotsuite`, branch `codex/hmm-knn-research-package`, using the audit packet and this review as source of truth.

## Prime directive
Do not optimize model performance. First make the repository safe, deterministic, and non-leaky. The HMM/KNN branch has no demonstrated edge and must remain research-only/observe-only.

## Required PR sequence

### PR-001: Canonical live-readiness gate
Create `assert_live_ready(config, store, context)` and call it from every live-capable entrypoint: `serve`, `manual`, `smoke-live`, operator console, root launchers, and order execution. In LIVE, fail startup if any hard risk cap is zero/disabled, webhook secret is default, Hyperliquid credentials are missing, `enable_live` is false, exchange reconciliation has not completed, or scheduleCancel cannot be set.

Tests:
- LIVE + `TBS_MAX_DAILY_LOSS_QUOTE=0` fails.
- LIVE + `TBS_MAX_OPEN_RISK_NOTIONAL=0` fails.
- LIVE + default webhook secret fails.
- LIVE + research_only artifact fails.
- PAPER mode remains usable.

### PR-002: Fix root launcher config loss
Replace manual `AppConfig(...)` reconstruction in `run_manual.py` with a method that preserves every field. Prefer a canonical CLI wrapper. Add regression tests that all AppConfig fields survive runtime-mode override.

### PR-003: Ban research jobs in LIVE
Modify `OperatorConsoleService._assert_research_job_allowed` so build/train/calibrate/replay/research jobs are rejected in LIVE regardless of whether a position is open. If monitoring is allowed, it must be read-only and isolated.

Tests:
- LIVE flat + `build-dataset` rejects.
- LIVE flat + `train-model` rejects.
- LIVE flat + `research-hmm-knn` rejects.
- PAPER/SIM can run research.

### PR-004: Enforce HMM/KNN observe-only status
No live signal engine may load artifacts with `research_only=true` or `observe_only=true`. BTC-only artifacts must not load for ETH. Add manifest validation and tests.

### PR-005: Fix dataset leakage and invalid feature defaults
Replace silent zero-fill with train-only imputation and availability flags. Mark any artifact with high missingness as non-promotable. Fix `entry_price` labeling so signal-bar close is not promotable; add executable fill simulation using post-signal latency and Hyperliquid book snapshots.

Tests:
- Missing feature column creates availability flag.
- Validation/test values are not used for imputer fit.
- `signal_bar_close` entry source makes artifact non-promotable.

### PR-006: Verify and fix WT3D computation
Audit whether WT3D is currently computed on sparse signal-event rows. If yes, rewrite it to compute on full continuous Binance completed-bar series and then join to events by timestamp. Add tests proving WT3D feature timestamps are `<= signal_time_ms`.

### PR-007: Fix purge/embargo for multi-horizon labels
Replace fixed `purge_embargo_bars=8` with label-window-aware purging. No training label window may overlap validation/test label windows, especially for 7-day labels.

### PR-008: Hyperliquid idempotent execution skeleton
Implement deterministic `cloid`, order-intent journaling, retry dedupe, cancel-by-cloid, reduce-only exits, scheduleCancel heartbeat, and restart reconciliation. Do not connect this to HMM/KNN signals yet.

Tests:
- Retry after timeout does not duplicate exposure.
- Duplicate signal dedupes.
- Partial fill reconciles correctly.
- Restart cancels/reconciles before new orders.
- Dead-man schedule remains active during unsafe states.

### PR-009: Binance + Hyperliquid journal/replay foundation
Add append-only journals for Binance raw events and Hyperliquid execution/account events. Feature generation must read from journals, not direct websocket state. Add replay tests.

### PR-010: ETH first-class support
Add ETHUSDT Binance data and ETH Hyperliquid execution metadata. Metrics and promotion gates must be separate for BTC and ETH. BTC-only research may not be generalized to ETH.

## Do not do yet
- Do not promote HMM/KNN live.
- Do not tune thresholds to get more trades.
- Do not add more oscillators before fixing data integrity.
- Do not merge root live scripts until preflight tests pass.
- Do not assume Binance signal price is executable on Hyperliquid.

## Definition of done
The repo is safer even if no strategy is profitable. Live mode cannot start with disabled risk limits. Research cannot run inside live runtime. HMM/KNN cannot trade. Every order is idempotent. Every feed and execution event is journaled. Dataset labels are point-in-time and cost-aware. BTC and ETH are validated separately.
```

---

## 11. Test gap checklist

Add or verify these tests.

### Config and entrypoint tests

```text
LIVE disabled risk caps fail
LIVE default webhook secret fails
LIVE missing Hyperliquid key fails
LIVE enable_live false fails
run_manual preserves full config
root launchers call canonical CLI/preflight
```

### Research isolation tests

```text
LIVE cannot queue build/train/replay/research jobs
research artifacts cannot be loaded by live signal engine
observe_only artifacts cannot trade
BTC-only artifacts cannot trade ETH
```

### Dataset leakage tests

```text
future bars never include signal bar or earlier
features never use future rows
WT3D uses completed bars only
purge/embargo removes overlapping label windows
imputation is train-only
zero-fill is removed or explicitly flagged
entry price is executable or artifact non-promotable
```

### Model validation tests

```text
KNN neighbor pool excludes validation/test rows
same-regime KNN handles insufficient neighbors with no-trade
meta-model KNN diagnostics are out-of-fold
cost units are consistent
funding cost is horizon-aware
```

### Execution tests

```text
deterministic cloid generation
retry idempotency
cancel by cloid
scheduleCancel heartbeat
partial fills
reduce-only exits
exchange rejection handling
stale websocket handling
REST rate-limit handling
restart reconciliation
open-order cleanup
basis too wide no-trade
spread too wide no-trade
book depth insufficient no-trade
```

### Chaos tests

```text
Binance websocket disconnect
Hyperliquid websocket disconnect
REST 429 / rate-limit response
clock skew
DB locked / slow write
process crash after submit before ack
process crash after partial fill
network partition during open position
funding spike
basis dislocation
```

---

## 12. Evidence anchors for this audit

The audit packet is the source of truth for repo-specific findings. External references used only to validate production assumptions:

1. Hyperliquid official docs: rate limits include REST weight caps, websocket connection/subscription caps, and address-based action limits.
   `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits`

2. Hyperliquid official docs: websocket user subscriptions include user fills, user funding, user events, BBO, and clearinghouse/account state style feeds.
   `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions`

3. Hyperliquid official docs: exchange endpoint supports order, cancel, cancel-by-cloid, and scheduleCancel; `cloid` is a 128-bit hex string; scheduleCancel is the dead-man style future cancel-all operation.
   `https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint`

4. Binance futures connector docs/code: USD-M futures websocket client documents aggregate trades, mark price/funding, and kline streams.
   `https://github.com/binance/binance-futures-connector-python/blob/main/binance/websocket/um_futures/websocket_client.py`

5. Financial Innovation 2025: BTC/ETH crypto trading research supports information-driven sampling and triple-barrier labeling over naive next-bar prediction.
   `https://link.springer.com/10.1186/s40854-025-00866-w`

6. Digital Finance 2025: regime-switching/HMM-style state variables have a plausible role in cryptocurrency forecasting, but with caveats and not as standalone proof of tradability.
   `https://link.springer.com/article/10.1007/s42521-024-00123-2`

7. Journal of Financial Markets 2026: order flow has explanatory and predictive power for cryptocurrency returns and can dominate fundamentals in nonlinear ML settings.
   `https://www.sciencedirect.com/science/article/pii/S1386418126000029`

8. Journal of Economic Dynamics and Control 2024: cross-cryptocurrency return predictability exists in Binance data, supporting BTC/ETH lead-lag and relative-strength features.
   `https://www.sciencedirect.com/science/article/pii/S0165188924000551`

---

## 13. Final advisor conclusion

The branch is directionally interesting but not production-ready. The most valuable work is not more KNN tuning. The immediate edge-producing possibility, if any, is more likely to come from:

```text
correct venue-aware execution
strict risk control
leakage-free event-driven data
perp microstructure features
cross-asset BTC/ETH features
state-aware no-trade filters
```

The HMM/KNN module can remain as an offline diagnostic layer. It should not be merged into live execution, should not be marketed as profitable, and should not influence autonomous orders until it passes hard validation and shadow-mode criteria.
