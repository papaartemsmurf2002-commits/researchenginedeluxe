# V2 Roadmap Implementation Status

Status: v2 foundation, bounded-loop, and historical dataset/data-source surfaces self-checked through WPR106-524 final-audit handoff
Source roadmap: `docs/REDX_V2_READY_TO_USE_IMPLEMENTATION_ROADMAP_2026_06_20.md`
Closeout packet: `docs/work_packets/WPR106-414-v2-roadmap-milestone-status-closeout.md`
Control-doc sync: `docs/work_packets/WPR106-415-v2-control-doc-sync-and-completion-audit.md`
Latest readiness sync: `docs/work_packets/WPR106-472-v2-readiness-doc-ci-full-suite-closeout.md`
Latest data collection sync: `docs/work_packets/WPR106-521-v2-gold-panel-materializer.md`
Latest bounded-loop data-load sync: `docs/work_packets/WPR106-522-v2-backtest-data-load-worker-loop-wiring.md`
Latest archive-ref cycle sync: `docs/work_packets/WPR106-523-v2-archive-ref-cycle-spec.md`
Latest final-audit handoff sync: `docs/work_packets/WPR106-524-v2-final-audit-readiness-closeout.md`

## Boundary Statement

The v2 roadmap foundation is research-only. No packet in this implementation
sequence creates a candidate-ready, paper-ready, live-ready, order-placement,
sizing, runtime-mode, or promotion-ready claim. Research outputs remain
`research_only`, `observe_only`, and `promotion_ready: false` unless a later
explicit promotion process changes them.

At closeout time, `docs/KNOWN_ISSUES.md` reports no open P0 issues and no open
P1 issues. WPR106-473 opens one P2 operational data-source issue,
`ISSUE-R106-030`, for old Hyperliquid public intraday candle windows returning
empty while daily history works. Phase 22 UI is
self-checked as a read-only static visibility surface. WPR106-469 through
WPR106-471 prove the bounded public diagnostic loop can execute all required
durable stages while preserving blocker evidence; WPR106-472 closes the stale
README/CI/full-suite validation gaps. WPR106-473 adds bounded historical
current-universe Hyperliquid candle/funding collection plus Binance kline
sanity validation, but keeps the generated reports sandbox diagnostic because
the universe is still current-public rather than historical as-of. WPR106-524
records the final-audit handoff state: the foundation is ready for independent
final audit after clean handoff validation, while agentic strategy testing
remains blocked until that audit and separate readiness evidence pass.

## Phase Coverage

| Phase | Status | Evidence |
| --- | --- | --- |
| 0 - Repository intake, source lock, safety rails | self_checked | WPR106-391, `V2-AUD-SCOPE-001`, `V2-AUD-SEC-001` |
| 1 - v2 package skeleton, configuration, audit markers | self_checked | WPR106-392, `V2-AUD-PKG-001`, `V2-AUD-SCOPE-002` |
| 2 - Contract files and schema-first foundation | self_checked | WPR106-393, `V2-AUD-CONTRACTS-001`, `V2-AUD-SCOPE-003`, `V2-AUD-ARCH-001`, `V2-AUD-SEC-002` |
| 3 - Legacy subsystem inventory and classification | self_checked | WPR106-394, `V2-AUD-LEGACY-001` |
| 4 - Archive layout, raw writer, manifests, snapshots | self_checked | WPR106-395, `V2-AUD-ARCH-002`, `V2-AUD-ARCH-003` |
| 5 - Hyperliquid universe manager and catalog | self_checked | WPR106-396, `V2-AUD-UNIV-001`, `V2-AUD-HIP3-001` |
| 6 - Data quality and coverage service | self_checked | WPR106-397, `V2-AUD-QUAL-001` |
| 7 - Durable workers and collector jobs | self_checked | WPR106-398, `V2-AUD-WORKER-001`, `V2-AUD-COLLECT-001` |
| 8 - Bronze/silver market-data pipelines | self_checked | WPR106-399, `V2-AUD-ARCH-004`, `V2-AUD-QUAL-002` |
| 9 - Backtest data service enforcement | self_checked | WPR106-400, `V2-AUD-BTDATA-001` |
| 10 - Declarative strategy spec lane | self_checked | WPR106-401, `V2-AUD-STRAT-001` |
| 11 - Vectorized backtest engine and artifacts | self_checked | WPR106-402, `V2-AUD-BTENG-001` |
| 12 - Cost, funding, slippage, and impact models | self_checked | WPR106-403, `V2-AUD-COST-001` |
| 13 - Append-only ledger and generated spreadsheet | self_checked | WPR106-404, `V2-AUD-LEDGER-001` |
| 14 - Walk-forward validation and overfit controls | self_checked | WPR106-405, `V2-AUD-VAL-001` |
| 15 - Lead Book and lead workflow | self_checked | WPR106-406, `V2-AUD-LEAD-001` |
| 16 - Event-driven engine skeleton and microstructure path | self_checked | WPR106-407, `V2-AUD-BTENG-002` |
| 17 - Trades, BBO/L2, official-file collection expansion | self_checked | WPR106-408, `V2-AUD-ARCH-005`, `V2-AUD-COLLECT-002` |
| 18 - Useful legacy migration into v2 contracts | self_checked | WPR106-409, `V2-AUD-LEGACY-010`, `V2-AUD-STRAT-002` |
| 19 - Cross-venue adapter and first comparable venue | self_checked | WPR106-410, `V2-AUD-XVENUE-001` |
| 20 - Deep validation and final hard-test governance | self_checked | WPR106-411, `V2-AUD-FINAL-001`, `V2-AUD-VAL-002` |
| 21 - Security and hygiene hardening | self_checked | WPR106-412, `V2-AUD-SEC-003` |
| 22 - Future v2 UI | self_checked | WPR106-413, WPR106-416, `V2-AUD-UI-001`, `docs/V2_FUTURE_UI_DEFERRAL.md`, `docs/contracts/ui_visibility_contract.md` |

## Post-Roadmap Operational Coverage

| Area | Status | Evidence |
| --- | --- | --- |
| Public diagnostic bounded cycle | self_checked with blockers | WPR106-469 generated, enqueued, and ran universe, candle, coverage, strategy queue, vectorized backtest, validation gate, ledger, Lead Book, and audit jobs. WPR106-470 fixed the public universe mode, and WPR106-471 made validation gate manifests authoritative for ledger validation status. The final cycle remained `sandbox_diagnostic` and `completed_with_blockers`. |
| Historical public dataset collection | self_checked with current-universe caveat | WPR106-473 adds `redx collectors historical-perps`. The top-25 daily run `wpr106-473-top25c-1d-2024-2026` collected 25/25 current eligible instruments from 2024-01-01 through 2026-06-01, with 14/25 passing full-window technical coverage and 24/25 Binance sanity checks passing. The BTC/ETH/SOL funding smoke collected 744 funding rows per symbol for January 2024. Reports remain `sandbox_diagnostic` and `accepted_research_ready=false`. |
| Hyperliquid data-venue roadmap foundation | self_checked schema foundation | WPR106-474 adds local strict-free source registry, cost-class, symbol-map, and data-family coverage schemas plus fixtures and validators for `DATA-001` and the initial schema portions of `DATA-002`/`DATA-016`. Paid/keyed, requester-pays, free-sample historical-proof, ambiguous mapping, forward-capture-only, external proxy, diagnostic, and boundary-violating cases fail closed. |
| Cross-venue symbol-map resolver | self_checked scaffold | WPR106-475 adds deterministic candidate generation and probe-driven verification for `DATA-002`, covering Binance, Bybit, OKX, Bitget, MEXC, Gate, KuCoin, HTX, dYdX, Coinbase, Kraken, Pyth, DexScreener, and GeckoTerminal. WPR106-502 adds Deribit perpetual candidate coverage for `BASE-PERPETUAL` instruments. WPR106-505 adds DefiLlama context candidate coverage. Candidate symbols are not trusted until explicit probe evidence marks them verified. |
| Universe data-source manifest bridge | self_checked bridge | WPR106-476 connects existing Hyperliquid universe snapshot rows to strict-free source-registry and symbol-map snapshot manifests for `DATA-003`. The bridge writes deterministic refs under `manifests/source_registry/` and `manifests/symbol_maps/`, rejects requester-pays/paid/keyed/strict-free-unaccepted sources before writes, preserves below-threshold rows as blocker evidence, and performs no venue/API fetch. |
| Binance Vision availability scanner | self_checked metadata scanner | WPR106-477 adds strict-free Binance Vision source samples, daily USD-M/spot trades, aggTrades, and 1m kline URL builders, injectable ZIP/checksum HEAD probes, and metadata-only availability manifests for `DATA-004`. The scanner requires verified Binance symbol-map refs and does not download or parse archives. |
| Binance Vision ZIP parser validation | self_checked local parser | WPR106-478 starts `DATA-005` by parsing local Binance Vision daily ZIP bytes for trades, aggTrades, and 1m klines with optional checksum verification, single-CSV validation, duplicate/gap/monotonicity diagnostics, and stable normalized-row hashes. It does not download archives or write raw/bronze/silver tables. |
| Binance Vision local archive ingest | self_checked local ingest | WPR106-479 ingests already-available local Binance Vision ZIP bytes through the parser into raw archive records, bronze/silver 1m kline Parquet, and raw trade/aggTrade microstructure captures with quality/storage refs. It does not download archives, run reconstructed-bar comparison, or write coverage reports. |
| Binance Vision reconstructed-bar comparison | self_checked quality gate | WPR106-480 reconstructs 1m OHLCV buckets from parsed trades or aggTrades and compares them against parsed 1m klines with explicit tolerances, missing-bucket blockers, stable report identity, and research-only boundary flags. |
| Binance Vision data-family coverage | self_checked coverage builder | WPR106-481 builds deterministic `DataFamilyCoverageReport` rows from Binance Vision availability, parser, archive-ingest, and reconstructed-bar comparison evidence. Full archived and reconstruction-checked daily 1m kline evidence can be accepted only as external-comparison coverage; missing mappings, ZIPs, parser output, ingest/archive refs, checksum verification, duplicate IDs, gaps, partial buckets, and failed comparisons become blocker metadata. |
| Binance Vision downloader cache | self_checked bounded downloader | WPR106-482 downloads available Binance Vision ZIP/checksum rows through an injectable GET client into deterministic archive-root-contained raw cache paths, writes source-download manifests with SHA-256/byte/count/checksum/cache-hit metadata, reuses cache without network calls, and fails closed for non-available rows, HTTP errors, max-byte violations, and checksum mismatches. |
| Binance Vision daily backfill orchestration | self_checked bounded chain | WPR106-483 chains one daily availability row through downloader/cache, parser, target archive ingest, optional reconstructed-bar comparison, and data-family coverage JSON writing. Completed rows return target/comparison/download/coverage refs; blocked rows still write non-accepted coverage reports with explicit blocker metadata. |
| Binance Vision backfill batch coordination | self_checked bounded batch | WPR106-484 coordinates bounded runs from an availability manifest by selecting target rows by source ID, matching optional comparison rows by symbol/date, running daily backfills under a max-row cap, and writing batch manifests with completed/blocked/accepted counts and blocker summaries. |
| Binance USD-M derivatives context foundation | self_checked schema/request foundation | WPR106-485 starts `DATA-006` by registering `binance_usdm_public_derivatives_context` as a strict-free public-rate-limited external context source and adding offline deterministic request builders for funding-rate history, open interest, open-interest statistics, mark/index/premium klines, taker buy/sell volume, long/short ratios, and basis. |
| Binance USD-M derivatives fetch normalize | self_checked fetch-normalize foundation | WPR106-486 consumes one prebuilt Binance derivatives context request through an injectable GET client, parses endpoint JSON shapes, and returns normalized context rows with source timestamps, publication timestamps, bucket seconds, numeric fields, unit annotations, stable hashes, and fail-closed blocker metadata. |
| Binance USD-M derivatives pagination | self_checked bounded pagination | WPR106-487 coordinates bounded multi-page derivatives context fetches, requiring explicit start/end windows for historical families, keeping current OI one-page, advancing cursors from normalized timestamps and bucket seconds, preserving page URLs/fetch IDs, and failing closed on blocked pages, missing bounds, non-advancing cursors, and max-page exhaustion. |
| Binance USD-M derivatives archive ingest | self_checked archive ingest | WPR106-488 writes completed paginated derivatives context rows into local raw JSONL.zst and generic silver `derivatives_context` Parquet archive artifacts with source/page refs, timestamps, bucket metadata, numeric/unit/raw field JSON, and research-only boundary flags. Blocked, empty, and timestamp-missing page results fail closed before archive writes. |
| Binance USD-M derivatives coverage | self_checked coverage builder | WPR106-489 builds `DataFamilyCoverageReport` rows for archived derivatives context families separately from candle/trade coverage. Complete archived context windows can be accepted as external-comparison coverage when refs and buckets are present; current OI snapshots, missing buckets, blocked inputs, and missing archive evidence stay non-accepted blocker reports. |
| Binance USD-M derivatives backfill orchestration | self_checked local chain | WPR106-490 chains one derivatives context family/symbol through bounded pagination, local raw/silver archive ingest, and coverage-report JSON writing. Completed attempts return page/ingest/coverage refs; blocked attempts still write non-accepted coverage reports with explicit blockers. |
| Binance USD-M derivatives worker routing | self_checked durable handoff | WPR106-491 exposes the bounded single-family/symbol derivatives context backfill chain as a durable `binance_derivatives_context_backfill` worker job with fixture-payload and explicit public-API modes, page/archive/coverage output refs, accepted-coverage metadata, and blocker refs. |
| Hyperliquid public REST source registry | self_checked DATA-007 registry alignment | WPR106-492 registers native strict-free source entries for Hyperliquid funding history, recent candle snapshots, and one-shot L2 book snapshots. The entries align with existing bounded collector routes while preserving recent-window/snapshot caveats and `accepted_historical_coverage_proof=false`. |
| Hyperliquid public WebSocket source registry | self_checked DATA-008 source gate | WPR106-493 registers native strict-free source entries for Hyperliquid trades, BBO, L2 book, and candle WebSocket streams, then requires public WebSocket worker specs to declare the exact matching `source_registry_source_id` before stream fetch. Successful jobs expose that source ID in output refs; missing or mismatched IDs fail before archive writes. |
| Hyperliquid official requester-pays registry | self_checked DATA-009 strict-free gate | WPR106-494 registers the full quarantined official requester-pays source set for L2 book, asset contexts, node fills by block, node fills, and node trades. All five validate as native Hyperliquid sources but fail strict-zero-dollar mode, require operator gates, and cannot claim accepted historical coverage proof. |
| Bybit/OKX public market source registry | self_checked DATA-010 foundation | WPR106-495 registers public-rate-limited Bybit and OKX market source entries as external-comparison-only, strict-free-allowed sources for candles, trades, BBO/L2, funding, and open interest. Both remain non-native to Hyperliquid and `accepted_historical_coverage_proof=false`; collectors, probes, availability matrices, downloads, and accepted coverage remain later work. |
| Bybit/OKX availability matrix foundation | self_checked DATA-010 endpoint/mapping scaffold | WPR106-496 adds deterministic Bybit/OKX public REST request builders plus metadata-only availability manifests with injectable probes. Verified symbol mappings and strict-free external-comparison source entries are required; recent/snapshot-only endpoints are blocked as endpoint-limit rows rather than historical coverage proof. |
| Bybit/OKX smoke fetch normalization | self_checked DATA-010 smoke collector scaffold | WPR106-497 adds an in-memory injected-response smoke fetch/normalization layer for supported date-window Bybit/OKX endpoints. Rows carry source/request/timestamp/raw/numeric/hash metadata and remain external comparison outputs; empty, malformed, API-error, and snapshot-only cases fail closed without archive writes. |
| Alt derivatives public source registry | self_checked DATA-011 foundation | WPR106-498 registers MEXC, Bitget, Gate, KuCoin, and HTX public derivatives market sources as public-rate-limited external-comparison-only entries. All five remain non-native to Hyperliquid and `accepted_historical_coverage_proof=false`; probes, availability matrices, collectors, downloads, and accepted coverage remain later work. |
| Alt derivatives availability matrix foundation | self_checked DATA-011 endpoint/mapping scaffold | WPR106-499 adds deterministic public REST candle request builders plus metadata-only availability manifests with injectable probes for MEXC, Bitget, Gate, KuCoin, and HTX. Verified symbol mappings and strict-free external-comparison source entries are required; rows remain non-native and non-accepted historical coverage proof. |
| Alt derivatives smoke fetch normalization | self_checked DATA-011 smoke collector scaffold | WPR106-500 adds an in-memory injected-response smoke fetch/normalization layer for DATA-011 candle endpoints. Rows carry source/request/timestamp/raw/numeric/hash metadata and remain external comparison outputs; empty, malformed, API-error, and bad-source cases fail closed without archive writes. |
| dYdX/Deribit public source registry | self_checked DATA-012 foundation | WPR106-501 registers dYdX indexer and Deribit public sources as public-rate-limited external comparison/reference context entries. Both remain non-native to Hyperliquid and `accepted_historical_coverage_proof=false`; overlap proof, availability matrices, collectors, downloads, and accepted coverage remain later work. |
| dYdX/Deribit availability matrix foundation | self_checked DATA-012 endpoint/mapping scaffold | WPR106-502 adds deterministic dYdX indexer candle and Deribit TradingView candle request builders plus metadata-only availability manifests with injectable probes. Verified mappings and strict-free external-comparison source entries are required; rows remain non-native and non-accepted historical coverage proof. |
| dYdX/Deribit smoke fetch normalization | self_checked DATA-012 smoke collector scaffold | WPR106-503 adds an in-memory injected-response smoke fetch/normalization layer for dYdX indexer and Deribit TradingView candle responses. Rows carry source/request/timestamp/raw/numeric/hash metadata and remain external comparison outputs; empty, malformed, API-error, and bad-source cases fail closed without archive writes. |
| Spot/oracle/on-chain context source registry | self_checked DATA-013 foundation | WPR106-504 registers Coinbase spot, Kraken spot, Pyth Hermes, DefiLlama, DexScreener, and GeckoTerminal sources as strict-free spot/oracle/on-chain context entries. They remain non-native and `accepted_historical_coverage_proof=false`; availability matrices, probes, collectors, downloads, archive writes, and accepted coverage remain later work. |
| DefiLlama context symbol candidate | self_checked DATA-013 resolver extension | WPR106-505 adds `defillama_context` to deterministic symbol-map candidate generation so later context availability can require explicit verified mapping evidence. Unprobed DefiLlama candidates remain `not_checked` and blocked downstream. |
| Spot/oracle/on-chain context availability matrix | self_checked DATA-013 endpoint/mapping scaffold | WPR106-506 adds deterministic request builders and metadata-only availability manifests for Coinbase spot, Kraken spot, Pyth Hermes, DefiLlama, DexScreener, and GeckoTerminal. Verified symbol/context mappings and strict-free role-aligned source entries are required before probes; rows remain non-native and non-accepted as historical coverage proof. |
| Spot/oracle/on-chain context smoke fetch normalization | self_checked DATA-013 smoke collector scaffold | WPR106-507 adds an in-memory injected-response smoke fetch/normalization layer for Coinbase spot, Kraken spot, Pyth Hermes, DefiLlama, DexScreener, and GeckoTerminal responses. Rows carry source/request/timestamp/raw/numeric/hash metadata and remain context/external comparison outputs; empty, malformed, API-error, and bad-source cases fail closed without archive writes. |
| Generic trade-bar reconstruction | self_checked DATA-014 foundation | WPR106-508 starts venue-neutral trade-to-bar reconstruction with stable input, bar, and report models. Already-normalized trade rows can be bucketed into OHLCV bars with source registry and symbol-map refs; native and external rows stay separated, and empty or mixed-provenance cases fail closed without archive writes or accepted coverage. |
| Generic reconstructed-bar comparison | self_checked DATA-014 quality gate foundation | WPR106-509 adds venue-neutral comparison between reconstructed trade bars and source-native candle bars. Matching buckets can pass as quality metadata; missing reconstructed buckets, extra reconstructed buckets, tolerance breaches, or mismatched provenance fail closed without archive writes or accepted coverage. |
| Orderflow feature reconstruction | self_checked DATA-015 foundation | WPR106-510 starts venue-neutral orderflow feature reconstruction from already-normalized trade rows. Bucketed VWAP, buy/sell/unknown volume, quote volume, trade counts, and imbalance features retain source registry and symbol-map refs; empty input, missing side, zero-volume buckets, and mixed provenance fail closed without archive writes, gold panels, or accepted coverage. |
| Funding/OI context feature reconstruction | self_checked DATA-015 foundation | WPR106-511 adds deterministic funding, open-interest, open-interest-statistics, and basis feature rows from already-normalized derivatives context rows. Rows preserve source refs, symbol-map refs, family/timestamp/numeric/unit metadata, and provenance; empty input, unsupported families, missing timestamps/numerics, non-finite numeric values, and mixed provenance fail closed without archive writes, gold panels, or accepted coverage. |
| BBO spread feature reconstruction | self_checked DATA-015 foundation | WPR106-512 adds deterministic BBO mid-price, absolute spread, spread-bps, and top-of-book size-imbalance features from already-normalized BBO rows. Rows preserve source refs, symbol-map refs, timestamp/sequence metadata, and provenance; empty input, missing timestamps/sizes, crossed books, bad prices, and mixed provenance fail closed without archive writes, gold panels, or accepted coverage. |
| L2 depth feature reconstruction | self_checked DATA-015 foundation | WPR106-513 adds deterministic bid-depth, ask-depth, total-depth, depth-imbalance, and book-level metadata features from already-normalized L2 snapshot rows. Rows preserve source refs, symbol-map refs, timestamp/sequence metadata, and provenance; empty input, missing timestamps, zero total depth, negative depths, invalid book levels, and mixed provenance fail closed without archive writes, gold panels, or accepted coverage. |
| Cross-venue basis feature reconstruction | self_checked DATA-015 foundation | WPR106-514 adds deterministic absolute and bps price-basis rows from already-normalized price observations against a requested primary venue. Rows remain external-comparison only and preserve primary/comparison venue/source metadata; empty input, insufficient venue coverage, missing/duplicate primary prices, missing comparison prices, missing timestamps, mixed context, and bad prices fail closed without archive writes, gold panels, or accepted coverage. |
| Data-family coverage gate | self_checked DATA-016 foundation | WPR106-515 adds a deterministic gate over existing `DataFamilyCoverageReport` objects. Required families pass only when already accepted reports meet the requested minimum; empty inputs, missing required families, rejected family reports, mismatched symbol/ref context, and empty required-family sets fail closed without archive writes, gold panels, candidate evidence, or promotion claims. |
| Gold research panel manifest | self_checked DATA-017 foundation | WPR106-516 adds deterministic metadata-only `GoldResearchPanelManifest` output over a passed coverage gate and feature refs. Blocked gates, missing archive refs, empty feature refs, missing required feature families, uncovered feature families, blocked feature refs, and mismatched ref context fail closed without writing gold panel rows, archive data, accepted coverage evidence, candidate evidence, or promotion claims. |
| Gold research panel row assembly | self_checked DATA-017 foundation | WPR106-517 adds in-memory `GoldResearchPanelRow` and `GoldResearchPanelAssemblyResult` output over a ready manifest and timestamped feature-column values. Blocked manifests, empty inputs, duplicate column/timestamp pairs, missing non-nullable values, unknown columns, and feature-report mismatches fail closed without writing gold panel files, archive data, accepted coverage evidence, candidate evidence, or promotion claims. |
| Gold research panel artifact write | self_checked DATA-017 foundation | WPR106-518 writes ready in-memory gold panel assemblies to the archive `gold` layer through the existing Parquet writer, records file-manifest evidence, and writes assembly JSON under `manifests/gold_panels/`. Blocked or empty assemblies, unsafe partitions, and duplicate writes fail closed without provider downloads, accepted coverage evidence, candidate evidence, or promotion claims. |
| Data venue runbook and operator docs | self_checked DATA-018 foundation | WPR106-519 adds `docs/runbooks/v2_hyperliquid_data_venue_runbook.md` covering the strict-free source order, requester-pays quarantine, prerequisites, archive layers, data-family coverage gates, gold panels, fail-closed handling, validation commands, and operator stops. This is documentation-only and creates no source behavior, archive artifacts, accepted coverage evidence, candidate evidence, or promotion claims. |
| Multi-symbol coverage and gold-panel preflight | self_checked DATA-016/DATA-017 bridge | WPR106-520 adds a research-only preflight over existing coverage and feature reconstruction refs. It aggregates `DataFamilyCoverageReport` objects across declared symbols, evaluates per-symbol required-family gates, maps accepted feature reports into `GoldResearchPanelFeatureRef` rows, and builds per-symbol manifest preflight results. Missing coverage/features and blocked reports remain explicit blockers; this writes no archive rows or gold panel files and creates no accepted coverage evidence, candidate evidence, or promotion claims. |
| Gold panel materializer | self_checked DATA-017 bridge | WPR106-521 adds an all-or-nothing materializer over ready preflight output and explicit per-symbol row-value inputs. It assembles every declared symbol and writes gold-layer artifacts only when every symbol is ready, complete, and source-row-hashed. Blocked preflights, missing inputs, duplicate or incomplete row values, missing source row hashes, and unknown input symbols fail before writes; output remains archive refs only with no accepted coverage evidence, candidate evidence, or promotion claims. |
| Bounded loop backtest-data load wiring | self_checked worker/autonomy bridge | WPR106-522 adds a durable `backtest_data_load` worker stage between `strategy_queue_scan` and `vectorized_backtest`. The stage loads through `BacktestDataService`, returns archive/universe/coverage/data-manifest refs, and generated fixture/public cycles bind those refs into vectorized backtests with expected-ref verification. The loop remains research-only operational evidence and creates no accepted coverage evidence, candidate evidence, paper/live/order/sizing/runtime behavior, promotion claim, or readiness claim. |
| Existing archive-ref bounded cycle | self_checked worker/autonomy bridge | WPR106-523 adds `source=existing_ref` durable universe/archive checks and `redx autopilot archive-cycle-spec` for local archive refs plus local declarative JSON/YAML strategy specs. The generated loop verifies refs before coverage, strategy queue scan, backtest-data load, vectorized backtest, validation, ledger, Lead Book, and audit; focused evidence includes a no-blocker final audit while `accepted_research_ready=false` and all promotion/candidate/paper-live/order/sizing/runtime flags remain false. |
| Final-audit handoff | ready_for_independent_audit | WPR106-524 records the handoff state after WPR106-472 through WPR106-523, with no open P0/P1 known issues, one non-blocking P2 data-source caveat, Python 3.11 validation as the authoritative local lane, and explicit separation between final audit readiness and agentic strategy testing readiness. |
| Readiness blocker audit | self_checked | WPR106-455 and WPR106-462 require current loop evidence, a passing final audit report, nonempty ledger and Lead Book artifacts, and zero open P0/P1 counts before any autonomous-readiness report can pass. |
| CI and full-suite evidence | self_checked | WPR106-472 adds `tests/v2 -q` to the checked-in CI baseline and records Python 3.11 full-suite evidence: 2235 passed, 2 skipped. |

## Milestone Status

| Milestone | Status | Evidence |
| --- | --- | --- |
| M0 - Product scope and safety foundation | self_checked | Product scope, no-touch registry, audit index, v2 package skeleton, and import-boundary tests exist through WPR106-391 to WPR106-393. |
| M1 - Dynamic Hyperliquid 1m-bar research loop foundation | self_checked | Universe, archive, coverage, backtest-data enforcement, strategy spec validation, vectorized engine, cost model, run artifacts, and ledger are implemented through WPR106-395 to WPR106-404. The implementation is fixture/sandbox-safe and research-only. |
| M2 - Validation and Lead Book readiness | self_checked | Walk-forward validation, overfit controls, trial-family evidence, Lead Book schema/store/gates, human inspection, and agent approval are implemented through WPR106-405 and WPR106-406. |
| M3 - Aggressive market-data expansion | self_checked | Trade/BBO/L2 fixture capture schemas, official-file preservation, storage budget evidence, collectors, and event-driven fixture consumption are implemented through WPR106-407 and WPR106-408. |
| M4 - Deep validation and final hard-test governance | self_checked | One-active deep-validation guard, max-three final slots, frozen evidence requirements, pre-2024 diagnostic fallback, post-lockbox edit rejection, and non-live survivor reports are implemented through WPR106-411. |
| M5 - Cross-venue comparison | self_checked | Fixture-only Binance USDT-M venue adapter capability, provenance-preserving raw/silver rows, universe snapshot support, and Hyperliquid-first default preservation are implemented through WPR106-410. |

## Acceptance Test Coverage

The roadmap acceptance themes are covered by focused v2 tests and contract
tests rather than by live provider execution:

- universe and HIP-3 behavior: `tests/v2/test_universe_phase5.py`;
- archive, raw-before-normalization, snapshots, and silver rebuilds:
  `tests/v2/archive/test_archive_phase4.py` and
  `tests/v2/archive/test_archive_phase8.py`;
- coverage and data quality: `tests/v2/test_data_quality_phase6.py`;
- durable workers and collectors: `tests/v2/test_workers_phase7.py` and
  `tests/v2/test_microstructure_collection_phase17.py`;
- backtest data enforcement: `tests/v2/test_backtest_data_phase9.py`;
- strategy spec validation: `tests/v2/test_strategy_specs_phase10.py`;
- vectorized and event-driven run artifacts:
  `tests/v2/test_backtest_engine_phase11.py` and
  `tests/v2/test_event_driven_phase16.py`;
- costs and stress rows: `tests/v2/test_cost_models_phase12.py`;
- append-only ledger and generated exports: `tests/v2/test_ledger_phase13.py`;
- validation and overfit controls: `tests/v2/test_validation_phase14.py`;
- Lead Book workflow and gates: `tests/v2/test_lead_book_phase15.py`;
- final hard-test governance: `tests/v2/test_final_validation_phase20.py`;
- cross-venue fixture behavior: `tests/v2/test_cross_venue_phase19.py`;
- security hygiene: `tests/v2/test_security_hygiene_phase21.py`;
- read-only v2 UI visibility: `tests/v2/test_ui_visibility_phase22.py`;
- v2 import boundaries and contract docs:
  `tests/v2/test_import_boundaries.py` and
  `tests/v2/test_contract_docs.py`.
- bounded historical-perps collection and Binance sanity validation:
  `tests/v2/test_historical_dataset_collection_phase36.py`.
- Binance USD-M derivatives context source/request foundation:
  `tests/v2/test_binance_derivatives_context_phase48.py`.
- Binance USD-M derivatives context fetch/normalize foundation:
  `tests/v2/test_binance_derivatives_fetch_phase49.py`.
- Binance USD-M derivatives bounded pagination:
  `tests/v2/test_binance_derivatives_pagination_phase50.py`.
- Binance USD-M derivatives archive ingest:
  `tests/v2/test_binance_derivatives_archive_ingest_phase51.py`.
- Binance USD-M derivatives coverage:
  `tests/v2/test_binance_derivatives_coverage_phase52.py`.
- Binance USD-M derivatives local backfill orchestration:
  `tests/v2/test_binance_derivatives_backfill_phase53.py`.
- Binance USD-M derivatives durable worker routing:
  `tests/v2/test_binance_derivatives_worker_phase54.py`.
- Spot/oracle/on-chain context availability matrix:
  `tests/v2/test_spot_oracle_context_availability_phase61.py`.
- Spot/oracle/on-chain context smoke fetch normalization:
  `tests/v2/test_spot_oracle_context_fetch_normalize_phase62.py`.
- Generic trade-bar reconstruction:
  `tests/v2/test_bar_reconstruction_phase63.py`.
- Generic reconstructed-bar comparison:
  `tests/v2/test_bar_reconstruction_phase63.py`.
- Orderflow feature reconstruction:
  `tests/v2/test_feature_reconstruction_phase64.py`.
- Funding/OI context feature reconstruction:
  `tests/v2/test_feature_reconstruction_phase65.py`.
- BBO spread feature reconstruction:
  `tests/v2/test_feature_reconstruction_phase66.py`.
- L2 depth feature reconstruction:
  `tests/v2/test_feature_reconstruction_phase67.py`.
- Cross-venue basis feature reconstruction:
  `tests/v2/test_feature_reconstruction_phase68.py`.
- Data-family coverage gate:
  `tests/v2/test_data_family_coverage_gate_phase69.py`.
- Gold research panel manifest:
  `tests/v2/test_gold_research_panel_phase70.py`.
- Gold research panel row assembly:
  `tests/v2/test_gold_research_panel_phase71.py`.
- Gold research panel artifact write:
  `tests/v2/test_gold_research_panel_phase72.py`.
- Gold research panel preflight:
  `tests/v2/test_gold_research_panel_preflight_phase73.py`.
- Gold research panel materializer:
  `tests/v2/test_gold_research_panel_materializer_phase74.py`.
- Bounded loop backtest-data load wiring:
  `tests/v2/test_workers_phase7.py`,
  `tests/v2/test_autopilot_research_cycle_phase26.py`,
  `tests/v2/test_autopilot_research_cycle_runner_phase27.py`,
  `tests/v2/test_autopilot_fixture_cycle_phase28.py`,
  `tests/v2/test_autopilot_public_cycle_phase30.py`, and
  `tests/v2/test_autopilot_scheduler_phase33.py`.

Latest broad validation recorded by WPR106-472:

```text
py -3.11 -m pip check: passed
py -3.11 -m compileall -q src/tradingbotsuite: passed
tests/v2: 328 passed
py -3.11 tests/contracts: 463 passed
default-python tests/contracts: 463 passed
tests/research_sandbox: 226 passed
live/artifact boundary lane: 103 passed
monolithic tests: 2235 passed, 2 skipped
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-473 validation:

```text
tests/v2/test_historical_dataset_collection_phase36.py: 2 passed
compile historical_dataset.py and cli/main.py: passed
compile src/tradingbotsuite: passed
tests/v2: 330 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
real top-25 daily collection: 25/25 collected, 14/25 full-window technical coverage, 24 Binance passes, 1 Binance warning
real BTC/ETH/SOL funding smoke: 3/3 bars collected, 744 funding rows per symbol
```

Latest focused WPR106-474 validation:

```text
tests/v2/test_data_source_registry_phase37.py: 10 passed
compile src/tradingbotsuite: passed
```

Latest focused WPR106-475 validation:

```text
tests/v2/test_symbol_map_resolver_phase38.py: 7 passed
```

Latest focused WPR106-476 validation:

```text
tests/v2/test_universe_data_source_manifest_bridge_phase39.py: 5 passed
```

Latest focused WPR106-477 validation:

```text
tests/v2/test_binance_vision_availability_phase40.py: 5 passed
```

Latest focused WPR106-478 validation:

```text
tests/v2/test_binance_vision_parser_phase41.py: 5 passed
```

Latest focused WPR106-479 validation:

```text
tests/v2/test_binance_vision_archive_ingest_phase42.py: 2 passed
```

Latest focused WPR106-480 validation:

```text
tests/v2/test_binance_vision_reconstruction_phase43.py: 3 passed
```

Latest focused WPR106-481 validation:

```text
tests/v2/test_binance_vision_coverage_phase44.py: 4 passed
```

Latest focused WPR106-482 validation:

```text
tests/v2/test_binance_vision_downloader_phase45.py: 3 passed
```

Latest focused WPR106-483 validation:

```text
tests/v2/test_binance_vision_backfill_phase46.py: 3 passed
```

Latest focused WPR106-484 validation:

```text
tests/v2/test_binance_vision_backfill_batch_phase47.py: 2 passed
```

Latest focused WPR106-485 validation:

```text
tests/v2/test_binance_derivatives_context_phase48.py: 5 passed
```

Latest focused WPR106-486 validation:

```text
tests/v2/test_binance_derivatives_fetch_phase49.py: 5 passed
```

Latest focused WPR106-487 validation:

```text
tests/v2/test_binance_derivatives_pagination_phase50.py: 5 passed
```

Latest focused WPR106-488 validation:

```text
tests/v2/test_binance_derivatives_archive_ingest_phase51.py: 4 passed
```

Latest focused WPR106-489 validation:

```text
tests/v2/test_binance_derivatives_coverage_phase52.py: 4 passed
```

Latest focused WPR106-490 validation:

```text
tests/v2/test_binance_derivatives_backfill_phase53.py: 4 passed
```

Latest focused WPR106-491 validation:

```text
tests/v2/test_binance_derivatives_worker_phase54.py: 3 passed
```

Latest baseline WPR106-491 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 409 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-492 validation:

```text
tests/v2/test_data_source_registry_phase37.py: 11 passed
```

Latest baseline WPR106-492 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 410 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-493 validation:

```text
tests/v2/test_data_source_registry_phase37.py + tests/v2/test_workers_phase7.py + tests/v2/test_microstructure_collection_phase17.py: 108 passed
```

Latest baseline WPR106-493 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 419 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-494 validation:

```text
tests/v2/test_data_source_registry_phase37.py: 13 passed
```

Latest baseline WPR106-494 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 420 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-495 validation:

```text
tests/v2/test_data_source_registry_phase37.py: 14 passed
```

Latest baseline WPR106-495 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 421 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-496 validation:

```text
tests/v2/test_bybit_okx_availability_phase55.py: 5 passed
```

Latest baseline WPR106-496 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 426 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-497 validation:

```text
tests/v2/test_bybit_okx_fetch_normalize_phase56.py: 5 passed
```

Latest baseline WPR106-497 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 431 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-498 validation:

```text
tests/v2/test_data_source_registry_phase37.py: 15 passed
```

Latest baseline WPR106-498 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 432 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-499 validation:

```text
tests/v2/test_alt_derivatives_availability_phase57.py: 4 passed
```

Latest baseline WPR106-499 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 436 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-500 validation:

```text
tests/v2/test_alt_derivatives_fetch_normalize_phase58.py: 4 passed
```

Latest baseline WPR106-500 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 440 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-501 validation:

```text
tests/v2/test_data_source_registry_phase37.py: 16 passed
```

Latest baseline WPR106-501 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 441 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-502 validation:

```text
tests/v2/test_reference_derivatives_availability_phase59.py + tests/v2/test_symbol_map_resolver_phase38.py: 11 passed
```

Latest baseline WPR106-502 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 445 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-503 validation:

```text
tests/v2/test_reference_derivatives_fetch_normalize_phase60.py: 5 passed
```

Latest baseline WPR106-503 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 450 passed
tests/contracts: first attempt hit known Windows socketpair setup error after 462 passed; sequential rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-504 validation:

```text
tests/v2/test_data_source_registry_phase37.py: 17 passed
```

Latest baseline WPR106-504 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 451 passed
tests/contracts: first attempt hit known Windows socketpair setup error after 462 passed; sequential rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-505 validation:

```text
tests/v2/test_symbol_map_resolver_phase38.py: 7 passed
```

Latest baseline WPR106-505 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 451 passed
tests/contracts: first attempt hit known Windows socketpair setup error after 462 passed; sequential rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-506 validation:

```text
tests/v2/test_spot_oracle_context_availability_phase61.py: 4 passed
```

Latest baseline WPR106-506 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 455 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-507 validation:

```text
tests/v2/test_spot_oracle_context_fetch_normalize_phase62.py: 5 passed
```

Latest baseline WPR106-507 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 460 passed
tests/contracts: first attempt hit known Windows socketpair setup error after 462 passed; sequential rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-508 validation:

```text
tests/v2/test_bar_reconstruction_phase63.py: 5 passed
```

Latest baseline WPR106-508 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 465 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-509 validation:

```text
tests/v2/test_bar_reconstruction_phase63.py: 9 passed
```

Latest baseline WPR106-509 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 469 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-510 validation:

```text
tests/v2/test_feature_reconstruction_phase64.py: 6 passed
```

Latest baseline WPR106-510 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 475 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-511 validation:

```text
tests/v2/test_feature_reconstruction_phase64.py + tests/v2/test_feature_reconstruction_phase65.py: 13 passed
```

Latest baseline WPR106-511 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 482 passed
tests/contracts: first attempt hit known Windows socketpair setup error after 462 passed; sequential rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-512 validation:

```text
tests/v2/test_feature_reconstruction_phase64.py + tests/v2/test_feature_reconstruction_phase65.py + tests/v2/test_feature_reconstruction_phase66.py: 20 passed
```

Latest baseline WPR106-512 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 489 passed
tests/contracts: first attempt hit known Windows socketpair setup error after 462 passed; sequential rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-513 validation:

```text
tests/v2/test_feature_reconstruction_phase64.py + tests/v2/test_feature_reconstruction_phase65.py + tests/v2/test_feature_reconstruction_phase66.py + tests/v2/test_feature_reconstruction_phase67.py: 27 passed
```

Latest baseline WPR106-513 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 496 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-514 validation:

```text
tests/v2/test_feature_reconstruction_phase64.py + tests/v2/test_feature_reconstruction_phase65.py + tests/v2/test_feature_reconstruction_phase66.py + tests/v2/test_feature_reconstruction_phase67.py + tests/v2/test_feature_reconstruction_phase68.py: 34 passed
```

Latest baseline WPR106-514 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 503 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-515 validation:

```text
tests/v2/test_data_family_coverage_gate_phase69.py: 7 passed
```

Latest baseline WPR106-515 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 510 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-516 validation:

```text
tests/v2/test_gold_research_panel_phase70.py: 8 passed
```

Latest baseline WPR106-516 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 518 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-517 validation:

```text
tests/v2/test_gold_research_panel_phase71.py: 8 passed
```

Latest baseline WPR106-517 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 526 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-518 validation:

```text
tests/v2/test_gold_research_panel_phase72.py: 5 passed
```

Latest baseline WPR106-518 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 531 passed
tests/contracts: first attempt hit Windows socketpair WinError 10055 after 462 passed; rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-519 validation:

```text
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest baseline WPR106-519 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 531 passed
tests/contracts: first attempt hit Windows socketpair WinError 10055 after 462 passed; rerun 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-520 validation:

```text
tests/v2/test_gold_research_panel_preflight_phase73.py: 5 passed
```

Latest baseline WPR106-520 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 536 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-521 validation:

```text
tests/v2/test_gold_research_panel_materializer_phase74.py: 5 passed
```

Latest baseline WPR106-521 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 541 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-522 validation:

```text
compile src/tradingbotsuite: passed
tests/v2/test_workers_phase7.py tests/v2/test_autopilot_research_cycle_phase26.py tests/v2/test_autopilot_research_cycle_runner_phase27.py tests/v2/test_autopilot_fixture_cycle_phase28.py tests/v2/test_autopilot_public_cycle_phase30.py tests/v2/test_autopilot_scheduler_phase33.py: 87 passed
```

Latest baseline WPR106-522 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 543 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest focused WPR106-523 validation:

```text
compile src/tradingbotsuite: passed
tests/v2/test_autopilot_archive_cycle_phase75.py tests/v2/test_workers_phase7.py: 63 passed
archive-ref fixture cycle: completed with final audit status pass and no blockers
```

Latest baseline WPR106-523 validation:

```text
compile src/tradingbotsuite: passed
tests/v2: 548 passed
tests/contracts: 463 passed
git diff --check: passed with expected LF-to-CRLF warnings only
```

Latest WPR106-524 final-audit handoff validation:

```text
compile src/tradingbotsuite: passed
tests/v2 on Python 3.11: 548 passed, 1 warning
focused archive-ref lane on Python 3.11: 63 passed, 1 warning
contract-doc/autonomous-readiness focused lane on Python 3.11: 9 passed, 1 warning
contracts on Python 3.11: unsplit sweep hit local WinError 10055 pytest-asyncio setup after 462 passed; isolated async contract then passed and remaining contracts passed with 462 passed, 1 deselected
git diff --check: passed with expected LF-to-CRLF warnings only
```

Warnings observed in the Python 3.11 lanes are deprecation/runtime warnings
only; no assertion failures were observed.

## Phase 22 UI Status

`V2-AUD-UI-001` was initially planned/deferred because the roadmap labels
Phase 22 as future and delayed. WPR106-416 implements and self-checks the later explicit UI
packet as a read-only static visibility surface after the archive, data,
backtest, ledger, Lead Book, validation, cross-venue, and security foundation
packets were already self-checked.

The implementation renders a supplied `V2VisibilitySnapshot` to static HTML and
adds `redx ui render` for root-contained snapshot input and root-contained HTML
output. It does not modify legacy GUI paths, run collectors/backtests/workers in
a UI process, or introduce paper/live/order/sizing/runtime/promotion behavior.

## Safe Defaults Still In Force

The roadmap open-question defaults remain active until future packets replace
them:

- local archive roots stay protected by path policy;
- storage budget uses warning/reporting and no silent deletion;
- backup policy remains hash-manifest based;
- RWA reference metadata is required before accepting RWA evidence;
- maker assumptions stay blocked unless queue-model evidence exists;
- final hard-test selection requires explicit recorded selection notes.

## Remaining Operational Work

The foundation is ready for independent final audit. Agentic strategy testing
must wait for that audit and a separate readiness report over real evidence
paths. A later packet still must supply broad real historical as-of Hyperliquid
universe snapshots, Binance Vision downloader/archive-write coverage, accepted
full-universe coverage, and automated backfill/gold-panel consumption before
accepted research readiness. WPR106-523 proves the bounded loop can finish with
no blockers when supplied local archive/universe refs, strategy specs,
coverage, backtest data, validation, ledger, Lead Book, and audit evidence all
pass; that evidence remains operational research evidence only.
WPR106-473 proves current-public daily history can be collected and technically
checked for many perps; it also proves older 1h Hyperliquid public windows can
be empty even when Binance has 1h history, so intraday accepted evidence needs
another trusted Hyperliquid/as-of source or a clearly labeled cross-venue/proxy
path. WPR106-476 adds the manifest bridge needed for later availability
scanners and backfill jobs to consume source-registry and symbol-map refs
instead of ad hoc source/mapping assumptions. WPR106-477 adds Binance Vision
availability manifests, WPR106-478 adds local ZIP parser/checksum validation,
WPR106-479 adds local parser-to-archive ingest, WPR106-480 adds reconstructed
bar comparison, and WPR106-481 adds data-family coverage report construction;
WPR106-482 adds bounded downloader/cache integration, and WPR106-483 adds the
single-day local backfill chain. WPR106-484 adds bounded availability-manifest
batch coordination. WPR106-485 starts Binance USD-M public derivatives context
with source registration and offline request builders. WPR106-486 adds
single-request injectable fetch/normalize output with hashes, timestamps,
bucket seconds, numeric fields, and unit annotations; later packets still need
multi-page pagination, archive writes, coverage reports, and durable worker
integration before unattended operation. WPR106-487 adds bounded multi-page
pagination with page result IDs, page URL refs, cursor advancement, and
max-page blockers; archive writes, coverage reports, and durable worker
integration remain later work. WPR106-488 adds local raw/silver archive ingest
for completed paginated derivatives context rows; coverage reports and durable
worker integration remain later work. WPR106-489 adds derivatives
data-family coverage reports for archived context rows; durable worker
integration remains later work. WPR106-490 adds the local one-shot backfill
chain for one derivatives family/symbol. WPR106-491 adds the durable worker
route for that bounded one-family/symbol chain, including fixture-payload tests
and explicit public-API mode. WPR106-492 aligns existing Hyperliquid public REST
collector sources with checked source-registry entries for funding history,
recent candle snapshots, and one-shot L2 book snapshots while preserving
non-historical-coverage caveats. WPR106-493 adds checked Hyperliquid public
WebSocket source entries for trades, BBO, L2 book, and candle streams and
requires matching `source_registry_source_id` declarations before public
WebSocket stream fetch. WPR106-494 registers the full quarantined Hyperliquid
official requester-pays source set and proves strict-zero-dollar mode rejects
all five official source IDs. WPR106-495 starts `DATA-010` by registering
Bybit and OKX public market sources as public-rate-limited external-comparison
entries that are strict-free allowed but non-native and non-accepted as
historical coverage proof. WPR106-496 adds deterministic Bybit/OKX request
builders and metadata-only availability manifests with injected probes, while
marking recent/snapshot-only endpoints as endpoint-limit blockers instead of
historical evidence. WPR106-497 adds an in-memory smoke fetch/normalization
layer for supported date-window Bybit/OKX fixture responses; it emits stable
research-only normalized rows but performs no archive writes and creates no
accepted historical coverage proof. WPR106-498 starts `DATA-011` by
registering MEXC, Bitget, Gate, KuCoin, and HTX public derivatives sources as
strict-free public-rate-limited external-comparison entries with no accepted
historical coverage proof. WPR106-499 adds deterministic candle request
builders and metadata-only availability manifests for those five venues, with
verified symbol maps and injected probes required before any availability row
can pass. WPR106-500 adds in-memory smoke fetch normalization for DATA-011
candle fixture responses; it emits stable research-only normalized rows but
performs no archive writes and creates no accepted historical coverage proof.
WPR106-501 starts `DATA-012` by registering dYdX indexer and Deribit public
sources as strict-free public-rate-limited external-comparison/reference
entries with overlap and context caveats. WPR106-502 adds metadata-only
availability matrices for dYdX indexer candles and Deribit TradingView candles,
including Deribit `BASE-PERPETUAL` symbol candidate coverage; it still writes
no archive market-data rows and creates no accepted historical coverage proof.
WPR106-503 adds in-memory smoke fetch normalization for injected DATA-012
candle responses; it emits stable research-only normalized rows but performs no
archive writes and creates no accepted historical coverage proof.
WPR106-504 starts `DATA-013` by registering Coinbase spot, Kraken spot, Pyth
Hermes, DefiLlama, DexScreener, and GeckoTerminal as strict-free
spot/oracle/on-chain context sources with non-native and non-coverage-proof
boundaries. Availability matrices, probes, collectors, downloads, archive
writes, and accepted coverage remain later work.
WPR106-505 adds `defillama_context` to deterministic symbol-map candidates so
later context availability can require explicit verified mapping evidence
instead of ad hoc context IDs.
WPR106-506 adds deterministic DATA-013 spot/oracle/on-chain availability
matrices with verified-mapping gates and strict-free source-role validation.
WPR106-507 adds in-memory smoke fetch normalization for injected DATA-013
responses; it emits stable research-only normalized rows but performs no
archive writes and creates no accepted historical coverage proof.
WPR106-508 starts DATA-014 with generic trade-to-bar reconstruction models and
OHLCV bucketing for already-normalized rows; source-native candle comparisons,
archive writes, accepted coverage, and gold panels remain later work.
WPR106-509 adds generic reconstructed-vs-source candle comparison as quality
metadata; archive writes, accepted coverage, and gold panels remain later work.
WPR106-510 starts DATA-015 with generic orderflow/VWAP feature reconstruction
from already-normalized trade rows; funding/OI/BBO/L2/cross-venue feature
families, archive writes, accepted coverage, and gold panels remain later work.
WPR106-511 adds funding/OI/basis context feature reconstruction from
already-normalized derivatives context rows; BBO/L2/cross-venue feature
families, archive writes, accepted coverage, and gold panels remain later work.
WPR106-512 adds BBO spread feature reconstruction from already-normalized BBO
rows; L2/cross-venue feature families, archive writes, accepted coverage, and
gold panels remain later work.
WPR106-513 adds L2 depth feature reconstruction from already-normalized L2 rows;
cross-venue feature families, archive writes, accepted coverage, and gold
panels remain later work.
WPR106-514 completes the DATA-015 feature reconstruction foundation with
cross-venue basis features; archive writes, accepted coverage, and gold panels
remain later work.
WPR106-515 starts DATA-016 with a generic gate over existing coverage reports;
full family-specific accepted coverage evidence, archive writes, and gold
panel row materialization remain later work. WPR106-516 starts DATA-017 with
metadata-only gold research panel manifests over passed coverage gates and
feature refs; actual joined gold panel row writes, nullable feature alignment,
and durable accepted panel artifacts remain later work. WPR106-517 adds
in-memory gold panel row assembly from ready manifests and timestamped feature
values; durable gold panel file writes and archive-integrated row materializers
remain later work. WPR106-518 adds archive-root-contained gold-layer Parquet
writes for ready assemblies plus assembly JSON manifests and file-manifest
evidence; broader automated gold panel materializer jobs remain later work.
WPR106-519 adds the v2 Hyperliquid data-venue runbook and completes the
DATA-018 foundation for strict-free source order, requester-pays quarantine,
coverage gates, gold panels, validation, and operator stops.
WPR106-520 adds the multi-symbol coverage and gold-panel preflight bridge over
existing coverage and feature reconstruction refs. WPR106-521 adds the
all-or-nothing materializer for ready preflights and explicit per-symbol
row-value inputs, writing gold-layer artifacts only when every declared symbol
assembles cleanly with source row hashes. Backtest-data consumption of
accepted gold refs and broad unattended backfill scheduling remain later work.
WPR106-522 wires the bounded cycle over explicit archive-backed
`backtest_data_load` refs. WPR106-523 adds the existing archive-ref bounded
cycle spec lane over supplied local archive/universe refs and local
declarative JSON/YAML strategy specs, including focused no-blocker audit
evidence. Neither packet converts those refs or run results into accepted
research readiness, candidate, paper/live, order, sizing, runtime, promotion,
or readiness evidence.
