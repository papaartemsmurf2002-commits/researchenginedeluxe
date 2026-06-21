# Research Roadmap Direction Comparison - 2026-06-20

Packet: `WPR106-388-multi-venue-perp-roadmap-ingest-and-direction-comparison`

## Imported Source

The external roadmap has been imported unchanged as:

- `docs/RESEARCH_ENGINE_DELUXE_V2_MULTI_VENUE_PERP_RESEARCH_ROADMAP.md`

This comparison treats that roadmap as a product-scope proposal until a later
orchestrator packet explicitly adopts it as authoritative. It does not change
research/live boundaries, candidate gates, data contracts, runtime behavior, or
promotion status.

## Documents Compared

| Document | Date | Direction |
| --- | --- | --- |
| `docs/RESEARCH_V4_IMPLEMENTATION_AGENT_HANDOFF.md` | 2026-05-07 | Build a durable research-only discovery engine with checkpointed long runs, HMM/GMM/KNN truthfulness, immutable trial records, and no promotion authority. |
| `docs/RESEARCH_NEXT_PHASE_REAL_STRATEGIES_FILTERS_FEATURES_PLAN.md` | 2026-05-11 | Stop chasing top scores; harden strategy truthfulness, independent events, exit lab, filter ablation, multiple-testing gates, and durable BTC/ETH evidence before adding more strategies. |
| `docs/NEXT_AGENT_HANDOFF_WPR106_85_2024_FORWARD_BROAD_STRATEGY_SEARCH.md` | 2026-06-10 | Run broad 2024-forward BTC/ETH strategy searches with May 2026 as a hard holdout, realistic costs, monthly stability, ablations, negative controls, and no candidate claims without gates. |
| `docs/work_packets/WPR106-228-rapid-strategy-iteration-sandbox-foundation.md` | 2026-06-18 | Add a rapid sandbox beside strict validation so agents can triage strategy catalogs and local multi-venue archive descriptors quickly, while emitting only descriptor-only validation requests. |
| `docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md` | 2026-06-20 | Current authoritative roadmap: finish the rapid sandbox product around local 2024+ archive roots, bounded sweeps, artifact catalogs, next-action dashboards, strict-validation descriptor handoffs, and performance proof. |
| `docs/RESEARCH_ENGINE_DELUXE_V2_MULTI_VENUE_PERP_RESEARCH_ROADMAP.md` | 2026-06-20 | Proposed v2 pivot: make the core product a data-first, multi-instrument Hyperliquid perpetual research platform with dynamic universe discovery, owned archive, continuous collectors, data service, backtester, and central ledger. |

## Executive Comparison

The v2 roadmap is not just a refinement of the current roadmap. It changes the
center of gravity.

Current repo direction is:

```text
existing strategy/catalog sources + explicit local 2024+ archives
  -> rapid sandbox triage
  -> artifact catalog / blocker queues / next actions
  -> descriptor-only strict-validation handoff
  -> strict research cycle remains the validator
```

The v2 roadmap direction is:

```text
dynamic Hyperliquid universe discovery
  -> continuous raw and normalized venue archive
  -> deterministic data snapshots and lockbox-aware reads
  -> multi-instrument backtest engine
  -> append-only performance ledger
  -> agent iteration over all liquid perps
```

They are compatible at the boundary level: both preserve research-only,
observe-only, non-promotable outputs and both reject shallow, overfit evidence.
They differ on product priority. The existing roadmap finishes an agent sandbox
around local archive descriptors. The v2 roadmap says the main product is now
the archive/universe/data-service layer itself.

## Main Differences

| Topic | Previous/current direction | Imported v2 roadmap |
| --- | --- | --- |
| Default universe | BTC/ETH are the canonical research identity, with sandbox support for multi-venue descriptors. | All Hyperliquid perpetuals above USD 5M daily notional volume; BTC/ETH become fixtures and smoke symbols, not the product scope. |
| Data posture | Use checked fixtures, local Binance/OKX/Bybit/Hyperliquid/archive descriptors, and explicit local roots. No downloads in sandbox materializer packets. | Own a central archive. Discover, collect, normalize, and snapshot Hyperliquid data continuously; later add compatible venue adapters. |
| Historical coverage rule | 2024-forward search; May 2026 has been used as a named hard holdout in recent packets. | Reported tests must use 2024+ data, require at least 6 months, prefer 12 months, and exclude the latest 1-2 full months as a rolling lockbox. |
| Engine focus | Strict research cycle plus rapid sandbox triage and descriptor-only strict-validation handoffs. | Backtest data service and backtest engine become first-class product layers. |
| Agent loop | Agents ingest strategy catalogs and archive descriptors, run bounded sweeps, index artifacts, and request strict validation. | Agents run strategies against deterministic archive snapshots and append all outcomes, including failures, to a central performance ledger/spreadsheet. |
| Venue expansion | Local-root materializer and descriptor candidates; no provider downloads or source mutation in the current sandbox roadmap. | Hyperliquid native REST/WebSocket/S3 collection first; cross-venue adapter interface later. |
| Performance layer | Sandbox throughput telemetry, memory reductions, bounded archive scanning, and no speed claim without artifacts. | Parquet/DuckDB/Polars are the intended data-service substrate. |
| Governance | Strong research/live boundary, candidate-pack gates, artifact integrity, strict-validation descriptor preflight. | Same boundary, plus stronger data-governance primitives: universe snapshots, archive snapshots, coverage ledgers, lockbox enforcement, and append-only experiment ledger. |

## Development Status

Relative to the current authoritative completion roadmap, development is far
along.

- The strict research stack already exists: data contracts, feature registry,
  strategy registry, backtesting, research cycle, discovery, candidate-pack
  gates, live-boundary tests, and operator surfaces.
- BTC/ETH research has produced extensive negative evidence. The current stage
  repeatedly ended fail-closed with no candidate pack, no paper/live artifact,
  no sizing/order/runtime change, and no promotion claim.
- The rapid sandbox has progressed from foundation to a broad local archive and
  agent-navigation toolchain. Current commands include rapid sandbox runs,
  suites, summaries, artifact indexing, archive audits, archive manifest
  building, strategy catalog building, iteration runs, preflight, venue
  expansion request export/materialization, strict-validation request export
  and preflight, next-action dashboard, throughput summaries, artifact
  verification, and ranking.
- Recent packets closed publication coherence, CI coverage, materializer,
  dashboard, strict-validation descriptor preflight, container-loader bounds,
  source-discovery bounds, and memory-pressure issues. The latest WPR106-387
  validation recorded full sandbox, contracts, live CLI boundary, compile, and
  full-suite validation passing with 1896 passed, 1 skipped, and one XGBoost
  device warning.
- `docs/KNOWN_ISSUES.md` currently reports no open P0 or P1 issue. The open
  items are P2-level, including a local Windows socket exhaustion condition
  that can block contract-baseline collection in this Windows session.

Relative to the imported v2 roadmap, development is only partially aligned.

- The repo has multi-venue sandbox descriptors and local archive loading, but
  not a first-class central archive service.
- The repo has Hyperliquid-adjacent code and a Hyperliquid SDK dependency, but
  a code scan did not find an implemented `metaAndAssetCtxs`/`dayNtlVlm`
  universe collector in `tradingbotsuite`.
- The repo has many sandbox commands and artifact ledgers, but not the v2
  `experiment_ledger.parquet` append-only performance ledger.
- The repo has 2024+ enforcement in sandbox surfaces, but not the v2 rolling
  1-2 full month lockbox enforced by a backtest data service.
- The repo has Parquet-heavy research artifacts, but `duckdb` and `polars` are
  not current project dependencies.
- The repo can scan explicit local roots, but it is not yet a continuous
  WebSocket/REST/S3 collector that owns forward history for all liquid
  Hyperliquid perps.

## Direction Compatibility

### Compatible

- Research-only, observe-only, non-promotable outputs.
- 2024+ modern-market evidence requirement.
- Fail-closed validation and explicit blocker reasons.
- Need for data provenance, hashes, manifests, and reproducible artifacts.
- Agent-friendly iteration with standardized artifacts.
- Trial logging and multiple-testing controls.
- Multi-venue eventual scope.

### Tension Or Conflict

- `docs/ACTIVE_INDEX.md` still defines the canonical identity as a modular
  BTC/ETH perpetual-futures research engine. The v2 roadmap says that framing
  is outdated and should be replaced by liquid Hyperliquid-perp universe scope.
- The current completion roadmap intentionally avoids provider downloads in
  sandbox materializer packets. The v2 roadmap makes continuous provider
  collection a primary product objective.
- The current sandbox is a triage layer whose outputs are not candidate
  evidence. The v2 roadmap's ledger/backtester could be misread as stronger
  validation unless it inherits the same fail-closed gate language.
- The current May 2026 holdout policy is a fixed recent holdout for the
  2024-forward search. The v2 roadmap generalizes this into a rolling latest
  1-2 full month lockbox. That is a better long-term rule but needs migration
  work so old reports are not reinterpreted.
- The current roadmap already completed several materializer/dashboard/bridge
  packets. The v2 roadmap would reprioritize away from remaining sandbox polish
  toward archive and universe services.

## What Needs To Be Done

If the repo stays on the current authoritative roadmap, the next work should be
limited to the active-index guidance: newly discovered blocker repairs,
broader inherited publication cleanup, and measured performance proof. Do not
rerun the completed materializer sequence.

If the v2 roadmap is adopted, the next work should start with an explicit
product-scope migration packet, not with a collector daemon:

1. Open an A0-style documentation and contract packet that decides whether
   canonical identity changes from BTC/ETH to liquid Hyperliquid perpetuals.
   Update `README.md`, `START_HERE.md`, `docs/ACTIVE_INDEX.md`, roadmap docs,
   and boundary/contracts only after that decision is explicit.
2. Define central archive contracts before collecting data: archive root,
   raw/bronze/silver/gold layers, manifest schemas, source hashes, coverage
   ledgers, immutable snapshot IDs, and research-only metadata.
3. Implement a fixture-backed Hyperliquid universe snapshot collector for
   `metaAndAssetCtxs`/`dayNtlVlm` first. It should prove USD 5M eligibility,
   as-of snapshots, excluded-instrument archival, no future-volume leakage,
   and no live order imports.
4. Add the backtest data-service gate around existing local data before
   launching continuous capture: 2024+ start, minimum 6 usable months,
   preferred 12 months, rolling 1-2 full month lockbox exclusion, as-of
   universe snapshots, and coverage minimums.
5. Add the central experiment ledger as a validating append-only artifact.
   It should accept failed trials, reject missing manifests, dedupe run IDs,
   export CSV/XLSX views from the canonical table, and remain non-promotable.
6. Only then build the continuous Hyperliquid collector. The daemon should
   write raw payloads before normalization, record reconnect/gap evidence, and
   avoid running inside the ASGI/operator process.
7. Treat DuckDB/Polars/CCXT as explicit dependency decisions with tests and
   lockfile/reproducibility notes, not incidental imports.

## Practical Direction Decision

The v2 roadmap is directionally strong and better matches a scalable research
platform, but it is a pivot. It should not silently supersede
`docs/RESEARCH_ENGINE_DELUXE_COMPLETION_ROADMAP.md` until a scope packet
updates the active index, canonical identity, and contracts.

Recommended decision:

```text
Adopt v2 as the next product-scope target after closing or freezing the current
rapid-sandbox completion line. Do not discard the sandbox work. Reclassify it
as the agent lab and fast triage layer that will sit above the future central
archive/data-service layer.
```

That gives a coherent architecture:

```text
Hyperliquid universe + central archive
  -> backtest data service with lockbox and coverage gates
  -> existing strict research cycle for validation
  -> existing rapid sandbox for idea triage and catalog iteration
  -> central ledger and dashboard for agent navigation
```

## Bottom Line

The repo is developing well under the current direction: the strict research
pipeline and rapid sandbox are substantially built, validated, and fail-closed.
The major gap is that the current system is still archive-descriptor and
BTC/ETH-history centered. The imported v2 roadmap asks for the missing platform
foundation: dynamic Hyperliquid universe discovery, owned historical data,
snapshot-aware data reads, lockbox enforcement, and an append-only performance
ledger.

The next best implementation packet, if v2 is accepted, is A0 product-scope
migration plus archive/universe contracts. Starting with WebSocket collection
or broad strategy search before those contracts would recreate the exact
provenance and overfitting risks the repo has spent R106 hardening against.
