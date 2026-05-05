# Stage R62 Liquidation Fixture Intake Foundation Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR62-01-liquidation-fixture-intake-foundation.md`
Status: closed

## Scope

R62 added the research-only data foundation needed before any liquidation classifier work. It allows local Crypto Lake exports and anonymous free-sample fetches to normalize `liquidation` archive rows, and it allows `liquidation` to be materialized as an optional historical fixture-pack context family.

The stage does not implement `liquidation_absorption_classifier_v1`, add liquidation features, wire liquidation into checked BTCUSDT/ETHUSDT cycles, add live stream ingestion, or create promotion/live evidence.

## Intake Behavior

- `fetch-crypto-lake` now accepts `--data-family liquidation`.
- Crypto Lake `liquidation`, `liquidations`, `force_order`, and related aliases normalize to the canonical `liquidation` family.
- Normalized rows preserve `event_time_ms`, `symbol`, `side`, `price`, `quantity`, provider identity, optional receive time, and optional force-order fields.
- Liquidation manifests are tagged as perpetual context with retention, coverage, stream-health, diagnostic-only, and non-promotable metadata.
- Variable-cadence liquidation archives do not infer gaps from missing timestamps and do not treat same-timestamp events as duplicates.

## Fixture Behavior

- Historical fixture packs can now accept `liquidation` context manifests from `crypto_lake` or `binance_vision`.
- Fixture materialization slices liquidation rows by event time using the existing no-lookahead context policy.
- Same-timestamp liquidation events aggregate deterministically into fixture rows with event count, quantity, quote notional, buy/sell notional, side imbalance, dominant side, and VWAP-style price columns when source fields permit.
- Missing liquidation context remains omitted optional context. Unknown windows are not zero-filled.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py tests\contracts\test_historical_fixture_pack_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- Full compile passed.
- WPR62 focused suite: 53 passed.
- Full contract suite: 334 passed.

## Research Boundary

This stage does not add live signals, promotion readiness, paper/shadow/testnet/canary behavior, live configuration writes, order placement, position sizing, runtime mode changes, or performance claims.

## Next Stage

The classifier remains gated. The next practical packet should add liquidation-derived feature columns or durable checked liquidation fixture evidence before any classifier strategy is introduced.
