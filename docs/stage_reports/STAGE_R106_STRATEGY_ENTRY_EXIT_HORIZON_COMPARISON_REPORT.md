# Stage R106 Strategy Entry Exit Horizon Comparison Report

Date: 2026-06-07
Work packet:
`docs/work_packets/WPR106-69-strategy-entry-exit-horizon-comparison.md`

## Boundary

This report compares local research-only artifacts. It does not run new
compute, rewrite generated artifacts, create candidate packs, place orders,
change live/paper runtime mode, change sizing, or make promotion-ready claims.
All referenced outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`.

## Evidence Read

Compared evidence surfaces:

- Latest forced autopilot run:
  `run-research-autopilot-1dd8e0a820a9457fb967a27c4ce1491e`.
- Previous forced autopilot run:
  `run-research-autopilot-93c17f8f75b742ceba023cba6fea3c5b`.
- Latest BTC/ETH candidate-depth historical-cycle rankings.
- Prior valid exact-discovery ledgers at
  `exact-entry-sweep-btcusdt-candidate-depth-v1` and
  `exact-entry-sweep-ethusdt-candidate-depth-v1`.
- Latest failed isolated exact-discovery ledgers from the 61-hour run.
- WPR106-31 frozen-entry exit-lab matrices and candidate gates.
- WPR106-46 exact replay-overlay cycle smokes.
- WPR106-47 full replay exit-lab audit.
- All local `candidate_rankings.parquet` files under checked historical-cycle
  and operator-run historical-cycle evidence.

## Latest Candidate-Depth Strategy Surface

The latest BTC/ETH candidate-depth historical cycles are the strongest current
evidence for transparent fixed-holding strategies:

| Symbol | Rows | Strategies | Exit | Positive Net | Positive Expectancy |
| --- | ---: | --- | --- | ---: | ---: |
| BTCUSDT | 55 non-baseline | range, trend, volatility | fixed_holding_window | 0 | 0 |
| ETHUSDT | 55 non-baseline | range, trend, volatility | fixed_holding_window | 0 | 0 |

Best current non-baseline rows:

| Symbol | Best Strategy | Horizon | Trades | Costed Expectancy | Net Return | Max DD | Final Score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | volatility_breakout_v1 | 24h | 1950 | -0.000694 | -0.902303 | -0.951940 | -1.854937 |
| ETHUSDT | trend_following_v1 | 24h | 2053 | -0.000368 | -0.918704 | -0.965111 | -1.884183 |

Horizon trend:

- `24h` is consistently least bad for current fixed-holding transparent
  strategies, but it is still strongly negative and does not beat no-trade.
- `12h` is worse than `24h` and usually approaches total loss.
- `4h` and `1h` overtrade heavily; median trade counts are roughly 7.5k and
  12k+, with net return effectively `-1.0`.
- BTC's least-bad transparent family is `volatility_breakout_v1`; ETH's is
  `trend_following_v1`. That is not a candidate-ready trend, only a negative
  control ranking.

## KNN Entry Model Surface

The latest isolated exact-discovery run is not analytically usable. BTC and ETH
each wrote 570240 blocked rows, all with `blocker_code:
trial_execution_error`. This is runtime-regression evidence only.

The prior stable exact-discovery ledgers are useful as old lead-shape evidence:

| Symbol | Interesting Rows | Interesting Horizons | Avg Final | Best Final | Avg Signal Rate | Avg Overlap |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| BTCUSDT | 22560 | 1h only | 0.462828 | 0.469263 | 0.167256 | 0.441305 |
| ETHUSDT | 23040 | 1h only | 0.462500 | 0.468973 | 0.164057 | 0.437226 |

KNN horizon trend:

- Only `1h` survived as interesting in the prior valid discovery ledgers.
- `2h` and `4h` were dominated by overlap and signal-rate blockers.
- The best recurring setting was `cosine` distance with `k=13`; larger `k`
  and non-cosine distances were weaker on final score.
- Feature sets are close. BTC favored `compact_wt3d_base` on best/average
  score; ETH had better average expectancy on `price_trend_vol`, but
  `compact_wt3d_base` still produced the best final score.

The replay-overlay cycle smoke shows why the old KNN discovery leads are not
yet tradable entries:

| Symbol | Strategy | Horizon | Exit | Trades | Costed Expectancy | Net Return | Final Score |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| BTCUSDT | hmm_knn_local_analog_filter_v2 | 1h | fixed_holding_window | 10987 | -0.001987 | -1.000000 | -2.001987 |
| ETHUSDT | hmm_knn_local_analog_filter_v2 | 1h | fixed_holding_window | 10996 | -0.001942 | -1.000000 | -2.001942 |

Interpretation: KNN discovery finds short-horizon structure, but the accepted
events are too dense and overlapping. The easy forward path is not more broad
KNN grid search; it is sparse-event construction, overlap suppression, and
entry context gating.

## Exit Model Surface

Latest exit labs from the 61-hour run have no comparison power because the
latest discovery produced no valid interesting candidates:

- BTC blocked reason: `interesting_candidates_missing`.
- ETH blocked reason: `interesting_candidates_missing`.
- Comparison count: 0.

The WPR106-31 full frozen-entry exit labs compare `simple_runner_v1` against
`fixed_holding_window` for 24 BTC and 24 ETH replayed KNN leads:

| Symbol | Gate Rows | Gate Status | Reason | Best Delta |
| --- | ---: | --- | --- | ---: |
| BTCUSDT | 24 | blocked | exit_lab_no_improving_exit_over_fixed_holding | 0.0 |
| ETHUSDT | 24 | blocked | exit_lab_no_improving_exit_over_fixed_holding | 0.0 |

Matrix comparison:

- BTC fixed holding: avg net `-1.0`, avg expectancy `-0.001921`.
- BTC simple runner: avg net `-1.0`, avg expectancy `-0.001918`.
- ETH fixed holding: avg net `-1.0`, avg expectancy `-0.001977`.
- ETH simple runner: avg net `-1.0`, avg expectancy `-0.001970`.
- Simple runner produced tiny expectancy/profit-factor nudges but no net-return
  or drawdown improvement.

Exit-model trend: do not spend the next compute budget on a broad simple-runner
exit grid. It does not rescue dense 1h KNN entries. Exit work should follow
entry thinning, or focus on genuinely different risk exits once sparse leads
exist.

## Broader Historical Strategy Scan

Across 23 local `candidate_rankings.parquet` artifacts, every row is rejected.
Older context/perp artifacts contain positive-looking rows, but they are not
candidate-depth current evidence:

| Surface | Symbol | Positive Net Rows | Best Strategy | Best Horizon | Best Exit | Best Net | Trade Count |
| --- | --- | ---: | --- | --- | --- | ---: | ---: |
| older_context | BTCUSDT | 195 | funding_crowding_fade_v2 | 72h | fixed_holding_window | 0.037995 | 1 |
| older_context | ETHUSDT | 50 | perp_basis_convergence_v2 | 72h | fixed_holding_window | 0.112280 | 5 |

Older-context trend:

- Context/funding/OI families are more interesting than transparent
  price-only families, especially at `72h` and `24h`.
- The best rows are too low-density to trust: many have 1 to 8 trades.
- All are rejected because cost-stress survival fails and/or split, side,
  regime, ablation, comparator, or stability evidence is incomplete.
- `funding_aware_exit_v1` often ties fixed holding on top rows.
  `oi_contraction_exit_v1` appears weaker overall, though it has some BTC 4h
  support.

These older context rows are useful for research direction, not for candidate
eligibility.

## Decision

There is no candidate-ready strategy in the current evidence.

Clear trends:

- Current transparent fixed-holding price strategies are a dead end as-is.
- If transparent fixed-holding is used again, keep it as a negative control;
  `24h` is the least-bad horizon.
- KNN entries show a short-horizon discovery signal, but only in a dense,
  overlapping 1h form that collapses under fixed-holding backtest.
- Simple runner exits do not fix dense KNN entries.
- Older context/funding/OI strategies are the most plausible next research
  direction, but only with strict trade-count, comparator, split, and
  cost-stress evidence.

Lowest-compute next phase:

1. Run the reduced 3456-trial no-regime exact-discovery phase only after the
   WPR106-68 preflight blocks invalid runtime paths.
2. Bias discovery toward the old valid `1h`, `cosine`, `k=13` neighborhood,
   but add sparse-event and overlap-thinning constraints before exit labs.
3. Defer `2h`/`4h` KNN expansion until signal-rate and overlap blockers are
   reduced on the 1h surface.
4. Add a bounded current-candidate-depth context/perp retest focused on
   `perp_basis_convergence_v2`, `funding_crowding_fade_v2`,
   `funding_window_timing_v1`, and `oi_flow_breakout_v2`, with high minimum
   trade-count floors and required ablation/comparator evidence.
5. Treat `funding_aware_exit_v1` and `fixed_holding_window` as the first exit
   comparison for context/perp retests; do not prioritize `simple_runner_v1`
   until entries are sparse enough that exits can matter.

This path cuts compute by avoiding broad failed surfaces: no more full-grid
570240-trial discovery attempts, no broad simple-runner exit expansion, and no
large transparent fixed-holding search unless it is explicitly a control.
