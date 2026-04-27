# Microstructure Reliability

## Source Basis

- Binance USD-M local-book contract: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/How-to-manage-a-local-order-book-correctly
- Binance USD-M routed websocket split: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Important-WebSocket-Change-Notice
- Binance USD-M websocket connection rules: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Connect
- Binance USD-M diff-depth stream: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Diff-Book-Depth-Streams
- Binance USD-M aggTrade stream: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Aggregate-Trade-Streams
- Binance USD-M order-book REST endpoint: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book
- Binance Python connector and flowsurface were used as implementation references for stream grouping, connection lifecycle, and request-budget architecture; Binance official docs remain authoritative when examples disagree.
- Sato and Kanazawa's square-root impact paper is used as a feature-design caution for signed-flow diagnostics, not as a trading signal. See `docs/MICROSTRUCTURE_SQUARE_ROOT_IMPACT_FINDINGS.md`.

## What The Current Errors Mean

- `depth stream gap ... expected pu ... got ...`
- This means Binance diff-depth updates arrived with a sequence break.
- Official local-book handling says the book should be resynced from a REST snapshot when this happens.
- This is noisy, but not automatically catastrophic.

- `429 Too Many Requests` on `/fapi/v1/depth`
- This means the resync snapshot itself was rate-limited.
- When that happens, queue-imbalance fields are temporarily unavailable until the next successful resync.

## What This Affects

- It mainly affects entry-time microstructure quality.
- It does not break the 15m candle path used for ATR, time barriers, and core exit supervision.
- For this BTC stack, median holding time around 6 bars means depth precision is much more important for entry filtering than for open-position exit management.

## Current Engineering Stance

- Keep diff-depth/local-book support because it is the right base for future OFI work.
- Follow Binance's routed websocket split instead of the legacy mixed endpoint:
  - `/public` for diff-depth and `bookTicker`
  - `/market` for `aggTrade` and `kline`
- Prefer combined `stream` sessions per route:
  - one `/market` socket for regular market feeds
  - one `/public` socket for high-frequency order-book feeds
  - this matches Binance's migration guidance and reduces avoidable connection churn
- Keep reads passive:
  - UI and operator snapshot polling must never trigger a depth snapshot fetch
- Use a dedicated depth repair worker:
  - one in-flight resync per symbol
  - explicit `cold`, `buffering`, `bootstrapping`, `resync_pending`, `backoff`, `stale`, and `synced` states
- Use correctness-first snapshots:
  - `250ms` diff-depth stream remains the runtime default
  - resync snapshot now uses the full `1000`-level book so L1/L5/L10 queue metrics stay reliable after larger moves
- Use planned websocket rotation:
  - Binance websocket sessions are treated as time-bounded
  - the runtime reconnects before the 24h expiry window using `TBS_BINANCE_WS_PLANNED_RECONNECT_MS` plus bounded jitter
  - planned reconnects are counted separately from error reconnects
- Validate the reconstructed local book:
  - both sides must be non-empty
  - best bid must stay below best ask
  - enough levels must exist for the configured queue metrics, default `TBS_BINANCE_DEPTH_REQUIRED_LEVELS=10`
  - invalid books mark queue/depletion unavailable and schedule one bounded repair rather than exposing stale queue values
- Use shared REST budgeting:
  - depth snapshots, klines, and context endpoints now share one Binance REST budget instead of racing each other
- Keep public-flow math aligned with the public book:
  - when Binance provides aggTrade `nq`, use it instead of raw `q`
  - this avoids mixing RPI-only size into signed-flow metrics while `bookTicker` and diff-depth still exclude RPI liquidity

## Operator Guidance

- If `Market Data` is healthy but `Microstructure` is unhealthy:
  - signed flow and top-of-book can still be used if `entry_ready=true`
  - queue imbalance and depth depletion should be treated as unavailable
  - open-position exit supervision can still continue from 15m bars
  - the console now suppresses stale queue/depletion values instead of showing the last cached book snapshot as if it were still live

- If both bar health and microstructure are unhealthy:
  - do not trust new entries
  - keep the system in a wait-and-recover posture

## What To Watch In The Console

- `Predictions` shows a heuristic short-horizon pressure view:
  - up / down / neutral probabilities from square-root signed flow, flow/price alignment, bookTicker imbalance, synced queue imbalance, and depth-depletion bias
  - confidence and coverage explain how much of the live microstructure stack is currently usable
  - this is visualization only, not a calibrated predictor and not a live gating input
- `depth_gap_count`
- `depth_resync_count`
- `depth_reconnect_resync_count`
- `depth_rate_limit_count`
- `depth_gap_resync_count`
- `depth_planned_reconnect_count`
- `depth_error_reconnect_count`
- `depth_alignment_mismatch_count`
- `depth_invalid_book_count`
- `depth_buffer_high_watermark`
- `depth_dropped_buffered_event_count`
- `depth_sync_state`
- `repair_in_flight`
- `buffered_event_count`
- `backoff_until_ms`
- `next_planned_reconnect_time_ms`

## Ready-To-Ship Microstructure Checklist

- Binance websocket root stays `wss://fstream.binance.com`; the adapter derives `/market` and `/public`.
- Runtime uses two combined BTC sockets:
  - `/market/stream?streams=btcusdt@kline_15m/btcusdt@aggTrade`
  - `/public/stream?streams=btcusdt@bookTicker/btcusdt@depth`
- Depth speed stays `250ms` unless you intentionally test `TBS_BINANCE_DEPTH_UPDATE_SPEED_MS=100`.
- Depth snapshots use `limit=1000` and weight `20`; UI polling must not trigger this REST call.
- The first replayed depth event may align by official `U <= lastUpdateId <= u` overlap or by the futures `pu == lastUpdateId` chain observed live.
- Every later depth event must satisfy `pu == previous u`; otherwise queue depth is degraded and one bounded repair is scheduled.
- Queue imbalance and depth depletion are hidden whenever the book is stale, unsynced, crossed, empty, or below required levels.
- `aggTrade` signed flow uses `nq` when present and retains raw `q` diagnostics.
- RPI depth is intentionally out of scope; public `bookTicker` and normal diff-depth are the queue/top-of-book sources.
- A planned reconnect before 24h expiry must increase planned counters, not error counters.

Healthy-enough behavior:

- occasional gap count increases
- occasional resyncs
- rate-limit count stays low and stops climbing
- microstructure returns to healthy quickly

Needs further engineering attention:

- gap count climbs continuously
- rate-limit count keeps increasing during quiet periods
- queue imbalance is unavailable for long stretches
- `depth_sync_state` stays in `backoff` or `resync_pending` for long stretches
- microstructure remains unhealthy long enough to interfere with normal entry testing
