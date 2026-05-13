# WPR103-01 Durable Public Archive Fixtures

Owner: Codex Research Agent
Stage: R103 durable BTC/ETH data foundation
Status: closed
Created: 2026-05-13

## Goal

Create compact, checked-in BTCUSDT and ETHUSDT multi-window fixture packs from
Binance Vision public archive data so the branch has durable source evidence
instead of latest-window REST or free-sample data for the next candidate
validation stage.

## Allowed paths

- `.gitignore`
- `docs/KNOWN_ISSUES.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/BRANCH_TECHNOLOGY_AND_DEVELOPMENT_REFERENCE.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `data/research/fixtures/btcusdt_public_archive_multi_window_v1/**`
- `data/research/fixtures/ethusdt_public_archive_multi_window_v1/**`
- `configs/research/**`
- `tests/contracts/**`
- `tests/historical/**`

## Constraints

- Fixtures must be generated from public archive source data with checksum
  evidence and must remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- Do not commit raw downloaded Binance Vision ZIP/JSONL archives.
- Do not write candidate packs, promotion artifacts, live configuration,
  runtime-mode changes, sizing behavior, or order-placement behavior.
- Compact fixtures can support research-cycle execution, but they are not
  OOS acceptance evidence or live signal evidence.
- Preserve existing dirty work and do not revert unrelated changes.

## Planned implementation

1. Download and checksum-verify BTCUSDT/ETHUSDT Binance Vision daily archives
   for 15m klines, 1m klines, and aggTrades over four declared market windows.
2. Build compact fixture packs containing the selected 15m, 1m, and aggTrade
   rows, with manifest source metadata, provider capability metadata,
   checksum/source-hash evidence, gap/duplicate evidence, and window-selection
   metadata.
3. Unignore only the compact fixture pack directories.
4. Validate fixture manifests with both historical fixture-pack validation and
   durable public archive readiness checks.
5. Update orchestrator docs and issue state without claiming candidate-ready
   strategy performance.

## Validation target

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\historical -q
$env:PYTHONPATH='src'; python -m pytest -q
git diff --check
```

## Exit evidence

Implemented:

- Added compact checked-in BTCUSDT and ETHUSDT public archive multi-window
  fixture packs under:
  - `data/research/fixtures/btcusdt_public_archive_multi_window_v1/`
  - `data/research/fixtures/ethusdt_public_archive_multi_window_v1/`
- Fixtures were generated from checksum-verified Binance Vision USD-M daily
  archives for 15m klines, 1m klines, and aggTrades across trend, drawdown,
  range, and high-volatility windows.
- Raw aggTrade archive rows were compacted to 1m trade-flow proxy rows while
  preserving selected raw row counts and source archive metadata in the
  manifests.
- Updated durable readiness configs for both symbols with actual fixture
  manifest paths and hashes.
- Added checked-in fixture readiness contract coverage.
- Resolved `ISSUE-R101-003` as a durable data-foundation blocker while leaving
  candidate validation as R104 work.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\contracts\test_data_contracts.py -q
# 57 passed

python -m compileall -q src\tradingbotsuite
# passed
```

Full-suite and diff validation are recorded in the final push pass.

```powershell
$env:PYTHONPATH='src'; python -m pytest -q
# 1337 passed, 1 skipped, 92 warnings

git diff --check
# passed with line-ending warnings only
```
