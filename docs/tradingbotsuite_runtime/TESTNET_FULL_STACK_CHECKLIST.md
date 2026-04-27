# Testnet Full-Stack Manual Validation Checklist

## Objective

Use the operator console `Long` and `Short` buttons as a controlled BTC full-stack validation path before the final V2 TradingView and training workstream.

In `live` mode with Hyperliquid testnet configured, these buttons already use the same canonical engine path as normal signal handling:

- manual signal creation
- Binance closed-bar and microstructure checks
- decision packet construction
- execution intent creation
- Hyperliquid order placement
- protection placement
- supervision
- reconcile
- persistence and operator feed updates

For manual live-testnet validation, automatic Binance-driven supervision now applies a short hold window before it is allowed to flatten the position. This gives you time to inspect the entry, protective orders, and command trail before testnet drift can immediately trigger a close from real-market Binance prices.

For this validation path, Binance remains the canonical pricing source for entry context and exit barriers. Hyperliquid testnet is currently used only as the execution venue for opening and closing the position. Testnet fill drift is recorded for execution diagnostics, but it does not rewrite the Binance-anchored supervisory TP / SL state.

The only difference from the later TradingView path is the upstream signal source.

## Preconditions

- runtime mode is `live`
- Hyperliquid base URL points to testnet
- testnet account is configured and funded with mock balance
- Binance market data is healthy
- operator console login works
- no ambiguous safety state is active

## Validation Pass

### 1. Health pre-check

- Open `Overview`
- Confirm:
  - runtime state is not `safe_mode`
  - market data is healthy
  - execution is healthy
  - depth/book state is not degraded for a long stretch

### 2. Long-entry pass

- Open `Control`
- Optional: enable the short-lived testnet TP/SL checkbox if you want to validate trigger-order placement and auto-cancel behavior on Hyperliquid testnet
- Click `Long Full Stack`
- Verify in the result boxes:
  - a manual signal was created
  - the packet was accepted
  - entry reports were produced
  - protective reports were produced
  - if the checkbox was enabled, the `Testnet TP/SL` card shows `Cleanup Armed = true` and lists the TP / SL clo ids
- Verify in `Timeline`:
  - decision packet event
  - execution events
  - supervision snapshot
  - no immediate ambiguity or stale-health event
  - use Timeline with `Show Health` and `Show Metrics` disabled by default so the trade sequence stays readable

If the checkbox was enabled, wait at least `10s` and then confirm:

- the position may still remain open, because Binance-driven supervision is the canonical close path
- the short-lived testnet TP/SL orders were canceled
- the current position no longer shows active TP / SL clo ids for that test-only validation pass

### 3. Reconcile pass

- Click `Reconcile`
- Confirm:
  - local and exchange position state agree
  - no `reconciliation_mismatch`
  - no `reconciliation_stale`

### 4. Supervision pass

- Watch `Overview`
- Confirm:
  - supervision snapshot updates
  - bars-since-entry and elapsed time move correctly
  - candidate exit reason is readable
  - MFE / MAE and basis fields are present

### 5. Exit pass

Use one of these:

- wait for the engine to exit naturally
- click `Supervise` during a condition that should cause a close
- send the opposite-side manual signal to test flip-close-then-open behavior

Confirm:

- close reports are persisted
- position state becomes `flat` or flips cleanly
- exit reason is recorded
- trade close attribution appears in the runtime summaries

## What To Check Carefully

- no duplicate order placement from repeated button presses
- protection placement is visible after entry
- reconcile freshness remains inside the configured gap budget
- rate-limit or depth issues degrade the runtime visibly instead of failing silently
- UI summaries match persisted state rather than transient terminal noise

## Failure Cases Worth Testing

- run `Refresh Health` while Binance depth is degraded
- restart the app with an open testnet position and confirm reconcile rebuilds state
- attempt a signal while the runtime is in a blocked or degraded state
- intentionally trigger a same-direction duplicate and verify it is ignored cleanly
- intentionally trigger an opposite-side signal and verify close-then-flip sequencing

## Pass Criteria

- one manual long and one manual short complete through the full stack on testnet
- no orphaned protective-order confusion appears in the operator feed
- reconcile remains stable after entry and exit
- runtime attribution records are understandable enough to review the session afterward
- the operator can follow the whole flow from the browser without relying on raw terminal spam
