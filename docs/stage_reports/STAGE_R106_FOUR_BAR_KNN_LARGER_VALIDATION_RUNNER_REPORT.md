# Stage R106 Four-Bar KNN Larger Validation Runner Report

Date: 2026-06-09

Work packet:
`docs/work_packets/WPR106-77-four-bar-knn-larger-validation-runner.md`

Status: Completed as research-only, observe-only, and `promotion_ready: false`.
No long matrix validation was run in this packet. No candidate pack,
paper/live artifact, live config, runtime-mode change, order placement, sizing
change, venue intake, or promotion claim was created.

## Purpose

WPR106-76 selected larger validation as the next phase, but the selected rows
can be long-running. This packet added a durable runner and operator UI launch
path so the larger validation can be run reproducibly without leaving the next
operator to reconstruct commands by hand.

## Implementation

Added `src/tradingbotsuite/research/knn_four_bar_validation.py` with a
research-only WPR106-77 runner. It:

- builds or reuses deterministic BTCUSDT/ETHUSDT four-bar validation datasets
  from the existing public-archive fixture roots;
- writes narrow no-RSI experiment specs for only the WPR106-76 selected rows;
- optionally runs the existing cached HMM/KNN experiment matrix runner;
- writes consolidated JSON/CSV summaries with cost, split, stress, no-RSI, and
  unimplemented-venue-dependency gates;
- emits `run_four_bar_knn_larger_validation.ps1` as a replay command.

The selected rows are intentionally narrow:

- BTCUSDT `15m -> 1h` price/vol/flow Lorentzian inverse compatible, used for
  top-score sparse validation.
- BTCUSDT `1h -> 4h` price/vol/flow Lorentzian inverse compatible, used for
  primary KNN validation.
- ETHUSDT `15m -> 1h` price/vol/flow Lorentzian inverse compatible, used for
  transparent trend/vol and KNN comparator validation.
- ETHUSDT `1h -> 4h` price-path Lorentzian uniform same-regime, used for
  aligned-flow top-score validation.

Added CLI command:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main run-four-bar-knn-larger-validation --output-dir hmm_knn_four_bar_validation\wpr106_77_larger_validation_r106_v1 --sample-rows-per-interval 8000 --workers 1 --skip-monitor
```

Added `run-four-bar-knn-larger-validation` to the research command registry and
boundary contract so live preflight treats it as research-only.

Added an optional operator Research UI card named `Four-Bar KNN Validation`.
It queues the same guarded job through
`/api/operator/research/jobs/run-four-bar-knn-larger-validation`. Operator runs
write isolated output under
`data/research/operator_runs/hmm_knn_four_bar_validation/<job_id>/`.

## Smoke Evidence

A specs-only smoke ran against the real BTC/ETH fixture roots:

```powershell
$env:PYTHONPATH='src'
python -m tradingbotsuite.main run-four-bar-knn-larger-validation --output-dir hmm_knn_four_bar_validation\wpr106_77_cli_smoke --sample-rows-per-interval 20 --workers 1 --skip-monitor --skip-matrix
```

Outputs:

- `data/research/hmm_knn_four_bar_validation/wpr106_77_cli_smoke/four_bar_knn_larger_validation_manifest.json`
- `data/research/hmm_knn_four_bar_validation/wpr106_77_cli_smoke/four_bar_knn_larger_validation_summary.json`
- `data/research/hmm_knn_four_bar_validation/wpr106_77_cli_smoke/four_bar_knn_larger_validation_summary.csv`
- `data/research/hmm_knn_four_bar_validation/wpr106_77_cli_smoke/run_four_bar_knn_larger_validation.ps1`

The smoke manifest passed the research-boundary check, recorded
`skip_matrix: true`, built 40-row BTC and ETH sampled datasets, wrote BTC/ETH
specs, and set `next_phase.decision: larger_validation_pending`.

## Validation

Passed:

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`: 449 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py tests\live\test_preflight.py -q`: 45 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q`: 48 passed, 2 existing environment warnings.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`: 92 passed.
- `$env:PYTHONPATH='src'; python -m tradingbotsuite.main run-four-bar-knn-larger-validation --help`
- Specs-only real-fixture smoke command above.

## Research Boundary

All new outputs remain research-only, observe-only, and `promotion_ready:
false`. This packet only adds execution scaffolding for larger validation. It
does not create live signals, candidate packs, paper/live readiness, order
placement, position sizing, runtime-mode changes, venue intake, or promotion
claims.
