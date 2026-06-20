# WPR106-78 Next Agent Handoff - Four-Bar KNN Larger Validation

Date: 2026-06-09

## State

WPR106-76 built the minimal durable BTC/ETH four-bar no-RSI dataset layer:
signal-close plus four completed bars, event-end/purge metadata, fixed-hold
labels, close-path features, aggTrade flow proxies, and explicit missingness
for absent flow/perp context.

WPR106-77 added the research-only larger-validation runner and optional
operator UI button for the selected no-RSI BTC/ETH rows. It did not run the
long matrix at that time.

WPR106-78 ran the larger-validation command locally with a long command
timeout:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-four-bar-knn-larger-validation --output-dir hmm_knn_four_bar_validation\wpr106_78_full_run --sample-rows-per-interval 8000 --workers 1 --skip-monitor
```

The command was given a 10,800,000 ms timeout and completed successfully as a
process. It wrote artifacts under:

`data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/`

## Result

The matrix run failed for a concrete data-coverage reason, not because the
entry lead was proven unprofitable:

- BTCUSDT dataset row count: 64.
- ETHUSDT dataset row count: 64.
- Each source fixture has 32 base cycle rows and 480 lower-timeframe/aggTrade
  context rows.
- BTC 15m->1h and ETH 15m->1h experiments failed with
  `ValueError: No objects to concatenate`.
- BTC 1h->4h and ETH 1h->4h experiments failed with
  `ValueError: dataset is too small for HMM/KNN walk-forward research`.
- No matrix records or gate-pass rows were produced.
- The summary decision is `venue_intake_feature_packet`, but that should be
  interpreted as "current compact fixtures cannot answer larger validation",
  not as a negative KNN result.

Primary artifact paths:

- Manifest:
  `data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/four_bar_knn_larger_validation_manifest.json`
- Summary JSON:
  `data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/four_bar_knn_larger_validation_summary.json`
- Summary CSV:
  `data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/four_bar_knn_larger_validation_summary.csv`
- BTC matrix manifest:
  `data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/matrices/btcusdt/experiment_manifest.json`
- ETH matrix manifest:
  `data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/matrices/ethusdt/experiment_manifest.json`

## Boundary

All WPR106-78 outputs are research-only and observe-only. The manifest records:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `candidate_pack_written: false`
- `paper_artifact_written: false`
- `live_artifact_written: false`
- `order_placement_used: false`
- `position_sizing_used: false`
- `runtime_mode_changed: false`

Do not create candidates, paper/live artifacts, sizing, order placement,
runtime-mode changes, or promotion claims from these outputs.

## Next Direction

Open the next packet as a venue-intake feature packet or a prerequisite data
coverage packet. The immediate objective is to provide enough BTCUSDT and
ETHUSDT event history for the four-bar KNN walk-forward matrix to form valid
splits before any further KNN tuning.

Concrete next work:

- Verify whether a larger BTC/ETH local historical catalog already contains
  compatible bars, lower-timeframe bars, and aggTrade context that can feed the
  WPR106-76 four-bar dataset builder without changing semantics.
- If not, design OKX/Bybit or broader Binance public-archive intake for
  research-only BTC/ETH venue-derived features: bars, aggTrade or trade-flow
  proxy, funding, open interest, premium/basis, and explicit missingness.
- Preserve event-end and purge metadata and the fixed four-bar same-entry
  long/short comparison.
- Re-run larger validation only after each symbol/interval has enough labeled
  event rows to satisfy walk-forward splits and the decision-gate trade floors.
- Judge entry quality separately from exit quality; this packet produced no
  valid larger-validation entry-quality result.

For general OpenAI/Codex developer guidance, use the official OpenAI Developers
portal: https://developers.openai.com/. Repo work remains governed by
`AGENTS.md`, `docs/ORCHESTRATOR_STAGE_LEDGER.md`, and
`docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`.

## Next Goal Prompt

```text
/goal WPR106-79: Continue from WPR106-78. Use AGENTS.md, docs/ORCHESTRATOR_STAGE_LEDGER.md, and docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md as the governing repo instructions. For general Codex/OpenAI developer guidance, reference the official OpenAI Developers portal: https://developers.openai.com/. Inspect WPR106-78 artifacts under data/research/hmm_knn_four_bar_validation/wpr106_78_full_run and treat the result as a data-coverage blocker, not a KNN profitability conclusion. Choose exactly one research-only next phase: map an existing larger local BTC/ETH archive into the four-bar dataset contract, or design OKX/Bybit/Binance venue-derived feature intake for enough BTC/ETH history to run valid four-bar HMM/KNN walk-forward splits. Preserve event-end/purge semantics and same-entry fixed four-bar labels; judge entry quality separately from exit quality. Keep all outputs research_only, observe_only, promotion_ready false; do not create candidates, paper/live artifacts, order placement, sizing, runtime-mode changes, or promotion claims.
```
