# Stage R106 Research Analytics Next Agent Handoff

Date: 2026-05-25
Work packet: `docs/work_packets/WPR106-13-research-analysis-handoff-and-analytics-step.md`
Branch role: research/experimentation only

## Boundary

This handoff is research-only. Nothing here is a live signal, promotion claim,
runtime-mode change, order-placement path, or sizing recommendation. Every
artifact discussed remains `research_only`, `observe_only`, and
`promotion_ready: false` unless a later promotion process proves otherwise.

## Operator Intent Compiled

The operator does not want another long BTC/ETH discovery run that ends with a
large but hard-to-use artifact pile. The desired system is an iterative research
machine:

- one command or master UI button can run the useful BTC/ETH research sequence
  without intervention;
- completed data is reused and never discarded unless corrupt;
- every long run produces analysis that explains which feature sets, KNN
  settings, filters, exits, and data windows helped or failed;
- run-to-run comparisons show whether a mutation improved the research process;
- Sortino ratio and pure ROI are the main performance metrics, with trade count,
  independent events, drawdown, cost-stress survival, and split consistency used
  as guardrails;
- the system stays open to drastic research changes, new venues, and new
  feature/filter families.

The next agent should treat this as a research-product problem, not only a
compute problem. A fast run that produces ambiguous evidence is not enough.

## New Analysis Step

WPR106-13 adds a repeatable analysis helper:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.research_discovery.analysis_report --cycle <historical-cycle-output-dir> --discovery <exact-discovery-output-dir> --out <analysis-output-dir>
```

For the current BTC artifacts it was run as:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.research_discovery.analysis_report --cycle data\research\operator_runs\historical_cycles\r105-btcusdt-durable-public-archive-candidate-depth-v1\run-historical-research-cycle-3f12dcdc483945cfa753e4eb00d42280 --discovery data\research\operator_runs\discovery_runs\exact-entry-sweep-btcusdt-candidate-depth-v1 --out data\research\operator_runs\analysis\r106_btc_current_analysis
```

Outputs:

- `data/research/operator_runs/analysis/r106_btc_current_analysis/research_analysis.json`
- `data/research/operator_runs/analysis/r106_btc_current_analysis/research_analysis.md`

The helper summarizes:

- historical-cycle feature-set, strategy, exit-policy, and holding-window
  performance;
- pure ROI through `net_return_after_fees_slippage_funding`;
- trade-level Sortino when aggregate trade ledgers are available;
- gate and ranking blocker reason counts;
- split summary;
- exact-discovery feature-column-set, label-horizon, KNN, and filter-setting
  summaries;
- discovery blocker counts and top interesting rows.

This should become a mandatory post-run step for both BTC and ETH before the
next mutation is chosen.

## Current BTC Evidence

Historical cycle:

- Path:
  `data/research/operator_runs/historical_cycles/r105-btcusdt-durable-public-archive-candidate-depth-v1/run-historical-research-cycle-3f12dcdc483945cfa753e4eb00d42280`
- Symbol: `BTCUSDT`
- Candidate count: `63`
- Candidate pack written: `false`
- Pack eligible candidates: `0`
- Positive pure ROI candidates: `0`
- Positive costed expectancy candidates: `0`
- All candidates are blocked/fail-closed.
- Active exit policy in this cycle: `fixed_holding_window` only.
- Best non-baseline pure ROI is still negative, about `-0.902303`.
- Best non-baseline costed expectancy is still negative, about
  `-0.000694193`.

The BTC brute-force cycle did not bring a tradable or promotion-ready candidate
to the table. It did bring useful falsification evidence: current fixed-holding
families on the active feature sets are not enough.

Exact discovery:

- Path:
  `data/research/operator_runs/discovery_runs/exact-entry-sweep-btcusdt-candidate-depth-v1`
- Completed trials: `570240/570240`
- Interesting rows: `22560`
- Blocked rows: `547680`
- Filter-blocked rows: `0`
- Exact ledgers were repaired from durable trial JSONs after a final Parquet
  dtype failure.

Discovery leaders from the current analysis:

- `compact_wt3d_base` had `11520/285120` interesting rows
  (`~4.04%`).
- `price_trend_vol` had `11040/285120` interesting rows (`~3.87%`).
- Strongest KNN setting cluster by interesting rate is no-regime `1h`,
  `k=34`, especially cosine/manhattan distance.
- Best realized-expectancy maxima are small:
  `compact_wt3d_base` about `0.00042502`,
  `price_trend_vol` about `0.000340502`.
- Top final-score rows are not top realized-expectancy rows; analysis must keep
  ROI/Sortino primary rather than trusting density scores alone.

Discovery blockers:

- `overlap_ratio_above_ceiling`: `237162`
- `signal_rate_above_discovery_ceiling`: `210886`
- `signal_rate_near_ceiling`: `99622`
- `trial_execution_error`: `10`

The ten trial execution errors were MemoryError-shaped rows and should be
retried or explicitly marked as accepted residual error before the BTC exact
ledger is called analytically clean.

## Data Fullness

The central catalog is now the data source of truth. The completed BTC cycle
used the Binance Vision public archive candidate-depth fixture:

- primary bars: `221952` 15m rows;
- window: `2020-01-01T00:00:00Z` through `2026-04-30T23:45:00Z`;
- lower-timeframe bars: about `3.33M`;
- aggTrades: about `3.29M`;
- duplicate/gap checks for primary 15m bars passed in prior validation;
- checksum-verified monthly archive coverage is present.

This is materially better than the old compact R104 screening fixtures. It does
not resolve the operator's market-regime concern by itself. A full 2020-2026
window can let early crypto market structure dominate results. The next research
autopilot should run both:

- full-window evidence for long-horizon robustness;
- modern-window evidence, at minimum a 2024-01 through 2026-04 profile, for
  current-market relevance.

Do not throw away the full archive. Add windowed specs and analysis dimensions
on top of it.

## Overfit Protection Status

The BTC cycle has overfit diagnostics, but not a clean final untouched holdout:

- split methods are purged/embargoed and anchored walk-forward;
- purge/embargo is `2` bars;
- overfit report uses proxy penalties:
  trial-count log penalty, family-rank PBO proxy, split/cost-stress CPCV proxy,
  and stability-decision penalty;
- all current candidates remain review/blocked;
- only the shortlist received heavier split/cost/stability enrichment.

This is good enough to reject weak candidates. It is not enough to promote a
candidate. Next work should add explicit frozen-entry validation with a
modern-window holdout that is not used for search tuning.

## Exit Model Status

The backtest engine and exit lab infrastructure already support many exit
families:

- fixed holding;
- triple barrier and ATR/volatility-scaled barriers;
- regime flip;
- funding/OI and basis/premium normalization exits;
- GMM transition;
- KNN remaining-edge and dynamic barrier exits;
- trailing ATR after profit;
- max-MAE stop;
- adverse-selection/alpha-decay style exits.

But the current BTC R106 cycle only evaluated `fixed_holding_window`.

The operator's previously described simple runner logic is not implemented as a
first-class exit policy. `simple_runner_v1`, `activation_pct`, `runner_gap_pct`,
and runner-step semantics appear in handoff docs but not in the backtest exit
policy registry. The closest existing policy is `trailing_atr_after_profit`,
which is not the same as a simple pct activation/gap runner.

Next agent should implement or configure a frozen-entry exit lab before running
more giant entry sweeps:

1. Select strongest exact-discovery entry rows by pure ROI proxy,
   realized expectancy, event count, and side balance.
2. Freeze entries.
3. Compare fixed holding versus simple runner, barrier, KNN remaining-edge,
   KNN dynamic barrier, basis/premium normalization, funding/OI, and trailing
   risk exits.
4. Rank by Sortino and pure ROI, not only final discovery score.
5. Keep split, cost-stress, and holdout labels explicit.

## KNN And Filter Status

KNN is not dead, but it is not proven. The exact BTC sweep generated many
interesting rows, mostly no-regime `1h` KNN configurations, but the strongest
realized edge is small and the blocker distribution shows density/overlap
problems.

Current active exact-discovery feature-column sets:

- `price_trend_vol`
- `compact_wt3d_base`

Current active exact-discovery did not use orderflow feature sets, HMM-backed
regime filters, or wider feature/filter ablation families.

Needed KNN analytics:

- compare KNN settings by feature set, distance metric, horizon, `k`,
  `min_neighbor_count`, probability threshold, vote margin, and density filters;
- measure how overlap, side collapse, and signal-rate filters correlate with
  Sortino and pure ROI after an exit model is applied;
- group candidate families by prediction signatures to avoid rerunning duplicate
  behavior;
- compare no-regime KNN against GMM/HMM/regime-local variants only after simple
  no-regime entries survive frozen-entry exit tests.

The new analysis helper starts this grouping, but it does not replace a full
feature/filter ablation lab.

## Orderflow Status

AggTrade orderflow feature infrastructure exists from earlier R94 work. It
includes proxy features such as taker-buy quote share, signed quote imbalance,
sqrt signed imbalance, CVD slope, quote-volume/trade-count z-scores,
large-trade imbalance, burst, sweep proxy, and quality columns.

Current BTC R106 active cycle and exact-discovery specs did not include those
orderflow feature sets. Therefore the current BTC outcome says nothing strong
about orderflow usefulness.

Next work should add matched orderflow ablations only after a simple entry/exit
baseline is alive enough to compare. Otherwise orderflow adds search surface
without making the artifacts more interpretable.

## Provider And Catalog Direction

The central historical data catalog is the right architecture. It should remain
the only source of truth for active data readiness and generated specs.

Current implemented candidate-depth path:

- Binance Vision public archives.

Visible but not fully implemented/provider-ready expansion paths:

- Bybit archives/API;
- Hyperliquid archives;
- Crypto Lake or paid vendor paths where credentials and license terms allow.

Future provider work should add data into the catalog through the same contracts:

- source provider and venue metadata;
- interval/family coverage;
- checksum/hash/provenance evidence where possible;
- gap and duplicate checks;
- row counts;
- fixture-pack manifest references;
- research-only and promotion flags.

Do not create one-off data buttons or hidden side sources. Add providers behind
the catalog and let research jobs consume the catalog output.

## UI And Operator Workflow

The current Research UI is usable but still too slow and too job-history heavy
for day-long research. The UI should be treated as an operator console with a
single required workflow, not a pile of diagnostics.

Recommended UI model:

- top: one concise instruction block showing the required sequence and current
  next action;
- primary section: one master `Run Research Autopilot` button;
- required evidence cards: catalog, BTC cycle, BTC discovery, ETH cycle, ETH
  discovery, analysis, candidate eligibility;
- each card shows status, progress bar, ETA, artifact path, and one local action
  button only when manual intervention is useful;
- diagnostics/legacy/R104/R105 compatibility moved to collapsed sections;
- UI polling should use a cached progress endpoint and stop fetching every job
  detail on every refresh.

The master job should be resumable and idempotent:

1. refresh or reuse historical data catalog;
2. run missing BTC/ETH cycle jobs;
3. run missing BTC/ETH exact discovery jobs;
4. run analysis artifacts for each completed symbol;
5. run run-to-run comparison;
6. run candidate eligibility;
7. stop at the first failed required step with a clear recovery command.

## Performance And Durability Notes

Exact discovery performance improved enough to complete BTC, but the workflow
still writes and rehydrates too many artifacts. A background review of the
runner identified a specific next optimization:

- make `stop_after_trials=0` a true metadata-only resume path;
- apply zero-trial stopping before `_load_existing_trial_records()`;
- skip ledger rewrite, snapshot record hydration, and real-context preparation
  when no execution is requested;
- read existing Parquet ledger counts from metadata where possible;
- longer term, persist a compact `trial_records_index.parquet` or JSONL summary
  at write time so resume/rebuild does not require reading hundreds of thousands
  of per-trial JSON files.

This matters for the operator console because artifact-only repair and progress
refresh should be seconds, not minutes.

Performance policy from the operator: throughput is more important than perfect
stability for prolonged research, as long as durable resume works and partial
progress is not lost. Do not reduce worker caps just to make failures less
likely unless the failure loses data.

## Recommended Next Objective

Name the next work packet something like:

`WPR107-01-research-autopilot-analysis-and-frozen-entry-exit-lab`

Scope:

1. Add an operator master research job that sequences catalog reuse, BTC/ETH
   cycle, BTC/ETH exact discovery, analysis, comparison, and eligibility.
2. Add modern-window cycle/discovery specs from the same catalog data.
3. Add frozen-entry exit lab execution for top exact-discovery leads.
4. Add run-to-run delta reports comparing BTC/ETH feature sets, KNN settings,
   filters, exits, Sortino, pure ROI, blockers, and data windows.
5. Make Research UI progress cached, faster, and explicit about required versus
   diagnostic/legacy steps.
6. Add metadata-only resume and compact trial index if runner refresh remains
   slow.

Do not start by expanding the search space. First make the results from the
existing BTC run analytically useful, then run ETH through the same improved
post-run analysis.

