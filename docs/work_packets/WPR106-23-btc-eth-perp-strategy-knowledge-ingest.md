# WPR106-23 BTC ETH Perp Strategy Knowledge Ingest

Status: closed

## Scope

Ingest the external report
`C:/Users/papaa/Downloads/btc_eth_perp_strategies_master_report.md` as a
repo-native research knowledge artifact. This packet is documentation-only and
must catalog the report as a possible base of knowledge for future testing, not
as an implementation roadmap or acceptance claim.

## Allowed paths

- `docs/work_packets/WPR106-23-btc-eth-perp-strategy-knowledge-ingest.md`
- `docs/stage_reports/STAGE_R106_BTC_ETH_PERP_STRATEGY_KNOWLEDGE_INGEST_REPORT.md`
- `docs/research_knowledge/README.md`
- `docs/research_knowledge/BTC_ETH_PERP_STRATEGY_KNOWLEDGE_BASE.md`
- `docs/research_knowledge/source_reports/btc_eth_perp_strategies_master_report.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `START_HERE.md`

## Constraints

- Do not edit source code, configs, tests, fixtures, generated artifacts, or
  live/promotion behavior.
- Do not convert the external report into an implementation next step.
- Preserve the distinction between economic hypotheses, backtest requirements,
  and empirical acceptance.
- Keep all strategy notes research-only, observe-only, and
  `promotion_ready: false` by policy.
- Do not claim profitability, candidate readiness, paper readiness, promotion
  readiness, or live readiness.

## Acceptance

- A searchable knowledge-base document exists under `docs/research_knowledge/`.
- The external source report is imported under
  `docs/research_knowledge/source_reports/` so future agents do not lose
  details that are too long for the catalog.
- The document summarizes strategy families, feature/data requirements,
  validation standards, red-team cautions, and project fit.
- The document states that the source report is a hypothesis catalog, not
  standalone proof or a work queue.
- `START_HERE.md` and the orchestrator ledger point agents to the knowledge
  artifact.
- Validation records `git diff --check`.

## Planned validation

- `git diff --check`

## Closeout

- Imported the full source report to
  `docs/research_knowledge/source_reports/btc_eth_perp_strategies_master_report.md`
  so future agents do not lose detailed source context.
- Added `docs/research_knowledge/BTC_ETH_PERP_STRATEGY_KNOWLEDGE_BASE.md`
  as a detailed hypothesis catalog covering venue structure, strategy ranking,
  strategy cards, feature groups, data/simulator standards, experiment backlog,
  ML guidance, validation standards, and red-team cautions.
- Added `docs/research_knowledge/README.md` and linked the catalog from
  `START_HERE.md`.
- Updated the orchestrator ledger and wrote the stage report.
- No source code, configs, fixtures, generated artifacts, tests, live behavior,
  runtime mode, sizing, order placement, or promotion readiness changed.
- Validation passed:
  - `git diff --check`
