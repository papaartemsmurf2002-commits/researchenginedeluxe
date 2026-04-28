# Dataset Building Guide

## Purpose

For the full architecture and source-reliability framework behind this builder, see:

- [TRADINGVIEW_V2_DATA_FRAMEWORK.md](c:/Users/papaa/Music/tradingbotsuite/docs/TRADINGVIEW_V2_DATA_FRAMEWORK.md)

The dataset builder creates the research dataset used by the V2 BTC acceptance layer.

The goal is simple:

- take real stored BTC signal history
- reconstruct what the engine knew at signal time
- label each signal with the same triple-barrier logic used by the trading engine
- write a reproducible dataset for offline training and evaluation

This is a research step only. It does not change live trading behavior by itself.

## What The Builder Needs

The builder does not start from raw price candles alone. It needs both signal history and market context.

Required inputs:

- persisted BTC signals in SQLite
- enough historical Binance 15m bars to reconstruct ATR, volatility, and future outcomes

Helpful but non-fatal inputs:

- funding history
- open interest history
- premium / basis context
- signal-time microstructure snapshot already stored in decision packets

Important detail:

- missing research-only features do not cause fake values to be invented
- they are stored as explicit missingness flags

So the dataset can still build even when some additive context is unavailable.

## What Counts As A Usable Signal

Not every stored signal becomes a dataset row.

A signal is only kept if the builder can do all of the following:

- find enough lookback bars for ATR and regime features
- reconstruct the signal-time feature snapshot
- find enough forward bars to evaluate the outcome
- produce a real triple-barrier label

Signals are skipped when the builder cannot label them safely.

This is intentional. A smaller honest dataset is better than a larger contaminated one.

## What The Builder Actually Does

### Step 1. Load Stored BTC Signals

The builder reads persisted BTC signals from SQLite.

TradingView chart exports must be imported first:

```bash
python -m tradingbotsuite.main import-tv-chart-export --path "BINANCE_BTCUSDT.P, 15 (2).csv" --symbol BTCUSDT --strategy-version kernel_v1
```

Use a new `--strategy-version` whenever the TradingView indicator/model logic is materially changed or optimized. TradingView chart exports are rolling windows, so repeated exports with shifted dates are expected; each import writes a batch manifest and stores source lineage in the signal raw payload.

The current default project CSV is a merged chart-export artifact. Its merge manifest is `data/imports/tradingview_exports/BINANCE_BTCUSDT.P_15_combined_manifest.json`. Binance-only warmup rows are intentionally signal-free and should be treated as context for closed-bar feature calculations, not as TradingView signal history.

The chart-export importer uses only `Buy` as a candidate long signal and `Sell` as a candidate short signal. It ignores `StopBuy`, `StopSell`, `Shapes`, and `Chars`.

For each signal it uses:

- `signal_id`
- `symbol`
- `direction`
- `tv_bar_time_ms`
- stored decision packet context when available

### Step 2. Preload Historical Bars Efficiently

The builder calculates the full 15m bar range it needs across the whole signal set and fetches that range once in paginated chunks.

Why this matters:

- older versions fetched overlapping kline history again and again per signal
- that was wasteful and could trigger Binance `429`
- the current implementation fetches one shared range and slices locally per signal

This makes dataset building much more reliable and much lighter on Binance.

### Step 3. Rebuild Signal-Time Features

For each signal, the builder reconstructs the feature packet at the signal timestamp.

Current BTC features include:

- ATR
- Hurst
- signed taker imbalance
- top-of-book imbalance
- queue imbalance from local book snapshots
- funding context
- open interest context
- premium / basis context
- realized volatility
- ATR percentile
- volatility shock features
- session / time-of-day features

These are the same kinds of features used by the live/shadow engine path, but assembled for offline research.

### Step 4. Freeze Barrier Math

The builder uses the same barrier logic as the live engine:

- normal live/webhook/manual entry price defaults to the signal-time reference bar
- TradingView chart-export bootstrap entries use `next_bar_open_plus_configured_slippage` when that normalized entry is present in the imported raw payload
- TP and SL are set from ATR multiples
- the vertical barrier is based on the configured bar budget

The plotted TradingView `Buy`/`Sell` marker price is stored as `signal_marker_price` for audit only. It is not used as the fill price or as the label.

### Step 5. Label The Outcome

The builder walks through future bars in time order and applies the same exit evaluation logic:

- stop loss first if the bar hits SL
- take profit if the bar hits TP
- time barrier if the bar budget expires first

The final label includes:

- exit reason
- binary accept label
- PnL multiple in ATR terms

This lets the research layer ask:

- which signals would have been worth accepting
- which signals should likely have been filtered out

## What Gets Written

The dataset builder writes two main outputs.

### 1. Parquet Dataset

Path:

- `data/research/<plan_version>/btcusdt_dataset.parquet`

This is the row-level dataset used for training and evaluation.

Each row represents one proposed BTC signal at decision time.

### 2. Dataset Manifest

Path:

- `data/research/<plan_version>/dataset_manifest.json`

This is the summary and reproducibility file.

It includes:

- plan version
- symbol
- row count
- dataset path
- dataset hash
- config snapshot
- missing-feature rates

The missing-feature rates are especially useful because they tell you whether the dataset is rich enough to trust or too sparse in key areas.

## What You Need Before Running It

Minimum practical requirements:

- BTC signals already stored in the database
- working Binance historical bar access
- enough sample count to produce labeled rows

If you have almost no BTC signal history yet:

- the dataset may build but be too small for useful training
- or it may produce too few label-complete rows

If that happens, the right action is usually:

- collect more BTC signals
- or import historical BTC TradingView signal history

## How To Run It

### Browser Workflow

If the operator UI is enabled:

1. Open `Research`
2. Click `Build Dataset`
3. Wait for the job to finish
4. Review the dataset artifact card
5. Check row count and missing-feature rates before training

### CLI Workflow

Use:

```bash
python -m tradingbotsuite.main build-dataset
```

This creates the parquet file and dataset manifest under the configured research output directory.

## How To Judge Whether The Dataset Is Good Enough

Check these first:

- row count is not trivially small
- labels are not all one-sided
- missing-feature rates are not extreme in the features you care about
- the build completed without inventing fallback values

Healthy signs:

- row count is large enough to support training and calibration
- funding / OI / premium missingness is low to moderate
- labels contain both winners and losers

Warning signs:

- very small dataset
- one-sided labels
- very high missingness in several important context features
- repeated rate-limit or exchange errors during every build

## Why Missing Features Are Allowed

Research data is messy in real life. Exchanges rate-limit, some endpoints are unavailable, and some older contexts are incomplete.

The current design deliberately allows additive research features to be missing because:

- the core label path should still work from bars and stored signal context
- missingness itself can be informative
- failing closed is better than making up numbers

So the builder prefers:

- `feature missing + missing flag`

over:

- fake default pretending the data was known

## How Binance Rate Limits Are Handled

The builder now reduces Binance pressure in two ways:

- it preloads one shared bar range and slices locally
- it soft-fails additive context features into missingness when appropriate

That means:

- a temporary issue in open interest or premium context should not kill the whole build
- a heavy overlapping kline-fetch pattern should no longer be the normal behavior

If Binance still rate-limits aggressively:

- wait for cooldown
- rerun the build
- check whether the issue is short-term exchange pressure or a persistent configuration problem

## What Happens Next

Once the dataset exists, the normal sequence is:

1. train model
2. calibrate model
3. run replay evaluation
4. review metrics before trusting anything

Do not jump straight from dataset build to live gating.

The dataset is the foundation, not the decision to promote the model.

## Short Practical Checklist

- make sure BTC signals exist in SQLite
- build dataset
- inspect row count
- inspect missing-feature rates
- confirm the dataset is not one-sided
- only then move to training
