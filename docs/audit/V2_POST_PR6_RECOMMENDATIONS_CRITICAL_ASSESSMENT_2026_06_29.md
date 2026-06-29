# V2 Post-PR6 Recommendations Critical Assessment

Date: 2026-06-29
Packet: `docs/work_packets/WPR106-566-post-pr6-audit-and-next-agent-goal.md`
Input report: `C:/Users/papaa/Downloads/POST_PR6_RECOMMENDATIONS.md`
Reviewed PR6 commit: `e39aed3 finish pr5 follow-up scale path`

## Boundary

This is a docs-only audit. It does not change source behavior, tests,
generated evidence, ledgers, Lead Book rows, archive data, runtime mode, live
code, paper code, order placement, sizing, promotion, or candidate-pack truth.

Per owner instruction, the post-PR6 report section about trade-frequency and
losing-month validation is ignored. This assessment does not recommend changing
those policies.

## Verdict

The post-PR6 recommendation report is directionally correct and should be
pursued, with one priority adjustment:

```text
Archive intelligence and data-requirement resolution should be the next
highest-priority implementation target.
```

PR6 already completed the first practical scale step: it added a fast lane,
columnar loading surface, strict spread mode, part-backed ledgers, OF Parquet
parts, and bounded Bybit/OKX pagination helpers. The repo is no longer blocked
on the original PR5 math/performance issues.

The next bottleneck is agent efficiency and sweep ergonomics: agents need to
know what data exists, what a strategy requires, what is missing, and when a
fast/summary run is trustworthy enough to continue.

## PR6 Work Audit

### Confirmed As Implemented

- `fast_vectorized` engine lane exists in
  `src/tradingbotsuite/v2/backtest_engine/engine.py`.
- `BacktestColumnarDataSlice` and `load_panel_columnar()` exist in
  `src/tradingbotsuite/v2/backtest_data/**`.
- Reference-versus-fast parity tests exist in
  `tests/v2/test_backtest_engine_phase11.py` and
  `tests/v2/test_backtest_engine_phase12.py`.
- USD `account_notional_usd`, `trade_notional_usd`, and participation math are
  present in cost/backtest artifacts.
- Monthly validation folds and diagnostic `full_window` folds exist.
- `spread_observation_policy=accepted_research_strict` exists.
- Ledger append parts, append log, sidecar part index, and
  `compact_ledger_parts()` exist in `src/tradingbotsuite/v2/ledger/service.py`.
- OF-style `parquet_parts` output exists in
  `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`.
- Bounded Bybit/OKX paginated request planning and injected-probe fetch helpers
  exist in `src/tradingbotsuite/v2/data_sources/bybit_okx.py`.

### Important Limitations

- The fast lane is a first NumPy implementation, not a finished high-throughput
  sweep system. It still uses Python signal compilation when no `SignalFrame`
  is supplied, converts several Arrow columns through `to_pylist()`, and writes
  full artifacts.
- Fast-lane parity coverage is fixture-level. There is no policy yet for
  routine sampled reference audits during large sweeps.
- There is no `archive_inventory` package, archive inventory CLI, or strategy
  data-requirement resolver.
- There is no structured `DataGapRequest` flow.
- There is no `artifact_mode = full | summary | metrics_only`.
- Ledger parts are currently one Parquet file per appended row. This avoids
  full-ledger rewrites but will create many tiny files in long sweeps.
- Ledger reads concatenate all part tables into memory before validation and
  leaderboard operations.
- OF Parquet part output is useful, but materializers still aggregate each
  source into in-memory bucket dictionaries before writing output parts.
- OF feature part indexes are per materialization output; there is no central
  feature-store catalog for discovery across materialized features.
- Venue probe expansion is now correctly low priority. Additional venues should
  be added only after inventory/resolver evidence proves missing data.

## Recommendation Assessment

| Recommendation | Assessment | Priority |
| --- | --- | --- |
| Archive inventory/discovery tools | Correct and not implemented. This should be next. | Very high |
| Strategy data-requirement resolver | Correct and not implemented. Pair with inventory. | Very high |
| Fast-lane rollout with parity audits | Correct. PR6 added fast lane, but not the rollout policy. | High |
| Artifact-light mode | Correct and not implemented. Likely the next bottleneck after fast lane. | High |
| Ledger part batching | Correct. PR6 parts are one row each. | Medium/high |
| Streaming/parallel OF materialization | Correct. PR6 part output is not streaming source processing. | Medium |
| Archive-first agent rule | Correct. Should be added once inventory/resolver exist. | High |
| Collector adapter template | Correct, but after resolver/gap request. | Medium |
| Data gap request objects | Correct. Should be part of resolver design. | Medium/high |
| Fast-lane benchmark suite | Correct. Useful after fast-lane audit policy. | Medium |
| Feature-store catalog | Correct. Useful with OF materialization and derived features. | Medium |
| More venue probes | Correctly low priority. Do only on proven gaps. | Low |
| GPU acceleration | Correctly low priority. CPU/Arrow/NumPy path comes first. | Low |
| Full event-driven backtest | Correctly deferred until queue/intrabar research requires it. | Low/medium |

## Corrected Priority Order

### 1. Archive Inventory And Data Requirement Resolver

Implement first. This prevents agents from collecting data that already exists
and gives every strategy idea a deterministic answer:

- can it be tested now;
- on which instruments;
- over which date ranges;
- with which evidence mode;
- what fields/families are missing;
- whether collection is forbidden, unnecessary, or narrowly needed.

This should include `DataGapRequest` objects and a rule that future agents must
query inventory/resolver before writing collectors or collecting data.

### 2. Fast-Lane Rollout Policy And Parity Audit

PR6 added the fast lane. The next step is controlled use:

- new families and small fixtures run reference plus fast lane;
- large sweeps default to fast lane;
- a configured sample rate reruns reference parity audits;
- suspicious results can be replayed under reference engine and stricter costs.

### 3. Artifact-Light Sweep Mode

Full artifacts are valuable for auditability, but large sweeps should not write
full positions/trades/equity for every weak run. Add:

- `full`;
- `summary`;
- `metrics_only`;
- deterministic replay-to-full.

### 4. Ledger Part Batching

Upgrade one-row ledger parts to multi-row batches with configurable row and
size limits. Keep compaction and hash/index integrity.

### 5. Feature Store Catalog And Streaming OF Materialization

Add a discoverable feature catalog for materialized OF/funding/OI/derived
features. Then improve OF materializers to stream source rows, flush bucket
windows, and optionally process sources in parallel.

### 6. Collector Template And Optional Venue Probes

Only after inventory/resolver can prove a gap, add collectors through a
research-only adapter template. More venues are a response to a proven data gap,
not a default project direction.

## Things The Next Agent Should Not Do

- Do not change trade-frequency or losing-month policy from this audit.
- Do not add venues by default.
- Do not treat gitignored local archive data as missing.
- Do not collect data before inventory/resolver says the slice is missing.
- Do not remove the Python reference engine.
- Do not weaken PR5/PR6 math fixes.
- Do not touch live, paper, order-placement, sizing, runtime-mode, promotion,
  candidate-pack, secret, local-state, or generated-evidence paths.

## Recommended Next Work Packet

The next implementation packet should be:

```text
docs/work_packets/WPR106-567-v2-archive-inventory-and-data-requirement-resolver.md
```

Its first deliverables should be:

- archive inventory schemas and service;
- archive inventory CLI/search;
- strategy data-requirement resolver;
- structured `DataGapRequest`;
- archive-first agent rule in docs;
- fixture-backed tests proving agents can discover existing data and avoid
  unnecessary collection.

After WPR106-567, continue with fast-lane rollout policy, artifact-light mode,
ledger part batching, and streaming feature-store work.
