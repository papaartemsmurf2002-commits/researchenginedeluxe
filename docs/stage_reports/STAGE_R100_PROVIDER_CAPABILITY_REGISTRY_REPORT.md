# Stage R100 Provider Capability Registry Report

Date: 2026-05-13
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR100-01-provider-capability-registry.md`
Input reviewed: `C:\Users\papaa\Downloads\deep-research-report (1).md`

## Summary

WPR100-01 implemented the report's safest high-fit recommendation: make data
source capability, durability, retention, and health policy explicit in
contracts and generated fixture metadata.

Most model, strategy, KNN, exit, and truthfulness recommendations in the report
were already covered by existing branch work. The remaining major gap is
durable BTC/ETH derivative context data, which requires provider access or data
generation and was not appropriate to fake in this packet.

## Changes

- Added `DataProviderCapability` and
  `provider-capability-registry-v1` metadata in
  `src/tradingbotsuite/data/contracts.py`.
- Added capability payloads for existing Binance REST, Binance USD-M REST
  latest-window context, Binance Vision, Crypto Lake, and registered-only
  Hyperliquid archive source/family surfaces.
- `build_data_manifest()` now attaches provider capability metadata.
- `validate_data_manifest()` rejects mismatched provider capability metadata
  when supplied.
- Generated fixture-pack source and context-family entries now carry capability
  metadata.
- Fixture validation rejects context entries whose capability metadata
  contradicts the source, family, latest-window, or free-sample contract.
- Added contract tests for public archive, latest-window REST, local vendor
  export, free-sample, and mismatch cases.

## Deferred Items

The report also recommends several larger items that remain future packets:

- Build a real `btc_eth_core_fixture_pack_v1` with multi-year BTCUSDT/ETHUSDT
  perps, mark/index/premium, funding, and spot context.
- Add durable vendor layers for OI, taker/ratio, liquidation, bookTicker, and
  depth.
- Add provider adapters for Tardis/Kaiko/CoinAPI/CCXT or equivalent vendor
  manifests.
- Run the curated candidate batch for basis convergence, OI-flow breakout,
  funding crowding fade, ETH residual, and liquidation diagnostics.
- Deepen regime/HMM and KNN audits only if true HMM or new KNN exit-layer paths
  are introduced.
- Unify exit required-context metadata in a later exit-specific packet.

These were not implemented because they require new data, provider access, or
broader cross-module behavior and would be unsafe to represent as completed
from a report alone.

## Boundary

This packet did not add providers, download data, generate artifacts, run
candidate batches, write candidate packs, claim data readiness, alter live
execution, alter live config, place orders, change runtime mode, authorize
promotion, or touch sizing behavior.

All new metadata remains research-boundary support only.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_data_contracts.py tests\contracts\test_historical_fixture_pack_contract.py -q
# 53 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 417 passed

git diff --check
# passed with line-ending warnings only
```

## Decision

WPR100-01 is closed. The branch now has explicit provider capability metadata
for existing data surfaces, improving durability/retention truthfulness without
making new data or live-readiness claims.
