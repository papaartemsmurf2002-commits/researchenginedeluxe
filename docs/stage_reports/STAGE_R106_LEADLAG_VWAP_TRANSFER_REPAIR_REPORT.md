# Stage R106 WPR106-207 Lead-Lag VWAP Transfer Repair Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-207 follows WPR106-206 by testing the two noncanonical source families
with useful May-transfer hints: WPR106-133 cross-symbol lead-lag and
WPR106-128 anchored VWAP. The packet is an artifact-level transfer repair and
small-portfolio audit. It does not recompute source signals or change shared
strategy code.

Pre-May row scoring, behavior deduplication, portfolio construction, and
selection use only 2024-01-01 through 2026-04-30. May 2026 is loaded only
after the selected components and portfolios are fixed, and is used only as a
benchmark holdout.

## Implementation

The packet-local runner is:

- `data/research/wpr106_207_leadlag_vwap_transfer_repair/scripts/run_wpr106_207_leadlag_vwap_transfer_repair.py`

The runner loads WPR106-128 and WPR106-133 selected pre-May metrics and
accepted-trade rows, recomputes metrics from trade returns instead of trusting
copied metric columns, hashes behavior signatures, deduplicates rows by
accepted trade timing/side/return sequence, and builds small equal-sleeve
daily-return portfolios from the top pre-May deduped components.

Costs are recomputed from trade `gross_return` and `round_trip_cost` at
1.00x, 1.25x, 1.50x, and 2.00x. Portfolio daily return is the equal-sleeve
average of component daily returns, with inactive sleeves contributing zero.
The runner reports member trades per active day, sleeve-weighted trades per
active day, overlap-day share, active component count, monthly return stability,
drawdown, best-month concentration, and cost-stress survival.

Runtime was 74.68 seconds. CUDA was not used and no speedup claim was made.

## Pre-May Results

Source inputs:

- 52 WPR106-128 anchored-VWAP selected rows and 12,263 accepted pre-May trades.
- 59 WPR106-133 lead-lag selected rows and 17,305 accepted pre-May trades.
- 111 source rows behavior-deduped to 92 rows.

Component repair:

- 0 strict pre-May components.
- 0 annual-target components.
- 45 loose source components before behavior deduplication.
- 35 fixed selected components after pre-May-only scoring and deduplication.

Small-portfolio repair:

- 35,420 candidate portfolios generated from the top 22 deduped components.
- 535 strict pre-May portfolios.
- 670 annual-target portfolios.
- 17,669 loose portfolios.
- 60 fixed selected portfolios, all strict and annual-target.
- Selected portfolio median pre-May return: +1.064106.
- Selected portfolio median losing months: 3.5.
- Best selected pre-May portfolio return: +1.116917.
- Worst selected pre-May max drawdown: -0.064251.

Top selected portfolio:

- `port207-3a1b07cdd1c0eb3a`.
- Five ETHUSDT sleeves: three anchored-VWAP flow-impulse rows, one
  cross-symbol leader-momentum row, and one cross-symbol relative-strength row.
- Source counts: three WPR106-128 sleeves and two WPR106-133 sleeves.
- Pre-May return: +1.024348.
- Three losing months, with annual losses 1/1/1 for 2024/2025/2026 Jan-Apr.
- Max drawdown: -0.062198.
- Member trades per active day: 2.977011.
- Sleeve-weighted trades per active day: 0.595402.
- Overlap-day share: 0.689655.
- Cost-stress survival: 4/4.

## May Benchmark

The frozen component set is mixed in May:

- 15 positive components.
- 20 negative components.
- Median component May return: -0.005001.
- Best component May return: +0.065272.
- Worst component May return: -0.132690.

The best component May row is WPR106-133
`leadlag-18708dffa1413dce`, but it had seven pre-May losing months and failed
the annual target before May was inspected. VWAP momentum components also show
positive May returns, but they likewise entered this packet as loose rows with
seven pre-May losing months.

The frozen selected portfolios fail May:

- 0 positive May portfolios.
- 60 negative May portfolios.
- 0 flat May portfolios.
- Median selected portfolio May return: -0.022084.
- Best selected portfolio May return: -0.020186.
- Worst selected portfolio May return: -0.023982.

The top selected portfolio `port207-3a1b07cdd1c0eb3a` benchmarks at
-0.020186 in May over 46 member trades, with May max drawdown -0.029869 and
zero cost-stress survival.

## Interpretation

WPR106-207 rejects the lead-lag / anchored-VWAP transfer repair as
candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready.

The packet produced strong-looking pre-May portfolios: combining loose VWAP
and lead-lag rows reduced losing months from seven per component to three or
four at the selected portfolio level while keeping active trade rates inside
the requested 1 to 5 trades/day band. That improvement did not transfer to May.
The lead-lag sleeves needed for pre-May stability were May-negative often
enough that every selected combined portfolio lost in the benchmark month.

The useful negative evidence is specific: pre-May-only portfolio construction
can hide source-row instability in these two families. A later source-level
rebuild should not treat WPR106-128/WPR106-133 portfolio repair as a candidate
path unless it introduces a genuinely causal filter that removes the May-losing
lead-lag sleeves without using May feedback.

The next broad-search direction should move away from this transfer-repair
pocket. Reasonable follow-up remains fresh calendar/session source
reconstruction with causal controls, or a new source-level variant that changes
signal logic before pre-May selection rather than merely composing rejected
rows.

## Artifacts

- `data/research/wpr106_207_leadlag_vwap_transfer_repair/controls/source_artifact_index.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/controls/component_behavior_index.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/pre_may/leadlag_vwap_component_metrics.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/pre_may/deduped_component_metrics.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/pre_may/selected_component_repair_rows.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/pre_may/portfolio_repair_candidates.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/pre_may/portfolio_repair_candidates_top5000.csv`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/pre_may/selected_portfolio_repair_rows.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/pre_may/selected_portfolio_daily_returns.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/pre_may/selected_portfolio_monthly_returns.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/may_benchmark/selected_component_may_benchmark_metrics.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/may_benchmark/selected_portfolio_may_benchmark_metrics.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/may_benchmark/selected_portfolio_may_daily_returns.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/may_benchmark/selected_portfolio_may_monthly_returns.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/selected_pre_may_may_portfolio_comparison.parquet`
- `data/research/wpr106_207_leadlag_vwap_transfer_repair/wpr106_207_leadlag_vwap_transfer_repair_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_207_leadlag_vwap_transfer_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
