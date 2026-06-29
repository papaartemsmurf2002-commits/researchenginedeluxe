# Autonomous Research Agent Context Contract

Status: v2 read-only handoff contract
Audit IDs: `V2-AUD-AUTONOMY-019`, `V2-AUD-AUTONOMY-020`

## Purpose

The autonomous research agent context is a deterministic read-only JSON
snapshot for agents starting research-only strategy work. It tells the agent
where authoritative data and readiness reports live, which instruments are in
the current project lane, what data can be used without paid access, what must
be called off or materialized before use, and which minor fixes an agent may
perform inside a scoped packet.

It is navigation and policy metadata only. It is not strategy evidence,
accepted research evidence, candidate-pack evidence, a paper/live signal,
sizing instruction, order-placement instruction, runtime-mode change, or
promotion artifact.

## Schema Names

- `AutonomousResearchAgentContext`
- `AgentContextReportRef`
- `AgentInstrumentContext`
- `AgentDataLane`
- `AgentCollectionRule`
- `AgentSelfRepairPolicy`

## Command

```powershell
python -m tradingbotsuite.v2.cli.main autonomy agent-context --repo-root .
```

The command prints `autonomous_research_agent_context_v1` JSON to stdout. With
`--output-path`, it may also write the same JSON to a non-secret `.json` path.
It must not fetch venue data, run workers, enqueue jobs, execute strategies,
append ledgers, update the Lead Book, rewrite generated evidence, or touch live
runtime state.

## Required Content

The context must include:

- schema version, context ID, run ID, created timestamp, and repo root;
- the manager-level autonomous readiness status, if the local WPR106-556 report
  exists;
- explicit `candidate_or_live_ready=false`;
- the dynamic lockbox month and ordinary-iteration end-exclusive timestamp;
- current project symbols and instrument mappings for Hyperliquid and Binance
  USD-M research identifiers;
- report refs for WPR106-546 project bars, WPR106-544 collection ledger,
  WPR106-549 OF-style status/external raw archive, WPR106-552 feature
  materialization, WPR106-556 readiness, product scope, known issues, and the
  data catalog;
- data lanes with allowed uses, blocked uses, and next actions;
- no-paid/public collection rules;
- minor self-repair policy and escalation rules;
- a concise first-read file list that starts with `AGENTS.md` and
  `docs/RESEARCH_AGENT_QUICKSTART.md`, plus command hints;
- the full research-only boundary invariant.

## Research Boundary

Every context must preserve:

```json
{
  "research_only": true,
  "observe_only": true,
  "promotion_ready": false,
  "candidate_evidence": false,
  "candidate_pack_eligible": false,
  "live_signal": false,
  "paper_signal": false,
  "sizing_instruction": false,
  "order_placement_instruction": false,
  "runtime_mode_change": false
}
```

A context may report `autonomous_research_ready=true` only when it is reading a
passing manager readiness report with zero blockers. That status does not
change the forbidden candidate, paper/live, order, sizing, runtime, promotion,
or production-trading boundary.

## No-Paid Public Data Rules

Agents may use official public/no-paid archives and unsigned public APIs only
inside scoped packets and with raw-before-normalization provenance, source
access mode, checksums where available, row counts, coverage, quality, and
provider labels. Binance/Bybit rows must not be relabeled as Hyperliquid-native
rows. Current/recent public APIs must remain current/recent diagnostics unless
archive-backed historical/as-of evidence exists.

Paid vendors, private credentials, account APIs, requester-pays buckets, and
operator-gated sources are blocked for autonomous collection under this
contract.

## Self-Repair Rules

Minor self-repair is allowed for stale handoff wording, focused tests, retrying
documented interrupted validation, contract-preserving parser/schema handling,
and explicit skip/blocker evidence for untestable strategy inputs.

A work packet is required for any code change, generated evidence path, data
collection/materialization run, strategy spec, backtest, validation, ledger, or
Lead Book mutation. Escalate or record a known issue for possible boundary
violations, corrupt data, checksum mismatch, unexplained accepted-lane coverage
gaps, paid/gated data requirements, major schema changes, evidence rewrites, or
candidate/promotion implications.

## Forbidden

- Fetching or downloading data from the context command.
- Treating the context as coverage proof, strategy evidence, or readiness proof
  beyond the parsed manager report status.
- Suppressing missing reports, missing data families, partial windows, budget
  blockers, operator-gated sources, or lockbox restrictions.
- Substituting 1m bars for missing OF/L2/trade inputs.
- Emitting candidate-pack, paper/live, sizing, order, runtime, promotion, or
  production-trading claims.
