# Backtest Agent: Pipeline Evidence Stage Handoff

Date: 2026-04-29

## Task

Add evidence-stage orchestration without making model tuning the focus of this pass.

## Work Done

- Evidence stage can run either a single HMM/KNN research artifact or an experiment matrix when a valid dataset is available.
- If no dataset exists, evidence stage records `dataset_not_available` and skips cleanly.
- Experiment matrix support preserves existing `workers` and monitoring settings from the pipeline spec.

## Validation

`tests/tradingbotsuite/test_data_pipeline.py::test_prepare_hmm_knn_research_data_evidence_stage_skips_without_dataset` covers the safe skip path.

## Boundary

Evidence outputs remain HMM/KNN research artifacts only. They are not live signals or sizing inputs.

## Issues

No unresolved issue was added.
