# WPR106-399 V2 Bronze Silver Market Data Pipelines

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Implement Phase 8 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: add
fixture-backed bronze and silver archive pipelines for candles, funding, and
asset contexts so collected raw payloads can become backtest-ready silver bars,
funding intervals, and normalized context rows with gap/normalization
manifests, coverage updates, and an initial archive snapshot.

This packet does not implement the Phase 9 backtest data service, strategies,
backtest engines, ledgers, Lead Book storage, UI, paper/live behavior, order
placement, sizing, runtime-mode changes, candidate packs, or promotion
behavior.

## Audit IDs

- `V2-AUD-ARCH-004`
- `V2-AUD-QUAL-002`

## Dependencies

- `docs/contracts/archive_contract.md`
- `docs/contracts/data_quality_contract.md`
- `src/tradingbotsuite/v2/archive/**`
- `src/tradingbotsuite/v2/data_quality/**`
- `src/tradingbotsuite/v2/workers/**`

## Allowed Paths

- `docs/contracts/archive_contract.md`
- `docs/contracts/data_quality_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `src/tradingbotsuite/v2/archive/**`
- `src/tradingbotsuite/v2/data_quality/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-399-v2-bronze-silver-market-data-pipelines.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Do not call venue APIs or implement continuous collectors in this packet.
- Do not implement the backtest data service or strategy execution.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Raw payloads remain immutable; bronze/silver writes must create manifest rows
  and source-file references.
- Missing or malformed rows must produce normalization/gap evidence, not silent
  accepted evidence.

## Acceptance Criteria

- Fixture raw candle payloads can flow raw -> bronze candles -> silver 1m bars.
- Fixture raw funding payloads can flow raw -> bronze funding -> silver funding
  intervals.
- Fixture raw asset context payloads can flow raw -> bronze context -> silver
  normalized context.
- Silver bar schema is stable, documented, and tested.
- Derived 5m, 15m, and 1h bars can be built from complete 1m rows.
- Incomplete derived windows are recorded in normalization manifests.
- Funding rows use UTC intervals and can be consumed by the future cost/funding
  model.
- Context rows normalize mark/oracle/open-interest fields.
- Coverage manifests update after silver bar builds.
- Initial archive snapshot can include silver file and coverage/quality
  manifests.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
git diff --check
```

No broad non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- A backtest data service, strategy executor, backtest runner, ledger append
  workflow, Lead Book store, candidate-pack, paper/live, order, sizing, runtime,
  or promotion behavior becomes necessary.

## Completion Notes

Closed on 2026-06-20.

- Added Phase 8 market-data schemas:
  - `BronzeCandleRow`
  - `SilverBarRow`
  - `BronzeFundingRow`
  - `SilverFundingIntervalRow`
  - `BronzeAssetContextRow`
  - `SilverAssetContextRow`
  - `NormalizationManifestRow`
- Added `NormalizationManifestStore` for
  `manifests/normalization_manifests.parquet`.
- Added raw-to-bronze rebuild helpers for fixture/local raw candles, funding,
  and asset contexts.
- Added bronze-to-silver rebuild helpers for:
  - 1m silver bars from bronze candles;
  - complete-window derived 5m, 15m, and 1h bars from 1m bars;
  - UTC funding intervals;
  - normalized mark/oracle/open-interest/context rows.
- Incomplete derived windows are recorded as normalization manifest evidence
  instead of silently filled.
- Silver bar builds write coverage reports through the Phase 6 data-quality
  manifest store.
- Silver market-data snapshots include coverage and quality manifest hashes.
- Hardened archive path partition encoding so namespaced v2 instrument IDs such
  as `hyperliquid:perp:BTC` remain valid on Windows paths while preserving the
  original manifest instrument ID.
- Added CLI commands:
  - `archive build-bronze`
  - `archive build-silver`
  - `archive snapshot-silver-market-data`
- Updated archive/data-quality contracts and the v2 operations runbook.
- Marked `V2-AUD-ARCH-004` and `V2-AUD-QUAL-002` as `self_checked`.
- No Phase 9 backtest data service, strategy execution, backtest engine, ledger
  append workflow, Lead Book storage, UI, paper/live behavior, order placement,
  sizing, runtime-mode changes, candidate-pack writing, or promotion behavior
  was implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\archive\test_archive_phase8.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

Result:

- Focused Phase 8 archive tests passed: 5 passed.
- Focused v2 tests passed: 54 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- Full `compileall` for `src\tradingbotsuite` passed.
- Contract tests passed: 462 passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
