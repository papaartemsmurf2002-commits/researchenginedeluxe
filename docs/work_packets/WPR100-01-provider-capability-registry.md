# WPR100-01 Provider Capability Registry

Status: closed
Owner: Codex Research Agent
Stage: R100 provider capability registry

## Goal

Implement the useful, low-risk recommendation from
`C:\Users\papaa\Downloads\deep-research-report (1).md`: make provider/data
capability, durability, retention, and health policy metadata explicit so
latest-window REST context, free samples, public archives, and local vendor
exports cannot be confused in manifests or generated fixture packs.

## Allowed Paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/data/contracts.py`
- `src/tradingbotsuite/data/historical_fixture_pack.py`
- `tests/contracts/test_data_contracts.py`
- `tests/contracts/test_historical_fixture_pack_contract.py`

## Scope

1. Add a provider capability registry for existing sources/families only.
2. Expose capability metadata on data manifests built through the contract
   helper.
3. Attach capability metadata to generated fixture-pack source and context
   family entries.
4. Validate supplied capability metadata when present.
5. Add contract tests for latest-window, free-sample, public-archive, and
   local-vendor capability behavior.

## Non-Goals

- No new provider implementation.
- No provider downloads or generated data changes.
- No candidate batch execution.
- No strategy, feature, exit, discovery, promotion, live, order-placement,
  runtime-mode, candidate-pack writing, or sizing behavior changes.
- No performance, profitability, data-readiness, or live-readiness claims.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_data_contracts.py tests\contracts\test_historical_fixture_pack_contract.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Exit Evidence

Completed on 2026-05-13.

Implemented:

- Added a provider capability registry for existing source/family surfaces:
  Binance REST, Binance USD-M latest-window REST context, Binance Vision,
  Crypto Lake, and registered-only Hyperliquid archive surfaces.
- Capability payloads record `durability_class`, `retention_limit`,
  `history_start`, `exchange_native`, `normalized`, `health_policy`,
  `diagnostic_only_by_default`, and `candidate_ready_default`.
- `build_data_manifest()` now attaches `provider_capability` metadata, and
  `validate_data_manifest()` rejects mismatched supplied capability metadata.
- Generated provider fixture-pack source entries and context-family entries now
  carry provider capability metadata.
- Fixture validation rejects context-family capability metadata that contradicts
  the source/family/latest-window/free-sample contract.

Deferred or intentionally not implemented:

- No Tardis, Kaiko, CoinAPI, CCXT, or other new provider adapter was added.
- No BTC/ETH multi-year fixture pack was generated or downloaded.
- No durable vendor-layer data was claimed for OI, taker/ratio, liquidation, or
  depth.
- No candidate batch, strategy plugin, HMM/KNN audit rewrite, exit API
  unification, promotion, or live-readiness work was included.
- Report recommendations that require new data/vendor access remain future
  packets, not partial claims.

Validation passed:

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
