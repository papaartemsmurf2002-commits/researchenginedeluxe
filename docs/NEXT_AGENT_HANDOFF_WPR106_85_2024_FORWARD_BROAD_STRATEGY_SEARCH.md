# WPR106-85 Next Agent Handoff - 2024-Forward Broad Strategy Search

Date: 2026-06-10

## Current State

WPR106-84 closed the one-sided side-veto gate representation blocker for the
optimized BTCUSDT aggTrade sparse lead. The gate can now represent declared
one-sided `sparse_event_filter_v1` rows only when paired opposite-side
controls, no-trade and transparent baselines, feature ablation, split/cost/
stability evidence, and research-only provenance are present.

The optimized BTCUSDT aggTrade sparse lead:

`941c7d1a1a3b8669c66e816ee465dc30cf18b1fba56c54b95555a027cdf046d6`

has complete side-veto/control/ablation/cost/stability evidence, but remains
rejected. It fails because split profit concentration is too high:

- aggregate net return after cycle costs: +20.174216043772766;
- aggregate trades: 319;
- split-01: 109 trades, +1.639084 net return, -0.188289 max drawdown;
- split-02: 121 trades, +0.039327 net return, -0.370509 max drawdown;
- max single split PnL share: 0.9765691016445411;
- final decision: rejected with `max_single_split_pnl_share_above_limit`.

This is useful negative evidence. Do not spend the next packet trying to force
this exact candidate through the gate. Use it as one reference point while
broadening the strategy search.

## Updated Overall Goal

Find a genuinely robust, research-only crypto strategy candidate by running a
broader 2024-forward search across old and new strategy families, with a hard
May 2026 holdout benchmark for promising leads. The next step is not to defend
one existing lead. It is to test many plausible families, fix or extend code
where the math or implementation blocks fair testing, allocate compute
intelligently, and reject families only after they have been given a serious
parameter, filter, feature, and execution-model search.

The target strategy profile is:

- positive after realistic fees, slippage, spread, and available funding costs;
- stable across months, with ideally zero to two losing months per year;
- not dependent on one regime, one short burst, or one validation split;
- able to tolerate normal active trading frequency, including 1 to 5 entries
  per day when the logic calls for it;
- supported by split, monthly, cost-stress, ablation, side/control, stability,
  and no-trade/transparent baseline evidence before any eligibility claim;
- research-only until all gates pass.

## Mandatory First Steps

Before coding, the next agent must:

1. Read `AGENTS.md`.
2. Read `docs/ORCHESTRATOR_STAGE_LEDGER.md`.
3. Read `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`.
4. Read:
   - `docs/stage_reports/STAGE_R106_SIDE_VETO_GATE_EVIDENCE_CLOSURE_REPORT.md`;
   - `docs/stage_reports/STAGE_R106_POST_SELECTION_SIDE_VETO_OPTIMIZER_REPORT.md`;
   - `docs/stage_reports/STAGE_R106_SPARSE_SIDE_VETO_VALIDATION_REPORT.md`;
   - `docs/NEXT_AGENT_HANDOFF_WPR106_82_POST_SELECTION_SIDE_VETO_OPTIMIZER.md`;
   - this handoff.
5. Write a new work packet before code or generated-evidence changes. The
   recommended packet name is
   `docs/work_packets/WPR106-85-2024-forward-broad-strategy-search.md`.
6. Keep edits inside the allowed paths declared by that packet.
7. Preserve research/live separation.

## Data Window Policy

The default research window should focus on modern market structure:

- Optimization and in-sample search window: start at 2024-01-01.
- Default optimization cutoff: 2026-04-30 23:59:59 UTC.
- Hard benchmark holdout: all of May 2026, from 2026-05-01 through
  2026-05-31 UTC.

May 2026 must not be used to tune:

- strategy choice;
- feature choice;
- threshold choice;
- filter choice;
- side-veto choice;
- exit choice;
- cost assumptions;
- model hyperparameters;
- candidate selection.

May 2026 should only be run after a lead is promising on the pre-May data. The
May benchmark must be reported separately as a holdout result and must include
trades, net return after costs, drawdown, Sortino or downside-risk metric,
monthly/day-level behavior, and whether it contradicts the in-sample story.

If a strategy family requires data that is not available back to 2024, such as
some order-flow, open-interest, liquidation, or venue-specific context
features, use the longest truthful available window. Shorter context windows
are allowed, but their limitation must be explicit in the artifact manifest,
stage report, and gate notes. Do not silently compare a short context-only
result to a full 2024-forward price-only result as if the evidence depth were
equal.

## Trade Frequency Policy

Do not reject a strategy solely because it trades often. A strategy with 1 to 5
entries per day can be normal behavior if:

- costs are applied realistically;
- trade overlap and holding-period assumptions are explicit;
- liquidity/slippage assumptions are stress-tested;
- monthly and split stability remain acceptable;
- drawdown and loss-streak behavior are tolerable.

The next search should avoid over-penalizing high-entry-count candidates at the
ranking stage. High frequency is a cost and robustness problem to test, not an
automatic disqualification. Conversely, a high trade count must not hide
clustering: report entries per day, active days, trade overlap, monthly trade
counts, and whether one event cluster drives most PnL.

## Stability Standard

For any promising lead, report at least:

- monthly net return after costs;
- number of losing months per calendar year;
- worst losing month;
- best month and its share of total PnL;
- max drawdown;
- trade count by month;
- split and regime performance;
- Sortino or equivalent downside-risk metric;
- cost-stress survival;
- no-trade and transparent baseline comparison;
- feature and filter ablations;
- stability-region evidence around nearby parameters.

The ideal lead should have zero to two losing months per year. If a strategy
has more losing months but still looks promising, the next agent may keep it as
a research lead only if it explains why the profile is still plausible, for
example strong downside control, low drawdown, or clear regime gating.

## Strategy Families To Revisit

The next packet should not stay narrowly focused on the rejected side-veto
lead. Revisit prior discarded families and test more novel variants before
declaring them dead. At minimum, consider:

- sparse event filters with different entry spacing, side gating, shock/ATR
  filters, flow confirmation, and post-selection logic;
- trend, range, volatility breakout, and transparent baseline derivatives;
- perp-context strategies using funding, open interest, liquidation, spread,
  volatility, and session/timing context;
- fixed-hold, primary-bar exit, and lower-timeframe exit variants when
  available;
- HMM/KNN and Lorentzian-space KNN variants;
- no-RSI four-bar KNN variants from the archive-backed mapping work;
- replay-overlay or discovery-lead families when representable by the current
  strategy contract;
- ensemble or veto approaches that combine simple signals only when each part
  has a clear economic reason;
- negative controls for any model-like strategy: shuffled labels, shifted
  context, no-KNN/no-regime variants, and transparent comparators.

When revisiting a discarded strategy, do not merely rerun the old settings. Try
meaningful alternatives:

- different features with a logical reason;
- different filters;
- different parameter ranges;
- different exit horizon;
- different cost assumptions inside realistic bounds;
- different regime gates;
- different side controls;
- different validation split granularity;
- different scoring function that rewards monthly stability and downside
  control, not just aggregate return.

## Lorentzian / KNN Direction

The Lorentzian-space KNN model is not frozen. The next agent may change its
code, parameters, feature construction, filter logic, and search ranges if the
work packet scopes those edits and tests them.

Acceptable Lorentzian/KNN exploration includes:

- alternative feature vectors with explicit logic;
- different distance weighting or neighbor aggregation;
- different `k`, lookback, spacing, threshold, and confidence settings;
- regime-aware and no-regime variants;
- volatility/session/funding/OI filters before or after KNN scoring;
- label horizon and event-end changes if split purge remains correct;
- CUDA, vectorized, multiprocessing, or caching improvements when they preserve
  deterministic evidence and artifact identity.

Do not assume the previous KNN rejection proves the whole model family is dead.
It only rejects the previously tested configuration under its data and cost
assumptions.

## Compute Strategy

Use compute aggressively but deliberately:

- Start with cheap diagnostic sweeps and parameter-range sanity checks.
- Materialize intermediate artifact hashes and summaries so long runs can be
  resumed or audited.
- Use multiprocessing, vectorization, caching, and batched evaluation when
  safe.
- Use CUDA/GPU work only if the backend is real, tested, and truthfully
  represented in manifests. Do not claim GPU acceleration for code paths that
  still run on CPU.
- Optimize expensive search spaces with staged funnels:
  1. broad cheap screen;
  2. cost-aware filter;
  3. monthly/split stability filter;
  4. ablation/control filter;
  5. May 2026 holdout benchmark;
  6. candidate-pack gate recheck only if all evidence passes.
- Long compute runs are allowed. If a run fails or times out, preserve the
  useful partial evidence, record the failure, and move to the next best
  strategy or narrower search.

Do not overfit to a single PnL target. Rank by a composite that includes
post-cost return, monthly consistency, drawdown, downside risk, trade count
adequacy, split balance, feature ablation, and benchmark holdout behavior.

## Correctness Requirements

The first technical priority remains math and code correctness. Before trusting
new results, audit:

- no lookahead in feature construction;
- completed-bar alignment;
- train/validation separation and purge/embargo logic;
- label event-end semantics;
- cost, fee, slippage, spread, and funding accounting;
- compounding versus summed-return metric names;
- trade overlap and position accounting;
- side gating and opposite-side controls;
- transparent/no-trade baselines;
- artifact hashes, manifests, and reproducibility metadata;
- candidate-pack rejection reasons.

If a correctness issue is found, fix or document it before expanding compute.
Update `docs/KNOWN_ISSUES.md` for blocking risks.

## Evidence Rules

For any lead that appears profitable, the next agent must produce or explicitly
explain missing evidence for:

- aggregate backtest;
- monthly performance table;
- 2024-forward split validation;
- May 2026 holdout benchmark;
- cost stress;
- feature ablation;
- filter ablation;
- side or opposite-action controls where relevant;
- no-trade baseline;
- transparent/simple-strategy baseline;
- stability region;
- negative controls for model-driven strategies;
- candidate-pack gate recheck.

Any missing evidence keeps the row research-only and fail-closed.

## Research Boundary

All outputs must remain:

- `research_only: true`;
- `observe_only: true`;
- `promotion_ready: false`.

The next packet must not:

- place orders;
- change runtime mode;
- write live configuration;
- create paper/live artifacts;
- import live order-placement adapters into research modules;
- claim candidate readiness without gate evidence;
- claim paper/live/promotion readiness.

## Suggested Starting Paths

- `docs/stage_reports/STAGE_R106_SIDE_VETO_GATE_EVIDENCE_CLOSURE_REPORT.md`
- `docs/stage_reports/STAGE_R106_POST_SELECTION_SIDE_VETO_OPTIMIZER_REPORT.md`
- `docs/stage_reports/STAGE_R106_SPARSE_SIDE_VETO_VALIDATION_REPORT.md`
- `docs/stage_reports/STAGE_R106_LOCAL_BINANCE_ARCHIVE_FOUR_BAR_MAPPER_REPORT.md`
- `docs/stage_reports/STAGE_R106_VENUE_FIRST_NO_RSI_KNN_FOUR_BAR_REPORT.md`
- `configs/research/sparse_side_veto_gate_evidence_btcusdt_r106_v1.json`
- `configs/research/sparse_side_veto_optimizer_btcusdt_r106_v1.json`
- `configs/research/no_rsi_knn_four_bar_matrix_btcusdt_r106_v1.json`
- `configs/research/no_rsi_knn_four_bar_matrix_ethusdt_r106_v1.json`
- `data/research/historical_cycles/sparse_side_veto_gate_evidence_btcusdt_r106_v1/`
- `data/research/hmm_knn_four_bar_archive_mapping/wpr106_79_full_local_archive_map/`
- `src/tradingbotsuite/research_cycle/runner.py`
- `src/tradingbotsuite/research/hmm_knn.py`
- `src/tradingbotsuite/research/hmm_knn_experiments.py`
- `src/tradingbotsuite/research/knn_four_bar.py`
- `src/tradingbotsuite/strategies/`
- `src/tradingbotsuite/features/`
- `src/tradingbotsuite/backtesting/`
- `src/tradingbotsuite/optimization/`
- `tests/contracts/`
- `tests/historical/`
- `tests/tradingbotsuite/`
- `tests/optimization/`

## Validation Baseline

Use focused validation for scoped edits, then run the branch baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Broaden tests when shared feature, split, backtest, strategy, optimizer, or
artifact contracts change.

## Next Goal Prompt

```text
/goal WPR106-85: Continue after WPR106-84 from C:\Users\papaa\Music\researchenginedeluxe. Read AGENTS.md, docs/ORCHESTRATOR_STAGE_LEDGER.md, docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md, docs/stage_reports/STAGE_R106_SIDE_VETO_GATE_EVIDENCE_CLOSURE_REPORT.md, and docs/NEXT_AGENT_HANDOFF_WPR106_85_2024_FORWARD_BROAD_STRATEGY_SEARCH.md. Start with math/code/data correctness, then create a research-only work packet for a broad 2024-forward strategy search. Optimize and validate on data from 2024-01-01 through 2026-04-30 by default, keep May 2026 completely out of tuning, and use May 2026 only as a benchmark holdout for promising leads. If a strategy family lacks data back to 2024, such as order-flow, open-interest, liquidation, or venue-specific context features, use the longest truthful shorter window and document the limitation. Do not reject strategies just because they create many entries; 1 to 5 trades per day can be normal if costs, overlap, drawdown, monthly stability, and split behavior are tested. Revisit prior discarded strategies and try novel variants before declaring them unprofitable, including sparse filters, trend/range/volatility, perp-context, funding/OI/liquidation/timing, fixed-hold and lower-timeframe exits, HMM/KNN, Lorentzian-space KNN, no-RSI four-bar KNN, replay-overlay where representable, ensembles, and negative controls. Lorentzian/KNN code, parameters, features, filters, and search ranges may be changed if scoped and tested. Use staged compute funnels, multiprocessing/vectorization/caching, and real CUDA only when truthful and validated; long compute runs are acceptable. For any promising lead require monthly profitability evidence, ideally zero to two losing months per year, split/cost/stability evidence, ablation, no-trade and transparent baselines, May 2026 holdout benchmark, and candidate-pack gate recheck. Keep every output research_only, observe_only, promotion_ready false. Do not create paper/live artifacts, place orders, change sizing/runtime/live config, or claim promotion readiness.
```
