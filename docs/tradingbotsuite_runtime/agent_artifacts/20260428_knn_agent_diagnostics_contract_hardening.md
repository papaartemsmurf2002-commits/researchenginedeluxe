# Agent name

KNN Agent

# Task received

Objective: harden neighbor diagnostics and same-regime guarantees.

Requested commands:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
rg -n "neighbor_diagnostics|neighbor_distance_quality|same_regime|fallback|knn_sweep|primary_k|lorentzian" src tests docs/tradingbotsuite_runtime
```

Requested tasks:

- Add or verify tests that `neighbor_diagnostics.csv` has enough fields to audit neighbor regime, distance quality, selected K, weighting mode, and source row references.
- Add a regression test if missing: KNN fallback cannot cross regimes unless explicitly configured.
- Write this artifact.

# Files read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_PROMPTS.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`

# Files changed

- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_knn_agent_diagnostics_contract_hardening.md`

# Commands/tests run

Initial requested focused test command:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Initial result:

```text
...................                                                      [100%]
19 passed in 4.88s
```

Requested search command:

```powershell
rg -n "neighbor_diagnostics|neighbor_distance_quality|same_regime|fallback|knn_sweep|primary_k|lorentzian" src tests docs/tradingbotsuite_runtime
```

Result summary:

- Found KNN diagnostics, same-regime, fallback, K sweep, primary K, and Lorentzian implementation/test/doc references.
- Confirmed fallback regression coverage already existed in `test_knn_same_regime_blocks_cross_regime_neighbors_until_fallback_is_enabled`.
- Confirmed diagnostics artifact test existed, but it did not yet require `neighbor_distance_quality` inside `neighbor_diagnostics.csv`.

Final focused test command after hardening:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_hmm_knn.py -q
```

Final result:

```text
.....................                                                    [100%]
21 passed in 5.67s
```

Final requested search command was rerun after hardening:

```powershell
rg -n "neighbor_diagnostics|neighbor_distance_quality|same_regime|fallback|knn_sweep|primary_k|lorentzian" src tests docs/tradingbotsuite_runtime
```

Result summary:

- Confirmed `neighbor_distance_quality` is now emitted in diagnostics and asserted in tests.
- Confirmed the model spec now documents the stronger `neighbor_diagnostics.csv` contract.

# Decisions made

- Added `neighbor_distance_quality` to successful neighbor diagnostic rows so the CSV can be audited without joining back to `knn_predictions.parquet`.
- Added `neighbor_distance_quality: None` to skipped diagnostic rows to keep the CSV schema stable across success and skip rows.
- Strengthened `test_hmm_knn_research_writes_expected_research_only_artifacts` to require diagnostics fields for selected K, weighting mode, primary flag, same-regime flag, fallback flag, skip reason, query/source row references, neighbor row references, neighbor distance, distance quality, weight, label, PnL multiple, and neighbor regime.
- Added value-level diagnostics assertions:
  - populated `neighbor_distance_quality` values are between `0.0` and `1.0`;
  - neighbor source rows do not come after query source rows;
  - populated neighbor regimes match query regimes in the default no-fallback path;
  - generated diagnostics include configured test K values and both weighting modes.
- Tightened the existing fallback regression test to assert that the no-fallback path produces no neighbor regime, while the explicit fallback path can cross from query regime `1` to neighbor regime `0`.
- Updated `HMM_MULTI_KNN_MODEL_SPEC.md` so `neighbor_diagnostics.csv` explicitly documents selected K, weighting, primary flag, same-regime/fallback flags, skip reason, source references, query/neighbor regimes, ranks, distances, distance quality, weights, labels, and PnL multiples.

# Assumptions

- `neighbor_distance_quality` in diagnostics should represent the combination-level quality for the selected neighbor set, repeated on each emitted neighbor row for that K/weighting combination.
- Skipped diagnostics should retain the same schema with null neighbor-specific fields.
- The existing fallback test was the right place to harden the cross-regime regression rather than adding a near-duplicate test.
- Existing modified and untracked files are part of the current HMM/KNN workstream and should not be reverted.

# Open issues or blockers

None.

`docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_ISSUES.md` reported no open issues before this task, and no new blocker was found.

# Handoff notes for other agents

- KNN diagnostics contract is stricter now and covered by focused tests.
- The diagnostics CSV now carries distance quality directly, which should simplify monitoring and artifact audits.
- Same-regime behavior remains the default; cross-regime fallback remains impossible unless `allow_cross_regime_fallback` is explicitly true.
- Focused HMM/KNN validation is green: `21 passed`.
- No live execution, sizing, live gates, Hyperliquid behavior, safety behavior, or operator live controls were changed.
