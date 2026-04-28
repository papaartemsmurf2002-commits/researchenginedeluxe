# Agent name

Feature Agent

# Task received

Add a research-only archive source contract for OF-style historical data sources that are not implemented yet: Binance Vision, Crypto Lake, and Hyperliquid archive. Keep it independent from live runtime and network calls, focused on schemas, source manifests, and validation helpers.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_INPUT_LOOKUP.md`
- `docs/tradingbotsuite_runtime/source_inputs/tradingbotsuite_critical_audit_orchestrator_next_agent.md`
- `docs/tradingbotsuite_runtime/source_inputs/orchestrator_btc_eth_perps_architecture_review_v3.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_SOURCE_LOG.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_public_contract_freeze.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_real_btc_lineage_quality.md`
- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `pyproject.toml`

# Files changed

- `src/tradingbotsuite/research/archive_sources.py`
- `tests/tradingbotsuite/test_archive_sources.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_of_archive_source_contract.md`

# Commands/tests run

```powershell
git status --short --branch
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_archive_sources.py -q
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Results:

- `tests/tradingbotsuite/test_archive_sources.py`: `8 passed in 0.14s`
- `tests/tradingbotsuite/test_hmm_knn.py`: `23 passed in 12.39s`

# Decisions made

- Added an offline-only source contract module under `src/tradingbotsuite/research/`.
- Defined descriptors for `binance_vision`, `crypto_lake`, and `hyperliquid_archive`, including symbol scope, likely data families, timestamp requirements, default diagnostic-only status, and caveats.
- Required manifest fields are enforced by `validate_archive_source_manifest()` and `assert_valid_archive_source_manifest()`.
- Event time is mandatory. Receive time is mandatory for point-in-time compatibility; an explicit unavailable reason is valid for research manifests but marks the source non-promotable.
- Hyperliquid archive remains diagnostic-only by default because archive rows cannot substitute for append-only local order/account/fill/funding/position journals.
- Source mismatch is modeled as a first-class quality flag instead of being hidden in free text.
- Missing book/account execution fields are preserved through `missing_fields`/`unavailable_fields`/`null_fields`. Protected book/account fields listed in `zero_filled_fields` invalidate the manifest.

# Assumptions

- This pass defines contracts only. It does not assert current availability, completeness, or schema stability for any provider.
- All three archive sources are diagnostic-only by default until a future agent proves point-in-time receive timestamps, coverage, source/schema parity, and replay compatibility.
- BTC and ETH symbols are interface scope only; Phase 1 HMM/KNN remains BTC-only unless separately assigned.

# Open issues or blockers

- None. `HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before implementation.

# Handoff notes for other agents

- Future data agents can use `validate_archive_source_manifest()` before accepting archive-derived research inputs.
- A manifest with unavailable receive time can still be valid for research but should not be treated as promotion-quality evidence.
- Provider-normalized archive fields that differ from live Binance USD-M or Hyperliquid journal fields should set `source_mismatch` or `source_mismatch_reason`.
- Do not zero-fill absent book, order, fill, funding, or position fields. Preserve missingness and let feature/model layers decide train-only imputation later.
