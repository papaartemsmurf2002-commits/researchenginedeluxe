# WPR106-391 V2 Phase 0 Scope Source Lock And Safety Rails

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Implement Phase 0 of
`docs/REDX_V2_READY_TO_USE_IMPLEMENTATION_ROADMAP_2026_06_20.md`: source-lock
the ready-to-use v2 roadmap, update top-level repository framing away from
BTC/ETH-only product scope, and add the initial v2 product-scope, decision,
no-touch, and audit safety-rail documents required before code-heavy v2 work.

This packet is documentation and governance only. It does not change source
behavior, tests, configs, generated research artifacts, archive files,
candidate gates, strategy code, runtime code, live/paper surfaces, sizing,
order placement, or promotion state.

## Audit IDs

- `V2-AUD-SCOPE-001`
- `V2-AUD-SEC-001`

## Dependencies

- `AGENTS.md`
- `README.md`
- `START_HERE.md`
- `docs/ACTIVE_INDEX.md`
- `docs/BRANCH_PURPOSE.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/REDX_V2_READY_TO_USE_IMPLEMENTATION_ROADMAP_2026_06_20.md`
- `docs/V2_ADOPTION_CONVERSATION_REPO_PACKAGE_2026_06_20.md`

## Allowed Paths

- `AGENTS.md`
- `README.md`
- `START_HERE.md`
- `docs/ACTIVE_INDEX.md`
- `docs/BRANCH_PURPOSE.md`
- `docs/PRODUCT_SCOPE.md`
- `docs/V2_DECISION_REGISTER.md`
- `docs/V2_NO_TOUCH_PATHS.md`
- `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/audit/prompts/V2_CHUNK_AUDITOR_PROMPT.md`
- `docs/work_packets/WPR106-391-v2-phase0-scope-source-lock-and-safety-rails.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Do not modify source code, tests, configs, generated data, or archive files.
- Do not interpret v2 docs as implemented M1/M2/M3/M4/M5 evidence.
- Historical BTC/ETH references may remain when explicitly labeled as legacy
  evidence, fixtures, smoke tests, or prior-stage documentation.

## Acceptance Criteria

- `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md` exists as the canonical
  source-lock copy of the ready-to-use roadmap.
- `docs/PRODUCT_SCOPE.md` states the v2 canonical identity, USD 5M
  Hyperliquid universe rule, research-only invariant, 2024+ floor, 6-month
  minimum, 12-month preference, dynamic lockbox, 0.98 coverage, and no
  paper/live/order/sizing future for this repo.
- `docs/V2_DECISION_REGISTER.md` records v2 implementation decisions.
- `docs/V2_NO_TOUCH_PATHS.md` records initial no-touch categories and paths.
- `docs/audit/V2_AUDIT_INDEX.md` records planned audit chunks.
- `docs/audit/prompts/V2_CHUNK_AUDITOR_PROMPT.md` exists.
- `README.md`, `START_HERE.md`, `AGENTS.md`, `docs/BRANCH_PURPOSE.md`, and
  `docs/ACTIVE_INDEX.md` no longer present BTC/ETH as the full current product
  scope.

## Validation

Documentation-only validation:

```powershell
git diff --check
rg -i "btc/eth|BTC/ETH|live-ready|paper-ready|trade-ready|order-ready|sizing-ready" README.md docs/ START_HERE.md AGENTS.md
```

The `rg` command is an audit scan, not a strict failure condition. Allowed hits
are historical references, legacy fixture/smoke roles, or explicit negations.

No compile or pytest validation is required because this packet does not change
implementation files.

## Stop Conditions

- A source, config, test, archive, generated-data, live, paper, runtime,
  sizing, order, candidate-pack, or promotion change becomes necessary.
- Any edit would imply M1 dynamic Hyperliquid research loop completion before
  implementation evidence exists.
- A blocking P0/P1 research/live boundary issue is discovered.

## Completion Notes

Closed on 2026-06-20.

- Created `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md` as a canonical
  source-lock copy of
  `docs/REDX_V2_READY_TO_USE_IMPLEMENTATION_ROADMAP_2026_06_20.md`.
- Added `docs/PRODUCT_SCOPE.md` with v2 canonical identity, USD 5M
  Hyperliquid universe rule, 2024+ floor, 6-month minimum, 12-month preference,
  dynamic lockbox, 0.98 coverage, and the research-only invariant.
- Added `docs/V2_DECISION_REGISTER.md` with D1-D29 implementation decisions and
  extra safe defaults.
- Added `docs/V2_NO_TOUCH_PATHS.md`, `docs/audit/V2_AUDIT_INDEX.md`, and
  `docs/audit/prompts/V2_CHUNK_AUDITOR_PROMPT.md`.
- Updated `README.md`, `START_HERE.md`, `AGENTS.md`,
  `docs/BRANCH_PURPOSE.md`, and `docs/ACTIVE_INDEX.md` so active framing no
  longer treats BTC/ETH as the full product scope.
- Recorded the Phase 0 repo-state snapshot in `docs/audit/V2_AUDIT_INDEX.md`.
- Marked `V2-AUD-SCOPE-001` and `V2-AUD-SEC-001` as `self_checked`.
- No source, test, config, generated data, archive, live, paper, runtime,
  candidate-pack, sizing, order-placement, or promotion behavior was changed.

Validation:

```powershell
git diff --check
Get-FileHash -Algorithm SHA256 -LiteralPath docs\REDX_V2_READY_TO_USE_IMPLEMENTATION_ROADMAP_2026_06_20.md,docs\V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md
rg -n "BTC/ETH perpetual|BTC/ETH .*research engine|BTC/ETH.*full|entire research universe|full research scope" README.md START_HERE.md AGENTS.md docs\ACTIVE_INDEX.md docs\BRANCH_PURPOSE.md docs\PRODUCT_SCOPE.md docs\V2_DECISION_REGISTER.md docs\V2_NO_TOUCH_PATHS.md
rg -n -i "paper-ready|live-ready|trade-ready|order-ready|sizing-ready|candidate-pack-ready" README.md START_HERE.md AGENTS.md docs\ACTIVE_INDEX.md docs\BRANCH_PURPOSE.md docs\PRODUCT_SCOPE.md docs\V2_DECISION_REGISTER.md docs\V2_NO_TOUCH_PATHS.md docs\audit\V2_AUDIT_INDEX.md docs\audit\prompts\V2_CHUNK_AUDITOR_PROMPT.md
```

Result:

- `git diff --check` passed with LF-to-CRLF warnings only.
- Canonical roadmap copy SHA256 matched imported source:
  `1035779BF4E1836E2CCFA79B181B24849C0690046A0FF56BD5646107117D3E51`.
- Stale-scope scan found only the explicit no-touch checklist line that keeps
  BTC/ETH as fixture/reference rather than full scope.
- Readiness-language scan found only explicit negations and one legacy active
  index resolution note.
