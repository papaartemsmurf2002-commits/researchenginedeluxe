# V2 Stability Audit

Date: April 11, 2026

## Summary

This document records the current V2 BTC acceptance-layer status after the stability and verification pass that explicitly excludes the deeper TradingView data-framework workstream.

The immediate goal of this pass was:

- verify critical math and replay assumptions
- make runtime feature construction align with research config
- improve manifest and replay observability
- harden observe-only scoring behavior
- prepare the codebase so the TradingView data-framework workstream can be added later without refactoring the base again

## Current Status

### Implemented

- closed-bar ATR and barrier construction
- shared triple-barrier label generation
- dataset build, training, calibration, replay evaluation, and shadow scoring
- config-driven volatility and regime feature windows through the research plan
- dataset manifests with feature version, label version, source mix, class balance, missing-feature rates, split summary, and plan hash
- artifact manifests with calibration method and versioning
- observe-only score metadata with explicit skip reasons
- promotion evaluation with explicit failure reasons instead of a single boolean
- optional adverse-selection and alpha-decay supervision flags, disabled by default

### Partial

- long-run execution-quality attribution is still lightweight
- promotion gating is now explicit, but still advisory and observe-only
- adverse-selection and alpha-decay exist behind safe flags and need replay proof before enabling

### Deferred

- deeper TradingView acquisition/history framework work
- ETH-specific modeling and ETH execution layer
- GUI-heavy tuning and parameter-lab workflows
- advanced multi-level OFI and HMM layers

## Critical Assumptions And Source Notes

### Binance local-book replay

Status:

- confirmed by official doc

Current assumption:

- buffered diff-depth events must be replayed only after the REST snapshot
- the first accepted event must satisfy Binance's documented `U/u/lastUpdateId` condition
- every subsequent event must maintain `pu == previous_u`, otherwise the local book must resync

Official source:

- https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/How-to-manage-a-local-order-book-correctly

### Binance funding history

Status:

- confirmed by official doc

Current assumption:

- funding history comes from `/fapi/v1/fundingRate`
- results are ascending and bounded by the documented `limit`

Official source:

- https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History

### Binance premium and open interest context

Status:

- confirmed by official doc

Current assumption:

- premium-index context comes from official premium-index kline data
- open interest uses the official USD-M open-interest endpoint
- if these endpoints are unavailable during research, features degrade into explicit missingness rather than fabricated values

Official sources:

- https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Premium-Index-Kline-Data
- https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest

### Hyperliquid protection and reconcile dependence

Status:

- confirmed by official doc for the general TP/SL and info/websocket surfaces
- some account/reconcile behavior remains implementation-dependent and should still be treated carefully in live mode

Current assumption:

- exchange-native TP/SL orders remain fail-safe protection
- Python-side supervision still owns strategy-specific exits and ambiguity handling

Official sources:

- https://hyperliquid.gitbook.io/hyperliquid-docs/trading/take-profit-and-stop-loss-orders-tp-sl
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint

### Logistic regression and isotonic calibration behavior

Status:

- confirmed by installed version and official doc

Current assumption:

- installed scikit-learn version is `1.8.0`
- logistic regression and isotonic calibration behavior should be interpreted using the 1.8.0 docs, not stale memory

Official sources:

- https://sklearn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
- https://sklearn.org/stable/modules/generated/sklearn.isotonic.IsotonicRegression.html

## Gaps To Watch Next

- validate adverse-selection and alpha-decay on replay before enabling them outside test fixtures
- extend execution attribution if live V2 trust work becomes the priority
- keep dataset and artifact determinism under watch as manifests grow
- leave [TRADINGVIEW_V2_DATA_FRAMEWORK.md](c:/Users/papaa/Music/tradingbotsuite/docs/TRADINGVIEW_V2_DATA_FRAMEWORK.md) for the next major workstream once the current V2 base stays stable over more replay and operator use
