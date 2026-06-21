# V2 Universe Contract

Status: v2 contract foundation
Audit ID: `V2-AUD-UNIV-001`

## Purpose

The universe manager defines instrument eligibility and prevents survivorship
bias in accepted research evidence.

## Initial Schema Names

- `UniverseConfig`
- `UniverseMode`
- `UniverseSnapshotRef`
- `InstrumentCatalogRow`
- `AssetContextSnapshotRow`
- `UniverseSnapshotRow`
- `UniverseRefreshResult`
- `HyperliquidInfoClient`

## Required Rules

- Default venue is `hyperliquid`.
- Default market type is `perpetual`.
- Default evidence threshold is `dayNtlVlm >= 5_000_000`.
- Accepted evidence uses `as_of` universe snapshots.
- Current-universe analysis is sandbox/current-only and cannot be evidence.
- BTC and ETH are fixture/reference symbols, not the whole universe.
- HIP-3/RWA instruments require namespace, reference market, oracle source,
  session calendar, listing age, weekend behavior, and caveats.
- Raw `metaAndAssetCtxs` payloads are archived before parser output is written.
- Hyperliquid universe refresh supports two audited source modes:
  `payload_file` for repeatable local payloads and `public_api` for the
  unsigned public `/info` `metaAndAssetCtxs` endpoint.
- Public API universe refreshes must record venue raw-request/raw-response
  provenance IDs, source endpoint, adapter ID, and raw payload hash. Tests must
  use injectable transports and must not require live network access.
- Excluded instruments remain in catalog and snapshot rows with exclusion
  reasons.

## Forbidden

- Current-universe evidence claims.
- Below-threshold accepted evidence without an explicit later contract change.
- HIP-3/RWA accepted evidence when required reference metadata is missing.
- Signed/private Hyperliquid endpoints, account state, orders, leverage/margin
  mutation, sizing, runtime-mode changes, or promotion behavior in universe
  refresh.
- Silent network fetches from CLI or durable worker calls when neither a local
  `payload_file` nor explicit `public_api` source mode is declared.
