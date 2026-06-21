# V2 Completion Audit Issues And Holes

Date: 2026-06-21
Packet: `docs/work_packets/WPR106-417-v2-audit-issues-and-holes-register.md`
Audit ID: `V2-AUD-COMPLETE-001`
Status: documentation audit, self-checked

## Bottom Line

The v2 roadmap foundation is locally self-checked, research-only, and guarded
against obvious live/paper/order/sizing/promotion boundary leaks in the v2
package. That does not mean the repository is production-ready, trading-ready,
candidate-ready, independently accepted, or free of holes.

My concern, stated plainly: the implementation has strong local contract and
v2 test evidence, but the current state is still a local, uncommitted,
self-checked roadmap foundation with environment-limited broad validation and
several known research/validation debts. Treat it as a research platform
foundation that can continue disciplined work, not as a completed trading
system.

## Validation Evidence From The Audit

Passed in the local checkout:

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - Result: `462 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\v2 -q`
  - Result: `169 passed`
- Grouped non-v2 validation completed before the environment blocker:
  - Result observed across completed groups: `901 passed, 1 skipped`
- `git diff --check`
  - Result: passed with existing LF-to-CRLF warnings only for already modified
    text files.

Not certified:

- A single monolithic `$env:PYTHONPATH='src'; python -m pytest tests -q` run
  was not completed. It first timed out, then async/operator subsets repeatedly
  hit local Windows `WinError 10055` during `socket.socketpair()` while pytest
  was creating asyncio/TestClient event loops. This matches the already-open
  `ISSUE-R106-026`.

## Boundary Scan Explanation

### No Direct V2 Live Runtime Imports Found

Static scan result:

```text
No direct v2 live/runtime/order-adjacent imports found in src/tradingbotsuite/v2.
```

What this means:

- The v2 package did not show direct imports such as
  `tradingbotsuite.live`, `tradingbotsuite.runtime`,
  `tradingbotsuite.adapters`, or `tradingbotsuite.core`.
- This supports the v2 design rule that archive, universe, data-quality,
  strategy-spec, backtest, ledger, Lead Book, validation, worker, and UI
  visibility modules stay research-owned rather than reaching into live
  execution surfaces.

What this does not prove:

- It is not a proof that the entire repo has no live code. The repo still
  contains legacy live-adjacent surfaces outside v2.
- It is not a proof that a future indirect dependency cannot introduce a
  boundary leak.
- It is not a substitute for import-boundary tests and no-touch review.

Concern:

- The v2 package currently looks clean, but the broader repo still carries
  live/runtime surfaces for historical reasons. Future agents must keep v2
  work inside the no-touch and import-boundary rules instead of treating the
  whole repo as a safe research-only namespace.

### No Unsafe V2 Boundary Flags Found

Static scan result:

```text
No true v2 boundary flags found for live/paper/sizing/order/runtime/candidate promotion.
```

What this means:

- I did not find v2 code assigning or declaring true values for flags such as
  `live_signal`, `paper_signal`, `sizing_instruction`,
  `order_placement_instruction`, `runtime_mode_change`,
  `candidate_evidence`, or `candidate_pack_eligible`.
- This is consistent with `docs/PRODUCT_SCOPE.md`, which requires v2 outputs
  to remain `research_only`, `observe_only`, and `promotion_ready: false`.

What this does not prove:

- It does not prove every possible JSON artifact produced by every future
  command will be correct.
- It does not prove old generated artifacts outside v2 have perfect boundary
  metadata.

Concern:

- Boundary flags are only as strong as the artifact writers and tests that
  enforce them. New commands, renderers, or exporters must keep writing the
  invariant explicitly, not rely on convention or document language.

### Readiness Language Hits Were Negated Or Historical

Static scan result:

```text
Readiness-language hits were docs/tests that negate those claims.
```

What this means:

- Terms such as `paper-ready`, `live-ready`, `trade-ready`, `order-ready`,
  `sizing-ready`, `signal-ready`, and `candidate-pack ready` still appear in
  the repository.
- In the v2-relevant scan, the hits were generally in policy docs, tests, stage
  reports, or research-knowledge docs saying those claims are forbidden,
  rejected, blocked, or not present.

What this does not prove:

- It does not mean old docs are easy to read safely out of context.
- It does not mean future summaries cannot accidentally quote a historical
  phrase without the negation.

Concern:

- The repo has a long history and many stage reports. Agents can still be
  misled if they search for positive-looking phrases without reading the
  surrounding negation. Canonical docs should remain the source of truth:
  `docs/PRODUCT_SCOPE.md`, `docs/V2_DECISION_REGISTER.md`,
  `docs/V2_NO_TOUCH_PATHS.md`, and `docs/audit/V2_AUDIT_INDEX.md`.

## Open Known Issues That Still Need Addressing

### `ISSUE-R106-026` - Windows Socket Exhaustion Blocks Async Contract Setup

Severity: P2
Status: resolved by WPR106-421
Source: `docs/KNOWN_ISSUES.md`

Why it matters:

- It blocks reliable full-suite and async/operator validation on this Windows
  host when local socket resources are exhausted.
- During this audit it prevented certification of the monolithic full test
  suite, even though compile, contracts, v2, and many grouped tests passed.

What needs to happen:

- Restart or clear the local Windows socket/network stack and rerun the full
  contracts plus broader async/operator suites.
- If the issue persists after a fresh session, open a test-infrastructure
  packet to avoid socketpair-dependent setup for local contract tests without
  weakening the behavior under test.

Concern:

- This is not a v2 source assertion failure, but it weakens audit confidence
  because it prevents a clean one-command full-suite pass on the current host.

### `ISSUE-R106-020` - Strategy And Exit Audit Follow-Up Risks Need Focused Tests

Severity: P2
Status: open
Source: `docs/KNOWN_ISSUES.md`

Why it matters:

- It records strategy and exit-semantics concerns that are not immediate
  deterministic P1 bugs, but still matter before any candidate or promotion
  interpretation.
- The issue covers latest-window context gating, GMM detector metadata,
  fixed-holding alias identity, lower-timeframe no-hit exit pricing/proof,
  fit-aware train-context wiring, cost-stress semantics, static
  volatility-scaled barrier naming, and path-dynamic funding-cost accounting.

Resolution:

- WPR106-421 adds focused contracts and regressions for latest-window strategy
  gating, GMM detector metadata, fixed-holding alias identity,
  lower-timeframe no-hit exit pricing/proof, static barrier canonical naming,
  and path-dynamic funding-cost accounting.
- Existing v2 validation and cost-model tests cover train-only validation rows,
  gross-only rejection, and base/stress cost rows.
- All affected outputs remain research-only and blocked from candidate, paper,
  live, sizing, runtime-mode, and promotion interpretation.

Concern:

- These were not just cosmetic issues. Before WPR106-421, they were places
  where strategy evidence could become misleading if later agents
  overinterpreted results before the semantics were tightened.

## Additional Audit Holes And Concerns

### Self-Checked Is Not Independent Acceptance

The v2 audit index shows the roadmap chunks as `self_checked`. That is useful
local evidence, but it is not the same as `independent_agent_audited` or
`accepted`.

Concern:

- The next serious step should include independent chunk review, especially for
  archive, backtest-data, ledger, validation, final-hard-test, and security
  contracts.

### The V2 Work Is Still Local And Uncommitted

The audited v2 docs, contracts, package, tests, and control-doc edits are
present in the working tree as local changes. Many files are untracked.

Concern:

- Local completion can be lost, omitted from a branch, or diverge from control
  docs unless the changes are intentionally staged, reviewed, committed, and
  pushed.

### Full-Suite Behavior Was Not Certified In One Process

Grouped suites provided strong coverage, but the monolithic full test command
was not certified because of the local socket exhaustion issue.

Concern:

- A grouped pass reduces risk but does not fully rule out cross-test resource
  leaks, order coupling, or teardown contamination. A clean full-suite run
  should be captured in a fresh validation session.

### Default Local Python Is 3.14 While The Project Targets 3.11+

The local `python` command resolves to Python 3.14.0. The project declares
`requires-python = ">=3.11"`, but the historical validation baseline and docs
do not pin a specific minor version.

Concern:

- Python 3.14 is newer than the likely intended validation floor. Some async
  failures may be resource exhaustion, but relying on an unpinned local Python
  makes audit results harder to compare. CI or final local evidence should pin
  a supported interpreter, ideally the same one used by the repository's CI.

### Static Scans Are Useful But Not Complete Security Proof

The import and flag scans are useful smoke checks, and the v2 tests passed, but
static text scanning is not a complete security review.

Concern:

- Future packets should preserve formal tests for import boundaries,
  root-contained path policies, secret redaction, artifact hash validation,
  unsafe-artifact rejection, and read-only UI behavior.

### V2 Is A Foundation, Not A Fully Populated Research Operation

The roadmap foundation implements contracts, schemas, local fixture-backed
flows, and read-only visibility. It does not prove that a full Hyperliquid
perpetual universe archive is populated and maintained for all instruments
above the USD 5,000,000 notional threshold.

Concern:

- The platform can be structurally ready while the actual operational archive,
  universe snapshots, coverage reports, lockbox evidence, and validation
  manifests still need real ongoing collection and review.

### No Candidate Or Promotion Evidence Exists

This is expected by design, not a bug. The audit did not find a candidate pack,
paper/live artifact, sizing instruction, order-placement instruction,
runtime-mode change, or promotion-ready artifact in v2.

Concern:

- If someone reads "completed successfully" as "we have a strategy ready to
  trade", they are wrong. Completion here means the research-only roadmap
  foundation is self-checked, not that any strategy passed final hard tests or
  became promotable.

### Legacy Repo Surfaces Still Need Respect

The old `tradingbot` package, live-adjacent runtime paths, legacy GUI/operator
paths, and historical generated artifacts still exist outside the v2 package.
The v2 no-touch registry exists because those areas are risky.

Concern:

- A broad cleanup or refactor could accidentally change live behavior,
  evidence history, or candidate-pack truth layers. Future agents should keep
  work packet scopes tight and explicitly name no-touch paths before touching
  them.

### Old Docs Can Still Carry Historical Framing

The top-level v2 docs have been updated, but the repository contains many old
stage reports and research knowledge files. Some contain historical wording
about readiness, candidates, performance, or legacy BTC/ETH work.

Concern:

- Future agents should cite current control docs first and treat older docs as
  historical evidence. The presence of old language is not itself a current
  claim, but it can still create handoff confusion.

## Straightforward Fixes Applied By This Packet

- Added this explicit issues-and-holes document.
- Added `V2-AUD-COMPLETE-001` to the v2 audit index.
- Linked the audit document from the active index and stage ledger.
- Added the fresh 2026-06-21 audit reproduction to `ISSUE-R106-026`.

No source behavior was changed.

## Recommended Next Actions

1. Reboot or otherwise clear the Windows socket/network stack, then rerun:

   ```powershell
   python -m compileall -q src\tradingbotsuite
   $env:PYTHONPATH='src'; python -m pytest tests\contracts -q
   $env:PYTHONPATH='src'; python -m pytest tests\v2 -q
   $env:PYTHONPATH='src'; python -m pytest tests -q
   ```

2. Open a focused test-infrastructure packet if `ISSUE-R106-026` persists in a
   fresh session.
3. Open focused packets for `ISSUE-R106-020` strategy/exit semantics.
4. Run independent audit of high-risk v2 chunks before marking any audit chunk
   beyond `self_checked`.
5. Stage and review the local v2 work intentionally so the control docs,
   contracts, code, and tests cannot drift.
