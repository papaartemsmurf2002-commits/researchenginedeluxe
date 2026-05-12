# WPR94-08 Perp Context Source/Version Audit

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Align perp context feature truthfulness with the BTC/ETH handoff without
silently changing the meaning of `features_perp_context_v2`.

## Allowed Paths

- `docs/work_packets/WPR94-08-perp-context-source-version-audit.md`
- `docs/stage_reports/STAGE_R94_PERP_CONTEXT_SOURCE_VERSION_AUDIT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/features/builders.py`
- `src/tradingbotsuite/features/packs.py`
- `src/tradingbotsuite/features/registry.py`
- `configs/features/features_perp_context_v3.json`
- `tests/features/test_feature_builders.py`
- `tests/contracts/test_feature_contracts.py`

## Scope

- Keep `features_perp_context_v2` semantics unchanged.
- Add a versioned `features_perp_context_v3` manifest/pack for source
  eligibility metadata.
- Add source eligibility flags:
  - durable provider archive
  - self-archived/local export
  - latest-window diagnostic
  - missing unknown
- Keep funding/OI/premium/taker flow missingness as `NaN` plus quality flags,
  never zero-filled context.
- Keep aggTrade wording as trade-flow proxy, not true OFI or book imbalance.

## Non-Goals

- No live trading behavior, live config writes, order placement, runtime mode
  changes, or sizing logic changes.
- No candidate-pack writing or promotion readiness.
- No new data provider.
- No true depth/L2 or liquidation candidate-ready claim.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py tests\contracts\test_feature_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

- `$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py tests\contracts\test_feature_contracts.py -q` - 35 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` - 379 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q` - 140 passed.
- `python -m compileall -q src\tradingbotsuite` - passed.
- `git diff --check` - passed with existing CRLF conversion warnings only.

## Exit Evidence

- Added versioned `features_perp_context_v3`/`perp_context_v3` while preserving `features_perp_context_v2` semantics.
- Added source eligibility flags for durable public archive, self-archived/local export, latest-window diagnostic, missing/unknown provenance, candidate-ready eligibility, and aggTrade-as-flow-proxy.
- Propagated fixture-family source/version metadata into context materialization evidence.
- Confirmed latest-window REST context remains diagnostic and blocks candidate-ready eligibility in v3.
- Confirmed missing funding/OI/premium context remains `NaN` with explicit quality/missingness flags, not zero-filled.
