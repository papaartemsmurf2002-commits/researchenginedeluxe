# TradingView to V2 Data Framework

## Status

This document is the source of truth for the BTC-only V2 data layer.

Its job is to lock the data architecture that later V2 research and model work will rely on:

- TradingView signal acquisition
- Binance market-context reconstruction
- canonical storage and lineage
- replayable dataset construction
- training and calibration handoff

This document does not authorize live model gating. It defines the data foundation only.

## 1. Objective

The goal of this phase is to make the V2 acceptance-layer input data trustworthy, reproducible, and easy to audit.

This means the system must be able to do two things well:

- bootstrap an initial BTC-only research dataset from reliable historical signal sources plus Binance history
- keep collecting higher-quality prospective signal data into our own database so future datasets are better than the bootstrap

The design principle is simple:

- TradingView supplies the candidate signal event
- Binance supplies the surrounding market context
- our framework supplies the label using the same frozen-ATR triple-barrier logic used by the engine

Anything that cannot be defended by official source support or by transparent reconstruction should be treated as unsupported for this phase.

## 2. Executive Conclusions

### 2.1 What TradingView can officially provide

Confirmed by official source:

- TradingView can export chart data to CSV, including tickers and indicators shown on the chart.
- TradingView can export strategy data from Strategy Tester, including the trade list export path.
- TradingView alert logs can be exported to CSV.
- TradingView can send webhook POST requests when alerts trigger.
- Pine alerts can originate from indicator alert conditions, `alert()` calls, and strategy order-fill events.

Implementation conclusion:

- There are official paths for both historical bootstrap and prospective capture.
- They are not equivalent in reliability or fidelity.
- The system should rank them explicitly rather than mixing them casually.

### 2.2 What TradingView does not provide as a dependable archive

Confirmed by official source:

- Alert trigger logs are deleted when they are older than 30 days.
- Only the most recent 100 trigger events are retained per alert.
- Webhooks may occasionally fail to reach the destination URL.
- TradingView alerts are snapshots of the script, inputs, and chart context at creation time, so later script edits do not retroactively update existing alerts.

Implementation conclusion:

- TradingView alert logs are a short-retention recovery tool, not the archive system.
- Existing alerts must be recreated after meaningful Pine changes.
- Our own persistence layer must be the long-term source of truth for V2 data.

### 2.3 Why prospective capture is still required even with history imports

Historical imports are good enough to start V2 research, but they are not the end state.

Implementation inference from the official constraints:

- strategy exports and chart exports can recover candidate signal history
- they do not guarantee the exact signal-time packet our engine would have observed live
- webhook capture into our database is the only reliable way to preserve future signal events with engine-time lineage, ingestion timestamps, and exact downstream decision packets

Implementation conclusion:

- historical bootstrap is allowed and recommended
- prospective capture is mandatory for long-term data quality

### 2.4 Why TradingView exits are not the model label

The V2 acceptance model is meant to answer one question:

- given a candidate directional signal, should the engine accept it?

That requires labels aligned to engine semantics, not chart-simulator semantics.

Implementation decision:

- TradingView provides the entry candidate only
- TradingView strategy exits may be used as an alignment reference
- the canonical label is always produced by our own triple-barrier engine logic using frozen ATR, direction-aware barriers, and the configured vertical barrier

### 2.5 Why Binance remains the context venue for this phase

Confirmed by official source:

- Binance USD-M futures exposes official APIs for kline history, funding history, mark price with next funding time, premium-index klines, open interest, basis, and depth reconstruction.
- Binance documents the exact local-book reconstruction process for diff-depth plus REST snapshot synchronization.

Implementation conclusion:

- Binance is sufficient as the primary historical and contextual market-data venue for BTC-perp V2 data building.
- The V2 data layer should stay venue-simple in this phase: TradingView for candidate signal generation, Binance for context reconstruction, our database for canonical storage.

## 3. Research-Backed Source Map

This section defines what each source proves and how much trust the architecture should assign to it.

### 3.1 TradingView Strategy Tester export

Reliability tier:

- historical bootstrap primary, when the Pine logic exists as a strategy

Confirmed by official source:

- TradingView provides a strategy-data export path from Strategy Tester.
- The export includes the list of trades.

What it is good for:

- reconstructing historical candidate long and short events
- obtaining trade timestamps and direction when the strategy is the authoritative source of entries
- bootstrapping a first V2 dataset before the webhook archive is deep enough

What it does not prove:

- it does not automatically make TradingView exits the correct model label
- it does not guarantee exact engine-time context, ingestion timestamps, or future research metadata

Architecture stance:

- preferred historical source when available
- import the entry event
- ignore TradingView exit semantics for labeling except as a validation reference

### 3.2 TradingView chart export

Reliability tier:

- historical bootstrap secondary

Confirmed by official source:

- TradingView chart export can save chart data, including tickers and indicators, into CSV.

What it is good for:

- recovering historical signal events from plotted indicator columns
- bootstrapping history when the Pine logic is indicator-based rather than strategy-based
- validating whether chart-visible signals line up with imported candidate events

What it requires from us:

- the chart must expose enough plotted information to reconstruct the event reliably
- reconstruction rules must be deterministic and documented

Architecture stance:

- acceptable when signal conditions can be reconstructed from explicit plotted columns
- not acceptable when the exported chart does not contain enough information to determine a unique signal event

### 3.3 TradingView alert log export

Reliability tier:

- tertiary and temporary

Confirmed by official source:

- alert logs can be downloaded as CSV
- entries older than 30 days are deleted
- only the most recent 100 trigger events per alert are kept

What it is good for:

- short-term recovery if our webhook receiver was down
- last-30-day gap filling
- operator audit of recent delivery activity

What it is not good for:

- durable archive
- long historical bootstrap
- authoritative research lineage

Architecture stance:

- backup source only
- never treated as the long-term archive

### 3.4 TradingView webhook alerts

Reliability tier:

- prospective primary

Confirmed by official source:

- webhook alerts are delivered as HTTP POST requests
- valid JSON messages are sent with `application/json`
- non-JSON bodies are sent as `text/plain`
- only ports 80 and 443 are accepted
- requests taking longer than about three seconds are cancelled
- IPv6 is not supported
- webhook alerts require TradingView 2-factor authentication
- webhooks may occasionally fail to reach the destination URL

What it is good for:

- turning TradingView into a prospective event emitter
- capturing the exact incoming signal payload and ingestion timestamp into our own archive
- creating a durable signal history that is no longer limited by TradingView alert retention

Architecture stance:

- the default path for all new BTC signals
- the recipient must acknowledge quickly and persist first
- all downstream enrichment happens after the signal is safely stored

### 3.5 Pine alerts behavior

Reliability tier:

- foundational source semantics

Confirmed by official source:

- indicators can create alert triggers via `alertcondition()` and `alert()`
- strategies can create alert triggers via `alert()` and order-fill events
- created alerts use a snapshot of the script, inputs, and current chart context
- more than 15 alerts in three minutes causes TradingView to halt further alerts
- alert timing can differ if alerts fire before bar close; TradingView recommends "Once Per Bar Close" to avoid that issue

Architecture stance:

- the recommended production setting for this phase is close-confirmed alerts on the 15m bar
- if the Pine logic changes, the operator must recreate affected alerts
- the document assumes non-repainting, bar-close-driven signal generation for dataset integrity

### 3.6 Binance context sources

Reliability tier:

- primary market-context source

Confirmed by official source:

- Kline history is available through the USD-M futures REST API.
- Funding history is available through `/fapi/v1/fundingRate`.
- Mark price returns `markPrice`, `indexPrice`, `lastFundingRate`, and `nextFundingTime`.
- Premium-index klines are available through `/fapi/v1/premiumIndexKlines`.
- Open interest is available through `/fapi/v1/openInterest`.
- Basis history is available through `/futures/data/basis`.
- Diff-depth reconstruction rules are formally documented and require the REST depth snapshot plus websocket event sequencing.

Architecture stance:

- closed 15m Binance bars are the canonical historical bar source for ATR and label generation
- Binance contextual endpoints are additive features and must carry missingness flags when unavailable
- signal-time local-book reconstruction is optional for the dataset row, but if present it must follow Binance's documented synchronization rules

### 3.7 Unsupported or high-risk paths

Explicitly unsupported for the recommended architecture:

- assuming an official TradingView bulk historical custom-signal API exists
- unofficial scraping of TradingView UI pages for production data collection
- browser automation as a routine archival path
- labeling the acceptance model with TradingView's own simulated exits

These paths are excluded because they are either unsupported by official source, operationally brittle, or semantically wrong for the acceptance task.

## 4. Source Hierarchy And Reliability Stance

The following source order is locked for this phase.

### 4.1 Candidate signal acquisition priority

For new signals:

1. TradingView webhook into our service

For historical bootstrap:

1. TradingView Strategy Tester export
2. TradingView chart export with reconstructable signal columns
3. TradingView alert log CSV export for short-retention recovery only

### 4.2 Market context priority

1. Binance USD-M futures closed 15m bars for ATR and label generation
2. Binance context endpoints for funding, premium, OI, basis, mark/index metadata
3. optional signal-time local-book or microstructure snapshots when available and synchronized correctly

### 4.3 Canonical storage priority

1. our SQLite database
2. versioned research outputs under `data/research/`
3. imported source files retained as lineage artifacts

TradingView itself is not the archive.

### 4.4 Conflict resolution

If multiple source records appear to describe the same candidate event, use this precedence:

1. webhook
2. strategy export
3. chart export
4. alert log

Conflict resolution rules:

- keep the higher-precedence source as canonical
- preserve the lower-precedence record as lineage evidence
- never silently merge conflicting direction values
- if direction or normalized time disagree after normalization, keep both records, mark a conflict, and exclude the ambiguous row from training until reviewed

## 5. Data Semantics For This Phase

### 5.1 What TradingView provides

TradingView provides the candidate signal event only.

Required semantics:

- symbol
- direction
- signal-time or bar-time reference
- source lineage

Optional semantics:

- external signal id
- strategy order id
- strategy metadata embedded in the alert or export
- raw message payload

### 5.2 What Binance provides

Binance provides the market context around the candidate event.

Examples:

- closed 15m bar sequence
- ATR inputs
- funding context
- premium or basis context
- open interest context
- realized volatility context
- optional signal-time microstructure state

### 5.3 What our framework provides

Our framework produces:

- normalized event identity
- canonical feature packet
- triple-barrier label
- dataset row lineage
- dataset manifest and reproducibility metadata

### 5.4 What is not the canonical label

The following are not the label for the acceptance model:

- TradingView strategy exits
- Pine backtest equity curves
- broker-emulator fill outcomes
- manual operator opinion

Those may be kept for comparison, but they do not define the supervised target.

## 6. Historical Bootstrap And Prospective Capture

### 6.1 Historical bootstrap mode

Purpose:

- produce the first useful BTC-only research dataset before prospective webhook history is deep enough

Path:

1. import historical TradingView signal events from the highest-quality available source
2. normalize the events into the canonical `tv_signal_event` shape
3. reconstruct Binance context for each normalized signal time
4. generate labels using the shared triple-barrier path
5. write dataset rows plus manifest for training handoff

Historical bootstrap is allowed to be imperfect in fidelity relative to future live capture.

What is not allowed:

- inventing missing core timestamps
- inferring direction from ambiguous chart artifacts
- labeling rows without enough ATR lookback or enough forward bars

### 6.2 Prospective capture mode

Purpose:

- build the durable, higher-fidelity archive that future V2 iterations should trust most

Path:

1. TradingView emits webhook POST
2. our ingress authenticates, validates, and persists the raw signal first
3. the runtime stores normalized signal identity and decision lineage
4. the system later reuses the persisted records for research dataset construction

Prospective capture gives us data that historical imports cannot fully reproduce:

- exact receive timestamp
- exact webhook payload
- exact engine-time decision lineage
- exact system-side missingness and health state

### 6.3 Relationship between the two modes

The two modes are complementary:

- historical bootstrap gives the first training sample
- prospective capture improves future sample quality

The architecture should support both permanently.

## 7. Canonical Timestamp Rules

Timestamp drift is one of the easiest ways to poison a research dataset. The following rules are locked.

### 7.1 Canonical event time

Every candidate event must normalize to `tv_bar_time_ms`.

Definition for this phase:

- `tv_bar_time_ms` is the authoritative TradingView signal bar timestamp used by the engine and the research pipeline
- it must refer to the same 15m decision bar across import, live capture, feature reconstruction, and label generation

### 7.2 Normalization rules

Required normalization steps:

- normalize vendor-specific ticker strings to canonical symbol `BTCUSDT`, while preserving raw source symbol
- convert source timestamps to epoch milliseconds
- map the signal to the 15m decision-bar clock used by the source record
- preserve both the normalized value and the raw source timestamp when they differ

If the source only provides an execution timestamp and not an explicit bar timestamp:

- infer the associated 15m decision bar only when the mapping rule is deterministic and documented
- otherwise mark the record ambiguous and exclude it from dataset construction

### 7.3 Alignment rules for Binance context

The dataset builder must align Binance bars to the same normalized event clock.

Required behavior:

- ATR uses only closed 15m Binance bars at or before `tv_bar_time_ms`
- the entry-anchor bar for label generation must reference the same normalized signal event time
- future outcome bars must begin strictly after the signal-time anchor and advance in correct chronological order

### 7.4 Clock fields we keep

Keep these distinct:

- `tv_bar_time_ms`
- `source_event_time_ms` when available
- `ingested_time_ms`
- `decision_time_ms` when the runtime later acts on the signal

Do not collapse them into a single timestamp column.

## 8. Canonical Schemas

The data layer should use stable record shapes that later training and replay code can consume without guessing.

### 8.1 `tv_signal_event`

Purpose:

- immutable candidate signal record

Required fields:

- `signal_id`
- `source_mode` as one of `strategy_export | chart_export | alert_log | webhook`
- `external_signal_id`
- `symbol`
- `raw_symbol`
- `direction`
- `tv_bar_time_ms`
- `source_event_time_ms`
- `ingested_time_ms`
- `source_lineage`
- `raw_payload_json`

Required lineage expectations:

- imported files carry file path, file hash, and import batch id
- webhook records carry raw request payload, source IP if available, and auth result metadata

Idempotency key:

- primary: `signal_id + symbol + tv_bar_time_ms`
- secondary import dedupe: `source_mode + external_signal_id + symbol + tv_bar_time_ms`

### 8.2 `market_context_snapshot`

Purpose:

- the reconstructed market packet for a normalized signal event

Required fields:

- `signal_id`
- `symbol`
- `tv_bar_time_ms`
- `binance_bar_time_ms`
- `entry_reference_price`
- `atr_length`
- `atr_value`
- `atr_source_bar_count`
- `realized_volatility`
- `atr_percentile`
- `volatility_shock_flag`
- `funding_rate`
- `funding_rate_change`
- `time_to_next_funding_ms`
- `open_interest`
- `open_interest_change`
- `premium_index_value`
- `basis_value`
- `microstructure_snapshot_json`
- `missing_flags_json`
- `context_version`

Rules:

- core ATR fields are mandatory for a dataset row
- additive research fields may be missing, but missingness must be explicit
- microstructure is optional in this phase when it cannot be reconstructed safely

### 8.3 `dataset_row`

Purpose:

- one research-ready example for one candidate BTC signal

Required fields:

- `signal_id`
- `symbol`
- `direction`
- `tv_bar_time_ms`
- `source_mode`
- `feature_version`
- `label_version`
- `model_version`
- `calibration_version`
- feature values
- feature missingness fields
- `label_exit_reason`
- `label_accept`
- `label_tp_price`
- `label_sl_price`
- `label_time_barrier_ms`
- `label_entry_price`
- `label_exit_price`
- `label_return_atr_multiple`
- `lineage_json`

Rules:

- `model_version` and `calibration_version` may be placeholders at dataset-build time
- features and labels must be tied to the same normalized event
- row order for replay and walk-forward logic is chronological by `tv_bar_time_ms`

## 9. Label Generation Contract

The label contract is locked to engine semantics.

### 9.1 Shared math path

The dataset label must use the same logic family as live and paper supervision:

- ATR from closed 15m bars only
- direction-aware TP and SL math
- frozen barrier values at entry
- vertical barrier in elapsed 15m bars and wall-clock time
- first-trigger-wins evaluation

### 9.2 Direction-aware barrier rules

Long:

- `tp = entry + k_tp * ATR`
- `sl = entry - k_sl * ATR`

Short:

- `tp = entry - k_tp * ATR`
- `sl = entry + k_sl * ATR`

### 9.3 What makes a label valid

A label is valid only if all of the following are true:

- the row has enough prior bars to compute ATR correctly
- the signal has a trustworthy normalized `tv_bar_time_ms`
- the builder has enough future bars to evaluate the vertical barrier window
- the first barrier hit can be determined deterministically

If any of those conditions fail, the row is skipped.

### 9.4 Use of TradingView exits

TradingView strategy exits may be stored for comparison only.

Allowed uses:

- sanity-checking entry reconstruction
- rough alignment analysis
- comparing engine labels to Pine strategy behavior

Not allowed:

- replacing the canonical label
- mixing TradingView exit outcomes into the supervised target

## 10. Missingness, Skips, And Fail Rules

### 10.1 Fail-closed conditions

The builder must fail closed or skip the row when:

- signal direction is ambiguous
- normalized event time is ambiguous
- ATR lookback is incomplete
- future bar coverage is incomplete for the configured vertical barrier
- duplicate events cannot be resolved deterministically

### 10.2 Fail-soft conditions

The builder may continue with explicit missingness flags when:

- funding data is unavailable
- OI data is unavailable
- premium or basis context is unavailable
- signal-time microstructure snapshot is unavailable
- research-only additive endpoints are temporarily rate-limited

Fail-soft means:

- preserve the row
- set the feature value to null or the agreed sentinel form
- set an explicit missingness flag
- record the condition in lineage or manifest metadata

### 10.3 Source precedence when data conflicts

If source records disagree:

- prefer the higher-ranked source from Section 4
- preserve the conflict in lineage
- exclude the row if the disagreement changes direction or normalized event time

### 10.4 Rate-limit handling

Rate limits are a data-quality risk, not just an infrastructure nuisance.

Required behavior:

- prefetch historical bar ranges in shared batches rather than per-row duplication
- back off and retry where the source contract permits
- allow additive context fields to degrade into missingness rather than fabricating values
- never silently substitute current-time endpoint values for old historical rows unless the feature definition explicitly allows that

## 11. Recommended Production Architecture For This Phase

### 11.1 Historical import path

1. receive source artifact from TradingView export
2. hash and register the raw artifact
3. parse into staging rows
4. normalize into canonical `tv_signal_event`
5. dedupe and conflict-check
6. reconstruct Binance context
7. generate shared triple-barrier labels
8. write dataset parquet plus manifest

### 11.2 Prospective webhook path

1. TradingView emits webhook
2. ingress validates auth, schema, and timestamp tolerance
3. raw payload and normalized event are persisted immediately
4. runtime produces decision packet and downstream lineage
5. research pipeline later reuses persisted signal and context records

### 11.3 Persistence layer

The long-term source of truth is our database plus versioned research outputs.

Recommended persistence responsibilities:

- raw-signal archival
- normalized-signal storage
- decision packet lineage
- context snapshot lineage
- dataset manifest lineage

### 11.4 Dataset builder boundary

Inputs:

- canonical stored signal events
- persisted decision lineage when available
- Binance historical bars and contextual history

Outputs:

- `data/research/<plan_version>/btcusdt_dataset.parquet`
- `data/research/<plan_version>/dataset_manifest.json`

### 11.5 Train and calibrate handoff

The handoff boundary is the dataset manifest and dataset file, not live gating.

The training pipeline should receive only:

- dataset path
- manifest metadata
- feature version
- label version
- reproducibility hash

No later step should need to infer how the dataset was built.

## 12. Training And Calibration Handoff Contract

A dataset is "ready for training" only when it satisfies all required acceptance checks.

### 12.1 Required outputs

The dataset build must emit:

- parquet dataset path
- manifest path
- dataset SHA-256 or equivalent reproducibility hash
- feature version
- label version
- row count
- class balance summary
- missing-feature rates
- source-window summary
- config snapshot

### 12.2 Required acceptance checks before training

The dataset should be rejected for training if any of the following are true:

- row count is zero
- labels are missing
- only one label class is present
- duplicate canonical event keys remain after normalization
- core ATR or entry-anchor fields are missing
- manifest lineage is incomplete

### 12.3 Recommended readiness checks

The operator should also review:

- whether the dataset is dominated by a single acquisition mode
- whether missingness is extreme in key additive features
- whether the time span is large enough for walk-forward splits
- whether bootstrap history is overly dependent on a low-fidelity source

## 13. Operator Workflow

### 13.1 Historical bootstrap workflow

Preferred order:

1. if the Pine logic exists as a strategy, export Strategy Tester trades
2. otherwise export chart CSV only if the plotted columns allow deterministic signal reconstruction
3. use alert log CSV only for short-retention recovery

Operator checks before import:

- source file is BTC-only or clearly filterable to BTC
- timestamps are present and interpretable
- direction is explicit or reconstructable without guesswork
- the artifact is retained locally for lineage

### 13.2 Prospective capture workflow

1. configure TradingView alerts to send webhook POSTs to our service
2. use JSON payloads
3. use close-confirmed bar alerts
4. keep alerts recreated after Pine changes
5. verify signals are landing in our database

### 13.3 When manual import is needed

Manual import is needed when:

- the prospective database is too shallow for useful training
- the webhook archive started after the strategy had already been generating signals
- there was a known downtime gap that exceeds alert-log retention

### 13.4 How to judge if enough data exists

The operator should not think only in row count.

A useful training set needs:

- enough rows
- both classes present
- enough time coverage for walk-forward evaluation
- acceptable missingness in the features intended for the baseline model

If those conditions are not met:

- continue prospective collection
- keep V2 in observe-only mode
- do not promote gating behavior

### 13.5 What to inspect before training

Inspect:

- dataset manifest
- missing-feature rates
- source-mode mix
- class balance
- date range
- duplicate/conflict counts

If any of these look suspect, fix the data issue before training.

## 14. Deferred Items

Explicitly deferred from this framework document:

- ETH perps and ETH-specific signal workflows
- live model gating and promotion rules beyond the dataset handoff boundary
- unofficial TradingView scraping or browser automation
- advanced microstructure capture beyond the current V2-start scope
- exchange-routing questions unrelated to the data layer

## 15. Acceptance Criteria For This Document

This document is complete for the planning phase when all of the following are true:

- it is BTC-only
- it covers both historical bootstrap and prospective capture
- it distinguishes official-supported TradingView paths from unsupported or risky ones
- it defines canonical record contracts and dataset handoff rules
- it states fail-soft and fail-closed behavior without ambiguity
- it leaves no major product decision open for a future implementer on the V2 data layer
- it is suitable for later inclusion in the GUI Guides section as a long-form operator reference

## 16. Official Source Notes

The statements in this document should be read using this evidence convention:

- confirmed by official source: directly stated in the cited TradingView or Binance documentation
- implementation inference from official source: not stated word-for-word, but directly follows from the documented behavior and the architecture constraints
- unsupported or risky: not supported by official source or operationally too brittle for the recommended design

## 17. Official References

TradingView:

- How to export chart data: https://www.tradingview.com/support/solutions/43000537255-how-to-export-chart-data/
- How can I export strategy data: https://www.tradingview.com/support/solutions/43000613680-how-can-i-export-strategy-data/
- Manage alerts: https://www.tradingview.com/support/solutions/43000595311-manage-alerts/
- Automatic deletion of old alert triggers from the Log: https://www.tradingview.com/support/solutions/43000766116-automatic-deletion-of-old-alert-triggers-from-the-log/
- How to configure webhook alerts: https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
- Webhook authentication: https://www.tradingview.com/support/solutions/43000680459-webhook-authentication/
- Pine Script alerts FAQ: https://www.tradingview.com/pine-script-docs/faq/alerts/

Binance USD-M futures:

- Kline candlestick data: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data
- Mark price: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price
- Get funding rate history: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
- Premium index kline data: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Premium-Index-Kline-Data
- Open interest: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest
- Basis: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Basis
- Diff book depth streams: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Diff-Book-Depth-Streams
- How to manage a local order book correctly: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/How-to-manage-a-local-order-book-correctly
