# Operator Guide

For day-to-day operation, start with `docs/OPERATOR_QUICKSTART.md`. This file
is the longer technical reference.

## Modes

- `shadow`: produces intended actions without exchange-side orders
- `paper`: simulates fills and uses the same decision path as live
- `live`: uses the Hyperliquid adapter and must be treated as opt-in

## Operator Console

Start the localhost browser console:

```powershell
$env:TBS_OPERATOR_UI_ENABLED="true"
$env:TBS_OPERATOR_UI_SECRET="change-this-local-secret"
python -m tradingbotsuite.main serve
```

Open `http://127.0.0.1:8000/ui`.

The browser console is now the primary local operator surface. The shell is still available as fallback.

For Hyperliquid testnet setup, the runtime first honors explicit `TBS_HL_*` environment variables. If they are missing, it also falls back to a local repo-root `hyperliquidtestnet.txt` file so live testnet preflight can still resolve the signer key and canonical account address.

## Live Preflight

Every live entry path now runs the canonical live preflight before engine startup, live runtime-mode switching, or live smoke execution. Live mode fails closed when webhook or operator secrets are unset/default, risk caps are zero, Hyperliquid signer/account indicators are missing, reconciliation is disabled, basis thresholds are disabled, a research command is requested, or a research-only artifact is configured as a live input.

For Hyperliquid testnet, keep `TBS_RUNTIME_MODE=live`, `TBS_HL_ENABLE_LIVE=true`, signer/account values, non-default secrets, and positive `TBS_MAX_DAILY_LOSS_QUOTE` plus `TBS_MAX_OPEN_RISK_NOTIONAL` set before using `manual`, `serve`, or `smoke-live`.

## Promotion And Shadow Diagnostics

Promotion candidates are shadow-only review artifacts. The operator Research page displays shadow diagnostics from stored shadow decision packets, including score status, confidence buckets, and operator-visible skip reasons. This panel is read-only and does not expose runtime-mode switches, manual signals, smoke-live, sizing, or order controls.

Live mode rejects promotion candidates as live order inputs. A candidate must pass the promotion validator and then load through the shadow loader before any shadow comparison report is considered useful.

## Stage 12 Research Planning

Feature ablation planning is research-only:

```powershell
python -m tradingbotsuite.main plan-feature-ablation --output-dir data/research/stage12/feature_ablation
```

The command writes a Stage 12.1 feature ablation manifest, per-hypothesis experiment specs, a CSV summary, and rejected/pending hypothesis notes. It does not run live, paper, or shadow execution and it cannot promote a model.

Full Stage 12 planning is also research-only:

```powershell
python -m tradingbotsuite.main plan-stage12-research --output-dir data/research/stage12
```

This writes manifests and experiment specs for substages 12.1 through 12.7 plus a completion-limitations artifact. It does not mark empirical hypotheses as accepted unless OOS and stress evidence is supplied.

## Stage 13 Readiness Planning

Stage 13 readiness planning is blocked-by-default and writes templates only:

```powershell
python -m tradingbotsuite.main plan-stage13-readiness --output-dir data/research/stage13/readiness
```

The command creates paper-run, shadow-archive, and testnet-validation manifest templates, a blocked readiness report, and rollback/operator checklists. It does not start paper, shadow, testnet, or live execution. The Research page displays the readiness report as a read-only diagnostic and does not expose mode switches, order controls, or canary controls there.

Console pages:

- `Overview`: health, position, safety, stream status, microstructure, recommendations, and recent traces in readable status cards
- `Control`: manual long/short, supervise, reconcile, refresh health, smoke live, and summarized command outcomes
  Control also includes runtime-mode switch buttons for `shadow`, `paper`, and `live`. Switching is blocked while a position is open, and `live` still uses the same Hyperliquid preflight checks before it becomes the active adapter path.
  In `live` mode against Hyperliquid testnet, Control also exposes an optional checkbox for short-lived TP/SL validation. When enabled, a confirmed manual entry fill places real testnet trigger orders, reports their clo ids in the result cards, and schedules automatic cancel after `10s` so testnet drift does not leave stale protections behind. Binance-based supervision remains the canonical exit path.
- `Timeline`: trade events, decision packets, action tickets, command results, jobs, and traces with expandable details
- `Research`: provider preparation, research experiments, historical-cycle review, V4 discovery runs, artifact summaries, charts, HMM/KNN monitoring, shadow diagnostics, and Stage 13 readiness review
- `Guides`: common warnings plus embedded operator and V2 research docs from the repo

## Research Page

Use the Research page for offline evidence work, not live decisions.

- `Provider Pipeline` runs `prepare-hmm-knn-research-data` with `Intake`,
  `Dataset`, `Evidence`, or `All` scope.
- `Research Experiment` queues configured bundles from `configs/experiments/`.
- `Historical Cycle Review` queues configs from `configs/research/` into
  isolated operator output directories so checked evidence is not overwritten.
- `V4 Discovery Run` queues or resumes HMM/KNN discovery specs from
  `configs/discovery/`; paused/resumed runs keep checkpoints, snapshots, and
  ledgers in the stable run-id directory.
- `Jobs`, `Artifacts`, profitability charts, gate charts, discovery-ledger
  charts, HMM/KNN monitoring, shadow diagnostics, and Stage 13 readiness are
  read-only review surfaces.

The Research page intentionally does not expose manual signal, smoke-live,
set-mode, sizing, or canary controls. Research jobs stay blocked in live mode
and while live position state is unsafe.

## Manual Signal Workflow

Start the shell:

```bash
python -m tradingbotsuite.main manual
```

Recommended first run:

```powershell
$env:TBS_RUNTIME_MODE="paper"
python -m tradingbotsuite.main manual
```

`cmd.exe` alternative:

```cmd
set TBS_RUNTIME_MODE=paper
python -m tradingbotsuite.main manual
```

Then type:

```text
l
status
s
status
supervise
quit
```

## What You Should See

Each manual `l` or `s` command should print the internal stages:

1. signal receipt
2. dedupe and safety-state check
3. Binance closed-bar fetch
4. Binance microstructure snapshot and basis snapshot
5. ATR, Hurst, and triple-barrier math
6. current-position lookup
7. decision packet generation
8. execution intents
9. execution reports
10. persistence confirmation

This output is intentionally verbose so you can validate the pipeline before using webhook automation.

The browser console is the easier read for day-to-day work. The shell remains useful when you explicitly want raw trace output.

## Live Monitoring In Manual Mode

Manual mode is now a live-data operator loop:

- it validates Binance market-data health on startup
- it clears stale safe-mode locks when fresh live data is available again
- it keeps live Binance `kline`, `aggTrade`, `bookTicker`, and diff-depth websocket caches warm in the background
- those streams now follow Binance's official websocket route split, with `kline` and `aggTrade` on `/market` and `bookTicker` plus diff-depth on `/public`
- it now keeps those feeds on two combined Binance sockets instead of four separate ones, which reduces connection churn and should make `missing_trade_stream` incidents less frequent
- it plans websocket rotation before Binance's 24h connection expiry and reports planned reconnects separately from error reconnects
- it prints the current exit-engine snapshot while a position is open
- it automatically executes the close path when live TP, SL, or time-barrier conditions are met
- it drains Hyperliquid websocket order and fill events into the console and persists them into `trade_events`
- it now tracks depth gap, resync, and depth-rate-limit counts so you can judge whether local-book instability is occasional or persistent
- it also tracks alignment mismatches, invalid local-book states, buffer high-watermark, and dropped buffered diff events

The monitor cadence is controlled by `TBS_MANUAL_POLL_SECONDS`.

## Hyperliquid Live Notes

- If you use an API wallet / agent wallet, keep the private key for signing but set the account address to the real master or subaccount public address.
- The adapter resolves agent wallets to the canonical trading account before reconcile and websocket subscription setup.
- TP and SL trigger prices are normalized to Hyperliquid's exchange rules before submission. This matters for BTC because valid perp prices are constrained by significant-figure and decimal-place rules, not just a generic tick size.
- Historical `userFills` snapshots are ignored in the live event queue so startup traces focus on fresh activity, not old fills.
- During close/flip flows, Hyperliquid may auto-cancel reduce-only protections. Those responses are treated as benign cancels rather than hard failures.
- Open live positions are protected by a maximum reconcile gap. If exchange reconciliation cannot be refreshed within that budget, the engine enters `reconciliation_stale` safe mode and refuses new action until it is resolved.
- Binance and Hyperliquid mids are monitored together. If their basis exceeds the configured threshold, live entries are rejected and open-position health can enter `basis_dislocation`.

## V1 Filter Logic

The current v1 acceptance layer is intentionally simple:

- Hurst is computed and stored as a regime feature, but it is not yet used as a hard gate.
- The primary hard filter is signed taker imbalance over `TBS_MICRO_PRIMARY_WINDOW_SECONDS`.
- Long signals require signed taker imbalance ratio greater than or equal to `TBS_SIGNED_IMBALANCE_RATIO_THRESHOLD`.
- Short signals require the mirrored negative condition.
- Top-of-book imbalance must align with the signal direction using `TBS_BOOK_IMBALANCE_RATIO_THRESHOLD`.
- Queue imbalance from the reconstructed diff-depth local book is now surfaced live as `queue_imbalance_l1`, `queue_imbalance_l5`, and `queue_imbalance_l10` for research and operator verification.
- If Binance exposes `nq` on `aggTrade`, the runtime uses it for signed-flow math so imbalance stays aligned with the public book streams that exclude RPI liquidity.
- If depth becomes stale or unsynced, queue-imbalance and depletion values are intentionally hidden until the local book is trustworthy again.
- Queue/depletion values are also hidden if the reconstructed local book is empty, crossed, or below the configured required level count.
- The depth layer defaults are `250ms` stream speed, `1000`-level snapshots, and 10 required book levels for queue metrics.

This gives you a clean baseline for ablation before moving to meta-labeling or more complex acceptance models.

## Hyperliquid Smoke

Use this to verify the live adapter without depending on a microstructure-aligned manual signal:

```bash
python run_live_smoke.py
```

Equivalent module entrypoint:

```bash
python -m tradingbotsuite.main smoke-live
```

What it does:

- runs the canonical live preflight
- runs account preflight
- starts Hyperliquid user streams
- submits one tiny long market entry
- waits for order activity and reconcile confirmation
- submits a matching close
- confirms the account is flat again

## API Health

Basic API status:

```bash
curl http://127.0.0.1:8000/health
```

Canonical detailed snapshot:

```bash
curl http://127.0.0.1:8000/health/details
```

`/health/details` is the same consolidated system view the engine now uses for manual-mode status reporting:

- persisted position
- safety state
- market-data health
- execution health
- stream status
- microstructure snapshot
- live exit snapshot

This is the fastest way to distinguish exchange/credential issues from engine decision-path issues.

## Useful Commands

- `status`: current persisted position and safety status
- `status` also prints the live Binance microstructure snapshot and the current market-stream status when available
- `supervise`: evaluate the current position against the newest closed bar
- `reconcile`: compare local state to the active execution adapter
- `trace off`: suppress step logs if you only want final packets and reports
- `trace on`: re-enable step logs

## Safety Expectations

- If Binance bars are stale, the engine should enter safe mode and reject new trades.
- If Binance microstructure streams are stale, the engine should treat market data as unhealthy in live mode.
- If only the local depth/book path is degraded, open-position exits can still continue from the 15m bar path, but new entries may be blocked until the local book recovers.
- If a same-direction position is already open, the new signal should be ignored.
- If an opposite-direction position is open, the engine should cancel exits, close, then reopen.
- If local and exchange state diverge in live mode, the engine should fail closed into safe mode.
- In live mode, an exchange response alone is not enough to trust an entry. The engine now requires reconcile confirmation before persisting a local open position or placing protections.
- If Binance and Hyperliquid basis exceeds the configured threshold, the engine should reject new live entries and surface the dislocation in health/status output.

## Persistence

SQLite stores:

- incoming signals
- decision packets
- current trade state
- append-only trade events
- action tickets
- runtime safety state

At entry, `trade_state` now also records:

- `hurst_at_entry`
- `imbalance_at_entry`

Default database location is controlled by `TBS_DB_PATH`.
