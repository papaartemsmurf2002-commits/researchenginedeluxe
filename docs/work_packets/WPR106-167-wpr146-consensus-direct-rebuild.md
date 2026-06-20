# WPR106-167 WPR146 Consensus Direct Rebuild

Status: closed
Date: 2026-06-12
Stage: R106 strategy research

## Objective

Rebuild the WPR106-166 behavior-consensus threshold 5 descriptor directly from
the WPR106-133 source trades, WPR106-136 feature cache, and fixed WPR106-146
behavior-representative KNN parameters. This verifies whether the descriptor is
reproducible outside the frozen selected-trade artifact and whether it should
remain the preferred research-only object for a future fresh non-May retest.

All fixed behavior representatives, consensus threshold choice, comparison
criteria, and parity checks come from WPR106-166 pre-May evidence only. May
2026 remains benchmark-only after the direct rebuild is frozen.

## Allowed Paths

- `docs/work_packets/WPR106-167-wpr146-consensus-direct-rebuild.md`
- `docs/stage_reports/STAGE_R106_WPR146_CONSENSUS_DIRECT_REBUILD_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_167_wpr146_consensus_direct_rebuild/**`

## Inputs

- Read-only WPR106-146 helper script and artifacts under
  `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/**`.
- Read-only WPR106-166 behavior-deduped row and consensus artifacts under
  `data/research/wpr106_166_wpr146_source_level_stability_ablation/**`.
- WPR106-136 accounting helpers reached through the WPR106-146 helper import.

## Method

- Load WPR106-166 behavior-deduped representatives and the threshold 5
  consensus descriptor.
- Rebuild WPR106-146 source lookup, source trades, May trades, and feature
  cache using WPR106-146 helper functions.
- Re-evaluate each fixed behavior representative from source trades and KNN
  parameters for pre-May and May.
- Rebuild raw-source cap-5 controls directly from source trades.
- Recompute consensus vote counts over raw cap-5 trades and apply the fixed
  threshold 5 rule.
- Compare direct-rebuild representative trades and consensus trades against the
  WPR106-166 frozen artifact outputs for pre-May and May.
- Record direct-rebuild metrics, parity diagnostics, and May benchmark metrics.
- Keep all outputs research-only, observe-only, and `promotion_ready: false`.

## Validation

- `python -m compileall -q data/research/wpr106_167_wpr146_consensus_direct_rebuild/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`

## Exit Criteria

- Write direct representative metrics/trades, raw cap-5 metrics/trades,
  threshold-5 consensus metrics/trades, parity diagnostics, summary, and stage
  report.
- Update the stage ledger with the packet decision.
- Do not write a candidate pack or make paper/live/promotion claims.

## Result

WPR106-167 rebuilt the WPR106-166 threshold-5 descriptor directly from WPR106-133
source trades, WPR106-136 features, and fixed WPR106-146 behavior
representative KNN parameters. The direct rebuild used only 2024-01-01 through
2026-04-30 for source replay and kept May 2026 benchmark-only.

All direct parity checks passed. The 17 fixed representatives exactly matched
the WPR106-146 frozen trade keys across pre-May and May, the raw cap-5 rebuild
matched the raw-source control trade keys, and the threshold-5 consensus
matched WPR106-166 metrics exactly: 254 pre-May trades, 26 active months, two
losing months, annual losses 1/1/0, +1.155278 pre-May net, -0.141007 max
drawdown, best-month share 0.146280, full cost-stress survival, and +0.065272
May with 17 trades.

The packet proves the descriptor is reproducible from source trades and fixed
KNN parameters, but rejects it as candidate-ready, portfolio-ready, or
promotion-ready evidence because the May benchmark is still the same raw
WPR106-133 source path and May is not a fresh independent holdout. The run did
not write a candidate pack, paper/live artifact, live config, order path, sizing
change, CUDA speedup claim, or promotion claim. Focused script compile, package
compile, and contracts passed; contracts reported 460 passed.
