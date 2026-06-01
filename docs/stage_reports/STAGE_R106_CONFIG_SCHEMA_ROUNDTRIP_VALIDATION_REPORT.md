# Stage R106 Config Schema And Roundtrip Validation Report

Date: 2026-05-31

Work packet: `docs/work_packets/WPR106-41-config-schema-roundtrip-validation.md`

## Scope

Added parser-level schema guards and roundtrip tests for active
historical-cycle and discovery-run JSON specs. This was config-boundary
hardening only.

This packet did not add strategies, filters, models, live/paper behavior,
order placement, promotion logic, candidate gate changes, or generated
research artifacts.

## Changes

- Added versioned schema summaries for historical-cycle and discovery-run
  specs.
- Historical-cycle specs now reject wrong `spec_version` values and unknown
  active parser fields in owned sections such as `data`, `features`,
  `validation`, `optimizer`, `compute`, and `exits`.
- Discovery-run specs now reject wrong `spec_version` values and unknown active
  parser fields, including top-level, `data`, `search`, `execution`, `budget`,
  and trial-template fields.
- Historical-cycle configs retain known documentary metadata keys so existing
  safety notes, blocker notes, and work-packet annotations remain parseable.
- Added focused roundtrip tests proving `from_payload(to_payload())` preserves
  effective parser contracts.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\research_discovery\test_discovery_spec.py -q` passed: 69 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 434 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_discovery_feature_sets.py tests\research_discovery\test_knn_study.py tests\research_discovery\test_hmm_materialization.py tests\research_discovery\test_exit_lab.py tests\research_discovery\test_ablation_matrix.py -q` passed: 86 tests.
- `git diff --check` passed with only existing CRLF warnings.

## Boundary Statement

Schema validation is limited to active research-cycle and discovery-run parser
contracts. It does not add runtime/paper/live fields, does not reinterpret
blocked configs as accepted, and does not alter candidate gates.

## Remaining Work

The next empirical packet should route WPR106-31 replayed KNN prediction
artifacts through historical-cycle overlay, ranking, full exit lab,
multiple-testing, validation floors, and candidate-pack eligibility without
weakening gates.
