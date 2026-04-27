# BTC Runtime Reliability Guide

## Objective

This guide covers the BTC-only runtime hardening layer that sits underneath the later TradingView data and training workstreams.

Its purpose is to explain:

- what the runtime now guarantees
- what degraded market-data mode means
- which safety states block entries
- which attribution records are persisted
- how to read the operator console without relying on raw terminal output

This guide does not define the deeper TradingView history/provenance work or promote live model gating.

## Runtime Guarantees

- The engine still uses one canonical BTC execution path for manual, webhook, shadow, paper, and live workflows.
- Closed 15m ATR, barrier construction, and vertical deadlines remain the canonical exit math.
- Binance diff-depth is treated as a reliability subsystem, not only as a feature source.
- Queue-imbalance fields fail soft into explicit unavailable state when the local book is degraded.
- Safety blocks and entry rejections continue to run on the engine path, not in the UI.

## Source-Backed Exchange Assumptions

- Binance local-book sync follows the official snapshot-plus-diff replay contract, including `U/u/pu` continuity and resync on sequence break.
  Source: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/How-to-manage-a-local-order-book-correctly
- Binance market-stream routing now follows the official websocket split:
  - `/market` for `kline` and `aggTrade`
  - `/public` for `bookTicker` and diff-depth
  Source: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Important-WebSocket-Change-Notice
- Binance order-book snapshots use the official USD-M futures depth endpoint.
  Source: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book
- Binance `aggTrade` remains the signed taker-flow source for the live BTC microstructure packet, using `m` as the aggressor-side proxy.
  Source: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Aggregate-Trade-Streams
- When Binance provides `nq` on `aggTrade`, the runtime prefers it over `q` so signed-flow metrics stay aligned with the public book and bookTicker streams, which exclude RPI liquidity.
  Sources:
  https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Aggregate-Trade-Streams
  https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Individual-Symbol-Book-Ticker-Streams
- Binance `bookTicker` remains the canonical live top-of-book source for best bid/ask price and size.
  Source: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Individual-Symbol-Book-Ticker-Streams
- Binance websocket sessions are handled as time-bounded connections; the runtime plans a reconnect before the 24h expiry instead of waiting for forced disconnect.
  Source: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Connect
- Hyperliquid TP/SL protection remains exchange-native fail-safe protection while Python still owns strategy supervision and ambiguity handling.
  Source: https://hyperliquid.gitbook.io/hyperliquid-docs/trading/take-profit-and-stop-loss-orders-tp-sl
- Hyperliquid account queries and websocket/user event handling still rely on the official info and websocket surfaces.
  Sources:
  https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
  https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket

## Market-Data Health Model

- `healthy`:
  - closed 15m bar clock is fresh
  - required live streams are fresh for the current mode
  - local book is synced
  - spread is within the configured threshold
- `degraded`:
  - bar clock is still usable
  - entry-quality data is impaired, such as stale depth or wide spread
  - queue-imbalance metrics may be unavailable
  - the operator should avoid forcing new entries
- `safe_mode`:
  - the runtime has entered fail-closed protection, such as stale market data or unresolved reconcile ambiguity
  - new trades are refused until the reason clears

## Depth Worker States

- `cold`:
  - depth stream has not buffered anything yet
- `buffering`:
  - websocket depth events are being buffered while waiting for a snapshot-aligned local book
- `bootstrapping`:
  - the dedicated depth repair worker is fetching and aligning the REST snapshot
- `synced`:
  - queue imbalance and depletion metrics are trustworthy
- `resync_pending`:
  - a gap or reconnect was detected and a repair is queued
- `backoff`:
  - Binance REST or repair pacing is delaying the next snapshot attempt
- `stale`:
  - the last depth event is too old to trust even if a prior snapshot existed

Read-path rule:

- operator polling and snapshot APIs are passive
- they report cached state only
- they do not trigger depth repairs themselves

Ready-to-ship depth rules:

- the default depth stream remains `250ms`
- the default snapshot limit is `1000`
- the local book must have non-empty bid and ask sides
- best bid must be below best ask
- the default required depth for queue metrics is 10 levels
- invalid queue-depth state degrades queue features only when signed trade flow and bookTicker are still fresh
- planned reconnects, error reconnects, alignment mismatches, invalid books, buffer drops, and buffer high-watermark are exposed as counters

## Safety States That Matter

- `stale_market_data`:
  - closed bars are stale or market data fetch failed
  - operator action: refresh health or restart after checking Binance connectivity
- `heartbeat_loss`:
  - Hyperliquid live stream freshness is outside the configured window
  - operator action: inspect websocket health before resuming
- `reconciliation_stale`:
  - open position state has not been refreshed within the configured gap budget
  - operator action: run Reconcile and keep trading disabled until it clears
- `reconciliation_mismatch`:
  - local and exchange position state disagree
  - operator action: reconcile immediately and do not force entries
- `basis_dislocation`:
  - Binance reference mid and Hyperliquid mid diverge beyond tolerance
  - operator action: inspect mids and wait for basis normalization
- `order_timeout`:
  - live order confirmation stayed ambiguous beyond the configured timeout
  - operator action: inspect the exchange state and reconcile before retrying

## Entry Blocks That Are Not Hidden

- `spread_abnormality`:
  - Binance spread in bps exceeds `TBS_MAX_SPREAD_BPS`
- `daily_loss_limit`:
  - realized closed-trade loss since the UTC day start exceeds `TBS_MAX_DAILY_LOSS_QUOTE`
- `open_risk_limit`:
  - intended BTC notional exceeds `TBS_MAX_OPEN_RISK_NOTIONAL`
- `microstructure_unhealthy`:
  - entry-quality depth/trade state is not trustworthy enough for the current microstructure gate

These are persisted as structured rejection reasons and surfaced through the console.

## Persisted Runtime Attribution

The runtime now appends operator-readable records instead of relying only on traces:

- `execution_metrics`
  - decision outcomes and latency
  - trade entry records
  - trade close records
  - reconcile checks
  - periodic market and execution health samples
- `health_events`
  - transitions in market or execution health state
  - reason code
  - operator-facing summary
  - recommended next action
- `supervision_snapshots`
  - bars since entry
  - elapsed time
  - candidate exit reason
  - MFE / MAE
  - current imbalance state
  - current basis state

## Operator Console Reading Guide

- `Overview`:
  - start here first
  - check `Runtime State`, `Market Data`, and `Execution`
  - then inspect `Supervision` and `Attribution`
- `Control`:
  - use this for manual `long`, `short`, `supervise`, `reconcile`, and `refresh-health`
  - the result boxes show the decision, execution reports, and resulting state together
- `Timeline`:
  - this is the structured feed for health changes, supervision records, execution metrics, packets, jobs, and commands
  - it is intended for incident review, not just raw scrolling
- `Guides`:
  - use this when the runtime shows a degraded or safe-mode state and you need the recommended operator response

## Important Environment Controls

- `TBS_STALE_BAR_AFTER_MS`
- `TBS_STALE_TRADE_AFTER_MS`
- `TBS_STALE_BOOK_TICKER_AFTER_MS`
- `TBS_STALE_DEPTH_AFTER_MS`
- `TBS_MAX_RECONCILE_GAP_MS`
- `TBS_MAX_SPREAD_BPS`
- `TBS_MAX_DAILY_LOSS_QUOTE`
- `TBS_MAX_OPEN_RISK_NOTIONAL`
- `TBS_BINANCE_REST_WEIGHT_BUDGET_PCT`
- `TBS_BINANCE_DEPTH_MAX_BUFFER_EVENTS`
- `TBS_BINANCE_DEPTH_RECONNECT_BACKOFF_MS`
- `TBS_BINANCE_DEPTH_RECONNECT_MAX_BACKOFF_MS`
- `TBS_BINANCE_DEPTH_RESYNC_MIN_INTERVAL_MS`
- `TBS_BINANCE_DEPTH_SNAPSHOT_DEFAULT_BACKOFF_MS`

Use `0` only for limits that are meant to be disabled, such as the daily loss or open-risk caps during local development.

## What This Guide Deliberately Leaves For Later

- deeper TradingView history/provenance and bootstrap capture work
- new dataset-building and model-training expansion
- ETH and cross-asset BTC/ETH work
- true multi-level OFI and HMM layers
- large tuning-lab GUI expansion
