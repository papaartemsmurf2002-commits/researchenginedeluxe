# Stage R48 Perp Plan Free Data Refresh Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR48-01-perp-plan-free-data-refresh.md`
Status: closed

## Scope

R48 refreshed `docs/RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md` after WPR47 closed the Crypto Lake free-data fallback work. This was a documentation-only packet.

## Changes

- Renumbered future perpetual implementation packets so the next implementation packet is WPR49.
- Added provider source priority:
  - durable repo fixtures and manifests,
  - Binance Vision/public Binance historical sources,
  - Binance USD-M REST latest-window context collectors,
  - Crypto Lake anonymous free sample as optional diagnostic fallback only.
- Added explicit Crypto Lake free-sample constraints:
  - no paid access assumption,
  - no provider-account or AWS-profile setup,
  - manifests must identify `source_access_mode: free_sample`,
  - free samples cannot satisfy broad OOS/stress, candidate-pack, or promotion gates by themselves.
- Updated the first future agent prompt to point at WPR49 and the Crypto Lake free-data runbook.

## Validation

```powershell
rg -n "WPR47-01 Perp|WPR48-01 Perp|Use this prompt after opening WPR47|Implement WPR47|paid Crypto Lake|AWS_PROFILE|AWS_ACCESS_KEY" docs\RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
rg -n "WPR49-01|WPR50-01|WPR51-01|WPR52-01|Crypto Lake free-sample|source_access_mode" docs\RESEARCH_V3_PERP_AGENT_DEVELOPMENT_PLAN.md
git diff --check
```

Results:

- No stale WPR47/WPR48 implementation references or paid/AWS credential references were found.
- WPR49-WPR52 roadmap references, Crypto Lake free-sample guidance, and `source_access_mode` guidance were present.
- `git diff --check` returned 0. Git reported existing LF-to-CRLF working-copy warnings only.

## Research Boundary

No code, live execution, promotion, generated market data, provider credentials, or secret material changed in this packet. The plan continues to require `research_only: true`, `observe_only: true`, and `promotion_ready: false` outputs for future research stages.
