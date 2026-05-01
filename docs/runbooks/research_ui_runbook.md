# Research UI Runbook

Stage: Stage 9 - Research UI and operator command layer

## Purpose

The research UI exposes research artifacts, experiment comparisons, diagnostics, and explicit research job actions. It is not a strategy implementation path and does not control live runtime mode.

## Entry Point

```python
from tradingbotsuite.ui.research_app import create_research_app
```

Mount or serve the returned FastAPI app for research-only review.

## Safety Rules

- UI routes are passive/read-only except explicit `/research/api/jobs/run-research-experiment` submissions.
- Research jobs are queued and visible at `/research/jobs` and `/research/api/jobs`.
- Displayed experiment metrics include manifest paths so every value can be traced to an artifact.
- The UI module must not import live execution adapters or live order placement code.
- Passive polling must not launch heavy jobs.

## Pages

- `/research`
- `/research/data-quality`
- `/research/datasets`
- `/research/features`
- `/research/backtests`
- `/research/experiments`
- `/research/equity`
- `/research/trades`
- `/research/regimes`
- `/research/knn-neighbors`
- `/research/promotion-candidates`
- `/research/jobs`
