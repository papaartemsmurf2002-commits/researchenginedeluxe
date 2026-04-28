# Agent name

Regime Agent

# Task received

Objective: harden HMM artifact contract and edge-case coverage.

Requested commands:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
rg -n "posterior_entropy|regime_no_trade|hmm_fit_end_row|regime_model_backend|_hmm_online_posterior|_posterior_frame" src tests docs/tradingbotsuite_runtime
```

Requested tasks:

- Add or verify test coverage that `regime_posteriors.parquet` always includes posterior columns, entropy, max probability, top regime, no-trade flag, backend, split id, source row index, and `hmm_fit_end_row`.
- Add a regression test if missing: invalid/degenerate posterior rows normalize to uniform uncertainty and become no-trade when thresholds require it.
- Write artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- Existing `docs/tradingbotsuite_runtime/agent_artifacts/` entries surfaced by the requested `rg`

# Files changed

- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_regime_agent_hmm_artifact_contract_edge_cases.md`

# Commands/tests run

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Exact baseline result:

```text
...................                                                      [100%]
19 passed in 4.94s
```

Requested search:

```powershell
rg -n "posterior_entropy|regime_no_trade|hmm_fit_end_row|regime_model_backend|_hmm_online_posterior|_posterior_frame" src tests docs/tradingbotsuite_runtime
```

The search confirmed implementation and coverage references in:

- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_monitoring.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_EXECUTION_RISK_REVIEW.md`
- prior agent artifacts under `docs/tradingbotsuite_runtime/agent_artifacts/`

Final validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Exact final result:

```text
.....................                                                    [100%]
21 passed in 5.85s
```

Final requested search rerun:

```powershell
rg -n "posterior_entropy|regime_no_trade|hmm_fit_end_row|regime_model_backend|_hmm_online_posterior|_posterior_frame" src tests docs/tradingbotsuite_runtime
```

Relevant new/strengthened test locations:

- `tests/tradingbotsuite/test_hmm_knn.py:265` adds `test_degenerate_regime_posterior_normalizes_to_uniform_no_trade`.
- `tests/tradingbotsuite/test_hmm_knn.py:493` strengthens the `regime_posteriors.parquet` contract assertion with posterior columns.
- `tests/tradingbotsuite/test_hmm_knn.py:502` strengthens the contract assertion for `regime_model_backend`.

# Decisions made

- Preserved production code because `_normalize_posterior`, `RegimeModel.posterior`, and `_posterior_frame` already had the needed behavior.
- Added a direct regression test for degenerate posterior rows through `RegimeModel.posterior` followed by `_posterior_frame`.
- The degenerate test uses a fake model that returns non-finite and zero-mass posterior rows. The normalized posterior is asserted as uniform `0.25` across four states.
- The degenerate test asserts the uniform rows become no-trade under the current production thresholds, with entropy approximately `1.0`, max probability `0.25`, backend recorded, split id recorded, source row index recorded, and `hmm_fit_end_row` recorded.
- Strengthened the artifact-level HMM/KNN research test so `regime_posteriors.parquet` must include posterior columns, `top_regime`, `top_regime_label`, `max_regime_probability`, `posterior_entropy`, `recent_regime_flip`, `regime_no_trade`, `regime_model_backend`, `walk_forward_split`, `source_row_index`, and `hmm_fit_end_row`.
- Added an artifact-level assertion that posterior probability columns sum to `1.0` for all generated regime rows.
- Did not change live gating, live sizing, Hyperliquid execution behavior, safety behavior, or operator live controls.

# Assumptions

- The task was scoped to HMM artifact contract and edge-case coverage in `tests/tradingbotsuite/test_hmm_knn.py`.
- The repository currently contains untracked HMM/KNN workstream files; they were treated as active workstream state and not reverted.
- The final focused HMM/KNN test suite result is the relevant validation for this scoped hardening pass.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this work, and no new blocker was found.

# Handoff notes for other agents

- The HMM artifact contract is now guarded at the generated `regime_posteriors.parquet` level.
- Degenerate posterior normalization now has explicit regression coverage.
- Future changes to posterior normalization or regime artifact schema should keep `test_degenerate_regime_posterior_normalizes_to_uniform_no_trade` and `test_hmm_knn_research_writes_expected_research_only_artifacts` green.
