# Operator Console

## Purpose

The operator console is a localhost-only browser layer over the existing engine. It does not contain trading logic. It reads current state from the engine and sends explicit commands back into the same backend used by the shell.

## Enable

```powershell
$env:TBS_OPERATOR_UI_ENABLED="true"
$env:TBS_OPERATOR_UI_SECRET="change-this-local-secret"
python -m tradingbotsuite.main serve
```

Open `http://127.0.0.1:8000/ui`.

## Security Defaults

- UI is disabled by default.
- Login uses the configured local operator secret.
- Browser mutations require both a signed session cookie and a CSRF token.
- Commands remain subject to all existing engine safety checks.

## Pages

- `Overview`
  - health, position, safety, stream status, recommendations, recent traces
- `Control`
  - manual long/short, supervise, reconcile, refresh health, smoke live
- `Timeline`
  - trade events, action tickets, decision packets, command results, jobs, traces
- `Research`
  - queue research jobs and inspect artifacts
- `Analysis`
  - upload or select a TradingView chart export, replay the current gate configuration immediately, inspect baseline-vs-filtered metrics, visualize accepted/rejected signals over the price path, and queue optimizer runs restricted to the selected filter components
- `Predictions`
  - live microstructure movement-probability visualization from signed flow, top-of-book imbalance, queue imbalance, and depth-depletion bias
  - this is a heuristic, observe-only display; it is not a calibrated model and does not approve entries
- `Guides`
  - common warnings and recommended next actions

## Research Jobs

Research jobs are serialized and stored in SQLite:

- `build-dataset`
- `train-model`
- `calibrate-model`
- `replay-eval`

They are blocked when:

- runtime mode is `live` and a position is open
- safety state is ambiguous

## Fallback

The manual shell still exists and uses the same engine path. Use it when you want raw terminal traces or when the browser console is unavailable.
