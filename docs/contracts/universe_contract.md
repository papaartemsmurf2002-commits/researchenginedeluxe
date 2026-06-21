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
- Excluded instruments remain in catalog and snapshot rows with exclusion
  reasons.

## Forbidden

- Current-universe evidence claims.
- Below-threshold accepted evidence without an explicit later contract change.
- HIP-3/RWA accepted evidence when required reference metadata is missing.
