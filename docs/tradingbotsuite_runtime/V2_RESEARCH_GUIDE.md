# V2 Research Guide

Repository migration note: this guide is preserved for reference. TradingView chart-export importing, dataset building, model training, calibration, and replay expansion are not the active workstream unless explicitly reapproved.

## Scope

V2 starts as a BTC-only research-first layer. It does not replace the V1 live accept/reject path yet.

For the architecture-level source of truth for TradingView acquisition, Binance context reconstruction, canonical storage, dataset contracts, and training handoff, see:

- [TRADINGVIEW_V2_DATA_FRAMEWORK.md](c:/Users/papaa/Music/tradingbotsuite/docs/TRADINGVIEW_V2_DATA_FRAMEWORK.md)

Included now:

- signal-time BTC feature enrichment
- replayable dataset builds from persisted signals plus exchange context
- shared triple-barrier labeling
- logistic-regression baseline training
- calibration with isotonic, plus Platt fallback for smaller calibration slices
- walk-forward replay evaluation
- shadow-only observe-mode packet scoring
- explicit promotion-failure reporting and confidence-bucket summaries

Deferred on purpose:

- ETH perps
- TradingView-driven ETH flow
- multi-level OFI / advanced HMM regime logic
- live model gating

## Commands

These module-style commands assume either:

- `python -m pip install -e .`
- or `PYTHONPATH=src`

Build the BTC dataset from persisted signals:

```bash
python -m tradingbotsuite.main build-dataset
```

Train the baseline:

```bash
python -m tradingbotsuite.main train-model --dataset data/research/v2-btc-research-1/btcusdt_dataset.parquet
```

Calibrate the trained baseline:

```bash
python -m tradingbotsuite.main calibrate-model --train-manifest data/research/v2-btc-research-1-btcusdt-artifacts/train_manifest.json
```

Run walk-forward replay evaluation:

```bash
python -m tradingbotsuite.main replay-eval --artifact-manifest data/research/v2-btc-research-1-btcusdt-artifacts/artifact_manifest.json
```

## Outputs

Dataset build:

- `data/research/<plan_version>/btcusdt_dataset.parquet`
- `data/research/<plan_version>/dataset_manifest.json`

Model and calibration:

- `.../model.pkl`
- `.../calibrator.pkl`
- `.../train_manifest.json`
- `.../artifact_manifest.json`

Replay evaluation:

- `.../metrics.json`
- `.../calibration.csv`
- `.../rejected_vs_accepted.csv`

The metrics output now also includes:

- confidence-bucket summary
- acceptance-rate stability across walk-forward splits
- mean absolute calibration error
- explicit `promotion_failures` reasons instead of only `promotion_ready`

## Browser Workflow

If the operator console is enabled, the browser `Research` page is now the easiest path:

- `Build Dataset` creates the parquet dataset and dataset manifest
- `Train Latest Dataset` uses the newest dataset manifest automatically
- `Calibrate Latest Train` uses the newest training manifest automatically
- `Replay Latest Artifact` uses the newest calibrated artifact automatically

The page summarizes job state, artifact manifests, and promotion-readiness metrics in cards instead of raw terminal output.

For a deeper operator-facing walkthrough of what dataset build needs, how it reconstructs rows, and how to judge output quality, see:

- [DATASET_BUILDING_GUIDE.md](c:/Users/papaa/Music/tradingbotsuite/docs/DATASET_BUILDING_GUIDE.md)

## Shadow Scoring

To append observe-only V2 scores into shadow-mode decision packets:

```powershell
$env:TBS_RUNTIME_MODE="shadow"
$env:TBS_RESEARCH_ARTIFACT_MANIFEST_PATH="C:\path\to\artifact_manifest.json"
python run_manual.py shadow
```

The engine then adds a `v2_acceptance` object into the decision packet feature snapshot with:

- `accept_probability`
- `base_probability`
- `confidence_bucket`
- `size_multiplier_candidate`
- `model_version`
- `calibration_version`
- `artifact_manifest_version`
- `artifact_manifest_sha256`
- `probability_threshold`
- `status`
- `scoring_fallback_reason`

This does not override the V1 live-safe baseline.

## When Operator Input Is Needed

Human input is only needed if the code cannot safely infer the answer.

Provide BTC historical TradingView signals if the SQLite database does not yet contain enough BTC samples for stable training:

- preferred fields: `signal_id`, `symbol`, `direction`, `tv_bar_time_ms`, optional generation timestamp
- preferred format: CSV or JSON

If exchange behavior conflicts with official docs, capture the raw response instead of guessing:

```bash
python -m tradingbotsuite.main smoke-live
```

Then provide the raw terminal output or raw JSON response for the mismatching endpoint.

## Fail-Closed Behavior

- Missing or stale feature sources are stored as explicit missingness flags, not fabricated defaults.
- Binance research endpoint rate limits now degrade into missing-feature context and backoff metadata instead of crashing the whole dataset job.
- Historical dataset rows avoid current-only Binance fields where those would misstate old signal-time context.
- Dataset bar history is now fetched as a shared paginated range and sliced locally per signal, which is much lighter on Binance than issuing overlapping kline requests for every row.
- Dataset build skips unlabeled rows instead of making up outcomes.
- Model training stops when the BTC sample is too small or one-sided.
- Replay evaluation uses walk-forward out-of-sample slices and keeps promotion blocked unless results beat the current baseline.
- If shadow scoring cannot safely use the loaded artifact, the packet records an explicit observe-only skip reason instead of guessing.
