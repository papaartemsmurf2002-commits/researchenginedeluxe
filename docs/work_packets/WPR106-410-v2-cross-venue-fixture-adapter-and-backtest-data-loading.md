# WPR106-410 V2 Cross-Venue Fixture Adapter And Backtest Data Loading

Status: closed
Owner: Codex Research Agent
Created: 2026-06-21

## Objective

Implement Phase 19 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md` by
adding a research-safe venue adapter interface and a first comparable
non-Hyperliquid fixture adapter. The packet must prove the v2 archive,
universe, coverage, snapshot, and backtest-data service can carry explicit
cross-venue provenance for one Binance USDT-M style fixture without changing
the Hyperliquid-first default.

This packet does not add live venue connectivity, CCXT network downloads,
private endpoints, account access, order placement, paper/live behavior,
sizing, runtime-mode changes, candidate packs, or promotion behavior.

## Audit IDs

- `V2-AUD-XVENUE-001`

## Dependencies

- Phase 4 archive layout and manifests.
- Phase 5 universe snapshots.
- Phase 8 silver market-data/archive snapshots.
- Phase 9 backtest-data service.
- Phase 17 storage/official-file posture.
- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/backtest_data_service_contract.md`

## Allowed Paths

- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/backtest_data_service_contract.md`
- `src/tradingbotsuite/v2/venues/**`
- `src/tradingbotsuite/v2/universe/**`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-410-v2-cross-venue-fixture-adapter-and-backtest-data-loading.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- The first comparable venue adapter is fixture/local only.
- Venue capabilities must explicitly reject secrets, signed/private endpoints,
  account state, order placement, leverage/margin mutation, sizing, and runtime
  mode changes.
- Cross-venue rows must keep venue and instrument provenance on every row and
  manifest.
- Hyperliquid remains the configured default primary venue.

## Acceptance Criteria

- `VenueAdapterCapability`, `VenueRawRequest`, and `VenueRawResponse` schemas
  validate public research-only adapter behavior.
- A Binance USDT-M style fixture adapter writes raw payload, silver bar rows,
  silver funding rows, coverage reports, a universe snapshot, and an archive
  snapshot with explicit `binance` venue provenance.
- `BacktestDataService` can load comparable bars and funding for the non-
  Hyperliquid fixture through the same archive/snapshot gates.
- Venue capabilities and rows reject live/order/sizing/runtime implications.
- Tests prove the Hyperliquid default remains unchanged.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_cross_venue_phase19.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

No broader non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- Real venue networking or CCXT integration becomes necessary.
- Private/signed endpoints, credentials, account state, orders, leverage,
  margin, sizing, paper/live artifacts, or runtime-mode changes enter scope.
- Cross-venue evidence would require weakening archive, universe, coverage, or
  backtest-data service gates.

## Completion Notes

Closed on 2026-06-21.

- Added v2 venue adapter schemas:
  - `VenueAdapterCapability`;
  - `VenueRawRequest`;
  - `VenueRawResponse`.
- Added a fixture-only Binance USDT-M adapter helper that writes:
  - raw fixture payloads;
  - silver bar rows with `venue: binance`;
  - silver funding rows with `venue: binance`;
  - coverage reports for bars and funding;
  - a Binance as-of universe snapshot;
  - a silver archive snapshot.
- Added a generic universe manifest append helper for cross-venue snapshot rows.
- Proved `BacktestDataService` can load Binance fixture bars and funding through
  the existing archive snapshot, universe snapshot, coverage, lockbox, and field
  projection gates.
- Locked in that Hyperliquid remains the default primary venue.
- Updated venue-adapter and backtest-data-service contracts.
- Marked `V2-AUD-XVENUE-001` as `self_checked`.
- No real venue networking, CCXT integration, private/signed endpoint, account
  state, order placement, leverage/margin mutation, paper/live artifact, sizing
  instruction, runtime-mode change, candidate pack, or promotion behavior was
  implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_cross_venue_phase19.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 19 tests passed: 4 passed.
- Full v2 tests passed: 135 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Contract-doc smoke passed: 2 passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
