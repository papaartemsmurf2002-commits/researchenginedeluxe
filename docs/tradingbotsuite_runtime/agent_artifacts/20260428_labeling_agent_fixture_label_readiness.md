# Labeling Agent Fixture Label Readiness

Date: 2026-04-28

## Scope

Verified that fixture/E2E research artifacts are realistic enough to validate the extended triple-barrier label contract for the BTC-only HMM/KNN research path.

This audit focused on generated dataset parquet outputs and HMM/KNN meta-prediction artifacts for:

- `label_exit_time_ms`
- `barrier_hit_type`
- `gross_return`
- `funding_paid_or_received`
- `max_adverse_excursion`
- `max_favorable_excursion`
- `time_in_trade`
- realized costed return fields produced during HMM/KNN artifact prep

## Commands Run

Initial baseline before the focused fixture readiness assertion:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
```

Result:

```text
35 passed in 13.70s
```

Search command:

```powershell
rg -n "label_exit_time_ms|barrier_hit_type|gross_return|funding_paid_or_received|max_adverse_excursion|max_favorable_excursion|time_in_trade" tests src docs/tradingbotsuite_runtime
```

The search confirmed implementation, unit coverage, and prior audit artifacts referenced the extended label fields, but the E2E fixture contract test did not yet assert that generated artifact rows contained populated label outcome values.

Final verification after the focused fixture/test adjustment:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_research.py tests/tradingbotsuite/test_hmm_knn.py -q
```

Result:

```text
36 passed in 13.56s
```

The final search command also found the new E2E assertions in `tests/tradingbotsuite/test_research.py` covering the required label fields.

## Fixture Readiness Findings

The existing E2E fixture already generated a non-trivial BTC research dataset:

- alternating long and short synthetic signals
- both accepted and rejected labels via `label_accept`
- HMM/KNN meta-prediction artifacts from the generated dataset

However, the E2E contract validation was too weak because it only checked high-level artifact presence and model outputs. It did not prove that generated parquet/meta rows carried populated extended label accounting fields.

I added a focused assertion block to `test_hmm_knn_research_consumes_dataset_builder_output` that now verifies:

- the dataset-builder parquet includes all required dataset-side label outcome fields
- the generated HMM/KNN meta-prediction artifact includes the full label outcome contract
- at least one generated row has non-null values for each required label outcome field
- `max_adverse_excursion`, `max_favorable_excursion`, and `time_in_trade` contain positive realized values
- `barrier_hit_type` includes both `take_profit` and `stop_loss`, so the fixture is not validating against a single uniform exit condition
- `realized_net_return_after_costs` is present in the HMM/KNN output where costed realized returns are produced

## Contract Status

Dataset artifact contract:

- `label_exit_time_ms`: present and non-null in generated rows
- `barrier_hit_type`: present and non-null in generated rows
- `gross_return`: present and non-null in generated rows
- `funding_paid_or_received`: present and non-null in generated rows
- `max_adverse_excursion`: present and non-null in generated rows
- `max_favorable_excursion`: present and non-null in generated rows
- `time_in_trade`: present and non-null in generated rows

HMM/KNN meta artifact contract:

- preserves dataset-provided label outcome fields
- includes `realized_net_return_after_costs`
- keeps label outcome fields auditable in outputs
- does not require label outcome fields as model features

## Files Changed

- `tests/tradingbotsuite/test_research.py`
  - Strengthened the E2E dataset-to-HMM/KNN artifact test with explicit generated-row label contract assertions.

## Conclusion

The fixture/E2E path is now realistic enough for label contract validation. It produces populated extended label fields, includes non-uniform barrier outcomes, and verifies that HMM/KNN artifacts preserve cost and exit accounting fields needed for downstream audit.
