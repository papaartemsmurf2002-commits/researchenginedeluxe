# Agent name

Labeling Agent

# Task received

Objective: harden exact label accounting around funding, MFE/MAE, and exit time.

Requested commands:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
rg -n "funding_paid_or_received|time_in_trade|max_adverse_excursion|max_favorable_excursion|barrier_hit_type|label_exit_time_ms|realized_net_return" src tests docs/tradingbotsuite_runtime
```

Requested tasks:

- Add or verify tests for funding sign by trade direction.
- Add or verify tests that MFE/MAE stop at the actual exit bar and do not include post-exit bars.
- Add or verify tests that `label_exit_time_ms` drives purge behavior.
- Write this artifact.

# Files read

- `src/tradingbotsuite/research/dataset.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `tests/tradingbotsuite/test_research.py`
- `tests/tradingbotsuite/test_hmm_knn.py`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_AGENT_RUNBOOK.md`
- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_MODEL_SPEC.md`
- prior Labeling Agent artifacts under `docs/tradingbotsuite_runtime/agent_artifacts/`

# Files changed

- `tests/tradingbotsuite/test_research.py`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_labeling_agent_cost_exit_accounting_hardening.md`

# Commands/tests run

Initial requested pytest command before adding the new hardening tests:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
```

Result:

```text
................................                                         [100%]
32 passed in 7.68s
```

Requested search command:

```powershell
rg -n "funding_paid_or_received|time_in_trade|max_adverse_excursion|max_favorable_excursion|barrier_hit_type|label_exit_time_ms|realized_net_return" src tests docs/tradingbotsuite_runtime
```

The search found existing implementation and tests for label outcome fields, realized net return, and `label_exit_time_ms` purge. It also showed that the requested `tests/tradingbotsuite` suite did not yet directly assert funding direction sign or post-exit MFE/MAE exclusion.

Final requested pytest command after hardening:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
```

Result:

```text
..................................                                       [100%]
34 passed in 8.48s
```

Final requested search command was rerun after hardening and now includes:

- `tests/tradingbotsuite/test_research.py::test_funding_paid_or_received_uses_trade_direction_sign`
- `tests/tradingbotsuite/test_research.py::test_label_mfe_mae_stop_at_actual_exit_bar`
- `tests/tradingbotsuite/test_hmm_knn.py::test_hmm_knn_walk_forward_uses_label_exit_time_for_purge`

# Hardening changes

## Funding sign by trade direction

Added `test_funding_paid_or_received_uses_trade_direction_sign` in `tests/tradingbotsuite/test_research.py`.

Coverage:

- Positive funding rate with a long position is recorded as paid funding: `-0.00040`.
- Positive funding rate with a short position is recorded as received funding: `0.00040`.
- Missing funding rate remains `None` instead of being fabricated.

Implementation audited:

- `src/tradingbotsuite/research/dataset.py::_funding_paid_or_received`
- Formula: `-(direction_sign * funding_rate * time_in_trade_hours / 8)`
- Direction sign: long `+1`, short `-1`.

## MFE/MAE stop at actual exit bar

Added `test_label_mfe_mae_stop_at_actual_exit_bar` in `tests/tradingbotsuite/test_research.py`.

Coverage:

- First future bar hits take profit.
- Second future bar contains extreme high/low values that would change MFE/MAE if post-exit bars were incorrectly included.
- Assertions prove accounting stops at the actual exit bar:
  - `exit_time_ms == 1_800_000`
  - `time_in_trade == 0.25`
  - `time_in_trade_bars == 1`
  - `max_favorable_excursion == 1.1`
  - `max_adverse_excursion == 0.2`

Implementation audited:

- `src/tradingbotsuite/research/dataset.py::_label_from_future_bars`
- The loop updates MFE/MAE for the current bar, evaluates exit on that same bar, and immediately returns `LabelOutcome` on the first exit condition.
- Post-exit bars are not visited after return.

## label_exit_time_ms drives purge behavior

Verified existing test in `tests/tradingbotsuite/test_hmm_knn.py`:

- `test_hmm_knn_walk_forward_uses_label_exit_time_for_purge`

Coverage:

- Constructs a dataset with `label_exit_time_ms = tv_bar_time_ms + 12 bars`.
- Asserts first test row starts after max train label exit time plus `purge_embargo_bars`.

Implementation audited:

- `src/tradingbotsuite/research/hmm_knn.py::_walk_forward_frames`
- When `label_exit_time_ms` is present, test start is moved beyond the maximum train label exit time plus embargo.
- If `label_exit_time_ms` is absent, the existing row embargo fallback remains in effect.

# Related accounting already covered

Existing tests continue to cover:

- `_prepare_dataset()` preserves real label outcome fields.
- `realized_net_return_after_costs` uses `gross_return`, fees, slippage, and funding.
- `barrier_hit_type`, MFE/MAE, and time fields remain public label outcome fields.
- No label outcome fields are listed in HMM/KNN manifest `feature_columns`.

# Notes on worktree state

`tests/tradingbotsuite/test_research.py` already had broader uncommitted changes before this hardening pass, including dataset-builder context and HMM/KNN dataset consumption tests. This hardening pass added only the direct funding-direction and post-exit MFE/MAE tests plus the helper imports needed for them.

# Final finding

The requested cost and exit accounting hardening is complete:

- Funding sign by trade direction is directly tested in the requested test suite.
- MFE/MAE stopping at the actual exit bar is directly tested in the requested test suite.
- `label_exit_time_ms` purge behavior was already tested and remains green.
- The exact requested pytest command passes with `34` tests.
