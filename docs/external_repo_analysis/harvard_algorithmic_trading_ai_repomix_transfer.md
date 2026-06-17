# External Repomix Transfer Report: `moondevonyt/Harvard-Algorithmic-Trading-with-AI` -> `ResearchEngineDeluxe`

Generated: 2026-06-17  
Target repo inspected through GitHub connector: `papaartemsmurf2002-commits/researchenginedeluxe` on `main`  
Source material inspected: uploaded Repomix file `repomix-output-moondevonyt-Harvard-Algorithmic-Trading-with-AI (1).md`  
Report type: docs-only external architecture-transfer analysis. This is **not** a work packet, not a stage-advancement claim, not a candidate-pack claim, and not live/paper/promotion evidence.

## Evidence notation

- `source:<path>:<line-range>` refers to line numbers in the extracted file section inside the uploaded Repomix, after Repomix compression.
- `repomix-header:<line-range>` refers to the packed Repomix header lines.
- `target:<path>:<line-range>` refers to line ranges observed in the current GitHub repo.
- Important limitation: the uploaded Repomix explicitly says empty lines were removed, content was compressed, and security checks were disabled (`repomix-header:29-36`). Some code bodies are replaced by `⋮----`, so implementation-level confidence is capped unless the original repo is fetched later.

---

## 1. Executive verdict

The source repo is **mostly not worth copying as architecture**. It is an educational trading repo organized around a simple **RBI** framing — Research, Backtest, Implement — with a few toy/teaching scripts, large checked-in OHLCV CSV files, and minimal operational discipline. The most useful material is not its code quality; it is the simple staged mental model and a set of anti-patterns that are useful as negative fixtures for `ResearchEngineDeluxe`.

`ResearchEngineDeluxe` is already much more mature. Its README defines the project as a research-only evidence system for BTC/ETH perpetual futures that must produce reproducible evidence and rejection reports, not live signals or sizing/order behavior (`target:README.md:5-8`). Its current structure already has provider intake, provenance/hashes, feature identities, historical cycles, candidate gates, and live-boundary rules (`target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:20-37`, `target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:43-60`). The imported source does **not** beat that architecture.

Direct answer:

- **Most useful source material:** the RBI stage separation from `README.md` and `backtest/README.md`, plus the simple research-source checklist in `research/README.md`.
- **Most useful adaptation:** create an `external_strategy_intake` / `source_research_intake` doc+schema for importing ideas from messy repos without turning them into candidate claims.
- **Most useful cautionary examples:** hard-coded local paths, committed data dumps without manifests, import-time live key/account setup, no tests, no source-quality evidence, no split/purge/multiple-testing validation, and direct API calls without typed contracts.
- **Most dangerous thing to copy:** `implement/bot.py` / `implement/nice_funcs.py` live-order path patterns. They mix globals, secrets, exchange calls, strategy logic, and scheduling with weak validation.
- **What to ignore:** MoonDev branding/banners, motivational trading claims, unvalidated strategy performance framing, broad book/resource lists except as optional seed metadata.
- **Confidence:** high that this source is low-maturity and mostly cautionary; medium on exact code mechanics because Repomix compression hides parts of implementation.
- **Highest-risk unknown:** whether the original, uncompressed repo has tests, manifests, hidden dependency files, or corrected code not visible in the uploaded Repomix. Nothing visible supports treating it as mature.
- **Best next action:** add a docs-only external source intake report or schema to your repo, then optionally add a “dirty external strategy fixture” validation test that deliberately rejects this kind of repo unless provenance, splits, costs, and candidate gates are supplied.

---

## 2. Material inventory

### 2.1 Source inventory: `moondevonyt/Harvard-Algorithmic-Trading-with-AI`

Apparent purpose: educational algorithmic-trading tutorial repo. The top README presents a simple RBI system: research, backtest, implement (`source:README.md:1-38`). It is not presented as a production research engine.

Visible directory structure:

| Area | Apparent role | Transfer value |
| --- | --- | --- |
| `research/` | Educational research reading/process notes | Low-to-medium; useful as rough source-discovery taxonomy only |
| `backtest/` | Backtesting scripts, data fetcher, large OHLCV CSVs | Medium as negative fixture / toy comparator source; low as architecture |
| `implement/` | Hyperliquid bot and helper functions | Mostly anti-pattern; do not copy into research engine |
| root config | `.env_example`, `.gitignore`, `.gitattributes` | Very weak security/config hygiene |

Full file inventory from the uploaded Repomix:

| File | Type | Lines | Classes | Functions |
| --- | --- | ---: | --- | --- |
| `backtest/data/BTC_15m_20250418_133857_historical.csv` | CSV data | 5001 |  |  |
| `backtest/data/BTC_1d_20250418_134026_historical.csv` | CSV data | 62 |  |  |
| `backtest/data/BTC-1h-1000wks-data.csv` | CSV data | 77376 |  |  |
| `backtest/data/BTC-6h-1000wks-data.csv` | CSV data | 12904 |  |  |
| `backtest/data/ETH-1d-1000wks-data.csv` | CSV data | 2977 |  |  |
| `backtest/data/SOL-1d-1000wks-data.csv` | CSV data | 1123 |  |  |
| `backtest/bb_squeeze_adx.py` | Python | 70 | BBSqueezeADX | init, next |
| `backtest/data.py` | Python | 93 |  | adjust_timestamp, get_ohlcv2, process_data_to_df, fetch_historical_data |
| `backtest/README.md` | Markdown/doc | 25 |  |  |
| `backtest/template.py` | Python | 41 | BollingerBandBreakoutShort | init, next |
| `implement/bot.py` | Python | 191 |  | print_banner, fetch_klines, calculate_indicators, analyze_market, check_for_entry_signals, bot, main |
| `implement/nice_funcs.py` | Python | 117 |  | ask_bid, get_sz_px_decimals, adjust_leverage_usd_size, get_ohlcv2, get_position, limit_order |
| `research/README.md` | Markdown/doc | 93 |  |  |
| `.env_example` | config | 1 |  |  |
| `.gitattributes` | config | 2 |  |  |
| `.gitignore` | config | 1 |  |  |
| `README.md` | Markdown/doc | 74 |  |  |

### 2.2 CSV/data inventory

The source has six checked-in market data files. That is useful as a data-quality stress example, not as trustworthy evidence.

| Source CSV | Rows | Start | End | Median interval | Duplicate timestamps | Big gaps >1.5x interval | Max gap |
| --- | ---: | --- | --- | --- | ---: | ---: | --- |
| `backtest/data/BTC_15m_20250418_133857_historical.csv` | 5000 | 2025-02-25 15:53:57.520 | 2025-04-18 17:38:57.520 | 0 days 00:15:00 | 0 | 0 | 0 days 00:15:00 |
| `backtest/data/BTC_1d_20250418_134026_historical.csv` | 61 | 2025-02-17 17:40:26.644 | 2025-04-18 17:40:26.644 | 1 days 00:00:00 | 0 | 0 | 1 days 00:00:00 |
| `backtest/data/BTC-1h-1000wks-data.csv` | 77375 | 2015-07-20 21:00:00 | 2024-05-19 17:00:00 | 0 days 01:00:00 | 9 | 28 | 0 days 16:00:00 |
| `backtest/data/BTC-6h-1000wks-data.csv` | 12903 | 2015-07-20 18:00:00 | 2024-05-19 12:00:00 | 0 days 06:00:00 | 0 | 1 | 0 days 12:00:00 |
| `backtest/data/ETH-1d-1000wks-data.csv` | 2976 | 2016-05-18 | 2024-07-12 | 1 days 00:00:00 | 0 | 1 | 3 days 00:00:00 |
| `backtest/data/SOL-1d-1000wks-data.csv` | 1122 | 2021-06-17 | 2024-07-12 | 1 days 00:00:00 | 0 | 0 | 1 days 00:00:00 |

Notes:

- `BTC-1h-1000wks-data.csv` has 77,375 rows, 9 duplicate timestamps, 28 large gaps, and max gap 16 hours. It should not be treated as clean evidence without explicit repair policy.
- `BTC-6h-1000wks-data.csv` has a 12-hour max gap.
- `ETH-1d-1000wks-data.csv` has a 3-day max gap.
- The 2025 Hyperliquid-derived files use `timestamp` with sub-second offset-looking values; older CSVs use `datetime`. Schema inconsistency matters for ingestion.

### 2.3 Source modules inspected

Deeply inspected:

- `README.md`
- `research/README.md`
- `backtest/README.md`
- `backtest/data.py`
- `backtest/bb_squeeze_adx.py`
- `backtest/template.py`
- `implement/bot.py`
- `implement/nice_funcs.py`
- all visible CSV headers and row/time-quality properties
- `.env_example`, `.gitignore`

Could not fully verify:

- exact indicator implementations in `bb_squeeze_adx.py`, `template.py`, and `implement/bot.py`, because Repomix compression replaced many code bodies with `⋮----`.
- dependency declarations, CI, package metadata, tests, deployment docs, and hidden excluded files. None are visible in the uploaded material.

### 2.4 Target repo context inspected

The target repo is not a generic research engine; it is a BTC/ETH perpetual futures research-only evidence system. Key current facts:

- Research-only identity: reproducible research evidence and rejection reports only; no live signals/order/sizing/promotions (`target:README.md:5-8`, `target:docs/ACTIVE_INDEX.md:11-15`).
- Current package split: `tradingbotsuite.data`, `features`, `strategies`, `backtesting`, `optimization`, `research_cycle`, `research_artifacts`, `live`, `promotion`, `web/ui` (`target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:83-99`).
- Research dataflow already covers provider/archive data -> manifest/fixture validation -> completed-bar/as-of features -> splits -> candidates -> backtests -> ranking/gates -> candidate pack only if gates pass (`target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:43-57`).
- Guardrails already require provenance, hashes, row counts, unsafe-source rejection, feature identity, split evidence, baseline comparators, gate evidence, and live-boundary rejection (`target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:138-210`, `target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:262-344`).
- Validation baseline is compile plus contract tests (`target:AGENTS.md:30-37`, `target:README.md:26-38`).

Implication: most source ideas should be adapted as **external intake/evaluation UX**, not copied into core architecture.

---

## 3. Architecture and flow map

### 3.1 Source repo architecture

Visible source flow:

```text
research notes
  -> backtest template / BB squeeze ADX script
  -> local CSV data files
  -> backtesting.py optimization
  -> implement/bot.py
  -> nice_funcs.py Hyperliquid helper calls
  -> live/pseudo-live scheduled loop
```

Critical observation: this is a simple teaching repo, not a research evidence engine. It lacks visible source manifests, stable schema contracts, feature identities, train/test split boundaries, candidate IDs, reproducible artifact records, evaluation gates, regression tests, and live-boundary enforcement.

### 3.2 Source data/control flow

- Research is documentation-first. `research/README.md` lists sources like academic resources, books, AI, trader interviews, and forums (`source:research/README.md:9-76`).
- Backtest scripts use local CSV paths and `backtesting.py`. `backtest/bb_squeeze_adx.py` loads a hard-coded CSV from `/Users/md/...` (`source:backtest/bb_squeeze_adx.py:1-3`), defines `BBSqueezeADX` (`source:backtest/bb_squeeze_adx.py:5-16`), then runs and optimizes a `Backtest` (`source:backtest/bb_squeeze_adx.py:55-70`).
- Data fetcher uses Hyperliquid-style candle snapshots, has a visible 5,000-bar cap note and global timestamp offset (`source:backtest/data.py:1-18`), then writes to another hard-coded local path (`source:backtest/data.py:86-93`).
- Implementation bot uses global symbol/leverage/position/strategy parameters (`source:implement/bot.py:21-46`), reads `HYPER_LIQUID_KEY` from environment (`source:implement/bot.py:14-18`), creates an account from that key (`source:implement/bot.py:48-49`), schedules runs every minute despite 6h candles (`source:implement/bot.py:181-189`), and calls helper functions for orderbook, positions, leverage, and orders.
- `nice_funcs.py` directly posts to `https://api.hyperliquid.xyz/info`, parses orderbook/meta/user state, computes size, and places orders via `exchange.order` (`source:implement/nice_funcs.py:1-117`).

### 3.3 Target-relevant flow comparison

`ResearchEngineDeluxe` already has a far stronger flow:

```text
provider/archive data
  -> data manifest / fixture pack
  -> provenance, hashes, row counts, context metadata
  -> completed-bar/as-of feature materialization
  -> feature-cache identity
  -> validation splits
  -> strategy candidate space
  -> reference/vector backtests
  -> split/regime/side/cost-stress/ablation/stability evidence
  -> rankings + gate report
  -> candidate pack only if all gates pass
```

That target flow is explicitly documented (`target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:43-57`). The source repo should therefore be used to strengthen intake controls around weak external repos, not to replace target components.

---

## 4. Extracted useful ideas

### A. Strong candidates to adapt

#### ID: STRONG-01

Category: ARCH / FLOW / DX  
Source: `README.md`, `backtest/README.md`, target docs  
Severity / usefulness: high  
Confidence: high  

Evidence: source README frames a simple `Research -> Backtest -> Implement` system (`source:README.md:8-38`); backtest README repeats backtesting as the validation phase after research (`source:backtest/README.md:1-25`). Target repo already has research-only staged evidence flow (`target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:43-57`).

What the source does: presents a very simple mental model for separating idea generation, historical validation, and implementation.

Why it matters for a research engine: your target repo is already sophisticated, but that complexity can make external strategy intake messy. A boring stage vocabulary helps prevent imported ideas from jumping straight to candidate-pack or runtime-adjacent paths.

Copy / adapt / reject: **Adapt, do not copy.**

Suggested adaptation for my repo: create `docs/external_source_intake/EXTERNAL_STRATEGY_INTAKE_CONTRACT.md` with stages like:

1. `idea_only`
2. `source_researched`
3. `formula_reconstructed`
4. `data_requirements_declared`
5. `diagnostic_backtest_only`
6. `split_validated`
7. `gate_eligible`
8. `candidate_pack_allowed`

Each stage must explicitly say what evidence exists and what is still blocked.

Verification needed: check whether an equivalent doc/schema already exists in `docs/contracts/` or `docs/work_packets/`.

Implementation risk: low. Docs/schema only. Risk is creating another parallel stage language that conflicts with existing WPR/stage ledger terms.

Minimal next step: add an external-intake contract doc mapping these simple stages to current `research_only`, `observe_only`, and gate states.

Larger refactor option: add a typed `ExternalStrategyIntakeManifest` Pydantic model used by strategy import tooling and artifact index.

---

#### ID: STRONG-02

Category: EVAL / CITE / DATA  
Source: `research/README.md`  
Severity / usefulness: high  
Confidence: medium-high  

Evidence: source research README lists broad source categories: academic resources, AI/ML resources, trader insights, online platforms, books, and best practices like documenting everything, cross-referencing multiple sources, identifying assumptions, and seeking counter-arguments (`source:research/README.md:9-93`).

What the source does: offers a broad but unsophisticated source-discovery taxonomy.

Why it matters for a research engine: your repo could benefit from a structured source-intake checklist for external strategy claims: where did the idea come from, what assumptions does it require, what data is needed, what counterarguments exist, and whether source quality is strong enough for implementation work.

Copy / adapt / reject: **Adapt.**

Suggested adaptation for my repo: convert the loose source list into a machine-checkable `source_quality` block:

```json
{
  "source_type": "paper|book|repo|forum|youtube|ai_generated|manual_hypothesis",
  "source_url_or_path": "...",
  "claim_type": "mechanism|formula|performance|implementation",
  "primary_evidence_available": false,
  "counterarguments_recorded": false,
  "assumptions": [],
  "data_requirements": [],
  "market_regime_requirements": [],
  "reproducibility_status": "unknown|partial|reproduced|rejected"
}
```

Verification needed: inspect existing target `docs/contracts/` for source-quality or imported-knowledge schemas before adding a new one.

Implementation risk: medium. Too much metadata can become paperwork unless it gates real actions.

Minimal next step: add it to docs as an optional external-source intake checklist, not mandatory for all internal experiments.

Larger refactor option: attach this schema to research artifact manifests and operator artifact UI filtering.

---

#### ID: STRONG-03

Category: DATA / TEST / ANTI  
Source: source CSV data files and `backtest/data.py`  
Severity / usefulness: high  
Confidence: high  

Evidence: source includes large checked-in OHLCV files with mixed `timestamp`/`datetime` columns, multiple intervals, duplicate/gap issues, and no visible manifest. `backtest/data.py` documents a Hyperliquid 5,000-bar limit and truncates to the latest 5,000 rows (`source:backtest/data.py:1-15`, `source:backtest/data.py:70-84`).

What the source does: gives messy real-world-ish market data examples and an API-capability limit.

Why it matters for a research engine: this is exactly the kind of external data that should be accepted only as diagnostic input unless it has source metadata, interval validation, hash manifests, row counts, gap policy, and capability labels. Your repo already requires provenance, hashes, row counts, unsafe-source rejection, gap/duplicate evidence, interval semantics, and diagnostic/free-sample metadata (`target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:138-160`).

Copy / adapt / reject: **Adapt as test fixture / rejection scenario, not as evidence.**

Suggested adaptation for my repo:

- Add a “dirty external OHLCV import” validation case that scans files like these and emits a fail-closed report:
  - schema mismatch: `timestamp` vs `datetime`
  - missing source/provider manifest
  - duplicate timestamps
  - interval gaps
  - unknown timezone/source clock
  - no content hash manifest
  - no data-license/source-access metadata
  - latest-window or API-limit metadata missing

Verification needed: confirm whether current data-contract tests already cover inconsistent timestamp names, duplicates, and gap policies for raw external CSV imports.

Implementation risk: low-to-medium. Avoid committing large CSVs. Use generated/small synthetic fixtures that mimic the failures.

Minimal next step: add a doc table of external CSV rejection reasons to data contracts.

Larger refactor option: add `external_csv_probe` CLI that produces a non-candidate `DataIntakeReview` artifact.

---

#### ID: STRONG-04

Category: SEC / AGENT / TEST  
Source: `implement/bot.py`, `implement/nice_funcs.py`  
Severity / usefulness: critical as negative test material  
Confidence: high  

Evidence: `implement/bot.py` reads `HYPER_LIQUID_KEY` and creates an account at module/global setup (`source:implement/bot.py:14-49`). `nice_funcs.py` includes live-adjacent helpers for orderbook, leverage sizing, user positions, and `exchange.order` (`source:implement/nice_funcs.py:1-117`). Target repo explicitly says research modules must not import order-placement adapters and research jobs must not place orders or write live configuration (`target:AGENTS.md:22-28`).

What the source does: puts live-adjacent exchange access close to strategy analysis and scheduled bot control.

Why it matters for a research engine: this is a perfect “do not allow this into research path” example. If your external import tooling ever ingests repos, it should flag `Account.from_key`, `Exchange(...)`, `exchange.order`, env secrets, and live REST endpoints as boundary violations.

Copy / adapt / reject: **Reject implementation; adapt as lint/signature tests.**

Suggested adaptation for my repo:

- Add a static import/lint review for external source imports:
  - detect `Account.from_key`, `Exchange`, `exchange.order`, `constants.MAINNET_API_URL`
  - detect `.env` / secret names
  - classify as `live_adjacent_source_detected: true`
  - block research artifact eligibility unless code is manually isolated and rewritten

Verification needed: inspect current `tests/contracts/test_import_boundaries.py` and live/promotion boundary tests to avoid duplicate logic.

Implementation risk: medium. Regex-only scanning can false-positive docs or safe examples. Treat it as review signal, not final proof.

Minimal next step: add this source as an example in a docs checklist.

Larger refactor option: add an `ExternalRepoRiskScanner` used by future repomix ingestion.

---

#### ID: STRONG-05

Category: EVAL / SEARCH / CITE  
Source: `backtest/bb_squeeze_adx.py`, `backtest/template.py`, `implement/bot.py`  
Severity / usefulness: medium-high  
Confidence: medium  

Evidence: visible strategy parameters include Bollinger Bands, Keltner Channels, ADX, take-profit, stop-loss (`source:backtest/bb_squeeze_adx.py:5-16`, `source:implement/bot.py:31-46`). Backtest scripts run optimization (`source:backtest/bb_squeeze_adx.py:62-70`, `source:backtest/template.py:29-41`).

What the source does: presents a small external strategy family that can be reconstructed as a diagnostic comparator: Bollinger/Keltner squeeze release with ADX threshold and fixed TP/SL.

Why it matters for a research engine: low-complexity external strategies are useful for testing the research pipeline, feature requirements, baseline comparator handling, and rejection reports. They should not be treated as alpha just because a tutorial used them.

Copy / adapt / reject: **Adapt only as a diagnostic external strategy spec, not as candidate evidence.**

Suggested adaptation for my repo:

- Add a reconstructed `external_bb_squeeze_adx_v0` spec under docs or strategy registry only if explicitly scoped.
- Mark it `external_tutorial_source`, `diagnostic_only`, `candidate_evidence: false`, `promotion_ready: false`.
- Require train/test splits, fees/funding/slippage, multiple-testing accounting, baseline comparators, and modern-window evidence before any gate path sees it.

Verification needed: the actual formulas are hidden by Repomix compression, so the original source or independent formula reconstruction is required.

Implementation risk: high if copied as a strategy; medium if used as a diagnostic comparator.

Minimal next step: record it as a rejected/diagnostic source idea, not code.

Larger refactor option: create a strategy-import pathway where external strategies start as immutable source descriptors and cannot enter optimization until contracts pass.

---

### B. Conditional candidates

#### ID: COND-01

Category: DATA / OPS  
Source: `backtest/data.py`  
Severity / usefulness: medium  
Confidence: medium-high  

Evidence: the source explicitly notes Hyperliquid max bars as 5,000 and uses a constant `BATCH_SIZE = 5000` plus `MAX_ROWS = 5000` (`source:backtest/data.py:1-15`).

What the source does: encodes a provider capability limit informally.

Why it matters for a research engine: provider capability limits should live in manifests or capability schemas, not in comments and hard-coded globals. Your target already cares about source capability and latest-window diagnostic limits (`target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:148-160`, `target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:262-276`).

Copy / adapt / reject: **Adapt if Hyperliquid candle fetching remains relevant.**

Suggested adaptation for my repo: add/confirm provider capability metadata:

```json
{
  "provider": "hyperliquid",
  "endpoint": "candleSnapshot",
  "max_bars_per_request": 5000,
  "history_depth_mode": "limited_window|archive_required",
  "candidate_depth_eligible": false,
  "requires_archive_backfill_for_long_horizon": true
}
```

Verification needed: verify current Hyperliquid API behavior before hard-coding. Provider limits may change.

Implementation risk: medium if stale provider assumptions become false.

Minimal next step: add a TODO/check in provider runbook, not code.

Larger refactor option: central provider capability registry consumed by intake and UI.

---

#### ID: COND-02

Category: SEARCH / EVAL  
Source: `research/README.md`  
Severity / usefulness: medium  
Confidence: medium  

Evidence: the source says to cross-reference sources, identify assumptions, consider risk first, and look for counterarguments (`source:research/README.md:77-93`).

What the source does: gives human advice rather than implementation.

Why it matters for a research engine: this maps well onto claim/evidence/contradiction tracking for strategy research reports.

Copy / adapt / reject: **Adapt if you plan a general research-report engine beyond trading cycles.**

Suggested adaptation for my repo: add report sections for imported hypotheses:

- `hypothesis`
- `source_claims`
- `assumptions`
- `contradictory_evidence`
- `required_data`
- `falsification_tests`
- `status`

Verification needed: check whether existing stage-report templates already include these fields.

Implementation risk: low.

Minimal next step: add to docs template only.

Larger refactor option: create `ClaimEvidenceMap` artifact model.

---

#### ID: COND-03

Category: PERF / TEST  
Source: `backtest/template.py`, `backtest/bb_squeeze_adx.py`  
Severity / usefulness: medium  
Confidence: low-medium  

Evidence: source uses `backtesting.py` optimizer over parameters like TP/SL, windows, std multipliers, with constraints (`source:backtest/template.py:29-41`, `source:backtest/bb_squeeze_adx.py:62-70`).

What the source does: simple grid-style parameter optimization.

Why it matters for a research engine: the idea is common and already present in your repo via optimization/candidate cycles. The source is useful only as a caution that optimization without split/purge/multiple-testing/stability is overfit bait.

Copy / adapt / reject: **Mostly reject; use as a negative benchmark.**

Suggested adaptation for my repo: add a “naive single-window optimizer” negative-control doc/test that demonstrates why candidate gates must block pretty in-sample results.

Verification needed: target likely already has multiple-testing and validation-floor manifests, so avoid redundant work.

Implementation risk: low if docs-only; high if someone uses it as an accepted optimizer.

Minimal next step: mention in external intake checklist.

Larger refactor option: add a deliberate overfit-control simulator to evaluation suite.

---

#### ID: COND-04

Category: OPS / UI  
Source: `implement/bot.py`  
Severity / usefulness: low-medium  
Confidence: medium  

Evidence: source bot prints market state, indicator values, signals, and scheduled status in a terminal loop (`source:implement/bot.py:60-191`).

What the source does: simple operator visibility via terminal prints.

Why it matters for a research engine: your repo already has an operator UI, artifact index, and boundary review. The only transferable idea is that operator surfaces should make current state readable. The implementation itself is weak.

Copy / adapt / reject: **Reject code; optionally adapt UX principle.**

Suggested adaptation for my repo: no action unless current UI lacks a simple “why no candidate?” explanation. If missing, expose rejection reasons, data readiness, and gate blockers more clearly.

Verification needed: inspect current operator UI reports before adding anything.

Implementation risk: low.

Minimal next step: none.

Larger refactor option: improve read-only report summaries in UI.

---

### C. Anti-patterns / things to avoid

#### ID: ANTI-01

Category: DATA / OPS / ANTI  
Source: `backtest/data/*.csv`  
Severity / usefulness: critical  
Confidence: high  

Evidence: the source commits large OHLCV CSV data directly, including a 5 MB BTC 1h file with duplicates and gaps, with no visible manifest/hashes/source license. Target docs explicitly say provider caches, local downloads, credentials, SQLite databases, and unreviewed generated artifacts should stay out of git (`target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:308-320`).

What the source does: treats local CSV files as repo data.

Why it matters for a research engine: unchecked data files rot, are hard to verify, can silently change evidence, and can be mistaken for candidate-depth datasets.

Copy / adapt / reject: **Reject.**

Suggested adaptation for my repo: preserve current manifest/hashing stance. Add external CSV rejection examples if helpful.

Verification needed: ensure `.gitignore` and data contracts still block raw provider cache commits.

Implementation risk: high if copied blindly.

Minimal next step: no import of source CSVs except tiny synthetic failure fixtures.

Larger refactor option: external data quarantine directory with mandatory manifest generation.

---

#### ID: ANTI-02

Category: DX / OPS / ANTI  
Source: `backtest/bb_squeeze_adx.py`, `backtest/template.py`, `backtest/data.py`  
Severity / usefulness: high  
Confidence: high  

Evidence: source scripts hard-code local absolute paths under `/Users/md/Dropbox/dev/github/...` (`source:backtest/bb_squeeze_adx.py:1-3`, `source:backtest/template.py:1-3`, `source:backtest/data.py:86-93`).

What the source does: makes scripts non-portable.

Why it matters for a research engine: path portability is already a known target concern; target docs record path rebasing and output-root fail-closed hardening in active stages (`target:docs/ACTIVE_INDEX.md:116-128`).

Copy / adapt / reject: **Reject.**

Suggested adaptation for my repo: use this as a static scanner rule for external code.

Verification needed: none for this source; visible.

Implementation risk: high if imported.

Minimal next step: external intake checklist: “absolute local paths found => diagnostic only.”

Larger refactor option: code scanner emits `portability_risk`.

---

#### ID: ANTI-03

Category: SEC / OPS / ANTI  
Source: `.env_example`, `.gitignore`, `implement/bot.py`  
Severity / usefulness: critical  
Confidence: high  

Evidence: `.env_example` contains only `HYPER_LIQUID_KEY=xxxxx`; `.gitignore` only ignores `.env`; `implement/bot.py` reads the key and constructs an account (`source:.env_example:1`, `source:.gitignore:1`, `source:implement/bot.py:14-49`).

What the source does: minimal secret hygiene with live-adjacent account setup in implementation code.

Why it matters for a research engine: target has explicit live/research boundaries and should not allow research imports to instantiate accounts, even if credentials are absent.

Copy / adapt / reject: **Reject.**

Suggested adaptation for my repo: scanner rule and docs risk entry.

Verification needed: inspect if current secret scanning/preflight catches env-key usage in research modules.

Implementation risk: critical if copied.

Minimal next step: none besides warning.

Larger refactor option: external repo risk scanner.

---

#### ID: ANTI-04

Category: TEST / EVAL / ANTI  
Source: whole source repo  
Severity / usefulness: critical  
Confidence: high  

Evidence: no visible `tests/`, no CI config, no `pyproject.toml`, no lockfile, no contract tests, no reproducible validation commands in uploaded source. Target repo has explicit validation baseline and contract tests (`target:README.md:26-38`, `target:AGENTS.md:30-37`).

What the source does: provides examples, not verified components.

Why it matters for a research engine: no tests means no trust boundary. Imported code must be treated as untrusted pseudocode.

Copy / adapt / reject: **Reject code copying.**

Suggested adaptation for my repo: require every imported strategy to arrive with tests or be implemented from scratch under target contracts.

Verification needed: original repo could contain excluded files, but uploaded material does not show them.

Implementation risk: high.

Minimal next step: external intake contract says “no tests visible => source maturity low.”

Larger refactor option: automatic repo maturity score.

---

#### ID: ANTI-05

Category: EVAL / PERF / ANTI  
Source: `backtest/bb_squeeze_adx.py`, `backtest/template.py`  
Severity / usefulness: high  
Confidence: medium-high  

Evidence: source backtests optimize parameters after loading a single local CSV (`source:backtest/bb_squeeze_adx.py:1-3`, `source:backtest/bb_squeeze_adx.py:55-70`). No visible split, purge, embargo, OOS, multiple-testing, baseline comparator, or stability evidence.

What the source does: classic one-file parameter optimization.

Why it matters for a research engine: this is how false-positive strategies are born. Your target already requires split/gate/multiple-testing and treats zero eligible candidates as valid (`target:docs/ACTIVE_INDEX.md:158-162`).

Copy / adapt / reject: **Reject as evidence; adapt as overfit-control example.**

Suggested adaptation for my repo: document this as a blocked pattern: “single-window optimized tutorial strategy is not eligible.”

Verification needed: original code hidden by compression, but missing eval files are visible enough.

Implementation risk: high if copied.

Minimal next step: add to external strategy intake risk table.

Larger refactor option: add naive-optimizer negative control.

---

#### ID: ANTI-06

Category: OPS / PERF / ANTI  
Source: `implement/bot.py`, `nice_funcs.py`  
Severity / usefulness: high  
Confidence: medium-high  

Evidence: source bot schedules the main bot every minute while fetching/analyzing 6h candles (`source:implement/bot.py:81-110`, `source:implement/bot.py:181-189`). Helpers perform direct HTTP requests and SDK actions with no visible timeout/backoff/schema validation (`source:implement/nice_funcs.py:1-117`).

What the source does: scheduled loop with direct API helpers.

Why it matters for a research engine: research jobs need bounded retries, artifact state, failure classification, and truthful metadata; live-adjacent code needs even stricter controls.

Copy / adapt / reject: **Reject.**

Suggested adaptation for my repo: no direct action; target already has operator/research job hardening. Use as external risk example.

Verification needed: none.

Implementation risk: high.

Minimal next step: no code import.

Larger refactor option: static scanner for unbounded `requests.post`, `schedule.every`, and direct SDK exchange calls.

---

#### ID: ANTI-07

Category: DATA / ANTI  
Source: `backtest/data.py`  
Severity / usefulness: medium-high  
Confidence: medium  

Evidence: source computes a global `timestamp_offset` by comparing the latest API timestamp to the system current date, then adjusts timestamps (`source:backtest/data.py:17-55`).

What the source does: ad hoc timestamp correction.

Why it matters for a research engine: timestamp manipulation is dangerous unless provenance and clock assumptions are recorded. It can create false alignment with candles/features.

Copy / adapt / reject: **Reject; adapt as test case for clock-source metadata.**

Suggested adaptation for my repo: data contracts should require clock/source timezone, raw timestamp preservation, adjustment reason, and deterministic transform identity.

Verification needed: inspect current data contracts for timestamp-adjustment provenance.

Implementation risk: high if copied.

Minimal next step: add to risk register.

Larger refactor option: timestamp-transform manifest identity.

---

#### ID: ANTI-08

Category: ARCH / ANTI  
Source: `implement/bot.py`  
Severity / usefulness: medium-high  
Confidence: high  

Evidence: source bot relies on global configuration and mutable globals such as `SYMBOL`, `LEVERAGE`, `POSITION_SIZE_USD`, strategy params, `squeeze_flag`, `squeeze_released`, and `last_candle_time` (`source:implement/bot.py:21-54`).

What the source does: global mutable state.

Why it matters for a research engine: global state breaks reproducibility and makes artifact identity unclear.

Copy / adapt / reject: **Reject.**

Suggested adaptation for my repo: preserve Pydantic/config-spec discipline. Do not let external strategy imports define runtime globals.

Verification needed: none.

Implementation risk: high if copied.

Minimal next step: external intake rule: global mutable state must be rewritten into config/artifact model.

Larger refactor option: config normalizer for imported strategy ideas.

---

### D. Interesting but low-priority

#### ID: LOW-01

Category: DX  
Source: `README.md`, `research/README.md`, `implement/bot.py`  
Severity / usefulness: low  
Confidence: high  

Evidence: source is tutorial/branding-heavy, with video/course links and MoonDev banner/quotes (`source:README.md:1-74`, `source:implement/bot.py:1-20`).

What the source does: tries to make trading automation approachable.

Why it matters for a research engine: onboarding clarity is useful, but your repo should not import branding or hype.

Copy / adapt / reject: **Reject.**

Suggested adaptation for my repo: maybe keep docs readable, but not motivational.

Verification needed: none.

Implementation risk: low.

Minimal next step: none.

Larger refactor option: none.

---

#### ID: LOW-02

Category: SEARCH / CITE  
Source: `research/README.md`  
Severity / usefulness: low-medium  
Confidence: medium  

Evidence: source lists books and broad resources (`source:research/README.md:26-76`).

What the source does: gives a reading list.

Why it matters for a research engine: it could seed a manual research bibliography, but it is too broad and not evidence-mapped.

Copy / adapt / reject: **Adapt only if building a bibliography/intake module.**

Suggested adaptation for my repo: optional `docs/research_sources/strategy_source_seed_list.md`, with quality tiers and not as evidence.

Verification needed: check if WPR106-23 or imported strategy master report already covers this.

Implementation risk: low.

Minimal next step: ignore for now.

Larger refactor option: bibliography with claim extraction.

---

## 5. Cross-source comparison

Because only one external Repomix was provided, this table compares internal source areas against the target repo architecture.

| Source area | Architecture quality | Implementation maturity | Research-engine relevance | Test/eval quality | Observability/reliability | Ease of adaptation | Hidden complexity | Copy risk | Overall rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `research/README.md` | Low | Low | Medium as checklist | None | None | Easy as docs | Low | Low | 1 |
| `README.md` RBI model | Low but clear | Low | Medium-high as intake stage vocabulary | None | None | Easy | Low | Low | 2 |
| `backtest/data.py` | Low | Low-medium | Medium as provider-limit/data-risk example | None | Weak | Medium as negative tests | Medium timestamp risk | High | 3 |
| `backtest/*.py` strategies | Low | Low | Medium as diagnostic toy strategy | Weak/none | None | Medium if rebuilt | Medium due compressed formulas | High | 4 |
| CSV datasets | None | N/A | Medium as dirty data fixtures | No manifests | None | Low; avoid large files | High provenance gaps | High | 5 |
| `implement/nice_funcs.py` | Low | Low | Low as implementation; high as boundary-risk example | None | Weak | Low | High live/API risk | Critical | 6 |
| `implement/bot.py` | Low | Low | Low as implementation; high as anti-pattern | None | Weak terminal prints only | Low | High live/state risk | Critical | 7 |
| Target `ResearchEngineDeluxe` current architecture | High | High relative to source | Direct | Strong contract baseline | Stronger artifact/stage model | N/A | High but documented | N/A | Baseline to preserve |

Main comparison result: the source repo should be treated as **external-source-intake training material**, not as an architectural donor.

---

## 6. Research engine improvement map

| Possible improvement for my repo | Source inspiration | Expected benefit | Implementation difficulty | Risk | Confidence | Verification needed | Suggested priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Add `ExternalStrategyIntakeManifest` docs/schema | RBI model + weak source maturity | Prevent messy external ideas from becoming candidate claims | Low docs / medium schema | Stage-language duplication | High | Check existing contracts/docs first | P1 |
| Add external source-quality checklist: source type, assumptions, counterarguments, data requirements, falsification tests | `research/README.md` | Better provenance and claim tracking for imported strategy ideas | Low | Paperwork bloat | Medium-high | Check stage report templates | P1 |
| Add dirty external CSV probe / rejection reasons | Source CSVs + no manifests | Better raw-source quarantine and data-quality reviews | Medium | Duplicate existing data contracts | High | Inspect `tests/contracts/test_data_contracts.py` | P1/P2 |
| Add provider capability metadata for Hyperliquid/API depth ceilings if not already explicit | `backtest/data.py` 5,000 bar note | Avoid accidental latest-window evidence overclaim | Low-medium | Stale provider behavior | Medium | Verify current API capability | P2 |
| Add external-repo risk scanner docs/rules for `Account.from_key`, `exchange.order`, hardcoded paths, `.env`, direct `requests.post` | `implement/*` | Keeps live-adjacent code out of research imports | Medium | False positives | High | Check import-boundary tests | P2 |
| Record BB Squeeze ADX as diagnostic external tutorial strategy, not candidate | `bb_squeeze_adx.py`, `bot.py` | Cheap end-to-end comparator/negative-control idea | Medium | Alpha cosplay if misused | Medium | Need original formulas | P3 |
| Add overfit-negative example: single-window optimized tutorial strategy | `backtest/*.py` optimization | Better explanation of why gates reject naive backtests | Low-medium | Redundant with existing gates | Medium | Check current eval docs | P3 |
| Add UI/readout improvement for “why no candidate” if current UI lacks it | source terminal status prints | Better operator comprehension | Medium | Distraction | Low-medium | Inspect current UI | P4 |
| Import reading list as bibliography seed | `research/README.md` | Minor research-source convenience | Low | Noise | Low | Check WPR106-23 imported report | P4/ignore |

---

## 7. Risk register

| Risk | Source/evidence | Probability | Impact | Why it matters | Mitigation | Verification step |
| --- | --- | --- | --- | --- | --- | --- |
| Copying tutorial bot code into research path | `implement/bot.py`, `nice_funcs.py`; live key/account/order helpers | Medium if imported naively | Critical | Violates research-only/live boundary | Reject code; static scanner; import-boundary tests | Inspect `tests/contracts/test_import_boundaries.py` |
| Treating local CSVs as clean evidence | checked-in CSVs with no manifests; BTC 1h duplicates/gaps | Medium | High | Corrupts feature/backtest/gate evidence | Quarantine; require manifests/hashes/gap policy | Data contract review |
| Overfitting naive backtest optimization | `bt.optimize` visible without split/gates | Medium | High | False candidates | Require split, purge, comparator, multiple-testing, stability | Check target gate docs/tests |
| Timestamp mutation without provenance | global `timestamp_offset` logic | Low-medium | High | Misaligned candles/features | Preserve raw timestamps; record transform identity | Inspect data contracts |
| Absolute local path leakage | `/Users/md/...` in scripts | High if copied | Medium-high | Non-portable, breaks CI/replay | Scanner/rewrite to config paths | Static search |
| Secrets and env key handling in imported code | `.env_example`, `HYPER_LIQUID_KEY`, `Account.from_key` | Medium | Critical | Credential and live-boundary risk | Never import; isolate examples | Secret scan / boundary test |
| Direct API calls without timeout/schema/retry | `requests.post` helpers | Medium | Medium-high | Silent failures and unreliable data | Provider adapters with typed responses and failure artifacts | Provider tests |
| Large generated data in git | source CSVs | Low in target due existing rules | Medium | Repo bloat and stale evidence | Keep current gitignore/data policy | Check `.gitignore` and data dirs |
| Repomix compression hides actual code | `repomix-header:34-36`; `⋮----` code gaps | High | Medium | False precision in analysis | Treat as source-level evidence only; fetch original if implementing | Fetch original repo before code adaptation |
| Motivational docs imply historical success transfers | README/backtest docs | Medium | Medium | Encourages weak evidence claims | Replace with falsification-first language | Review docs wording if adapted |

---

## 8. Missing information

| Missing information | Why it matters | Recommendation depends on it? | How to obtain/verify |
| --- | --- | --- | --- |
| Original uncompressed source code | Needed before implementing any formula/strategy exactly | Yes for BB Squeeze ADX implementation | Fetch original repo, inspect raw files, run tests if any |
| Source repo dependency files | Need to know packages/versions and reproducibility | Only for implementation; not for cautionary analysis | Check original repo for `requirements.txt`, `pyproject.toml`, lockfiles |
| Source repo test/CI state outside Repomix | Could slightly change maturity assessment | No for current verdict; yes for copying code | Inspect original repo branches/actions |
| Exact formula definitions hidden behind `⋮----` | Needed for deterministic strategy reconstruction | Yes for strategy plugin | Fetch raw code or write independent spec |
| Existing target schemas for imported external strategy/source quality | Avoid duplicate docs/models | Yes for implementation planning | Search `docs/contracts/`, `src/tradingbotsuite/research_artifacts/`, `src/tradingbotsuite/strategies/` |
| Current target provider capability metadata | Needed before adding Hyperliquid API limit metadata | Yes | Inspect provider manifest/code/tests |
| Current target external report/import process from WPR106-23 | The repo may already have imported-source knowledge handling | Yes | Read WPR106-23 packet/report |
| Whether user wants general research engine features beyond trading | Some source-discovery ideas are broader than trading | Partially | Scope next work packet |

Missing information is not blocking this report because the source is visibly low-maturity and the safest transfer is docs/schema/risk scanning rather than code.

---

## 9. Recommendations

### 1. Add an external strategy/source intake contract

Reason: this source shows the exact failure mode: an external repo can have a clear idea and teaching value while lacking enough evidence for candidate flow.

Source evidence: RBI model in source README/backtest docs (`source:README.md:8-38`, `source:backtest/README.md:1-25`); target already requires research-only evidence and candidate gates (`target:README.md:5-8`, `target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:43-57`).

Expected benefit: high. Makes future repomix imports safer and more systematic.

Implementation effort: low for docs; medium if Pydantic schema and artifact model are added.

Risk: medium if it duplicates current stage language.

Confidence: high.

First verification step: search existing target docs for “external source”, “imported strategy”, “source quality”, “claim evidence”.

When not to do it: if WPR106-23 already created an equivalent contract.

---

### 2. Use this source as a negative fixture for external repo risk scanning

Reason: it contains common hazards: hard-coded paths, raw data dumps, no tests, direct live API/order helpers, env keys, global mutable state, naive optimization.

Source evidence: hard-coded paths (`source:backtest/bb_squeeze_adx.py:1-3`, `source:backtest/data.py:86-93`), live key/account/order helpers (`source:implement/bot.py:14-49`, `source:implement/nice_funcs.py:1-117`), no visible tests/config.

Expected benefit: high for future external ingestion robustness.

Implementation effort: medium.

Risk: false positives if scanner is used as an absolute blocker instead of review signal.

Confidence: high.

First verification step: inspect existing import-boundary and artifact-validation tests.

When not to do it: if no future external repo ingestion/import is planned.

---

### 3. Add/confirm dirty raw CSV intake review

Reason: the source data files are plausible but not evidence-grade. BTC 1h has duplicates and gaps; multiple files use inconsistent timestamp columns; no manifests are visible.

Source evidence: CSV inventory in this report; target data provenance requirements (`target:docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md:138-160`).

Expected benefit: medium-high.

Implementation effort: medium.

Risk: duplicate of existing data-contract coverage.

Confidence: high.

First verification step: inspect `tests/contracts/test_data_contracts.py` and raw CSV loader behavior.

When not to do it: if existing raw-source intake already emits all these rejection reasons.

---

### 4. Record Hyperliquid provider limits as capability metadata only after verifying current API

Reason: source comments note a 5,000-bar cap. Provider ceilings affect whether evidence is latest-window diagnostic or candidate-depth.

Source evidence: `source:backtest/data.py:1-15`.

Expected benefit: medium.

Implementation effort: low-medium.

Risk: provider behavior may have changed; do not trust the tutorial comment.

Confidence: medium.

First verification step: verify current Hyperliquid candle endpoint behavior from provider docs or live adapter tests.

When not to do it: if Binance Vision/Crypto Lake catalog remains the source of truth for candidate-depth history and Hyperliquid candles are not used for long-horizon research.

---

### 5. Do not implement BB Squeeze ADX as a candidate strategy from this source

Reason: visible code is incomplete due compression, evaluation is weak, and the strategy is a common technical-analysis tutorial pattern.

Source evidence: `BBSqueezeADX` visible with params and `bt.optimize`, but formula bodies hidden and no split/gate evidence (`source:backtest/bb_squeeze_adx.py:5-70`).

Expected benefit of rejection: prevents alpha cosplay and duplicate weak strategies.

Implementation effort: none.

Risk: missing a cheap diagnostic comparator, but that can be revisited.

Confidence: high.

First verification step: none unless specifically scoping diagnostic comparator work.

When not to do it: only implement if a work packet explicitly asks for a diagnostic external tutorial strategy and blocks it from candidate evidence.

---

### 6. Preserve target research/live boundary and do not import `implement/*`

Reason: source implementation code is live-adjacent and not separated enough for your research repo.

Source evidence: account/key setup and exchange helper/order calls (`source:implement/bot.py:14-49`, `source:implement/nice_funcs.py:1-117`); target forbids research jobs from placing orders or writing live config (`target:AGENTS.md:22-28`).

Expected benefit: critical safety.

Implementation effort: none.

Risk: none.

Confidence: high.

First verification step: optional static search in target to ensure no accidental import of external live helpers.

When not to do it: never copy this code into research modules.

---

## 10. Handoff brief for implementation planning

### Highest-value ideas to adapt

1. **External strategy/source intake contract**
   - Target components: `docs/contracts/`, `docs/external_source_intake/`, maybe `src/tradingbotsuite/research_artifacts/`.
   - Purpose: prevent imported repomix ideas from skipping evidence gates.

2. **Source-quality / claim-evidence checklist**
   - Target components: stage report templates, external knowledge docs, artifact manifest docs.
   - Purpose: record source type, assumptions, counterarguments, data requirements, reproducibility status.

3. **Dirty external data review**
   - Target components: `tradingbotsuite.data`, data contracts, fixture-pack validation, tests.
   - Purpose: fail closed on raw CSVs without manifest/hashes/gap policy.

4. **External repo risk scanner / checklist**
   - Target components: docs first; optional tool later.
   - Purpose: flag hard-coded paths, env secrets, live SDK/order functions, direct API calls, missing tests.

5. **Optional diagnostic BB Squeeze ADX descriptor**
   - Target components: `docs/external_source_intake/` only at first.
   - Purpose: record as rejected/diagnostic external strategy, not candidate evidence.

### Rejected ideas and why

- Copying `implement/bot.py`: live-adjacent, global state, secret/account setup, weak scheduling, no target-compatible boundary.
- Copying `nice_funcs.py`: direct exchange helper code with order placement and weak API discipline.
- Importing source CSVs as evidence: no manifests/hashes/provenance; gaps/duplicates; inconsistent timestamp schema.
- Copying `backtest/*.py` as accepted strategy code: single-file local path, hidden formula bodies, no split/purge/multiple-testing/gates.
- Importing motivational docs/resource lists wholesale: too broad, not evidence-mapped.

### Likely target components

- `docs/contracts/`
- `docs/external_source_intake/` or `docs/research_sources/`
- `src/tradingbotsuite/data/` only if adding raw CSV probe
- `tests/contracts/test_data_contracts.py`
- `tests/contracts/test_import_boundaries.py`
- `src/tradingbotsuite/research_artifacts/` only if creating typed manifests
- operator UI/artifact index only later, if external source review artifacts should be visible

### Required verification tasks

1. Search target repo for existing external-source/imported-strategy contract.
2. Inspect WPR106-23 imported external strategy/report handling before adding new docs.
3. Inspect data contract tests for duplicate/gap/raw CSV behavior.
4. Inspect import-boundary tests for live SDK/order-placement patterns.
5. Verify current Hyperliquid API/data capability before recording any limit.

### Suggested implementation sequence

1. Docs-only packet: `External Source Intake Contract`.
2. Add example review entry for this Repomix as a low-maturity, diagnostic-only external source.
3. Add small synthetic dirty CSV fixtures to tests, not the large source CSVs.
4. Add static scanner/checklist for external repo risks.
5. Only later, if useful, add typed `ExternalStrategyIntakeManifest`.
6. Only later, if explicitly scoped, implement BB Squeeze ADX as diagnostic/rejected comparator with full independent formula reconstruction and no candidate eligibility.

### Open questions

- Does the repo already have an external-source knowledge base from WPR106-23 that should absorb this report?
- Should imported external sources become first-class artifacts in the operator UI?
- Is the research engine meant to support non-trading web/source research workflows later, or remain BTC/ETH perp evidence-only?
- Should provider capability metadata be centralized across Binance, Binance Vision, Crypto Lake, Hyperliquid, and local manifests?

### Suggested next prompt for creating an implementation roadmap

```text
Using docs/external_repo_analysis/harvard_algorithmic_trading_ai_repomix_transfer.md and the current ResearchEngineDeluxe repo, create a scoped work packet for an External Source Intake Contract. Before proposing code, inspect existing docs/contracts, WPR106-23, data contracts, import-boundary tests, and research_artifacts schemas. The packet must preserve research_only/observe_only/promotion_ready=false boundaries, avoid importing source code from the Harvard tutorial repo, and include focused validation commands.
```

---

## Bottom line

Take the **RBI stage vocabulary**, the **source-quality checklist idea**, and the **negative examples**. Do **not** take the implementation code, live bot, data files, or backtest results. The source is useful mainly because it demonstrates exactly what your repo should quarantine, annotate, and reject until evidence contracts are satisfied.
