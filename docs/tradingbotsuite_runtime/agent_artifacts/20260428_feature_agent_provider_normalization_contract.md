# Agent name

Feature Agent

# Task received

Turn `archive_sources.py` from descriptor-only into a provider-normalization contract for offline archive manifests. Define canonical normalized field families, add helper access to required/optional/protected fields, validate normalized-field coverage and explicit missingness, keep archive sources diagnostic-only by default, and avoid network/runtime/live execution changes.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `src/tradingbotsuite/research/archive_sources.py`
- `tests/tradingbotsuite/test_archive_sources.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_of_archive_source_contract.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_data_agent_missing_context_manifest_hardening.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_data_foundation_boundary_review.md`

# Files changed

- `src/tradingbotsuite/research/archive_sources.py`
- `tests/tradingbotsuite/test_archive_sources.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_provider_normalization_contract.md`

# Commands/tests run

```powershell
python -m py_compile src/tradingbotsuite/research/archive_sources.py
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_archive_sources.py -q
git diff --check -- src/tradingbotsuite/research/archive_sources.py tests/tradingbotsuite/test_archive_sources.py docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md
```

Results:

- `py_compile`: passed.
- `tests/tradingbotsuite/test_archive_sources.py`: `16 passed in 0.14s`.
- `git diff --check`: exit code `0`; line-ending warnings only.

# Decisions made

- Bumped `ARCHIVE_SOURCE_CONTRACT_VERSION` to `of-archive-source-provider-normalization-contract-v2`.
- Added canonical normalized field contracts for `kline`, `trade`, `agg_trade`, `book_ticker`, `depth_snapshot`, `liquidation`, `funding_rate`, `open_interest`, `premium_index`, `user_fill`, `user_funding`, `order_event`, and `position_snapshot`.
- Preserved aliases for legacy/source naming: `order_book_l2` and `book_snapshot` map to `depth_snapshot`; `bbo` maps to `book_ticker`.
- Added helpers to enumerate contracts and fetch field contracts globally or per source descriptor.
- Required manifest `normalized_fields` and validated it against family-required fields.
- Treated explicitly unavailable required fields as valid but diagnostic through `missing_required_normalized_fields`; unreported missing required fields are validation errors.
- Kept book and Hyperliquid account/execution missingness protected. Protected fields listed in `zero_filled_fields` remain invalid.
- Added quality flags for `provider_mismatch`, `missing_receive_time`, `unsupported_family`, `missing_required_normalized_fields`, protected missingness preservation, and source-specific caveats.
- Kept all supported archive sources diagnostic-only/non-promotable by default.

# Assumptions

- `normalized_fields` describes the canonical post-provider-normalization schema for a manifest, not necessarily every raw provider column in `schema_fields`.
- Explicit missingness can be valid for research manifests because these archives are diagnostic-only by default, but it must remain visible through quality flags and missing-field lists.
- `mark_price` is not a canonical family in this pass; premium/mark/index context belongs under `premium_index` unless a future task defines a separate family.
- Existing unrelated worktree changes in dataset, market-data, data-quality, execution-journal, and related tests appear to belong to other agents and were not modified.

# Open issues or blockers

None. `HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before implementation, and no blocker was appended.

# Handoff notes for other agents

- Data agents should emit `normalized_fields` in archive manifests and keep unavailable normalized fields explicit in `missing_fields`, `unavailable_fields`, or `null_fields`.
- Do not zero-fill absent book, depth, account, order, fill, funding, or position fields. Preserve missingness and let downstream research layers decide train-only imputation.
- Source/provider symbol or schema differences should set `source_mismatch`, `source_mismatch_reason`, or `provider_symbol` so validation emits provider mismatch quality flags.
- This work touched only offline research contract code/tests/docs. It did not change live gates, sizing, Hyperliquid execution, runtime behavior, or operator live controls.
