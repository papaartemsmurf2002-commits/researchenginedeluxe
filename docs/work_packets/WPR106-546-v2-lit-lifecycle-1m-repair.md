# WPR106-546 - V2 LIT Current-Contract 1m Lifecycle Repair

Status: complete
Owner: Codex Research Agent
Date: 2026-06-26

## Objective

Fix the WPR106-545 LIT 1m validation blocker without synthetic data by using
Binance's official current-contract lifecycle boundary. The current Binance
USD-M `LITUSDT` contract is Lighter Protocol and has official
`onboardDate=2025-12-23T17:30:00Z`; pre-onboard static/legacy `LITUSDT`
archive rows must not be treated as current-project bars.

This packet remains research-only central data readiness. It does not create
candidate-pack, paper/live, order, sizing, runtime-mode, promotion,
autonomous-strategy, or production-trading readiness.

## Allowed Paths

- `docs/work_packets/WPR106-546-v2-lit-lifecycle-1m-repair.md`
- `docs/KNOWN_ISSUES.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- New append-only generated central market-history artifacts under
  `data/research/central_market_history/**`

## No-Touch Paths

- Live runtime, order-placement, broker/execution, sizing, runtime config,
  promotion, shadow, and candidate-pack truth-layer paths.
- Existing generated research evidence under `data/research/**`, except the
  append-only `data/research/central_market_history/**` output root.
- Secrets, `.env`, credential files, private caches, local SQLite operator
  databases, requester-pays data, paid sources, fixture-only/synthetic data as
  accepted evidence, sandbox-only evidence as accepted evidence, and generated
  `outputs/**`.

## Plan

- Write a LIT lifecycle source-discovery artifact that records Binance
  `exchangeInfo` `onboardDate=1766511000000` and the official launch
  announcement URL.
- Append a current-contract LIT December 2025 lifecycle-sliced 1m manifest
  using only rows from `2025-12-23T17:30:00Z` through `2025-12-31T23:59:00Z`.
- Regenerate project-needed 1m validation and collection ledger so LIT uses
  the lifecycle-sliced December manifest and excludes pre-onboard stale rows.
- Validate compile, central generated scripts, contracts, no `.part` files,
  and research-only boundary flags.

## Result

WPR106-546 fixed the LIT blocker by lifecycle scoping, not by filling missing
bars. Binance `exchangeInfo` reports `LITUSDT` `onboardDate=1766511000000`
(`2025-12-23T17:30:00Z`), matching the official Binance Futures Lighter
Protocol LIT launch announcement. The repair script appended a current-contract
December 2025 manifest with 11,910 official 1m rows from onboard time through
month end and excluded 31,680 pre-onboard static/legacy archive rows from the
current project symbol.

Generated evidence:

- `data/research/central_market_history/manifests/wpr106-546-lit-current-lifecycle-source-discovery-report.json`
- `data/research/central_market_history/manifests/wpr106-546-binance-usdm-1m-bars-lit-2025-12-current-lifecycle-18e7a69259332547-batch_manifest.json`
- `data/research/central_market_history/manifests/wpr106-546-project-needed-1m-current-lifecycle-validation-report.json`
- `data/research/central_market_history/manifests/wpr106-546-project-needed-1m-current-lifecycle-readiness-collection_ledger-ecac33d5bf84.json`

The regenerated validation report passes all 29 project symbols with 715
current-lifecycle manifests, 31,032,285 verified project rows, 715 raw ZIPs,
zero raw failures, and zero `.part` files. The central store now has 919
normalized Parquet artifacts, 919 append-manifest rows, 41,513,873 normalized
rows, and uses approximately 46.982 GiB under the 300 GiB cap.
