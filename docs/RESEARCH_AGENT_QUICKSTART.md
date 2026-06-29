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
- WPR106-567 adds the archive-first preflight:

```powershell
python -m tradingbotsuite.v2.cli.main archive-inventory --summary
python -m tradingbotsuite.v2.cli.main archive-inventory --feature-catalog --summary
python -m tradingbotsuite.v2.cli.main archive-inventory --feature-catalog --feature-family <family> --instrument-id <instrument> --timeframe <tf> --accepted-only
python -m tradingbotsuite.v2.cli.main archive-inventory --missing-for-strategy <spec.json> --start-ts <ts> --end-ts <ts>
```

Run inventory/resolver before collecting data, materializing a new feature
slice, writing a collector, or adding venue support.
Use `--feature-catalog` to inspect existing OF/funding/OI/spread/derived
feature refs directly before planning new materialization work.
Resolver reports include `recommended_engine_lane`, `reference_audit_required`,
and `fast_lane_reason`; large sweeps and explicit fast-lane requests should use
the recommended fast lane only as triage until reference audit/parity evidence
exists. Every `DataGapRequest` includes the archive refs and coverage report
IDs checked before the gap was opened.

WPR106-567 also adds fast-lane audit/rerun tools:

```powershell
python -m tradingbotsuite.v2.cli.main fast-lane sample-reference-audits --sample-rate 0.05 --run-id <fast-run-id>
python -m tradingbotsuite.v2.cli.main fast-lane parity-report --reference-run <reference-run_manifest.json> --fast-run <fast-run_manifest.json>
python -m tradingbotsuite.v2.cli.main fast-lane reference-rerun-plan --fast-run <fast-run_manifest.json>
python -m tradingbotsuite.v2.cli.main fast-lane full-artifact-replay-plan --run <summary-or-metrics-run_manifest.json>
python -m tradingbotsuite.v2.cli.main fast-lane verify-full-artifact-replay --source-run <summary-or-metrics-run_manifest.json> --full-run <full-run_manifest.json>
python -m tradingbotsuite.v2.cli.main fast-lane benchmark-run --benchmark-tier smoke --strategy-spec-file <spec.json> --archive-root <archive> --output-root <out> --archive-snapshot-id <snapshot> --universe-snapshot-id <universe> --venue hyperliquid --instrument-id <instrument> --timeframe 1m --start-ts <ts> --end-ts <ts>
```

Use these before treating fast-lane sweep output as more than triage evidence.
Benchmark runs read existing archive refs, write under the requested output
root, and do not append archive data-request manifests.
Use `--benchmark-tier smoke` for one-off checks. `panel` and `sweep` tiers are
reserved for broader scopes and fail closed when the requested instrument/window
is too small for that label.
Use `full-artifact-replay-plan` for promising summary/metrics-only runs before
promoting them to full artifact replay; it preserves the source engine lane and
requires the same spec/data/config identity.
After the full replay is written, use `verify-full-artifact-replay` to confirm
the replay run preserves the light run's spec/data/config identity, matching
metrics, and full artifact set.

For proven raw-data gaps, convert resolver JSON to a bounded collector template
before writing any collector packet:

```powershell
python -m tradingbotsuite.v2.cli.main collectors gap-template --gap-request-file <resolver-report-or-gap.json>
```

This command emits template-only plans. It does not fetch data or authorize
collection, and it skips gaps that have no suggested collector. Venue-probe
templates require checked archive refs or coverage-report evidence from the
`DataGapRequest`; hand-written bare gaps fail closed.

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
- Use existing archive refs first. If data is missing, act only on the bounded
  `DataGapRequest` instrument/family/time range after a scoped work packet
  allows it; do not add venues proactively.
- Large sweeps may use `fast_vectorized` and `artifact_mode=summary` or
  `artifact_mode=metrics_only` for triage, but promising or suspicious results
  need sampled reference audit, parity reports, and full-artifact replay plans.
- Set benchmark capture explicitly when measuring runtime. Do not claim speedup
  unless a manifest or parity report contains measured benchmark evidence.
  Benchmark reports must include reference/fast runtime, data-load,
  artifact-write, and memory observations before they are accepted as benchmark
  evidence.
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
