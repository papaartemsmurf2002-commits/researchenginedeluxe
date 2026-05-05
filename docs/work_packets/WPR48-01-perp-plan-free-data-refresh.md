# WPR48-01 Perp Plan Free Data Refresh

Owner: Codex Research Agent
Status: closed
Stage: R48 perp plan free-data refresh
Date opened: 2026-05-05
Date closed: 2026-05-05

## Goal

Refresh the curated perpetual agent-development plan so the next implementation stage starts from the current branch reality:

- WPR47 is closed as the Crypto Lake free-sample fallback packet.
- Crypto Lake is an optional anonymous free-sample diagnostic fallback, not a paid/provider-account dependency.
- Perpetual feature and strategy work should start after this refresh with clean work-packet numbering.

## Allowed Paths

```text
docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
docs/work_packets/WPR48-01-perp-plan-free-data-refresh.md
docs/stage_reports/STAGE_R48_PERP_PLAN_FREE_DATA_REFRESH_REPORT.md
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Do not change code.
- Do not add provider credentials, paid Crypto Lake access assumptions, AWS-profile setup, or secret material.
- Preserve branch research boundaries: `research_only`, `observe_only`, and `promotion_ready: false`.
- Keep future data-collection instructions aligned with the free-sample fallback runbook.
- Do not reopen or overwrite WPR47 evidence.

## Required Behavior

- Renumber future perpetual implementation packets so they do not collide with closed WPR47/WPR48 work.
- Add source-priority guidance for provider data:
  - existing durable fixtures and manifests first,
  - Binance Vision/public Binance sources for broad historical data,
  - Binance USD-M REST context collectors for latest-window context,
  - Crypto Lake free sample only as an optional diagnostic fallback.
- Make clear that Crypto Lake free-sample evidence cannot satisfy broad OOS/stress or promotion gates by itself.
- Keep the first future agent prompt ready to copy for the next implementation packet.

## Validation

```powershell
rg -n "WPR47-01 Perp|WPR48-01 Perp|Use this prompt after opening WPR47|Implement WPR47|paid Crypto Lake|AWS_PROFILE|AWS_ACCESS_KEY" docs\RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
rg -n "WPR49-01|WPR50-01|WPR51-01|WPR52-01|Crypto Lake free-sample|source_access_mode" docs\RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
git diff --check
```

## Close Evidence

- Curated plan now names WPR49 as the next implementation packet.
- Crypto Lake guidance matches WPR47 free-sample fallback behavior and runbook.
- No code, live, promotion, or data artifact changes were made by this packet.
