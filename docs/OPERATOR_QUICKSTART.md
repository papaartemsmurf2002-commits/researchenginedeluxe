# Operator Quickstart

This is the short operator run card. Use the longer `docs/OPERATOR_GUIDE.md`
only when you need deeper runtime details.

## Start The Browser Console

- PowerShell setup: `$env:TBS_OPERATOR_UI_ENABLED="true"; $env:TBS_OPERATOR_UI_SECRET="change-this-local-secret"; $env:TBS_RUNTIME_MODE="paper"`
- Start server: `python -m tradingbotsuite.main serve`
- Open UI: `http://127.0.0.1:8000/ui`
- Login password: the value of `TBS_OPERATOR_UI_SECRET`
- First safe mode for local use: `paper`

## First Safe Run

- Open `Overview` and confirm system health, market data, safety state, and position state.
- Open `Control` and use `Refresh Health` before any manual signal.
- Use `Paper` mode until the full workflow is familiar.
- Send one small manual direction only when safety is green: `Long` or `Short`.
- Open `Timeline` and confirm the command, decision packet, execution report, and position update are present.
- Use `Supervise` to evaluate the active paper position against the newest closed bar.
- Use `Reconcile` if local position and exchange/runtime state look inconsistent.

## Page Map

- `Overview`: current health, position, safety, streams, microstructure, recommendations, and traces.
- `Control`: manual long/short, supervise, reconcile, refresh health, smoke-live, and mode switching.
- `Timeline`: chronological events, decisions, commands, jobs, and trace details.
- `Research`: offline research jobs and artifact summaries; not live signals.
- `Predictions`: current microstructure pressure and scoring diagnostics.
- `Guides`: this quickstart, the detailed operator guide, and reliability docs.

## Normal Daily Checklist

- Start in `paper` unless you intentionally prepared a live/testnet session.
- Check `Overview` first. Do not trade through red safety, stale data, or reconciliation warnings.
- Press `Refresh Health` after startup or after reconnects.
- Confirm `Position` is flat before mode switching or smoke testing.
- Use `Timeline` after every command. A button response alone is not enough; verify the event trail.
- Keep research jobs separate from trading decisions. They are offline diagnostics only.
- Stop and inspect logs if a command returns `success: false`.

## Button Rules

- `Refresh Health`: safe first response for stale or uncertain health.
- `Supervise`: safe for checking an open position against exit logic.
- `Reconcile`: use when position state is unclear or after exchange/API disruption.
- `Long` / `Short`: manual signal path; use in `paper` first.
- `Smoke Live`: live/testnet adapter smoke check; use only after live preflight is intentionally satisfied.
- `Set Mode`: blocked with open positions; live mode still requires full preflight.

## Safety Response Table

- `Market Data Stale`: press `Refresh Health`; if still stale, restart the server and do not send signals.
- `Depth Stream Degraded`: wait for stream recovery; entries may be blocked until local book quality returns.
- `Reconciliation Stale`: press `Reconcile`; if unresolved, keep trading disabled.
- `Basis Dislocation`: do not force entries; inspect Binance and Hyperliquid mids.
- `Daily Loss Limit Hit`: stop new entries for the UTC session and review trade attribution.
- `Position Ambiguity`: do not switch modes or send signals; run `Reconcile`.
- Open live position: research jobs and mode switching should stay blocked.

## Research Jobs

- Research jobs are offline and research-only.
- Use `Research` for provider preparation, research experiments, historical-cycle review, V4 discovery runs, artifact review, HMM/KNN monitoring, and Stage 13 readiness diagnostics. Current V4 discovery uses no-regime baselines and GMM regime modes, not a true HMM backend.
- The `Operator Board` summarizes data readiness, current run, progress, latest snapshot, blockers, leads, artifact count, and maturity.
- Maturity labels mean `Diagnostic`, `Screen-worthy`, or `Candidate-ready`; candidate-ready still requires later promotion approval before any handoff.
- Routine buttons cover preflight data readiness, quick/standard/deep discovery, pause after one trial, resume, snapshot review, candidate eligibility review, and artifact-list review.
- Empty research charts show missing-evidence reasons in page text.
- Historical-cycle and fresh discovery jobs write isolated operator output directories; paused/resumed discovery jobs keep checkpoint files in the stable run-id directory.
- Outputs must remain `research_only`, `observe_only`, and `promotion_ready: false` unless a later promotion process changes them.
- Do not treat research artifacts as live signals.
- Do not run research jobs in live mode or while live position state is unresolved.

## Live Or Testnet Checklist

- Use live/testnet only when you intentionally opt in.
- Required direction: set `TBS_RUNTIME_MODE="live"` and `TBS_HL_ENABLE_LIVE="true"` only for a prepared live/testnet session.
- Required secrets: non-default operator secret, webhook secret if webhooks are used, Hyperliquid signer key, and canonical account address.
- Required risk caps: positive daily loss limit and max open risk notional.
- Required checks: live preflight passes, account reconciles, market data is fresh, basis is normal, and position is flat before smoke testing.
- Safer testnet habit: run `Smoke Live` with tiny size first, confirm entry and close events, then confirm flat state.
- Never use live/testnet controls to validate research hypotheses.

## Shell Fallback

- Start manual paper shell: `$env:TBS_RUNTIME_MODE="paper"; python -m tradingbotsuite.main manual`
- Useful shell commands: `status`, `l`, `s`, `supervise`, `reconcile`, `trace off`, `trace on`, `quit`
- Use the shell when you want raw trace output; use the browser for normal operation.

## Common Fixes

- UI disabled or 404: set `TBS_OPERATOR_UI_ENABLED="true"` and restart.
- Cannot login: use the exact value of `TBS_OPERATOR_UI_SECRET`.
- CSRF or auth error: login again, then retry from the browser page.
- No model artifact warning: run the research workflow before expecting shadow scores.
- Stale stream warnings after network changes: restart the server, then press `Refresh Health`.
- Unexpected open position: do not send a new signal; run `Reconcile` and inspect `Timeline`.

## Stop Conditions

- Stop sending signals when safety is red, market data is stale, reconciliation is stale, basis is dislocated, or daily loss limit is hit.
- Stop live/testnet work if account state cannot be reconciled.
- Stop research-to-trading handoff if an artifact is not explicitly approved by a later promotion process.
- Stop and open an issue if the UI suggests a research artifact is directly usable for live execution.
