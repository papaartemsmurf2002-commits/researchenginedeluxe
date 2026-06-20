# WPR106-124 Causal Trade-Health Throttle Overlay Search

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Test whether causal trade-health throttles can remove the annual loss clusters
from active WPR106-123 flow/price rows without using May 2026 for tuning.
WPR106-123 found active 28-month rows with strong pre-May returns, but those
rows failed annual stability. This packet tests trade-history, daily-loss, and
monthly-health pause/resume overlays as a new filter mechanism before moving
away from this family.

## Scope

- Use WPR106-123 selected active diagnostic rows and their pre-May trade streams:
  - `data/research/wpr106_123_flow_price_absorption_divergence_search/pre_may/selected_pre_may.csv`
  - `data/research/wpr106_123_flow_price_absorption_divergence_search/pre_may/selected_pre_may_trades.parquet`
- Deduplicate equivalent source behaviors by actual pre-May trade fingerprint.
- Evaluate causal overlays only on 2024-01-01 through 2026-04-30:
  - cooldown after losing trades;
  - rolling trade-return health;
  - daily loss stop;
  - previous-month health gate;
  - hybrid monthly-health plus trade-cooldown gate.
- Keep May 2026 fully out of source choice, overlay-policy choice, parameter
  choice, ranking, and fixed selection.
- Use May only after fixed pre-May strict or loose overlay selections are
  written. May overlay state must be causal and may carry pre-May history
  forward, but cannot use future May trades to decide earlier May entries.
- Keep all artifacts `research_only: true`, `observe_only: true`, and
  `promotion_ready: false`.

## Allowed paths

- `docs/work_packets/WPR106-124-causal-trade-health-throttle-overlay-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_TRADE_HEALTH_THROTTLE_OVERLAY_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_124*/**`

## Out of scope

- No May 2026 tuning, feedback, source choice, overlay choice, parameter choice,
  ranking choice, or selection choice.
- No shared `src/tradingbotsuite` package, strategy registry, feature registry,
  backtest engine, optimizer, research-cycle, candidate-pack, live, runtime,
  config, or test changes.
- No candidate pack, paper/live artifact, order placement, position sizing,
  live runtime change, live configuration write, CUDA speedup claim, or
  promotion claim.
- No synthetic fallback data and no silent use of unavailable context as zero.

## Exit evidence

- A deterministic WPR106-124 runner and artifacts are written under
  `data/research/wpr106_124*/`.
- The report records source deduplication, overlay policies, evaluated row
  count, strict/loose/positive counts, selected rows, monthly and annual
  diagnostics, active-rate diagnostics, skip effects, cost-stress behavior,
  May benchmark result when applicable, and rejected/promising archetypes.
- May benchmark artifacts are written separately and only after fixed pre-May
  strict or loose selection.
- Validation baseline is run or explicitly reported if blocked:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`.

## Outcome

Closed as negative research evidence. The final runner deduplicated the 33
WPR106-123 selected diagnostics into 18 unique source trade behaviors with
4,588 pre-May source trades. It evaluated 32 causal trade-health overlay specs
per source, for 576 overlay rows.

The run found 498 positive pre-May rows, but 0 annual-target rows, 0 loose rows,
and 0 strict rows. May 2026 was not benchmarked because no strict or loose
pre-May overlay row existed.

The failure mode is explicit:

- Rolling-trade and hybrid throttles can reduce drawdown and trade count, and
  some rows get down to 5 to 7 losing months overall.
- No overlay satisfies the annual loss caps of 2024 <= 2, 2025 <= 2, and
  2026 Jan-Apr <= 1.
- Monthly-health gates were too blunt: they reduced active months and still did
  not produce annual-target rows.
- Active selected diagnostics remain annual failures, not holdout candidates.

Artifacts:

- `data/research/wpr106_124_causal_trade_health_throttle_overlay_search/wpr106_124_causal_trade_health_throttle_overlay_summary.json`
- `data/research/wpr106_124_causal_trade_health_throttle_overlay_search/pre_may/source_pool_deduped.csv`
- `data/research/wpr106_124_causal_trade_health_throttle_overlay_search/pre_may/health_overlay_ranking.parquet`
- `data/research/wpr106_124_causal_trade_health_throttle_overlay_search/pre_may/selected_pre_may.csv`
- `data/research/wpr106_124_causal_trade_health_throttle_overlay_search/may_benchmark/selected_may_benchmark_metrics.csv`

Validation passed:

```powershell
python -m compileall -q data/research/wpr106_124_causal_trade_health_throttle_overlay_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
