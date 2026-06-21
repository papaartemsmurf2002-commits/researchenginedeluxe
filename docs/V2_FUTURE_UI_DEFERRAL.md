# V2 Future UI Deferral

Status: implemented as read-only static visibility surface by WPR106-416
Audit ID: `V2-AUD-UI-001`
Source: Phase 22 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`

## Original Deferral Decision

Before WPR106-416, the v2 UI was intentionally not implemented in the early
foundation pass. Phase 22 was treated as a future visibility surface, not a
reason to rebuild the legacy GUI before the archive, data, backtest, ledger,
Lead Book, validation, cross-venue, and security foundation existed.

WPR106-416 is that later explicit packet. It names the UI source paths, command
boundary, tests, and no-touch constraints, then implements the UI as a static
read-only renderer rather than a job-running web process.

## Visibility Scope

The v2 UI may show:

- active universe;
- included and excluded instruments with reasons;
- HIP-3/RWA caveats;
- data collection status;
- archive coverage;
- gap reports;
- lockbox range;
- Lead Book rows and lead state;
- deep validation state;
- final hard-test candidates;
- audit chunk status;
- worker and job health.

## Not Allowed In This Deferral

- No legacy GUI or operator UI changes.
- No collectors, backtests, validation jobs, or workers running inside a UI
  process.
- No UI-owned business logic that changes v2 contracts.
- No live, paper, order-placement, sizing, runtime-mode, or promotion behavior.
- No generated evidence rewrites.

## Prerequisites For A Later UI Packet

A later `V2-AUD-UI-001` implementation packet must define:

- exact source and test paths;
- no-touch paths and explicit exceptions, if any;
- read-only versus command-capable surfaces;
- worker delegation boundaries for any command-capable action;
- path/output allowlists;
- authentication, cookie, and admin posture;
- import-boundary tests for live/runtime/order paths;
- visual and interaction validation appropriate to the selected frontend
  surface.

Until that packet exists, the correct behavior is to keep v2 usable through
schema-tested services, CLI surfaces already scoped by earlier packets, and
durable artifacts rather than a premature UI.

## WPR106-416 Implementation

WPR106-416 opens the later explicit UI implementation packet required by this
deferral. It implements `V2-AUD-UI-001` as a static read-only visibility
surface:

- `docs/contracts/ui_visibility_contract.md` defines the snapshot contract;
- `src/tradingbotsuite/v2/ui/**` renders escaped static HTML from a supplied
  `V2VisibilitySnapshot`;
- `redx ui render` reads a root-contained snapshot JSON file and writes
  root-contained static HTML;
- no legacy GUI/web/operator paths are modified;
- no collectors, workers, backtests, validation jobs, order logic, sizing
  logic, runtime-mode mutation, or promotion logic run in a UI process.
