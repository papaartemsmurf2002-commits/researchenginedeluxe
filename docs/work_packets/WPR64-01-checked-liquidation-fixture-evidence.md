# WPR64-01 Checked Liquidation Fixture Evidence

Stage: R64 checked liquidation fixture evidence
Owner: Codex Research Agent
Status: closed
Created: 2026-05-05

## Goal

Create a small checked research-only BTCUSDT fixture pack with real liquidation
context rows from Crypto Lake anonymous free-sample data. This packet supplies
the missing fixture evidence gate before any liquidation classifier design can
begin.

## Allowed paths

```text
.gitignore
src/tradingbotsuite/data/historical_fixture_pack.py
data/research/fixtures/btcusdt_liquidation_free_sample_v1/**
docs/runbooks/crypto_lake_free_data_runbook.md
tests/contracts/test_historical_fixture_pack_contract.py
docs/work_packets/WPR64-01-checked-liquidation-fixture-evidence.md
docs/stage_reports/STAGE_R64_CHECKED_LIQUIDATION_FIXTURE_EVIDENCE_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
```

## Constraints

- Do not implement `liquidation_absorption_classifier_v1` in this packet.
- Do not wire liquidation features into checked BTCUSDT or ETHUSDT provider
  cycles in this packet.
- Do not use TradingView exports, synthetic liquidation rows, paid Crypto Lake
  access, provider credentials, AWS profiles, or secret material.
- Preserve `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- Label Crypto Lake free-sample provenance as diagnostic fallback evidence.
- Do not interpret free-sample evidence as broad OOS/stress evidence,
  candidate-pack eligibility, promotion readiness, or a performance claim.

## Required behavior

- Use Crypto Lake anonymous free-sample `liquidations` data only where matching
  free-sample candle bars exist.
- Build a fixture pack with overlapping primary bars and `liquidation`
  context family rows.
- Ensure the checked fixture manifest validates and preserves free-sample
  primary-source and context metadata.
- Keep unknown liquidation windows missing, not zero-filled.
- Document exact commands, row counts, manifest paths, and validation.

## Exit validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\features -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close evidence

- Crypto Lake free-sample BTCUSDT candles fetched for 2023-02-01 to
  2023-02-02: 1,441 source rows, 0 gaps, 0 duplicates.
- Crypto Lake free-sample BTCUSDT liquidations fetched for 2023-02-01 to
  2023-02-02: 1,162 source rows.
- Checked fixture pack written to
  `data/research/fixtures/btcusdt_liquidation_free_sample_v1/`.
- Fixture-pack builder preserves Crypto Lake free-sample metadata on both the
  primary kline source block and the liquidation context block.
- Fixture manifest:
  `data/research/fixtures/btcusdt_liquidation_free_sample_v1/fixture_pack_manifest.json`.
- Fixture row count: 1,440 primary 1m bars.
- Liquidation context row count: 1,162 rows.
- Manifest hash:
  `1e237d15bbd4a84987f2b81344cc32a957c94cb6ed597d3e5b38bbc47304cc83`.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\features -q`
    - 53 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
    - 337 passed
