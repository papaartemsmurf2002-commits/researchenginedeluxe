# Stage R106 Four-Bar Larger Validation Run And Handoff Report

Date: 2026-06-09
Work packet: `docs/work_packets/WPR106-78-four-bar-larger-validation-run-and-handoff.md`

## Summary

WPR106-78 ran the WPR106-77 larger-validation command locally with an extended
timeout and wrote a next-agent handoff. The process completed and produced the
expected manifest and summary files, but the BTC/ETH matrices failed because
the current durable public-archive fixture packs are compact contract fixtures,
not larger validation datasets.

This is a data-coverage blocker. It is not evidence that the KNN lead passed or
failed profitability validation.

## Command Run

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-four-bar-knn-larger-validation --output-dir hmm_knn_four_bar_validation\wpr106_78_full_run --sample-rows-per-interval 8000 --workers 1 --skip-monitor
```

Command timeout supplied by the agent: 10,800,000 ms.

Process status: success.

Output directory:

`data/research/hmm_knn_four_bar_validation/wpr106_78_full_run/`

## Artifact Result

Top-level artifacts:

- `four_bar_knn_larger_validation_manifest.json`
- `four_bar_knn_larger_validation_summary.json`
- `four_bar_knn_larger_validation_summary.csv`
- `run_four_bar_knn_larger_validation.ps1`
- `datasets/`
- `matrices/`
- `specs/`
- `cache/`

Dataset rows:

- BTCUSDT: 64 rows.
- ETHUSDT: 64 rows.

Fixture coverage recorded by the dataset manifests:

- BTCUSDT source cycle rows: 32.
- ETHUSDT source cycle rows: 32.
- BTCUSDT lower-timeframe rows: 480.
- ETHUSDT lower-timeframe rows: 480.
- BTCUSDT aggTrade rows: 480.
- ETHUSDT aggTrade rows: 480.

Matrix status:

- BTCUSDT: failed.
- ETHUSDT: failed.

Concrete matrix errors:

- BTC 15m->1h: `ValueError: No objects to concatenate`.
- BTC 1h->4h: `ValueError: dataset is too small for HMM/KNN walk-forward research`.
- ETH 15m->1h: `ValueError: No objects to concatenate`.
- ETH 1h->4h: `ValueError: dataset is too small for HMM/KNN walk-forward research`.

Summary records: 0.
Gate-pass records: 0.

## Decision

Next phase: `venue_intake_feature_packet`.

Reason: the durable four-bar bridge exists, but the current local fixture roots
cannot answer larger KNN validation because they contain only compact fixture
coverage. The next packet should either map an existing larger local BTC/ETH
archive into the WPR106-76 dataset contract or design OKX/Bybit/Binance
venue-derived feature intake with enough history for valid four-bar
walk-forward splits.

## Boundary

The run remained research-only:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`
- `candidate_pack_written: false`
- `paper_artifact_written: false`
- `live_artifact_written: false`
- `order_placement_used: false`
- `position_sizing_used: false`
- `runtime_mode_changed: false`

No candidate pack, paper/live artifact, order placement, sizing,
runtime-mode change, venue intake implementation, or promotion claim was made.

## Handoff

Next-agent handoff:

`docs/NEXT_AGENT_HANDOFF_WPR106_78_FOUR_BAR_KNN_LARGER_VALIDATION.md`

The handoff includes a next `/goal` prompt and references the official OpenAI
Developers portal for general Codex/OpenAI developer guidance:

https://developers.openai.com/

Repo-specific work remains governed by `AGENTS.md`,
`docs/ORCHESTRATOR_STAGE_LEDGER.md`, and
`docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`.

## Validation

No source code was changed in WPR106-78. The validation evidence for this packet
is the successful CLI process completion and the generated failure manifests
above. No compile or test suite rerun was required for this docs/output-only
handoff packet.
