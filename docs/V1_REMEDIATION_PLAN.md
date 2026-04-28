# V1 Remediation Plan

Audit date: April 10, 2026

This plan reflects the code after the April 10, 2026 remediation pass.

## Wave 1: Stop-The-Line

Status: completed in this pass

- Prevent repeated Binance REST bootstrap on warm websocket cache.
- Add fail-fast validation for invalid strategy, timeout, and sizing config.
- Correct PowerShell-facing operator examples.
- Re-run the full automated suite after changes.

Exit gate:

- `python -m pytest` must stay green.

## Wave 2: Framework Completion Gaps

Status: materially complete for the current BTC-first v1 scope

- Keep the current signed taker imbalance plus top-of-book imbalance baseline as the active v1 hard-filter implementation.
- Preserve the explicit classification that queue imbalance is now available as infrastructure and operator-visible research context, without promoting it to a hard gate until testing proves the value.
- Keep the current acceptance baseline simple even though the local-book layer is now richer.

Exit gates:

- new depth-sync code must have deterministic replay fixtures
- out-of-order and reconnect handling must be covered by tests
- operator status output must surface depth health separately from bar/trade/bookTicker health

## Wave 3: Best-Practice Cleanup

Status: recommended next

- Move live Hyperliquid metadata bootstrap off constructor-time blocking I/O and into explicit async startup.
- Add one small verification command or script that prints the exact startup checks run before live mode is considered healthy.
- Consider centralizing health snapshots so manual shell, API health, and audit scripts all read the same shape.

Exit gates:

- no blocking network I/O in object constructors for live adapters
- startup failures remain fail-closed and operator-readable

## Wave 4: Verification And Research Hardening

Status: partially complete

- Keep using `python run_live_smoke.py` as the first-line live transport verification command.
- Capture one successful engine-level live trace with accepted microstructure alignment and persisted protections, then preserve a sanitized version of that trace for future regression work.
- Expand market-data fixtures to include depth resync and reconnect scenarios beyond the current unit coverage.

Exit gates:

- account-backed testnet smoke succeeds on current HEAD
- docs reflect the exact command path used in the smoke
- any exchange-specific quirks discovered during the smoke are encoded into tests or explicit risk notes
