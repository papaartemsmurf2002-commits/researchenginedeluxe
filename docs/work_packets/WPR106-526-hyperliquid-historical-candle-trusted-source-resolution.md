# WPR106-526 - Hyperliquid Historical Candle Trusted Source Resolution

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-COLLECT-022`
- `V2-AUD-XVENUE-014`
- `V2-AUD-QUAL-007`
- `V2-AUD-TESTINFRA-003`

## Objective

Resolve `ISSUE-R106-030` without weakening the research boundary by making the
historical-perps collector support an explicit trusted local Hyperliquid candle
record source for old intraday windows. The public `/info` `candleSnapshot`
path remains recent-window only; old intraday accepted-evidence claims require
operator-supplied Hyperliquid-native records with trusted-root containment,
source hashes, archive refs, coverage proof, and the existing final
backtest-data/readiness gates.

This packet does not fetch paid/requester-pays files, does not download from
S3, does not create accepted research readiness, and does not create
candidate, paper/live, order, sizing, runtime, or promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-526-hyperliquid-historical-candle-trusted-source-resolution.md`
- `AGENTS.md`
- `docs/contracts/collector_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/audit/V2_FINAL_AUDIT_HANDOFF_2026_06_24.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/cli/main.py`
- `src/tradingbotsuite/v2/collectors/historical_dataset.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/v2/test_historical_dataset_collection_phase36.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, or
  candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked legacy evidence under `data/research/fixtures/**`,
  `data/research/historical_cycles/**`, or existing WPR evidence directories.
- No secrets, `.env`, credential files, private cache paths, or local operator
  DBs.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_historical_dataset_collection_phase36.py -q
```

Baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add a trusted local candle records mode to `redx collectors historical-perps`.
- Require `trusted_source_root` containment for any records file.
- Preserve file SHA-256 and row-count provenance in the generated report.
- Keep public API empty old intraday windows as explicit endpoint-limit evidence,
  not as accepted Hyperliquid intraday data.
- Convert the single async contract fixture test to a synchronous collected
  manifest fixture if validation proves the async loop setup remains a local
  Windows socket blocker.
- Keep reports `sandbox_diagnostic` and `accepted_research_ready=false`.

## Decisions Made

- Kept public Hyperliquid `/info` `candleSnapshot` classified as
  recent-window-only after a fresh BTC 1h 2024-01-01 through 2024-01-08 probe
  returned HTTP 200 with zero rows.
- Added `HistoricalPerpDatasetConfig.candle_source`, with `public_api` as the
  default and `trusted_records` as the explicit trusted-file source mode.
- Added CLI flags:
  `--candle-source trusted_records`,
  `--trusted-candle-records-root`,
  `--trusted-candle-records-template`,
  `--trusted-candle-records-format`, and
  `--max-candle-records-file-bytes`.
- For trusted candle files, required root containment, safe JSON/JSONL/NDJSON
  extensions, size caps, non-empty object rows, symbol/timeframe/candle shape
  validation, requested-window filtering, source SHA-256, and source row-count
  evidence before raw archive writes.
- Converted the collected Binance context fixture-pack contract from a fake
  async fetcher path to a synchronous collected-manifest fixture after local
  validation again hit Windows `WinError 10055` during pytest-asyncio setup.

## Changed Files

- `AGENTS.md`
- `docs/work_packets/WPR106-526-hyperliquid-historical-candle-trusted-source-resolution.md`
- `docs/contracts/collector_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/audit/V2_FINAL_AUDIT_HANDOFF_2026_06_24.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/cli/main.py`
- `src/tradingbotsuite/v2/collectors/historical_dataset.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`
- `tests/v2/test_historical_dataset_collection_phase36.py`

## Acceptance Evidence

Fresh provider probe:

```text
Hyperliquid BTC 1h 2024-01-01..2024-01-08: HTTP 200, 0 rows
```

Focused validation:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2/test_historical_dataset_collection_phase36.py -q
# 5 passed, 1 warning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts/test_historical_fixture_pack_contract.py -q
# 42 passed, 1 warning
```

Baseline validation:

```powershell
python -m compileall -q src/tradingbotsuite
# passed
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/v2 -q
# 551 passed, 1 warning
$env:PYTHONPATH='src'; py -3.11 -m pytest tests/contracts -q
# 463 passed, 1 warning
git diff --check
# passed with expected LF-to-CRLF warnings only
```

During pre-fix validation, the unsplit and isolated async contract setup both
hit local Windows `WinError 10055` before the test body ran. The contract suite
passed after the test was converted to a synchronous collected-manifest fixture.

## Issue Status

- `ISSUE-R106-030`: resolved by WPR106-526.
- `ISSUE-R106-026`: remains resolved; WPR106-526 removes the last
  pytest-asyncio dependency from `tests/contracts`.

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion, or
  candidate-pack truth-layer path was changed.
- No legacy GUI path was changed.
- No checked legacy evidence under `data/research/fixtures/**` or
  `data/research/historical_cycles/**` was rewritten.
- No generated market-data artifacts were added.
- The packet creates no accepted research, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion claim.
