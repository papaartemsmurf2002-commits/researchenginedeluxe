# WPR66-01 Interval-Aware Feature Building

Stage: R66 interval-aware feature building
Owner: Codex Research Agent
Status: closed
Created: 2026-05-05

## Goal

Make historical research-cycle feature materialization use the primary bar
interval declared by the loaded dataset or fixture pack instead of always
assuming the 15m default. This unblocks local research-cycle validation for the
WPR64 1m liquidation free-sample fixture while keeping existing 15m fixtures
and cache identity behavior intact.

## Allowed paths

```text
src/tradingbotsuite/research_cycle/runner.py
tests/contracts/test_research_cycle_contract.py
tests/historical/test_full_cycle_local_fixture_pack.py
docs/work_packets/WPR66-01-interval-aware-feature-building.md
docs/stage_reports/STAGE_R66_INTERVAL_AWARE_FEATURE_BUILDING_REPORT.md
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Do not wire liquidation features or strategies into checked BTCUSDT or
  ETHUSDT provider-cycle configs in this packet.
- Do not create candidate-pack eligibility, promotion evidence, live signals,
  order placement, runtime writes, or live configuration changes.
- Do not use TradingView exports or synthetic evidence for liquidation
  validation.
- Treat WPR64 Crypto Lake free-sample liquidation fixture evidence as local
  diagnostic cycle validation only, not broad OOS/stress evidence or
  performance evidence.
- Preserve feature-cache identity separation by interval.

## Required behavior

- Resolve a cycle feature interval from validated fixture metadata when
  available.
- Preserve the 15m default for synthetic or unspecified local datasets.
- Include interval evidence in the feature-build manifest and feature records.
- Pass the resolved interval into feature-cache identity and registered feature
  materialization.
- Fail clearly when a fixture declares an unsupported or mismatched primary
  interval.
- Add regression coverage proving the WPR64 1m fixture can build liquidation
  features through the historical cycle without 15m bar-gap failures.

## Exit validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Close evidence

- Historical research-cycle feature building now resolves `primary_interval_ms`
  from fixture/source metadata before cache identity and materialization.
- Fixture `base_interval` is preferred, then constant dataset
  `source_interval`, then a uniform bar-time diff, with the 15m default kept
  only when no interval evidence exists.
- Feature-build manifests now expose interval evidence, and each feature-set
  record exposes the cache/materialization `interval_ms`.
- Cache identity already included `interval_ms`; WPR66 now passes the resolved
  interval into that identity and into registered feature materialization.
- Added WPR64 BTCUSDT liquidation free-sample cycle regression coverage using
  tmp output only. It validates 1m feature times, 1m cache identity,
  liquidation feature columns, no candidate pack, and diagnostic free-sample
  provenance.
- Preserved 15m fixture behavior and updated historical fixture-builder
  expectations for omitted optional `liquidation` context.
- Validation passed:
  - `python -m compileall -q src\tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py -q`
    - 26 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q`
    - 11 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
    - 367 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py -q`
    - 20 passed
  - `$env:PYTHONPATH='src'; python -m pytest tests\historical -q`
    - 35 passed
