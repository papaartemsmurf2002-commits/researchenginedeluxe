# ResearchEngineDeluxe — Practical Roadmap v2 for Multi-Instrument Perp Research

**Repository:** `papaartemsmurf2002-commits/researchenginedeluxe`
**Updated:** 2026-06-20
**Supersedes:** `researchenginedeluxe_combined_practical_improvement_plan.md` where it still assumes a BTC/ETH-only research scope.
**New product goal:** build an agent-friendly research platform that automatically collects and archives market data for **all Hyperliquid perpetual futures with daily notional volume above USD 5,000,000**, can also pull compatible data from other venues, and can efficiently backtest arbitrary strategy ideas on historical data from 2024 onward.

---

## 1. Executive conclusion

The previous roadmap was directionally useful, but it was still framed around a BTC/ETH perpetual-futures research workbench. That assumption is now outdated. The repository goal has shifted into a **multi-instrument, data-first, agent-friendly perpetual-futures research engine**.

The new core product is not live trading. It is a repeatable research loop:

```text
Discover liquid Hyperliquid perp universe
  -> collect raw venue data continuously
  -> normalize into a central archive
  -> expose fast historical datasets to any strategy
  -> run leakage-safe backtests on 2024+ data
  -> block overfit / underqualified experiments
  -> write standardized results into a central performance ledger/spreadsheet
  -> let agents iterate safely without corrupting data or hiding failed trials
```

The highest-priority work therefore changes. The old security, boundary, artifact, and operator hardening recommendations should not be deleted, because they are still good repo hygiene. But they are no longer the product center. The product center is now:

1. **Dynamic Hyperliquid universe discovery**: all perps, not BTC/ETH; include instruments whose current or as-of daily notional volume is above USD 5 million.
2. **Central data archive**: raw plus normalized market data, instrument catalog, coverage ledger, data quality reports, source provenance, hashes, and immutable snapshots.
3. **Automatic collection from multiple venues**: native Hyperliquid adapter first, then venue adapters through a common interface, with CCXT useful for standardized exchange coverage where it fits.
4. **Efficient backtest engine**: multi-instrument, deterministic, vectorized where possible, event-driven where needed, cost/funding/slippage-aware, and able to run many agent-generated ideas quickly.
5. **Agent-friendly experiment loop**: simple strategy specs, safe execution sandbox, standardized artifacts, and a central performance ledger/spreadsheet that agents append to only through a validating tool.
6. **Strict validation rules**: all reported strategy testing/backtesting must be on data from **2024-01-01 or later**; accepted backtests require at least **6 months** of usable data and should default to **12 months**; the most recent **1–2 full months** are a lockbox and must never be available to ordinary backtesting or agent iteration.

The most important architectural correction is this: **data collection is not a helper feature; it is the foundation**. Hyperliquid’s public candle endpoint only exposes the most recent 5,000 candles, while the official S3 archive is monthly, may be delayed or incomplete, and does not provide historical candles. That means the repo must maintain its own rolling archive if it wants 6–12 month backtests across many instruments at useful granularities.

---

## 2. Updated product definition

### 2.1 What the repository should become

ResearchEngineDeluxe should become a **perpetual-futures research operating system** with these layers:

```text
Venue adapters
  Hyperliquid native API / WebSocket / S3 archive
  CCXT-compatible exchanges where useful
  Future custom adapters for exchanges or vendors

Central archive
  raw immutable venue payloads
  normalized bronze/silver/gold Parquet datasets
  instrument catalog and as-of universe snapshots
  data quality, gap, and provenance metadata

Backtest data service
  fast filtered reads by venue, instrument, timeframe, field, and date
  deterministic snapshots by data_version / archive_snapshot_id
  no accidental access to lockbox months

Backtest engine
  strategy protocol
  vectorized multi-instrument path
  event-driven path for fills/order-book/slippage-sensitive ideas
  funding, fees, turnover, liquidity, borrow/carry, and missing-data handling

Agent lab
  strategy spec templates
  isolated run directory
  run manifest
  validation gate
  standardized metrics
  central performance ledger/spreadsheet append tool

Governance
  anti-overfitting controls
  command/path/security boundaries
  reproducible environments
  CI and benchmark gates
```

### 2.2 What should be removed from the old framing

The phrase “BTC/ETH perpetual-futures research workbench” should be replaced everywhere with something like:

> ResearchEngineDeluxe is a research-only platform for discovering, collecting, archiving, and backtesting strategies over liquid Hyperliquid perpetual futures and selected comparable venue data. The default universe is every Hyperliquid perp whose as-of daily notional volume is above USD 5 million, subject to coverage and validation gates.

The repo should not hardcode `BTC` and `ETH` as the research universe. BTC and ETH should remain fixture/smoke-test symbols because they are liquid and useful for fast CI, but they should not define the system scope.

### 2.3 What should remain from the previous roadmap

Keep these ideas because they still improve the repo:

- research-only boundary and no accidental live/promotion behavior;
- pickle artifact hardening;
- fail-closed webhook/operator secrets;
- explicit credential policy;
- operator UI cookie/admin hardening;
- ASGI worker separation;
- SQLite deployment constraint or job-store migration;
- command classification and path policy;
- dependency constraints and reproducibility;
- logging redaction;
- CI tiers and benchmark gates.

But reprioritize them around the new product. A security fix can remain P0 if it blocks safe operation, but the main roadmap should now be data/archive/backtest/agent-loop first.

---

## 3. External research that changes the plan

### 3.1 Hyperliquid universe and liquidity filtering

Hyperliquid’s `metaAndAssetCtxs` info request returns both a perpetual universe and per-asset context data. The context includes fields such as `dayNtlVlm`, funding, impact prices, mark price, mid price, open interest, oracle price, premium, and previous-day price. That directly supports the new requirement: select all perpetual instruments whose **daily notional volume exceeds USD 5,000,000**.

Practical implication: implement a `HyperliquidUniverseCollector` that stores a daily `universe_snapshot` and an `asset_context_snapshot`. Do not hardcode eligible coins.

### 3.2 Hyperliquid candles are not enough for long research

The official `candleSnapshot` endpoint supports common intervals, but only the most recent 5,000 candles are available. At 1-minute resolution, that is only a few days. At 15-minute resolution, it is roughly 52 days. At 1-hour resolution, it is roughly 208 days. That is insufficient for robust 6–12 month multi-instrument research at minute or 15-minute granularity.

Practical implication: use `candleSnapshot` for bootstrapping recent bars and gap checks, but not as the main historical archive. The project must record its own candles/trades/order-book data going forward and optionally backfill from official or licensed archives where possible.

### 3.3 Official historical archive is useful but incomplete for this goal

Hyperliquid’s historical data docs say data is uploaded to `hyperliquid-archive` approximately monthly, with no guarantee of timely updates and possible missing data. They also state that L2 book snapshots and asset contexts are available, but not historical candles; additional historical datasets must be recorded through the API by the user.

Practical implication: the central archive should combine:

- official S3 archive data for L2 and asset contexts where available;
- REST candle snapshots for recent bootstrap/gap repair;
- WebSocket streams for continuous trades, candles, L2, BBO, and asset contexts;
- funding history via the info endpoint;
- third-party historical vendors only if licensing and reproducibility are clear.

### 3.4 WebSocket capture is mandatory, not optional

Hyperliquid WebSocket subscriptions include `allMids`, `candle`, `l2Book`, `trades`, `bbo`, `activeAssetCtx`, and `allDexsAssetCtxs`. The docs also warn that automated users should handle server-side disconnects and reconnect gracefully.

Practical implication: build a capture daemon that treats reconnects, sequence gaps, duplicate messages, time drift, and backfill windows as first-class concerns. The daemon should write raw messages first, then normalized records.

### 3.5 Parquet/DuckDB/Polars are a good fit for the archive and backtester

Parquet is columnar and efficient for analytical reads. DuckDB can query Parquet directly and push filters/projections into scans. Polars lazy queries support whole-query optimization, parallelism, predicate pushdown, and projection pushdown.

Practical implication: CSV should be limited to fixtures and exports. The central archive should use partitioned Parquet with DuckDB/Polars as default read engines.

### 3.6 Time-series and investment backtest validation need stricter rules than random CV

`TimeSeriesSplit` exists because ordinary cross-validation can train on future data and evaluate on past data. Financial strategy mining also creates multiple-testing and backtest-overfitting risks; Bailey et al. propose Probability of Backtest Overfitting (PBO) using combinatorially symmetric cross-validation (CSCV) for investment simulations.

Practical implication: agent-generated strategy mining must record every trial, avoid random CV, use walk-forward or purged/embargoed time splits, and maintain a lockbox period that agents cannot touch.

---

## 4. Revised top priorities

| Rank | Priority | Work item | Why it matters now |
|---:|---|---|---|
| 1 | P0 | Dynamic Hyperliquid instrument universe manager | New scope is all liquid Hyperliquid perps, not BTC/ETH. |
| 2 | P0 | Central data archive with raw/normalized/provenance layers | 6–12 month multi-instrument backtests require owned historical data. |
| 3 | P0 | Continuous market-data collector | Hyperliquid candle history is limited; the repo must record data itself. |
| 4 | P0 | Efficient backtest data service | Agents need fast, deterministic reads without copying huge CSVs. |
| 5 | P0 | Strategy protocol and backtest engine | The system must run arbitrary ideas safely and consistently. |
| 6 | P0 | Validation gate: 2024+, minimum 6 months, lockbox 1–2 months excluded | Prevents shallow, stale, or overfit tests. |
| 7 | P0/P1 | Central performance ledger/spreadsheet append tool | Agents must write comparable results without manual spreadsheet drift. |
| 8 | P1 | Data quality and coverage reporting | Universe-wide research is useless if gaps and survivorship bias are hidden. |
| 9 | P1 | Worker separation for data collection/backtests | Heavy jobs should not run inside ASGI/operator server process. |
| 10 | P1 | Cross-venue adapter interface | The archive should pull comparable data from multiple venues, not just Hyperliquid. |
| 11 | P1 | Reproducibility: data snapshots, env lockfiles, artifact hashes | Enables later agents to reproduce claims. |
| 12 | P1/P2 | Existing security/hygiene hardening | Still valuable; keep it, but align it to the research platform. |

---

## 5. Target architecture

### 5.1 High-level architecture

```text
                         ┌─────────────────────────────┐
                         │  Agent / Human Researcher    │
                         └──────────────┬──────────────┘
                                        │ strategy spec / run request
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Agent Lab                                                            │
│ - spec templates                                                     │
│ - safe execution sandbox                                             │
│ - run manifests                                                      │
│ - performance ledger append tool                                     │
│ - no direct lockbox access                                           │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Backtest Engine                                                      │
│ - vectorized multi-instrument simulator                              │
│ - event-driven simulator where needed                                │
│ - funding/fees/slippage/liquidity models                             │
│ - walk-forward and anti-overfit validation                            │
└──────────────┬──────────────────────────────────────────────────────┘
               │ deterministic reads by snapshot_id
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Backtest Data Service                                                │
│ - DuckDB/Polars over partitioned Parquet                              │
│ - universe snapshots                                                  │
│ - coverage and quality filters                                        │
│ - lockbox exclusion enforcement                                       │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Central Data Archive                                                 │
│ raw/           immutable venue payloads                              │
│ bronze/        normalized source-equivalent records                  │
│ silver/        cleaned bars/trades/funding/context                   │
│ gold/          strategy-ready features/panels                         │
│ manifests/     source, hashes, coverage, data versions               │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Venue Collectors                                                     │
│ - Hyperliquid native REST/WebSocket/S3                                │
│ - CCXT-compatible venues where useful                                 │
│ - future custom exchange/vendor adapters                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Bounded contexts

The repo should split responsibilities into bounded packages or modules. Names can change, but the separation should remain:

| Context | Responsibility | Should not do |
|---|---|---|
| `venues` | API clients, rate limits, raw fetches, WebSocket capture | strategy logic, backtest scoring |
| `archive` | file layout, manifests, hashes, partitions, data versions | call exchange APIs directly except through adapters |
| `universe` | Hyperliquid liquid-perp selection, as-of snapshots, eligibility | cherry-pick only winning instruments |
| `data_quality` | gaps, duplicates, stale data, coverage reports | silently repair without provenance |
| `backtest_data` | efficient historical reads, panels, feature inputs | mutate archive data |
| `backtest_engine` | simulator, fills, costs, funding, metrics | network calls, credential access |
| `agent_lab` | strategy specs, run orchestration, ledger append | manual spreadsheet edits, lockbox leakage |
| `validation` | 2024+ gates, lockbox, walk-forward, PBO/CSCV | change strategy logic after seeing lockbox |
| `operator/web` | optional UI/control plane | execute heavy backtests in the ASGI loop |

---

## 6. Hyperliquid instrument universe manager

### 6.1 Eligibility rule

Default eligibility should be:

```text
eligible = instrument is a Hyperliquid perpetual
           AND dayNtlVlm >= 5_000_000 USD
           AND instrument is not disabled/delisted
           AND normalized market data coverage passes minimum requirements
```

Use daily notional volume from Hyperliquid asset context snapshots. Store the exact source timestamp and raw payload hash.

### 6.2 Current vs as-of universe

The system needs two universe modes:

1. **Current research universe**: today’s liquid perps above USD 5 million, useful for deciding what to collect and what agents should care about now.
2. **As-of backtest universe**: instruments that were eligible based only on information available at or before the backtest start or rebalance date.

This prevents survivor bias. A strategy should not get credit for selecting only today’s winners unless the experiment explicitly states that it is researching the current tradable universe and handles listing/coverage bias.

### 6.3 Universe snapshot tables

Create these archive tables:

#### `instrument_catalog`

| Column | Type | Notes |
|---|---:|---|
| `instrument_id` | string | Stable internal ID, e.g. `hyperliquid:perp:BTC`. |
| `venue` | string | `hyperliquid`, `binance`, `okx`, etc. |
| `venue_symbol` | string | Exact exchange symbol, including HIP-3 prefixes if present. |
| `canonical_symbol` | string | Normalized symbol used in strategy specs. |
| `market_type` | string | `perp`, `spot`, `future`; default scope is `perp`. |
| `base_asset` | string | BTC, ETH, SOL, etc. |
| `quote_asset` | string | Usually USD/USDC/USDT depending venue. |
| `settle_asset` | string | Usually USDC/USDT. |
| `first_seen_ts` | timestamp | First observed in archive. |
| `last_seen_ts` | timestamp | Last observed. |
| `status` | string | active, delisted, disabled, quarantine. |
| `sz_decimals` | int | Hyperliquid size precision where available. |
| `max_leverage` | decimal | Hyperliquid max leverage where available. |
| `only_isolated` | bool | Hyperliquid field where available. |
| `source_snapshot_id` | string | Raw source provenance. |

#### `universe_snapshot`

| Column | Type | Notes |
|---|---:|---|
| `snapshot_id` | string | Content hash or UUID. |
| `asof_date` | date | UTC date. |
| `venue` | string | Hyperliquid first. |
| `universe_rule_id` | string | Example: `hl_perps_day_ntl_vlm_gte_5m_v1`. |
| `instrument_id` | string | Internal ID. |
| `day_ntl_vlm_usd` | decimal | From asset context. |
| `open_interest` | decimal | From asset context. |
| `mark_px` | decimal | From asset context. |
| `oracle_px` | decimal | From asset context. |
| `funding` | decimal | Current funding estimate/rate. |
| `eligible` | bool | Final universe inclusion. |
| `exclusion_reason` | string | volume_below_threshold, insufficient_coverage, missing_context, etc. |
| `raw_payload_sha256` | string | Source hash. |

### 6.4 Universe update cadence

- Run `universe refresh` at least daily after UTC day close.
- Store raw `metaAndAssetCtxs` or equivalent payload before normalizing.
- If Hyperliquid returns multiple perp dexs, collect each dex and namespace symbols clearly.
- Never overwrite old universe snapshots.
- Add a test fixture where BTC/ETH pass, a low-volume coin fails, and a HIP-3 prefixed coin is handled correctly.

---

## 7. Central data archive

### 7.1 Archive design principle

The archive should be **append-only at raw level, deterministic at normalized level, and snapshot-addressable at research level**.

Agents should never directly modify archive files. Agents request data through the backtest data service, and every run records the `archive_snapshot_id`, `universe_snapshot_id`, and `feature_snapshot_id` it used.

### 7.2 Recommended layout

```text
data/archive/
  raw/
    venue=hyperliquid/
      datatype=meta_and_asset_ctxs/date=YYYY-MM-DD/run_id=.../*.jsonl.zst
      datatype=all_dexs_asset_ctxs/date=YYYY-MM-DD/run_id=.../*.jsonl.zst
      datatype=candles/interval=1m/date=YYYY-MM-DD/instrument=.../*.jsonl.zst
      datatype=trades/date=YYYY-MM-DD/hour=HH/instrument=.../*.jsonl.zst
      datatype=l2book/date=YYYY-MM-DD/hour=HH/instrument=.../*.jsonl.zst
      datatype=funding_history/date=YYYY-MM-DD/instrument=.../*.jsonl.zst
      datatype=s3_l2book/date=YYYY-MM-DD/hour=HH/instrument=.../*.lz4
  bronze/
    venue=hyperliquid/datatype=trades/date=YYYY-MM-DD/hour=HH/*.parquet
    venue=hyperliquid/datatype=candles/interval=1m/date=YYYY-MM-DD/*.parquet
    venue=hyperliquid/datatype=funding/date=YYYY-MM-DD/*.parquet
    venue=hyperliquid/datatype=asset_ctx/date=YYYY-MM-DD/*.parquet
  silver/
    bars/timeframe=1m/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    bars/timeframe=5m/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    bars/timeframe=1h/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    funding/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
    liquidity/venue=hyperliquid/date=YYYY-MM-DD/*.parquet
  gold/
    panels/timeframe=1m/universe_rule=hl_5m_v1/snapshot_id=.../*.parquet
    features/feature_set=.../snapshot_id=.../*.parquet
  manifests/
    ingestion_runs.parquet
    file_manifest.parquet
    data_coverage.parquet
    data_quality.parquet
    archive_snapshots.parquet
    universe_snapshots.parquet
  performance/
    experiment_ledger.parquet
    experiment_ledger.csv
    experiment_ledger.xlsx
```

### 7.3 Why not CSV as primary storage

CSV is acceptable for small fixtures, human exports, and compatibility, but it is not the right archive format for multi-instrument historical research. Use Parquet as the primary analytical format because it is columnar, compressed, and can be filtered by date/instrument/timeframe efficiently.

### 7.4 Data layers

| Layer | Purpose | Mutability | Example |
|---|---|---:|---|
| raw | Exact venue payloads or downloaded files | append-only | WebSocket trade JSON messages, S3 `.lz4` files |
| bronze | Parsed source-equivalent tables | rebuildable from raw | normalized trade rows, candle rows |
| silver | Cleaned research-ready market data | rebuildable with manifest | deduped OHLCV, funding, open interest, mark/oracle |
| gold | Feature panels and benchmark datasets | versioned snapshots | strategy-ready panels by universe and timeframe |

### 7.5 Minimum datasets

For the new goal, collect these first:

| Dataset | Why required | Source priority |
|---|---|---|
| instrument metadata | dynamic universe and precision | Hyperliquid `metaAndAssetCtxs` |
| daily asset context | volume threshold, OI, funding, mark/oracle | Hyperliquid `metaAndAssetCtxs`, WebSocket `allDexsAssetCtxs` |
| 1m candles | baseline strategy backtests | WebSocket candle capture + REST bootstrap |
| trades | slippage, volume validation, microstructure strategies | WebSocket trades, possible archive/vendor backfill |
| funding history | perp carry and net return | Hyperliquid `fundingHistory`, WebSocket/user-free market data where available |
| L2/BBO snapshots | liquidity filters, execution cost | WebSocket `l2Book`/`bbo`, official S3 L2 archive |
| data coverage | prevents fake performance due to gaps | internal manifests |

### 7.6 Data quality gates

Every archive snapshot should include:

- missing candle ratio by instrument/timeframe/day;
- duplicate timestamps and conflicting OHLCV rows;
- stale mark/oracle/funding records;
- abnormal zero-volume periods;
- time monotonicity checks;
- raw-to-bronze row count reconciliation;
- outlier checks for returns, spreads, and funding;
- delisting/listing status;
- coverage months available per instrument;
- whether the instrument qualifies for 6-month or 12-month testing.

A backtest should fail fast if the data slice does not meet the declared coverage threshold.

---

## 8. Venue adapters and automatic collection

### 8.1 Adapter interface

Create a stable interface like:

```python
class VenueAdapter(Protocol):
    venue: str

    def capabilities(self) -> VenueCapabilities: ...
    async def discover_markets(self) -> list[MarketDefinition]: ...
    async def fetch_asset_contexts(self, *, asof: datetime | None = None) -> list[AssetContext]: ...
    async def fetch_candles(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> list[Candle]: ...
    async def fetch_funding(self, symbol: str, start: datetime, end: datetime) -> list[FundingRate]: ...
    async def stream_trades(self, symbols: list[str]) -> AsyncIterator[Trade]: ...
    async def stream_candles(self, symbols: list[str], timeframe: str) -> AsyncIterator[Candle]: ...
    async def stream_l2(self, symbols: list[str]) -> AsyncIterator[OrderBookSnapshot]: ...
```

Keep native Hyperliquid support separate from CCXT. CCXT is useful for exchange normalization and broad coverage, but Hyperliquid-specific fields such as `dayNtlVlm`, HIP-3 dex prefixes, asset contexts, S3 archive layout, and WebSocket behavior need native handling.

### 8.2 Collection jobs

| Job | Cadence | Output | Notes |
|---|---:|---|---|
| `universe_refresh` | daily | raw context + `universe_snapshot` | all Hyperliquid perps above/below threshold, not just eligible |
| `recent_candle_bootstrap` | hourly/daily | recent 1m/5m/1h bars | limited by 5,000-candle API cap |
| `websocket_candle_capture` | continuous | raw + bronze candle messages | core archive builder |
| `websocket_trade_capture` | continuous | raw + bronze trades | needed for volume and slippage research |
| `websocket_l2_bbo_capture` | configurable | raw + bronze L2/BBO | storage-heavy; start with eligible universe or sampled snapshots |
| `funding_backfill` | daily | funding table | required for net perp returns |
| `official_s3_backfill` | monthly/manual | raw/bronze L2 and asset contexts | useful, but delayed and possibly incomplete |
| `coverage_audit` | daily | `data_coverage`, alerts | blocks unreliable backtests |

### 8.3 Storage and performance guardrails

L2 and trade data can become large. Start with a tiered collection policy:

- **Tier 1:** all eligible instruments, 1m candles, funding, daily contexts.
- **Tier 2:** trades for all eligible instruments, or at least the top N by notional volume until storage budget is proven.
- **Tier 3:** L2/BBO for top liquidity instruments and selected research campaigns.

Do not let the perfect tick archive block the basic 1m candle/funding archive. The first practical milestone is a complete 1m/carry/context archive for eligible instruments.

---

## 9. Backtest engine requirements

### 9.1 What “efficiently run any strategy” should mean

No engine can literally run any arbitrary code safely and comparably. In this repo, “any strategy” should mean:

> Any deterministic strategy idea that can be expressed through the supported strategy protocol, reads only approved historical datasets, declares its parameters, emits standardized target positions or orders, and can be evaluated with the repo’s cost, funding, and validation rules.

Support two strategy lanes:

1. **Declarative strategy specs** for agents: YAML/JSON expressions, indicators, thresholds, ranking rules, filters, entry/exit logic, and risk caps.
2. **Python strategy plugins** for advanced ideas: allowed only through a narrow `Strategy` protocol, no network, no credentials, no arbitrary file reads, and full run manifest capture.

### 9.2 Strategy protocol

A practical protocol:

```python
@dataclass(frozen=True)
class StrategyContext:
    run_id: str
    universe_snapshot_id: str
    archive_snapshot_id: str
    start: datetime
    end: datetime
    timeframe: str
    fee_model_id: str
    slippage_model_id: str
    lockbox_policy_id: str

class Strategy(Protocol):
    strategy_id: str
    version: str

    def required_inputs(self) -> StrategyInputs: ...
    def default_params(self) -> dict[str, Any]: ...
    def generate_signals(self, data: MarketPanel, params: dict[str, Any], ctx: StrategyContext) -> SignalFrame: ...
```

The engine converts `SignalFrame` into target positions/orders through a common portfolio and execution simulator.

### 9.3 Simulation layers

| Layer | Required behavior |
|---|---|
| price model | choose close, next-open, VWAP, mark, oracle, or event-driven fill basis explicitly |
| fee model | maker/taker, rebates if supported, conservative defaults |
| funding model | apply perp funding to open positions |
| slippage model | at least spread/volume-based; L2-aware when data exists |
| liquidity filter | cap participation rate and reject trades if volume/spread/OI insufficient |
| position model | support long/short/flat, leverage constraints, max notional, max concentration |
| missing data | fail or skip according to explicit policy; never silently forward-fill PnL-critical prices |
| multi-instrument alignment | common clock, per-instrument listing dates, missing bars handled deterministically |
| costs | report gross and net performance separately |

### 9.4 Data access API

Backtests should not open random files. They should request data through a stable API:

```python
panel = data_service.load_panel(
    universe_snapshot_id="...",
    instruments="eligible",
    timeframe="1m",
    start="2024-06-01",
    end="2025-05-31",
    fields=["open", "high", "low", "close", "volume", "funding", "open_interest"],
    exclude_lockbox=True,
    min_coverage=0.98,
)
```

This API should enforce:

- start date >= `2024-01-01` for reported strategy results;
- minimum usable duration >= 6 months;
- lockbox exclusion;
- coverage requirements;
- as-of universe validity;
- deterministic snapshot IDs.

### 9.5 Backtest outputs

Every run should produce:

```text
runs/<run_id>/
  run_manifest.json
  strategy_spec.yaml
  params.json
  data_manifest.json
  validation_manifest.json
  metrics.json
  equity_curve.parquet
  daily_returns.parquet
  trades.parquet
  positions.parquet
  per_instrument_metrics.parquet
  plots/optional
  log.txt
```

The `run_manifest.json` must include:

- git commit SHA;
- strategy ID and version;
- full parameter set;
- environment hash / lockfile ID;
- archive snapshot ID;
- universe snapshot ID;
- date windows;
- lockbox policy;
- trial group ID;
- parent experiment ID if this is an optimization run;
- agent/user ID;
- pass/fail status for every validation gate.

---

## 10. Agent-friendly research loop

### 10.1 Agent workflow

Agents should have a small number of safe commands:

```bash
# Discover current liquid Hyperliquid universe
redx universe refresh --venue hyperliquid --min-day-notional-usd 5000000

# Show coverage, not strategy results
redx data coverage --universe latest --timeframe 1m --since 2024-01-01

# Validate a strategy spec before running
redx strategy validate specs/strategies/my_strategy.yaml

# Run a single backtest with lockbox excluded
redx backtest run \
  --spec specs/strategies/my_strategy.yaml \
  --universe hl_5m_v1:2025-01-01 \
  --start 2024-06-01 \
  --end 2025-05-31 \
  --timeframe 1m \
  --exclude-lockbox

# Run a walk-forward validation
redx backtest walk-forward \
  --spec specs/strategies/my_strategy.yaml \
  --start 2024-01-01 \
  --end auto_non_lockbox_end \
  --min-window-months 6 \
  --exclude-lockbox

# Append results through a validating tool, not by editing the spreadsheet
redx ledger append --run runs/<run_id>/run_manifest.json
```

Agents should not directly edit central data, run outputs, or spreadsheets. They should call tools that validate schema and attach artifact hashes.

### 10.2 Strategy spec format

Example declarative spec:

```yaml
strategy_id: hl_cross_sectional_momentum_v1
version: 0.1.0
owner: agent
market_scope:
  venue: hyperliquid
  market_type: perp
  universe_rule: hl_perps_day_ntl_vlm_gte_5m_v1
inputs:
  timeframe: 1h
  fields:
    - close
    - volume
    - funding
    - open_interest
logic:
  signal_type: cross_sectional_rank
  lookback_hours: 168
  rank_metric: return
  long_top_quantile: 0.10
  short_bottom_quantile: 0.10
  filters:
    min_coverage: 0.98
    max_funding_abs: 0.001
risk:
  max_gross_leverage: 1.0
  max_instrument_weight: 0.05
  rebalance: 1h
execution:
  price_basis: next_bar_open
  fee_model: conservative_hyperliquid_taker_v1
  slippage_model: volume_participation_v1
validation:
  min_backtest_months: 12
  earliest_start: 2024-01-01
  exclude_lockbox: true
```

### 10.3 Central performance ledger/spreadsheet

The ledger should be append-only and machine-validated. The `.xlsx` spreadsheet can be the human-facing copy, but the canonical store should be Parquet/CSV plus run artifacts.

Required ledger columns:

| Column | Required | Notes |
|---|---:|---|
| `run_id` | yes | Unique immutable ID. |
| `experiment_id` | yes | Groups related trials. |
| `trial_index` | yes | Supports multiple-testing accounting. |
| `agent_or_user` | yes | Who/what initiated run. |
| `git_sha` | yes | Code provenance. |
| `strategy_id` | yes | Stable strategy ID. |
| `strategy_version` | yes | Strategy code/spec version. |
| `strategy_hash` | yes | Hash of strategy spec/code. |
| `params_hash` | yes | Hash of parameters. |
| `archive_snapshot_id` | yes | Data provenance. |
| `universe_snapshot_id` | yes | Universe provenance. |
| `feature_snapshot_id` | if used | Feature provenance. |
| `venue_scope` | yes | Hyperliquid, cross-venue, etc. |
| `instrument_count` | yes | Number actually traded/evaluated. |
| `timeframe` | yes | 1m, 5m, 1h, etc. |
| `backtest_start` | yes | Must be >= 2024-01-01. |
| `backtest_end` | yes | Must be before lockbox. |
| `usable_months` | yes | Must be >= 6. |
| `lockbox_policy_id` | yes | Shows current 1–2 month exclusion. |
| `lockbox_start` | yes | First excluded timestamp. |
| `lockbox_end` | yes | Last excluded timestamp or open-ended. |
| `data_coverage_min` | yes | Worst instrument/time coverage. |
| `gross_return` | yes | Before fees/slippage/funding. |
| `net_return` | yes | After fees/slippage/funding. |
| `annualized_return` | yes | Net. |
| `annualized_vol` | yes | Net. |
| `sharpe` | yes | Net returns. |
| `sortino` | should | Optional but useful. |
| `max_drawdown` | yes | Net equity. |
| `calmar` | should | Useful for ranking. |
| `turnover` | yes | Cost proxy. |
| `avg_daily_trades` | yes | Capacity/noise proxy. |
| `fee_paid` | yes | Simulated fees. |
| `funding_pnl` | yes | Perp funding contribution. |
| `slippage_cost` | yes | Simulated slippage. |
| `pbo_score` | if computed | Overfitting metric. |
| `walk_forward_pass` | yes | Boolean. |
| `validation_status` | yes | pass/fail/quarantine. |
| `failure_reason` | if failed | Do not hide failed trials. |
| `artifact_path` | yes | Run directory. |
| `artifact_sha256` | yes | Integrity. |
| `notes` | optional | Freeform but not used for ranking. |

### 10.4 Ledger ranking rules

Do not rank only by Sharpe. Use a composite report:

- pass/fail validation first;
- net return and drawdown;
- Sharpe/Sortino/Calmar;
- stability across walk-forward folds;
- performance by instrument bucket;
- turnover and cost sensitivity;
- performance decay across time;
- number of trials tried in the same experiment;
- PBO/CSCV or similar overfitting estimate where available;
- data coverage quality.

A failed strategy must still be written to the ledger. Hiding failed trials is one of the fastest ways to overfit with agents.

---

## 11. Validation and overfitting prevention

### 11.1 Hard date rules

These should be enforced in code, not just docs:

1. **No reported strategy backtest may start before `2024-01-01`.**
2. **No accepted backtest may use less than 6 months of usable data.**
3. **Default accepted research window should be 12 months where coverage exists.**
4. **The most recent 1–2 full months are lockbox data and must not be visible to ordinary backtest commands, optimization commands, leaderboard ranking, or agent iteration.**
5. **A warmup period may exist only for indicator initialization and must not contribute to reported PnL or metrics.**

Example lockbox policy on 2026-06-20:

```text
If lockbox_months = 2:
  lockbox_start = 2026-05-01 00:00:00 UTC
  ordinary_backtest_end <= 2026-04-30 23:59:59 UTC

If lockbox_months = 1:
  lockbox_start = 2026-06-01 00:00:00 UTC
  ordinary_backtest_end <= 2026-05-31 23:59:59 UTC
```

Use full calendar months to avoid ambiguity.

### 11.2 Lockbox access policy

Implement this as a physical and logical separation:

```text
data/archive/silver/.../date < lockbox_start      -> accessible to backtest
 data/archive/silver/.../date >= lockbox_start     -> inaccessible to ordinary backtest
```

The backtest data service should reject requests that overlap lockbox dates unless a special final-validation mode is used. Even then, final-validation output should not feed the ordinary agent leaderboard or parameter tuning loop.

### 11.3 Walk-forward validation

Minimum pattern:

```text
For each strategy:
  split non-lockbox 2024+ history into sequential folds
  train/tune only on earlier fold(s)
  validate on next fold
  roll forward
  record fold-level metrics
  require stability across folds
```

Use a `gap` or embargo around fold boundaries when labels or features use future horizons or rolling windows.

### 11.4 Overfitting controls for agent-generated strategies

Add these controls before allowing large agent sweeps:

- every trial is logged, including failures;
- parameter grids and search spaces are recorded before running;
- related trials share an `experiment_id`;
- leaderboard views show number of trials and best-vs-median performance;
- strategies are penalized for fragile performance concentrated in one instrument or one short period;
- PBO/CSCV-style diagnostics are computed for large strategy families;
- final candidate status requires passing walk-forward, cost sensitivity, instrument dispersion, and data-quality gates.

### 11.5 Disqualification rules

A run should fail validation if any of the following are true:

- backtest start before 2024-01-01;
- usable months < 6;
- overlaps lockbox period;
- missing `archive_snapshot_id` or `universe_snapshot_id`;
- data coverage below declared threshold;
- uses current universe in a way that creates survivor bias without labeling it;
- metrics are gross-only without net cost/funding report;
- strategy spec or params are not hashed;
- run is not appended to the ledger;
- run used external files/network/secrets not declared in manifest.

---

## 12. Revised findings

### F-GOAL-01 — BTC/ETH-only framing is now wrong

**Category:** Product / Architecture
**Severity:** high
**Confidence:** high

**Finding:** Any README, docs, tests, configs, fixtures, or CLI defaults that imply BTC/ETH are the whole research universe are now stale.

**Fix:** Replace product language with dynamic Hyperliquid liquid-perp universe. Keep BTC/ETH only as fast fixtures/smoke symbols.

**Acceptance criteria:** A `universe refresh` command can produce an eligible universe from a mocked Hyperliquid `metaAndAssetCtxs` payload where at least one non-BTC/ETH perp passes the USD 5M threshold.

---

### F-DATA-01 — Historical data archive is now the primary product dependency

**Category:** Data / Product
**Severity:** critical
**Confidence:** high

**Finding:** The new product requires 6–12 month historical tests across many instruments. Hyperliquid’s recent-candle API alone cannot provide that at useful intraday granularity.

**Fix:** Build central raw/bronze/silver/gold archive with continuous capture, source manifests, coverage checks, and Parquet storage.

**Acceptance criteria:** For a fixture universe, the archive can report coverage by instrument/timeframe/day and the backtest engine can load a deterministic panel from an archive snapshot.

---

### F-DATA-02 — Universe selection must be as-of, not hindsight-based

**Category:** Data / Validation
**Severity:** high
**Confidence:** high

**Finding:** Selecting today’s liquid instruments and backtesting them across the past can introduce survivor/listing/coverage bias.

**Fix:** Store daily universe snapshots and support as-of universe selection. Allow “current universe research” only when explicitly labeled.

**Acceptance criteria:** A backtest manifest states whether it used current or as-of universe, and validation warns/fails if a claimed historical result used hindsight selection.

---

### F-BT-01 — Backtest engine needs a formal strategy protocol

**Category:** Backtesting / Agent DX
**Severity:** high
**Confidence:** high

**Finding:** Agent-friendly “try any idea” will become chaos unless strategies share a protocol, data API, simulator, metric schema, and validation gates.

**Fix:** Implement declarative specs first, Python plugins second, all through a narrow interface.

**Acceptance criteria:** Two different strategies can run on the same data snapshot and write comparable metrics to the same ledger without custom result parsing.

---

### F-VAL-01 — Overfitting prevention must be enforced by the data service

**Category:** Validation / Research integrity
**Severity:** critical
**Confidence:** high

**Finding:** Docs alone cannot stop agents from testing against recent data or retrying until a strategy fits the latest month.

**Fix:** Lockbox dates must be enforced in the backtest data service and ledger validation. Ordinary backtest commands must not load lockbox rows.

**Acceptance criteria:** A test requesting data overlapping the lockbox fails before the strategy code runs.

---

### F-AGENT-01 — Performance spreadsheet must be append-only through a tool

**Category:** Agent DX / Reproducibility
**Severity:** high
**Confidence:** high

**Finding:** Manual spreadsheet edits will cause missing failed trials, inconsistent formulas, duplicate rows, and irreproducible claims.

**Fix:** Store canonical ledger as Parquet/CSV and export to XLSX/Google Sheets. Agents append only through `ledger append`, which validates artifacts and schemas.

**Acceptance criteria:** A run cannot appear in the leaderboard unless its run manifest, metrics, data snapshot, strategy hash, and validation status are present.

---

### F-OPS-01 — Research jobs and data collectors must be worker processes

**Category:** Ops / Architecture
**Severity:** high
**Confidence:** medium-high

**Finding:** The previous audits identified in-process operator jobs as a risk. Under the new goal, collectors and backtests are heavier and longer-running, so this risk becomes more important.

**Fix:** Keep ASGI/operator UI as control plane only. Run collectors/backtests in subprocesses or dedicated workers with durable job state.

**Acceptance criteria:** A long backtest or WebSocket capture does not block health/operator API responsiveness.

---

### F-SEC-LEGACY — Keep previous hardening work, but do not let it dominate product architecture

**Category:** Security / Repo hygiene
**Severity:** medium-high
**Confidence:** high

**Finding:** Webhook secret defaults, pickle loading, credential discovery, cookie hardening, path policies, and stale docs remain important. But the repo’s practical improvement now depends first on data/archive/backtest correctness.

**Fix:** Keep these as parallel P0/P1 safety packets, especially if affected code remains enabled. Do not delete them as “irrelevant.”

**Acceptance criteria:** Security fixes do not block archive/backtester work unless they touch the same files; they are tracked as separate packets.

---

## 13. Implementation roadmap

### Phase 0 — product spec migration and repo-state reset

**Goal:** Make the repo stop saying BTC/ETH-only and define the new platform contract.

Tasks:

- Update README/START_HERE/AGENTS/docs language to “liquid Hyperliquid perp universe,” not BTC/ETH-only.
- Add `docs/PRODUCT_SCOPE.md` with the USD 5M daily-notional rule.
- Add `docs/DATA_ARCHIVE_CONTRACT.md`.
- Add `docs/BACKTEST_VALIDATION_CONTRACT.md`.
- Keep prior repo hygiene/security TODOs, but move them under a supporting-hardening section.
- Freshly verify the repo state and mark stale audit docs historical.

Done criteria:

- No current-state doc claims BTC/ETH are the full research scope.
- The product contract states 2024+, 6–12 month minimum, and lockbox exclusion.
- A new agent can understand the data/archive/backtest objective in less than 10 minutes.

---

### Phase 1 — Hyperliquid universe manager

**Goal:** Dynamic list of eligible instruments.

Tasks:

- Add native Hyperliquid info client for `metaAndAssetCtxs`, `perpDexs`, and related context endpoints.
- Normalize universe metadata and asset context.
- Store raw payloads plus `instrument_catalog` and `universe_snapshot` tables.
- Implement threshold filter: `dayNtlVlm >= 5_000_000`.
- Add as-of universe selection.
- Add fixtures and tests for low-volume exclusions, non-BTC/ETH inclusions, HIP-3 prefixes, and missing context.

Done criteria:

- `redx universe refresh --venue hyperliquid --min-day-notional-usd 5000000` creates a snapshot.
- A test proves non-BTC/ETH instruments can be eligible.
- A test proves below-threshold instruments are archived but excluded.

---

### Phase 2 — central archive skeleton

**Goal:** Reliable storage before large backtests.

Tasks:

- Implement archive layout and manifest tables.
- Add raw JSONL/Zstd and Parquet writers.
- Add file hashing, byte size, row count, and schema version metadata.
- Add coverage reports.
- Add immutable snapshot IDs.
- Add CLI commands:
  - `archive init`
  - `archive validate`
  - `archive snapshot`
  - `data coverage`

Done criteria:

- A sample raw Hyperliquid payload can be normalized to bronze/silver Parquet.
- Coverage is queryable by instrument/date/timeframe.
- Archive snapshots are deterministic and referenced by backtest manifests.

---

### Phase 3 — collectors and backfill

**Goal:** Start building the 6–12 month dataset now.

Tasks:

- Implement recent REST candle bootstrap with awareness of the 5,000-candle cap.
- Implement WebSocket candle/trade/context capture.
- Implement funding history backfill.
- Implement S3 archive loader for official L2/asset contexts where useful.
- Add reconnect/gap handling.
- Add storage budget controls for trades and L2.
- Add alerting for capture downtime.

Done criteria:

- Collector can run continuously without corrupting archive.
- Reconnects produce gap records instead of silent holes.
- A coverage report shows daily data availability.

---

### Phase 4 — backtest data service

**Goal:** Fast, safe historical reads for agents and engine.

Tasks:

- Add DuckDB/Polars-backed panel loader.
- Enforce 2024+ and lockbox constraints at read time.
- Enforce coverage minimums.
- Support as-of universe snapshots.
- Support multi-timeframe reads.
- Add benchmark tests for common queries.

Done criteria:

- A request overlapping the lockbox fails.
- A request starting before 2024-01-01 fails for reported performance mode.
- A valid 6–12 month request returns a deterministic panel.

---

### Phase 5 — backtest engine and strategy protocol

**Goal:** Comparable strategy runs.

Tasks:

- Implement `Strategy` protocol.
- Implement declarative YAML strategy lane.
- Implement vectorized simulator.
- Implement funding, fees, and conservative slippage.
- Implement event-driven path only where required.
- Output standardized run artifacts.
- Add examples: momentum, mean reversion, funding/carry, volatility breakout, liquidity-filtered variants.

Done criteria:

- At least three strategy templates run over the same data snapshot.
- Metrics are comparable and net of costs/funding.
- Runs are reproducible by `run_manifest.json`.

---

### Phase 6 — performance ledger/spreadsheet

**Goal:** Agents write results safely and consistently.

Tasks:

- Implement canonical `experiment_ledger.parquet`.
- Export `.csv` and `.xlsx` views.
- Add `ledger append` validator.
- Add duplicate and failed-trial handling.
- Add leaderboard views that penalize multiple-testing and unstable folds.
- Add tests that invalid/missing manifests cannot enter the ledger.

Done criteria:

- Every accepted run has one ledger row.
- Failed runs can be logged and counted.
- Spreadsheet output is generated, not hand-edited.

---

### Phase 7 — anti-overfitting and validation hardening

**Goal:** Make agent iteration less likely to fool itself.

Tasks:

- Add walk-forward validation runner.
- Add purged/embargoed fold support where labels/features need it.
- Add PBO/CSCV spike for strategy families.
- Add cost sensitivity reports.
- Add instrument-bucket stability reports.
- Add “too many trials / weak median result” warnings.

Done criteria:

- Large sweeps produce both best strategy and overfitting diagnostics.
- Leaderboard shows trial counts and fold stability.
- Strategies can be rejected for fragile or overfit performance even if the headline Sharpe is high.

---

### Phase 8 — cross-venue expansion

**Goal:** Add additional venues without corrupting Hyperliquid-first design.

Tasks:

- Implement generic `VenueAdapter` interface.
- Add CCXT adapter where available.
- Add native adapters only when exchange-specific fields matter.
- Normalize symbols and market types.
- Add cross-venue data quality checks.
- Keep Hyperliquid USD 5M universe as the default strategy universe unless a spec declares otherwise.

Done criteria:

- Backtest data service can load comparable bars/funding for at least one non-Hyperliquid venue.
- Venue provenance is explicit in every row and run manifest.

---

### Phase 9 — supporting repo hardening

**Goal:** Keep old good ideas without derailing the product.

Tasks:

- Fail-closed webhook secret policy.
- Secure operator cookies/admin posture.
- Explicit credential loading policy.
- Pickle artifact hash/trusted-root validation.
- Command classification metadata.
- Path policy service.
- Dependency constraints.
- CI tiers and benchmarks.
- Logging redaction.

Done criteria:

- Security/hygiene risks from prior audits are either fixed or tracked with owners.
- Research/data/backtest commands remain isolated from live/order paths.

---

## 14. Agent ledger for implementation packets

### A0 — Product-scope migration

**Role:** documentation/product agent
**Objective:** Replace BTC/ETH-only framing with multi-instrument Hyperliquid perp research scope.
**Files:** README, START_HERE, AGENTS, docs scope files.
**Do not touch:** strategy algorithms or collectors.
**Acceptance:** docs state liquid Hyperliquid perp universe, USD 5M rule, 2024+ testing, 6–12 month minimum, lockbox exclusion.

### A1 — Hyperliquid universe collector

**Role:** data ingestion engineer
**Objective:** Build native collector for perpetual metadata and asset contexts.
**Files:** new `venues/hyperliquid`, `universe`, tests.
**Do not touch:** live order adapters.
**Acceptance:** fixture tests for eligibility and as-of snapshots pass.

### A2 — Archive manifest and layout

**Role:** data platform engineer
**Objective:** Implement archive directories, manifests, hashing, and Parquet writers.
**Files:** `archive`, `data_quality`, tests.
**Do not touch:** backtest strategy logic.
**Acceptance:** raw-to-bronze-to-silver fixture pipeline works and writes manifest rows.

### A3 — Continuous Hyperliquid capture

**Role:** market-data engineer
**Objective:** WebSocket/REST/S3 capture jobs for candles, trades, funding, asset context, L2 where configured.
**Files:** `venues/hyperliquid`, worker entrypoints, archive writers.
**Do not touch:** ledger or scoring.
**Acceptance:** reconnect/gap handling tested; coverage report updates.

### A4 — Data quality and coverage gates

**Role:** QA/data engineer
**Objective:** Detect gaps, duplicates, stale data, and insufficient coverage.
**Files:** `data_quality`, `archive/manifests`.
**Acceptance:** backtest cannot run when coverage is below threshold.

### A5 — Backtest data service

**Role:** analytics platform engineer
**Objective:** Fast DuckDB/Polars panel loader enforcing snapshots, dates, coverage, and lockbox.
**Files:** `backtest_data`.
**Acceptance:** lockbox overlap and pre-2024 starts are rejected in tests.

### A6 — Strategy protocol and declarative strategy lane

**Role:** backtest engine engineer
**Objective:** Allow agents to express ideas in validated specs and run through one simulator.
**Files:** `backtest_engine`, `strategies/specs`.
**Acceptance:** multiple example strategies run on same snapshot and emit same artifact schema.

### A7 — Metrics and cost model

**Role:** quant/backtesting engineer
**Objective:** Net-of-fees/funding/slippage metrics with per-instrument and fold-level reporting.
**Files:** `backtest_engine/metrics`, `execution_models`.
**Acceptance:** ledger includes gross/net, funding PnL, fee paid, slippage, drawdown, turnover.

### A8 — Ledger/spreadsheet writer

**Role:** agent tooling engineer
**Objective:** Validating append-only central performance ledger with XLSX export.
**Files:** `agent_lab/ledger`, `data/performance`.
**Acceptance:** invalid run manifests cannot be appended; failed trials can be appended and counted.

### A9 — Validation and anti-overfitting gates

**Role:** research validation engineer
**Objective:** Walk-forward, lockbox enforcement, trial logging, and PBO/CSCV spike.
**Files:** `validation`, `backtest_engine`.
**Acceptance:** ordinary backtests never touch recent 1–2 month lockbox; sweeps report trial counts.

### A10 — Worker separation

**Role:** platform engineer
**Objective:** Move collectors/backtests out of ASGI/operator loop.
**Files:** worker entrypoints, job queue/store, operator service.
**Acceptance:** long jobs do not block health/operator API.

### A11 — Cross-venue adapter

**Role:** venue integration engineer
**Objective:** Add generic venue interface and first non-Hyperliquid adapter.
**Files:** `venues/base`, `venues/ccxt`, tests.
**Acceptance:** cross-venue bars/funding can be archived with clear provenance.

### A12 — Existing security hardening

**Role:** security/config engineer
**Objective:** Preserve and implement useful prior audit items.
**Files:** config, operator UI, artifact loader, command registry, path policy.
**Acceptance:** fail-closed secrets, secure cookies, artifact hash checks, explicit credential loading, redaction tests.

---

## 15. Configuration examples

### 15.1 Universe config

```yaml
universe:
  id: hl_perps_day_ntl_vlm_gte_5m_v1
  venue: hyperliquid
  market_type: perp
  min_day_notional_usd: 5000000
  include_hip3_dexs: true
  refresh_cadence: daily
  timezone: UTC
  eligibility:
    require_active: true
    min_coverage_ratio: 0.98
    min_usable_months: 6
  storage:
    raw_payloads: true
    normalized_snapshots: true
```

### 15.2 Validation config

```yaml
validation:
  earliest_reported_backtest_start: "2024-01-01"
  minimum_usable_months: 6
  preferred_usable_months: 12
  lockbox:
    enabled: true
    months: 2
    align_to_full_calendar_months: true
    ordinary_backtests_can_access: false
    leaderboard_can_access: false
  folds:
    method: walk_forward
    embargo_bars: auto
    purge_overlapping_labels: true
  overfitting:
    log_all_trials: true
    require_experiment_id: true
    pbo_for_large_sweeps: true
```

### 15.3 Archive config

```yaml
archive:
  root: data/archive
  primary_format: parquet
  raw_format: jsonl.zst
  hash_algorithm: sha256
  engines:
    query: duckdb
    dataframe: polars
  partitions:
    bars: [venue, timeframe, date]
    trades: [venue, date, hour, instrument_id]
    funding: [venue, date]
    asset_context: [venue, date]
  lockbox_enforced_by: backtest_data_service
```

### 15.4 Ledger config

```yaml
ledger:
  canonical: data/archive/performance/experiment_ledger.parquet
  csv_export: data/archive/performance/experiment_ledger.csv
  xlsx_export: data/archive/performance/experiment_ledger.xlsx
  append_only: true
  require_validation_pass_for_leaderboard: true
  keep_failed_trials: true
  dedupe_keys:
    - run_id
    - strategy_hash
    - params_hash
    - archive_snapshot_id
```

---

## 16. Acceptance test suite additions

### 16.1 Universe tests

- `test_hyperliquid_universe_includes_non_btc_eth_above_5m`
- `test_hyperliquid_universe_excludes_below_5m_day_ntl_volume`
- `test_hyperliquid_universe_archives_excluded_instruments`
- `test_hyperliquid_universe_handles_hip3_prefixed_symbols`
- `test_asof_universe_does_not_use_future_volume_snapshot`

### 16.2 Archive tests

- `test_raw_payload_written_before_normalization`
- `test_file_manifest_has_sha256_size_rows_schema_version`
- `test_bronze_to_silver_rebuild_is_deterministic`
- `test_data_coverage_reports_missing_days`
- `test_archive_snapshot_id_changes_when_input_changes`

### 16.3 Backtest data service tests

- `test_reported_backtest_rejects_start_before_2024`
- `test_reported_backtest_rejects_less_than_6_months`
- `test_backtest_rejects_lockbox_overlap`
- `test_backtest_loads_only_declared_fields`
- `test_backtest_uses_asof_universe_snapshot`
- `test_warmup_bars_do_not_enter_reported_pnl`

### 16.4 Strategy and engine tests

- `test_declarative_strategy_validates_schema`
- `test_strategy_cannot_access_network_or_credentials`
- `test_same_run_manifest_reproduces_metrics_on_fixture_data`
- `test_funding_and_fees_affect_net_results`
- `test_missing_data_policy_is_explicit`

### 16.5 Ledger tests

- `test_ledger_append_rejects_missing_run_manifest`
- `test_ledger_append_rejects_missing_validation_status`
- `test_ledger_records_failed_trials`
- `test_ledger_rejects_duplicate_run_id`
- `test_xlsx_export_is_generated_from_canonical_ledger`

### 16.6 Overfitting tests

- `test_experiment_sweep_records_all_trials`
- `test_walk_forward_folds_are_time_ordered`
- `test_embargo_gap_excludes_boundary_rows`
- `test_leaderboard_warns_when_best_result_is_from_many_trials`

---

## 17. Practical first milestone

The first milestone should not attempt every venue or every market-data type. It should prove the full loop on a small but dynamic universe.

### Milestone M1: dynamic Hyperliquid 1m-bar research loop

Scope:

- Hyperliquid perps only.
- Universe from mocked or live `metaAndAssetCtxs` snapshot.
- Eligibility: `dayNtlVlm >= 5_000_000`.
- Data: 1m candles, funding, daily asset context.
- Storage: raw + silver Parquet + manifests.
- Backtest: vectorized bar engine.
- Strategies: 3 declarative examples.
- Validation: 2024+ start, minimum 6 months, lockbox exclusion.
- Ledger: append-only canonical file and XLSX export.

M1 acceptance:

```text
1. redx universe refresh creates a universe snapshot.
2. redx data coverage shows coverage by eligible instrument.
3. redx backtest run rejects pre-2024/short/lockbox-overlapping runs.
4. redx backtest run accepts a valid 6+ month non-lockbox window.
5. redx ledger append writes standardized run metrics.
6. A failed strategy trial is recorded rather than hidden.
```

This milestone is enough to make the repository useful to agents. L2, trades, cross-venue adapters, and PBO can follow without blocking the basic research loop.

---

## 18. What to defer or avoid

Do not do these first:

- Do not spend weeks perfecting live trading or promotion features before the archive/backtester exists.
- Do not hardcode a list of “good coins.” Use the USD 5M rule and snapshots.
- Do not let agents edit spreadsheets manually.
- Do not run leaderboards on the lockbox period.
- Do not accept one-week or one-month “good looking” backtests.
- Do not store large research archives as loose CSV files.
- Do not use today’s eligible universe for historical claims without labeling the survivor-bias risk.
- Do not let heavyweight collectors/backtests run in the ASGI process.
- Do not delete prior security hardening ideas; track them separately if they are not part of the first data milestone.

---

## 19. Updated risk register

| Risk | Probability | Impact | Mitigation |
|---|---:|---:|---|
| Hyperliquid API candle history insufficient for 6–12 month tests | High | Critical | Own archive, WebSocket capture, official S3/vendor backfill where available |
| Agents overfit by repeatedly testing recent months | High | Critical | Physical/logical lockbox exclusion and trial ledger |
| Survivor bias from current liquid universe | High | High | As-of universe snapshots and explicit current-universe labeling |
| Data gaps silently inflate performance | Medium-high | High | Coverage gates and gap manifests |
| Spreadsheet becomes inconsistent | High | Medium-high | Append-only validated ledger and generated XLSX export |
| L2/trade storage explodes | Medium | Medium-high | Tiered collection policy and storage budgets |
| Backtester too slow for agent iteration | Medium | High | Parquet + DuckDB/Polars + vectorized path + benchmarks |
| Cross-venue symbols are misnormalized | Medium | High | Instrument catalog with venue/canonical IDs and adapter tests |
| ASGI/operator process blocked by research jobs | Medium-high | High | Dedicated workers/subprocess runner |
| Old security issues remain in live-adjacent code | Medium | High | Keep prior hardening tasks as separate P1/P2 packets |

---

## 20. Final handoff summary

The revised direction is clear: ResearchEngineDeluxe should become a **data-first, multi-instrument, Hyperliquid-perp research platform**. The archive and backtest engine are now the main product, not side features. The repo should automatically discover all Hyperliquid perpetual futures above USD 5 million daily notional volume, collect and normalize data from Hyperliquid and later other venues, maintain a central historical archive, expose fast deterministic data snapshots to a backtest engine, and let agents run strategies through a safe protocol that writes every result into a central performance ledger.

The strict validation rules should be enforced in code:

- reported strategy tests/backtests only use data from 2024-01-01 onward;
- accepted backtests require at least 6 months and should prefer 12 months;
- the most recent 1–2 full months are lockbox data and ordinary backtests/agents cannot access them;
- every trial, including failures, is recorded;
- all results reference strategy, parameter, git, data, universe, and validation manifests.

The next best implementation packet is **not** another generic repo audit. It is:

1. migrate docs/product scope away from BTC/ETH;
2. implement Hyperliquid universe snapshots with the USD 5M `dayNtlVlm` rule;
3. build the central archive skeleton and coverage manifests;
4. add the backtest data service with 2024+/6-month/lockbox enforcement;
5. add the strategy protocol and ledger append tool.

Once that loop exists, agents can safely and quickly try ideas, compare results, and improve the repository without turning it into an untraceable pile of one-off scripts and cherry-picked spreadsheets.

---

## References used for the v2 update

- Hyperliquid Info endpoint docs: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
- Hyperliquid Perpetuals info docs: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals
- Hyperliquid historical data docs: https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data
- Hyperliquid WebSocket docs: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket
- Hyperliquid WebSocket subscriptions docs: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions
- Chainstack Hyperliquid `metaAndAssetCtxs` reference: https://docs.chainstack.com/reference/hyperliquid-info-meta-and-asset-ctxs
- Chainstack Hyperliquid `fundingHistory` reference: https://docs.chainstack.com/reference/hyperliquid-info-funding-history
- CCXT Hyperliquid docs: https://docs.ccxt.com/docs/exchanges/hyperliquid
- CCXT contract naming docs: https://github.com/ccxt/ccxt/wiki/manual
- DuckDB Parquet docs: https://duckdb.org/docs/current/data/parquet/overview.html
- DuckDB querying Parquet docs: https://duckdb.org/docs/current/guides/file_formats/query_parquet.html
- Polars LazyFrame docs: https://docs.pola.rs/py-polars/html/reference/lazyframe/index.html
- Polars optimization docs: https://docs.pola.rs/user-guide/lazy/optimizations/
- scikit-learn `TimeSeriesSplit`: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- Bailey et al., Probability of Backtest Overfitting / CSCV: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
