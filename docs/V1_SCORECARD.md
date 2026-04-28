# V1 Audit Scorecard

Audit date: April 10, 2026

Primary reference:

- [btc_eth_hybrid_framework_verified_blueprint.txt](c:/Users/papaa/Music/tradingbotsuite/btc_eth_hybrid_framework_verified_blueprint.txt)

Verification evidence used in this pass:

- `python -m pytest` -> `47 passed`
- public Binance smoke on April 10, 2026:
  - closed 15m bars fetched successfully
  - websocket-backed `aggTrade`, `bookTicker`, and diff-depth local-book snapshot became healthy
  - tracked symbol cache stayed warm without repeated REST bootstrap
- Hyperliquid testnet smoke on April 10, 2026:
  - entry filled
  - websocket events arrived
  - reconcile confirmed the open position
  - close filled
  - reconcile returned the account flat again

## Weighted Score

Overall weighted score: `92 / 100`

Category scores use the requested `0` to `5` scale.

| Category | Weight | Score | Weighted | Rationale |
| --- | ---: | ---: | ---: | --- |
| Execution safety and correctness | 20 | 5 | 20 | Live path now has fresh testnet smoke evidence plus fail-closed entry confirmation, protective normalization, reconciliation watchdogs, and stream-backed event handling. |
| Binance market-data and microstructure readiness | 15 | 5 | 15 | REST bootstrap plus websocket `kline`, `aggTrade`, `bookTicker`, and diff-depth local-book sync are in place, including queue-imbalance snapshots and auto-resync on depth continuity breaks. |
| State machine and persistence | 15 | 4 | 12 | Dedupe, same-direction ignore, flip sequencing, append-only events, and restart/reconcile persistence are present and well tested. Single-process SQLite WAL design matches the blueprint. |
| Framework feature coverage | 15 | 4 | 12 | ATR, frozen triple barriers, vertical barrier, Hurst as stored feature, signed taker imbalance, queue imbalance visibility, basis monitor, and manual operator visibility are implemented. Acceptance-model calibration remains intentionally bootstrap-level. |
| Testing and mathematical verification | 15 | 5 | 15 | The suite covers ATR math, barriers, Hurst bounds, microstructure aggregation, idempotency, flip logic, stale-data safe mode, stream event handling, and Hyperliquid contract fixtures. |
| Operability and documentation | 10 | 5 | 10 | README and operator guide now include PowerShell-safe examples, live smoke guidance, and audit artifacts. |
| Best-practice engineering quality | 10 | 4 | 8 | The codebase is modular and readable, and this audit tightened fail-fast config validation plus Binance stream bootstrap behavior. Remaining debt is mostly around production hardening depth rather than architecture. |

## Blueprint Checklist

| Blueprint area | Status | Evidence |
| --- | --- | --- |
| Webhook auth and dedupe | Implemented | FastAPI ingress plus HMAC in [app.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/web/app.py) and [security.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/core/security.py) |
| Binance 15m bars | Implemented | REST bootstrap + websocket cache in [binance.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/adapters/binance.py) |
| Signed taker imbalance | Implemented | `aggTrade` window aggregation in [binance.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/adapters/binance.py) |
| Top-of-book imbalance | Implemented | `bookTicker` snapshot logic in [binance.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/adapters/binance.py) |
| Hurst feature | Implemented | rolling estimator in [math.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/core/math.py) and decision snapshot storage in [engine.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/core/engine.py) |
| ATR-frozen triple barrier | Implemented | barrier math in [math.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/core/math.py) |
| Flip logic and duplicate lock | Implemented | state machine in [engine.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/core/engine.py) |
| Hyperliquid client-order-id execution path | Implemented | live adapter in [execution.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/adapters/execution.py) |
| Hyperliquid user streams and reconcile | Implemented | stream subscriptions and reconcile in [execution.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/adapters/execution.py) |
| SQLite WAL current state + append-only events | Implemented | schema in [sqlite_store.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/persistence/sqlite_store.py) |
| Manual operator shell with visible pipeline | Implemented | [manual_cli.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/manual_cli.py) |
| Queue imbalance from synced depth | Implemented | local-book reconstruction and queue-imbalance snapshots in [binance.py](c:/Users/papaa/Music/tradingbotsuite/src/tradingbotsuite/adapters/binance.py) |
| Funding, premium, open interest features | Partial | not yet captured in the market-data service |
| Acceptance probabilities and calibrated model versions | Deferred by blueprint | bootstrap placeholders only, consistent with later-phase acceptance-model work |
| Meta-labeling / adverse-selection exits / HMM / ETH | Deferred by blueprint | intentionally not part of the current BTC-first v1 core |

## Exchange-Assumption Verification

| Assumption | Status | Source |
| --- | --- | --- |
| Binance kline stream updates the current kline at 250ms cadence | Confirmed | Binance kline docs |
| Binance aggTrade stream aggregates trades by price and taking side at 100ms cadence | Confirmed | Binance aggTrade docs |
| Binance `bookTicker` pushes real-time best bid/ask updates | Confirmed | Binance bookTicker docs |
| Hyperliquid `orderUpdates`, `userEvents`, and `userFills` are valid websocket subscriptions | Confirmed | Hyperliquid websocket subscription docs |
| Hyperliquid websocket user streams emit initial snapshots with `isSnapshot: true` | Confirmed | Hyperliquid websocket subscription docs |
| Hyperliquid info queries must use the master or subaccount address rather than an agent wallet address | Confirmed | Hyperliquid info endpoint docs |
| Hyperliquid TP/SL failures can return `Invalid TP/SL price` style errors | Confirmed | Hyperliquid error responses docs |
| Hyperliquid price normalization logic based on SDK behavior and docs matches all edge cases | Partially confirmed | Official docs confirm error classes and tick/lot rules; current testnet smoke passed, but ongoing live validation is still prudent |

## Blueprint-Approved Deferrals

These are not counted as v1 failures in this score:

- full multi-level OFI beyond the current local diff-depth queue-imbalance layer
- hidden Markov regime layer
- ETH expansion and ETH-specific volatility scaling
- meta-label acceptance model and probability calibration
- adverse-selection / alpha-decay exit hierarchy
