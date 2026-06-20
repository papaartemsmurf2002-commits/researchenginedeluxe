# WPR106-75 Venue Scorecard

Status: research-only, observe-only, promotion-ready false.

## Decision

Primary new venue for the next intake packet: `okx_archive`.

Reason: OKX has the best public historical-data surface for this packet: trade
history, candles, funding, mark/index candle context, and L2 downloads/API
surfaces. WPR106-75 registers the source only; it does not implement broad
downloads or ingestion.

## Scorecard

| Venue | WPR106-75 role | Useful data surface | Current repo status | Caveat |
| --- | --- | --- | --- | --- |
| OKX | Primary next data intake | Historical trades, candles, funding, mark/index context, L2 downloads | `okx_archive` registered-only, diagnostic-only | No parser, checksum policy, gap validation, or point-in-time receive-time evidence yet |
| Bybit | Secondary venue | V5 market endpoints include klines, funding, trades, and open interest for contract markets | `bybit_archive` registered-only, diagnostic-only | Existing branch contract is registered-only until local ingestion is normalized |
| Hyperliquid | Diagnostic context | S3 archive has L2/book and asset-context style data; funding is hourly | `hyperliquid_archive` registered-only, diagnostic-only | Archive surface is not equivalent to complete point-in-time candle evidence |
| Deribit/options | Later packet | Volatility and options context | Out of WPR106-75 scope | Should be a separate volatility-context packet after core venue intake is settled |

## Registered Source Rules

- `okx_archive`, `bybit_archive`, and `hyperliquid_archive` are not candidate-ready by default.
- Any manifest from these sources remains research-only and non-promotional until ingestion contracts exist.
- Historical downloads or REST backfills do not create live receive-time evidence.
- Missing fields must be explicit; missing venue context must not be interpreted as real neutral values.

## Source References

- OKX historical data: https://www.okx.com/en-gb/historical-data
- OKX API v5 market data: https://app.okx.com/docs-v5/en/
- Bybit V5 open interest endpoint: https://bybit-exchange.github.io/docs/v5/market/open-interest
- Hyperliquid historical data: https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data
- Hyperliquid funding: https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding
