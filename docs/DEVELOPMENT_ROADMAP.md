# Development Roadmap

## Progress Review

- V1 BTC execution core is in place:
  - webhook ingestion
  - manual/browser operator control
  - SQLite persistence
  - Hyperliquid live adapter
  - ATR / triple-barrier exits
  - Binance bar and microstructure reference layer

- V2 research start slice is in place:
  - feature enrichment
  - dataset build
  - model train / calibrate / replay-eval
  - shadow observe-only scoring
  - TradingView-compatible BTC signal ingress remains part of the V2 path rather than a deferred V3 concern

## What Still Matters Most

- reliability
- observability
- keeping live behavior fail-closed
- proving V2 usefulness offline before changing live gating
- hardening the BTC base before returning to the deeper TradingView data-framework workstream

## Recommended Next Steps

### 1. Stabilize Binance Microstructure Further

- run with lighter depth defaults and watch the new counters
- collect evidence on:
  - gap frequency
  - resync frequency
  - rate-limit frequency
- only do deeper refactors if instability remains persistent after the lighter configuration

### 2. Improve Research Data Quality

- keep collecting BTC signals
- keep treating TradingView-origin BTC signals as first-class research inputs
- build larger datasets
- review missing-feature rates in the dataset manifest
- verify class balance before trusting calibration

### 3. Strengthen Research Evaluation

- compare V2 against V1 baseline over more samples
- add stability checks by month/session/regime
- keep deterministic dataset and replay outputs
- keep promotion blocked unless out-of-sample improvement is consistent

### 4. Prepare The V2 Acceptance Layer

- keep the BTC TradingView-to-dataset-to-acceptance path readable and trustworthy
- keep scoring in `shadow`
- review calibration buckets and expectancy
- use explicit promotion-failure reasons instead of a bare pass/fail read
- keep adverse-selection and alpha-decay disabled until replay evidence justifies them
- define a formal promotion gate before any paper/live influence

### 5. Defer V3 Work Explicitly

- ETH perp workflow and ETH-specific modeling
- cleaner GUI/operator layer for safe tweaking
- broader tuning and research instrument suite
- richer multi-venue or multi-asset expansion beyond BTC-core V2 needs

## Easy Operator Workflow

### For Reliability Work

- Open `Overview`
- Watch `Market Data`, `Execution`, and `Microstructure`
- Note gap / resync / rate-limit counts
- Use `Refresh Health` if the system is recovering

### For Research Work

- Open `Research`
- Run `Build Dataset`
- Run `Train Latest Dataset`
- Run `Calibrate Latest Train`
- Run `Replay Latest Artifact`
- Review artifact cards before doing anything else

### For Live Safety Checks

- Use `Control`
- Prefer `Shadow` then `Paper`
- Use `Smoke Live` only when you want to verify exchange plumbing itself
