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

- `docs/RESEARCH_AGENT_QUICKSTART.md` is the current concise operating guide
  for research agents. Start there after `AGENTS.md`.
- `docs/work_packets/WPR106-557-v2-agent-context-cleanup-and-handoff.md`
  adds the read-only machine-readable agent context handoff. Run
  `python -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root .`
  to print the current instrument map, data paths, no-paid collection rules,
  lockbox state, self-repair policy, and WPR106-556 manager readiness status.
- `docs/work_packets/WPR106-556-v2-autonomous-readiness-atlas-strategy-pass.md`
  is the current autonomous-readiness strategy verdict. The formal manager
  readiness report returns `autonomous_research_ready=true` with
  `blocker_count=0`, while all artifacts remain research-only and
  non-promotable.
- `docs/work_packets/WPR106-553-v2-final-repo-audit-agentic-iteration-testing-readiness.md`
  is the final repo audit packet. It marks the repo ready for research-only
  agentic iteration strategy testing under scoped packets. It was superseded
  for manager autonomous-readiness status by WPR106-556, but candidate-pack,
  paper/live, order/sizing/runtime, promotion, and production trading use
  remain forbidden.
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
2. `docs/RESEARCH_AGENT_QUICKSTART.md`
3. `docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md`
4. `docs/PRODUCT_SCOPE.md`
5. `docs/KNOWN_ISSUES.md`
6. the latest work packet for your task

Read long reference files only when your packet needs them:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md` for stage history or packet IDs;
- `docs/audit/V2_AUDIT_INDEX.md` for audit ownership/evidence;
- `docs/V2_DECISION_REGISTER.md` for scope-decision conflicts;
- `docs/V2_NO_TOUCH_PATHS.md` before touching protected areas;
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md` before broad shared-package,
  dependency, data, feature, backtest, artifact, or live-boundary changes;
- `docs/contracts/README.md` before changing contracts.

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
