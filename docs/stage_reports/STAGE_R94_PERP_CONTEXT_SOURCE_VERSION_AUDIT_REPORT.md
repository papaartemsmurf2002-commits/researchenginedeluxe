# Stage R94 Perp Context Source/Version Audit Report

Date: 2026-05-12
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR94-08-perp-context-source-version-audit.md`

## Scope

WPR94-08 added a versioned perp-context truthfulness surface without changing
the existing `features_perp_context_v2` contract.

## Completed

- Registered `features_perp_context_v3` and `perp_context_v3`.
- Added v3 source eligibility features:
  - `quality_context_durable_provider_archive`
  - `quality_context_self_archived`
  - `quality_context_latest_window_diagnostic`
  - `quality_context_missing_unknown`
  - `quality_context_candidate_ready_eligible`
  - `quality_agg_trade_flow_proxy_not_ofi`
- Extended fixture-family context evidence with source/version fields:
  `source_name`, `source_type`, `source_access_mode`, `schema_version`,
  `collector_version`, `ingestor_version`, `source_data_family`, and
  `feature_claim_scope`.
- Kept latest-window REST context diagnostic-only for v3 candidate eligibility.
- Kept aggTrade language scoped to trade-flow proxy evidence, not order-book
  imbalance or true OFI.

## Boundary Notes

- `features_perp_context_v2` semantics were not rewritten.
- Research outputs remain `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.
- No live trading behavior, live config, order placement, promotion readiness,
  or sizing logic changed.
- No large archive download or candidate-pack write was added.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py tests\contracts\test_feature_contracts.py -q
# 35 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 379 passed

$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
# 140 passed

python -m compileall -q src\tradingbotsuite
# passed

git diff --check
# passed with existing CRLF conversion warnings only
```

## Decision

WPR94-08 is complete. The next roadmap step is the dedicated AggTrade
orderflow feature pack.
