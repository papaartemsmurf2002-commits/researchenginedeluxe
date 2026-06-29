# Research Agent Quickstart

Status: WPR106-558 current agent handoff
Last updated: 2026-06-27

Use this file as the current operating guide for autonomous research agents.
The stage ledger, audit index, and old handoff files remain authority for
history, but they are not the fastest way to understand what to do next.

## Current State

- The repo is a research-only v2 perpetual-futures research platform.
- WPR106-556 is the current manager autonomous-readiness verdict:
  `autonomous_research_ready=true`, `blocker_count=0`.
- This is not candidate readiness, accepted research readiness, paper/live
  readiness, order or sizing readiness, runtime readiness, promotion readiness,
  production trading readiness, or a strategy-performance claim.
- WPR106-557 adds the machine-readable handoff:

```powershell
python -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root .
```

Run that command at the start of a research packet and use its JSON as the
current instrument/data/path/policy map.

## What To Read

Default reading path:

1. `AGENTS.md`
2. `docs/RESEARCH_AGENT_QUICKSTART.md`
3. `docs/V2_DATA_CATALOG_AND_AGENTIC_RESEARCH_POINTERS.md`
4. `docs/PRODUCT_SCOPE.md`
5. `docs/KNOWN_ISSUES.md`
6. the latest work packet relevant to your task

Read these only when needed:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`: historical packet ledger and stage
  authority; search it for packet IDs instead of reading it end to end.
- `docs/audit/V2_AUDIT_INDEX.md`: audit ownership and required evidence.
- `docs/V2_NO_TOUCH_PATHS.md`: before touching live/runtime, candidate-pack,
  generated-evidence, old-output, or secret/local-state paths.
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`: before broad package,
  dependency, data, feature, backtest, research-cycle, artifact, or
  live-boundary changes.
- `docs/V2_DECISION_REGISTER.md`: when a decision might conflict with product
  scope or evidence rules.

## Current Data Lanes

Use the agent-context command for exact paths. The practical lanes are:

| Lane | Current use | Rule |
| --- | --- | --- |
| Project 1m bars | Bar-only multi-instrument research over 29 project symbols | Use WPR106-546 report, respect lifecycle windows and lockbox. |
| Central collection ledger | Availability preflight for provider/family/symbol/window | Consult before requiring any nontrivial data family. |
| External OF-style raw archive | Raw source truth for official Binance USD-M OF-style families | Do not use directly as a backtest panel; materialize first. |
| WPR106-552 OF-style feature proof | Compact feature-materialization proof pack | Use only manifest-covered windows or open a compute packet. |
| Native Hyperliquid official history | Requester-pays/operator-gated provenance caveat | Do not chase under the current no-paid rule. |

Current 29 project symbols:

```text
AAVE, ADA, AERO, AVAX, BNB, BTC, DOGE, ENA, ETH, FARTCOIN, HYPE, IP,
JTO, JUP, KPEPE, LINK, LIT, NEAR, PUMP, SOL, SUI, TAO, UNI, VVV, WLD,
XMR, XPL, XRP, ZEC
```

BTC and ETH are fixtures/reference symbols, not the full product scope.

## Research Rules

- Write or update a work packet before any code change, data collection,
  materialization, generated artifact, strategy spec, backtest, validation,
  ledger append, or Lead Book mutation.
- Keep changes inside the packet's allowed paths.
- Use all relevant instruments available for the strategy and data lane; do not
  default to BTC/ETH-only tests unless the packet is explicitly a fixture or
  reference smoke.
- Use only no-paid public data unless the operator explicitly scopes otherwise.
- Preserve provider provenance. Do not relabel Binance/Bybit rows as
  Hyperliquid-native rows.
- Do not silently substitute bars for missing OF/L2/trade inputs.
- Treat skipped strategies, missing windows, budget blockers, and failed gates
  as useful evidence.
- Keep the latest full calendar month out of ordinary tuning unless a packet
  explicitly scopes final-test or benchmark use. As of 2026-06-27, the dynamic
  lockbox month is 2026-05.

## Minor Self-Repair

Agents may fix small issues inside a scoped packet when the fix is local and
does not change evidence meaning:

- stale handoff wording;
- missing cross-reference;
- focused test or parser/schema bug;
- interrupted validation rerun;
- explicit blocker/skip evidence for untestable inputs.

Escalate or record a known issue for:

- possible live/order/sizing/runtime or promotion boundary violation;
- data corruption, checksum mismatch, or unexplained accepted-lane coverage
  gap;
- paid, credentialed, requester-pays, or operator-gated data requirement;
- major schema change, generated-evidence rewrite, or candidate/promotion
  implication.

## Validation

For docs/context-only changes, run:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_autonomy_agent_context_phase79.py -q
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_contract_docs.py -q
git diff --check
```

For implementation work, use the AGENTS baseline and broaden tests according
to the touched subsystem.
