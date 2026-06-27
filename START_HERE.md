# Start Here

This repository is being developed through gated stages.

## Current checkout and identity

ResearchEngineDeluxe v2 is a research-only, data-first, multi-instrument
perpetual-futures research platform. The active direction is Hyperliquid-first:
instruments above USD 5,000,000 daily notional volume, 2024+ evidence, 6+
usable months, 12-month preference, 0.98 coverage, dynamic lockbox exclusion,
and as-of universe snapshots.

BTC and ETH remain fixture, smoke-test, reference, and legacy evidence symbols.
They are not the full v2 product scope. The active Python package is still
named `tradingbotsuite` for compatibility.

The current local checkout is `main`, documented by R106 as the migrated mirror
of `research/v3-experimental-engine`. Use this checkout for research platform
work only. The live runtime branch referenced by older docs is
`live/v1-runtime-hardening`.

Current data/catalog handoff:

- `docs/work_packets/WPR106-553-v2-final-repo-audit-agentic-iteration-testing-readiness.md`
  is the final repo audit packet. It marks the repo ready for research-only
  agentic iteration strategy testing under scoped packets, not for autonomous,
  candidate-pack, paper/live, order/sizing/runtime, promotion, or production
  trading use.
- `docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md` is the compact
  testing-agent entrypoint for WPR106-552.
- `docs/index.html` is the read-only local/GitHub Pages status page rendered
  from `docs/v2_visibility_snapshot_wpr106_552.json`.
- Bar-based proxy research over the 29 project symbols can use the WPR106-546
  lifecycle-scoped 1m bars, subject to lockbox and packet rules.
- Raw-heavy OF-style data is complete in the external WPR106-549 archive under
  strict-free/no-paid constraints; WPR106-552 adds the compact
  normalization/feature materialization proof pack at
  `data/research/of_style_feature_materialization/wpr106_552/manifests/wpr106-552-of-style-feature-materialization-report.json`.
- Unavailable requester-pays or native Hyperliquid historical official data is
  out of scope for data readiness and must not be treated as a blocker.

## First files to read

1. `AGENTS.md`
2. `docs/ACTIVE_INDEX.md`
3. `docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md`
4. `docs/PRODUCT_SCOPE.md`
5. `docs/V2_DECISION_REGISTER.md`
6. `docs/V2_NO_TOUCH_PATHS.md`
7. `docs/audit/V2_AUDIT_INDEX.md`
8. `docs/ORCHESTRATOR_STAGE_LEDGER.md`
9. `docs/KNOWN_ISSUES.md`
10. `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
11. `docs/BRANCH_PURPOSE.md`
12. `docs/contracts/README.md`
13. `docs/repo_cartography/REPO_INVENTORY.md`

## Research knowledge

Reference material that can help design future falsification packets lives in
`docs/research_knowledge/`. These documents are hypothesis catalogs only; they
are not implementation queues, candidate evidence, promotion evidence, or live
trading instructions.

## Current rule

Follow the active stage in `docs/ORCHESTRATOR_STAGE_LEDGER.md`. Open a work
packet before coding, keep edits inside that packet, and do not start
live/promotion execution work from this research branch unless a later ledger
decision explicitly scopes it. Do not add new strategy/model/filter or
paper/live behavior while open P0 blockers remain in `docs/KNOWN_ISSUES.md`.
For v2 work, also assign an audit ID from `docs/audit/V2_AUDIT_INDEX.md` and
respect `docs/V2_NO_TOUCH_PATHS.md`.
