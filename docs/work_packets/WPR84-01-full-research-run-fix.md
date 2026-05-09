# WPR84-01 Full Research Run Fix

## Objective

Diagnose and fix the failed operator full-research run without weakening
research-only boundaries or rewriting the branch structure.

## Diagnosis

The latest BTCUSDT historical-cycle artifacts completed but wrote no candidate
pack. The run failed the research gate for every row. The most important false
blocker was `feature_ablation_comparator_missing`: `features_perp_context_v2`
rows were forced to prove a same-strategy `features_price_trend_vol` comparator,
but the current perp-context strategies only support `features_perp_context_v2`.

The operator "Run Full Research Review" button also queued provider, experiment,
and historical-cycle jobs, but skipped the V4 discovery run that records the
candidate ledger and blocker diagnostics.

## Allowed paths

- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/historical/test_full_cycle_local_fixture_pack.py`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/work_packets/WPR84-01-full-research-run-fix.md`
- `docs/stage_reports/STAGE_R84_FULL_RESEARCH_RUN_FIX_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a blocking risk is discovered

## Constraints

- Preserve research-only, observe-only, and promotion-ready false semantics.
- Do not import or call live order-placement adapters.
- Do not make performance or promotion claims from the checked latest-month
  fixture.
- Do not make candidate-pack gates looser for WT3D or other optional feature
  claims that have runnable comparators.

## Exit criteria

- `features_perp_context_v2` no longer fails ablation evidence solely because a
  non-runnable price-only comparator is absent.
- The full-review UI queues the V4 discovery run in addition to provider,
  experiment, and historical-cycle jobs.
- Focused historical and operator UI tests cover both changes.
- Compile and contract validation pass.
