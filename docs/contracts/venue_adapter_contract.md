# V2 Venue Adapter Contract

Status: v2 Phase 19 fixture adapter foundation
Audit ID: `V2-AUD-XVENUE-001`

## Purpose

Venue adapters expose research-safe market-data access with provenance. They
must not expose order placement, account state, signing, sizing, or runtime
execution behavior to v2 research modules.

## Initial Schema Names

- `VenueAdapterCapability`
- `VenueRawRequest`
- `VenueRawResponse`
- `HyperliquidInfoClient`
- `BinanceFixtureArchiveResult`

## Required Rules

- Every response records venue, endpoint/source, request parameters, timestamp,
  rate-limit metadata when known, and raw payload hash.
- Provider quirks can only downgrade evidence scope.
- Venue capabilities may declare `supports_universe_metadata` for unsigned
  public metadata endpoints that feed instrument catalogs and universe
  snapshots.
- The Hyperliquid public-info adapter may call only the unsigned `/info`
  `metaAndAssetCtxs` endpoint for universe metadata and must preserve
  `public_unsigned` access mode plus raw request/response provenance.
- Cross-venue rows preserve venue provenance and must not dilute the
  Hyperliquid-first default.
- Venue capabilities must fail closed if they declare secret access, signed
  private endpoints, account state, order placement, leverage/margin mutation,
  sizing, or runtime-mode changes.
- The first comparable non-Hyperliquid venue is a fixture-only Binance USDT-M
  adapter. It may write raw payload, silver bars, silver funding rows, coverage
  reports, universe snapshots, and archive snapshots from local fixture rows.
- Binance fixture rows must carry `venue: binance`, a namespaced
  `instrument_id`, and `venue_provenance` on every silver row.
- Binance fixture capability must not become the default primary venue;
  Hyperliquid remains the default venue until a later explicit decision.

## Forbidden

- Secret/private-key access.
- Signed trading endpoints.
- Order, account, leverage, margin, or position mutation.
- Real CCXT or venue network downloads in the Phase 19 fixture adapter path.
- Extending the Hyperliquid public-info adapter beyond unsigned metadata
  without a new scoped packet and boundary audit.
- Treating cross-venue fixture rows as live execution proof, paper/live signal,
  sizing instruction, candidate-pack eligibility, or promotion evidence.
