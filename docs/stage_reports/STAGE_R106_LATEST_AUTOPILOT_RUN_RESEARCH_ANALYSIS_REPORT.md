# Stage R106 Latest Autopilot Run Research Analysis Report

Date: 2026-06-07
Work packet: `docs/work_packets/WPR106-67-latest-autopilot-run-research-analysis.md`

## Boundary

This report interprets local research artifacts only. It does not create or
validate candidate packs, live signals, paper-ready evidence, sizing behavior,
runtime-mode changes, or promotion-ready claims. All referenced artifacts remain
`research_only`, `observe_only`, and `promotion_ready: false`.

## Runs Compared

Latest run:

- Job id: `run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e`
- Manifest:
  `data/research/operator_runs/research_autopilot/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e/research_autopilot_manifest.json`
- Started: `2026-06-05T00:08:38.239348+00:00`
- Updated/completed: `2026-06-07T13:12:11.557559+00:00`
- Status: `completed`
- Execution status: `executed_upstream_compute`
- Status detail: `forced_upstream_recompute_executed`
- Requested symbols: BTCUSDT, ETHUSDT
- Forced upstream recompute: true
- Executed steps: 12
- Upstream executed steps: 4
- Downstream executed steps: 8
- Eligibility executed steps: 2
- Candidate pack written: false

Chronological previous autopilot run:

- Job id: `run-research-autopilot-93c17f8f75b742ceba023cba6fea3c5b`
- Status: `failed`
- Execution status: `failed`
- Status detail:
  `historical_research_cycle unknown schema keys: operator_job_id, operator_original_spec_path, operator_overwrite_protection`
- Started: `2026-06-04T18:26:56.098288+00:00`
- Updated: `2026-06-04T18:26:57.663984+00:00`
- Forced upstream recompute: true
- Upstream executed steps: 0

Previous reuse-review run:

- Job id: `run-research-autopilot-ccd44aee842b4cb488656565c92e2998`
- Status: `completed`
- Execution status: `reused_existing_evidence`
- Started: `2026-06-04T17:37:42.919890+00:00`
- Updated: `2026-06-04T17:37:44.467808+00:00`
- Forced upstream recompute: false
- Executed steps: 0
- All 13 autopilot steps skipped as already complete/current evidence.

## Operational Delta

The latest run is a real forced upstream compute iteration. It proves the
WPR106-66 historical-cycle schema handoff fix at operator-run scale: the prior
forced run failed before BTC cycle compute; the latest run got through BTC and
ETH historical cycles, exact discovery, analysis, deltas, exit labs, and
eligibility.

Approximate step timing from manifest timestamps:

| Step | Symbol | Result | Time from Prior Step |
| --- | --- | --- | ---: |
| Historical data catalog | - | skipped, catalog ready | - |
| Historical cycle | BTCUSDT | executed | 103.1 minutes |
| Exact discovery | BTCUSDT | executed | 1561.7 minutes |
| Historical cycle | ETHUSDT | executed | 184.4 minutes |
| Exact discovery | ETHUSDT | executed | 1811.9 minutes |
| BTC downstream analysis/delta/exit/eligibility | BTCUSDT | executed | about 1.0 minute |
| ETH downstream analysis/delta/exit/eligibility | ETHUSDT | executed | about 1.1 minutes |

The expensive part is still exact discovery. BTC exact discovery recorded
`elapsed_seconds: 92630.45499`; ETH recorded `elapsed_seconds: 107330.236765`.
Both requested 48 process workers but were capped to 8 by
`default_real_discovery_process_worker_cap`.

## Historical Cycle Findings

Latest BTC cycle manifest:

`data/research/operator_runs/historical_cycles/r105-btcusdt-durable-public-archive-candidate-depth-v1/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-btcusdt-cycle/research_cycle_manifest.json`

Latest ETH cycle manifest:

`data/research/operator_runs/historical_cycles/r105-ethusdt-durable-public-archive-candidate-depth-v1/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-ethusdt-cycle/research_cycle_manifest.json`

Both cycles:

- Candidate rows: 63
- Rejected candidates: 63
- Positive net-return candidates: 0
- Positive costed-expectancy candidates: 0
- Candidate pack written: false
- Backend used: `vector_fixed_holding` for all candidates
- Exit policy tested: `fixed_holding_window` only
- Strategy mix: 20 `volatility_breakout_v1`, 20 `range_reversion_v1`,
  15 `trend_following_v1`, 8 `baseline_no_trade`
- Feature mix: 59 `features_price_trend_vol`, 4
  `features_price_trend_vol_wt3d`
- Holding windows: 1h, 4h, 12h, 24h

Best non-baseline BTC row by net return and costed expectancy:

- Strategy: `volatility_breakout_v1`
- Feature set: `features_price_trend_vol`
- Holding window: 24h
- Trade count: 1950
- Costed expectancy: `-0.0006941928185695372`
- Net return after fees/slippage/funding: `-0.9023026198240086`
- Max drawdown: `-0.9519402043969919`
- Final score: `-1.85493701703957`
- Rank: 9

Best non-baseline ETH row by net return and costed expectancy:

- Strategy: `trend_following_v1`
- Feature set: `features_price_trend_vol`
- Holding window: 24h
- Trade count: 2053
- Costed expectancy: `-0.00036799607102412933`
- Net return after fees/slippage/funding: `-0.9187036959022561`
- Max drawdown: `-0.9651114877688433`
- Final score: `-1.8841831797421236`
- Rank: 9

Dominant cycle blockers:

- `no_trade_baseline_not_beaten`: all 63 rows per symbol
- `cost_stress_survival_rate_below_floor`: all 63 rows per symbol
- `stability_region_accepted_decision_required`: all 63 rows per symbol
- `stability_region_validation_enriched_required`: 55 rows per symbol
- `stability_region_split_cost_stress_scope_required`: 55 rows per symbol
- `split_and_cost_stress_evaluation_reserved_for_shortlist`: 47 rows per
  symbol
- `candidate_split_evidence_required`: 47 rows per symbol
- `cost_stress_scenario_set_incomplete`: 47 rows per symbol

Interpretation:

The historical-cycle result is stable negative evidence for the currently
tested transparent fixed-holding surface. It says the current fixed-holding
trend/range/volatility families do not beat no-trade after costs/stress on the
candidate-depth BTC/ETH archives. The 24h variants are "least bad", not
screen-worthy. Further research should not spend effort polishing these exact
fixed-holding candidates into eligibility; they need a different entry surface,
exit surface, or context filter.

## Exact Discovery Findings

Latest BTC exact discovery manifest:

`data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-candidate-depth-v1/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-btcusdt-discovery/discovery_run_manifest.json`

Latest ETH exact discovery manifest:

`data/research/operator_runs/discovery_runs/exact-entry-sweep-ethusdt-candidate-depth-v1/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-ethusdt-discovery/discovery_run_manifest.json`

Both discovery manifests record:

- `completed_trials: 570240`
- `blocked_candidates: 570240`
- `interesting_candidates: 0`
- `filter_blockers: 0`
- Candidate pack written: false

The blocked ledgers show:

- BTC `blocker_code` counts: `trial_execution_error: 570240`
- ETH `blocker_code` counts: `trial_execution_error: 570240`
- Feature set distribution is balanced at 285120 rows each for
  `price_trend_vol` and `compact_wt3d_base`
- Label horizon distribution is balanced at 190080 rows each for `1h`, `2h`,
  and `4h`

Sampled trial files across both symbol runs, including `trial-000001`,
`trial-001000`, `trial-050000`, `trial-100000`, `trial-250000`,
`trial-400000`, and `trial-570240`, all have:

- `status: failed`
- `blocker_code: trial_execution_error`
- `error_payload.error: regime_model_backend must match regime_mode`
- `regime_mode: none`
- `regime_detector_type: none`
- `regime_model_backend: none`
- `regime_gate_enabled: false`
- `same_regime_neighbor_pool_enabled: false`

A direct current-checkout no-regime `KnnStudySpec` validation passes, so this
report does not assign root cause to the validator itself. The evidence points
to a no-regime exact-discovery runtime path or accounting path that must be
reproduced in a focused packet.

This is now registered as:

`ISSUE-R106-019: Forced no-regime exact discovery produces failed trial ledgers`

Interpretation:

The latest exact-discovery outputs are operational evidence that autopilot can
launch long isolated discovery jobs, but they are not analytically valid lead
evidence. They should not be used for lead selection, exit labs, validation
floors, multiple-testing materialization, candidate-pack eligibility, or
promotion claims. Re-running the same full exact specs before fixing
`ISSUE-R106-019` would likely waste another multi-day compute window.

## Delta Findings

Latest BTC delta:

`data/research/operator_runs/analysis_deltas/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-btcusdt-analysis-delta/research_analysis_delta.json`

Latest ETH delta:

`data/research/operator_runs/analysis_deltas/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-ethusdt-analysis-delta/research_analysis_delta.json`

Cycle deltas are unchanged for both symbols:

- Candidate count delta: 0
- Best pure ROI delta: 0.0
- Best trade Sortino delta: 0.0
- Positive costed-expectancy count delta: 0
- Positive pure-ROI count delta: 0
- Pack eligible count delta: 0

Discovery deltas:

- BTC interesting candidates delta: `-22560.0`
- BTC interesting rate delta: `-0.03956228956228956`
- BTC top blocker shift includes `trial_execution_error: +570230`
- ETH interesting candidates delta: `-23040.0`
- ETH interesting rate delta: `-0.04040404040404041`
- ETH top blocker shift includes `trial_execution_error: +570240`

Interpretation:

The cycle delta is valid negative evidence: fixed-holding cycle quality did not
improve. The discovery delta should be treated as a runtime-regression signal,
not as proof that the KNN discovery search surface got worse. The prior
discovery evidence had many filter/quality blockers such as overlap ratio and
signal-rate ceilings; the latest run replaces those with execution errors.

## Exit Lab And Eligibility

Latest BTC exit lab:

`data/research/operator_runs/frozen_entry_exit_lab/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-btcusdt-frozen-entry-exit-lab/discovery_exit_lab_manifest.json`

Latest ETH exit lab:

`data/research/operator_runs/frozen_entry_exit_lab/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-ethusdt-frozen-entry-exit-lab/discovery_exit_lab_manifest.json`

Both exit labs:

- `blocked_reason: interesting_candidates_missing`
- Selected lead count: 0
- Comparison count: 0
- Candidate gate row count: 1
- Candidate pack written: false

Latest BTC eligibility:

`data/research/operator_runs/candidate_pack_eligibility/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-btcusdt-eligibility/candidate_pack_eligibility_manifest.json`

Latest ETH eligibility:

`data/research/operator_runs/candidate_pack_eligibility/run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e-ethusdt-eligibility/candidate_pack_eligibility_manifest.json`

Both eligibility manifests:

- Row count: 0
- Eligible count: 0
- Candidate pack written: false
- `gate_manifest_selection: missing_gate_manifests_fail_closed`
- Candidate universe status: `cycle_ranking_candidates_missing`
- Ranking overlap count: 0
- Multiple-testing manifest path: null
- Validation-floor manifest path: null

Interpretation:

The downstream fail-closed behavior is correct. With no valid discovery leads,
exit lab has nothing to compare, and eligibility should not attach stale
multiple-testing or validation-floor evidence to a fresh failed discovery run.
The `cycle_ranking_candidates_missing` wording is misleading in this run because
cycle rankings do exist; the practical cause is that the latest discovery
candidate universe is empty. That wording can be clarified in a later operator
truthfulness packet, but it is not the primary blocker.

## Useful Research Directions

1. Fix discovery runtime before more exact sweeps.

   Open a focused packet for `ISSUE-R106-019`. Use a bounded no-regime exact
   discovery fixture/spec that executes representative combinations and asserts
   trial records are `completed`, not merely persisted. Also harden manifest
   counts so `completed_trials` means successful trial execution, while failed
   durable records are counted separately.

2. Add exact-discovery preflight before 570240-trial sweeps.

   Run a small representative preflight per symbol before full exact discovery:
   both feature sets, all label horizons, a few K values, all active regime
   modes, and representative distance/threshold settings. The full run should
   not start if any preflight trial writes `trial_execution_error`. This would
   have caught the latest issue in minutes instead of consuming about 55 hours
   of discovery runtime.

3. Do not expand KNN search width until the current exact-discovery path is
   clean.

   The older valid discovery evidence was dominated by overlap and signal-rate
   blockers, meaning many KNN entries were too dense or insufficiently
   independent. After the runtime fix, research should bias toward sparser
   event construction, stronger event spacing/cooldown, side-balance controls,
   and independent-event accounting rather than simply adding more thresholds.

4. Treat fixed-holding transparent families as negative controls.

   BTC and ETH both reject all 63 fixed-holding cycle candidates, with no
   positive costed expectancy. Future strategy work should use these families
   as comparators and controls, not as the next candidate-pack target.

5. Move research energy into exit and context surfaces.

   The current cycle only tests fixed holding. Useful next surfaces are:
   lower-timeframe or primary-bar exit policies, cost-stressed exit selection,
   orderflow/aggTrade features, funding/OI context, liquidation context where
   durable evidence exists, BTC/ETH cross-asset residual context, and
   modern-window regime profiles. These should be evaluated against simple
   transparent baselines before being combined with KNN overlays.

6. Re-run exit labs only after valid discovery leads exist.

   The latest exit labs are blocked because the fresh discovery ledgers have no
   interesting candidates. Reusing older leads can still be useful for method
   research, but any fresh run-to-run conclusion must wait until exact discovery
   produces successful interesting ledgers again.

7. Separate full-window and modern-window conclusions.

   The candidate-depth archives cover a long crypto regime span. The full-window
   fixed-holding result is negative, but future work should also profile modern
   windows to avoid letting early-market behavior dominate current-regime
   interpretation. Modern-window evidence still must remain research-only until
   the same gates pass.

8. Keep discovery-to-cycle overlay alignment explicit.

   Older eligibility evidence already showed discovery/cycle identity mismatch
   problems. Once discovery is valid again, do not expect raw discovery IDs to
   overlap static cycle rankings. Materialize candidate-scoped overlays or specs
   that make discovery leads representable in historical-cycle evidence before
   asking the candidate-pack bridge for eligibility.

## Decision

The latest autopilot run is operationally useful and research-boundary safe:
it completed a forced upstream compute sequence without writing a candidate
pack or promotion claim. It is not a successful empirical strategy iteration.

The historical-cycle part is valid negative evidence against the current
fixed-holding transparent candidate surface. The exact-discovery part is a
blocking runtime/accounting regression and must not be used as lead evidence.
Further research should first fix and preflight exact discovery, then rerun a
bounded clean discovery pass before investing in exit labs, validation floors,
or candidate-pack bridge work.

## Validation

No source-code validation was required for this documentation-only packet.
Evidence was gathered by parsing the autopilot manifests, linked JSON manifests,
Parquet ledgers, sampled trial JSONs, and a direct no-regime `KnnStudySpec`
validation check with `PYTHONPATH=src`.
