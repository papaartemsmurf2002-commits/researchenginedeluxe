# Agent Guide

This branch is controlled by the orchestrator stage ledger.

## Branch role

`research/v3-experimental-engine` is the research and experimentation branch.
Its active v2 direction is a research-only, data-first, multi-instrument
Hyperliquid-perpetual research platform with compatible multi-venue comparison
support. It owns provider/archive intake, manifests, feature construction,
strategy research, backtesting, HMM/KNN experiments, optimizer work, rapid
sandbox work, Lead Book preparation, audit-by-chunk migration, and research UI
work.

## Active stage rules

- Use `docs/RESEARCH_AGENT_QUICKSTART.md` as the concise current research-agent
  handoff. Long ledgers and audit files remain authority, but search them for
  the relevant packet or rule instead of reading them end to end by default.
- Check `docs/ORCHESTRATOR_STAGE_LEDGER.md` before starting work.
- Read `docs/PRODUCT_SCOPE.md`, `docs/V2_DECISION_REGISTER.md`,
  `docs/V2_NO_TOUCH_PATHS.md`, and `docs/audit/V2_AUDIT_INDEX.md` before v2
  implementation work.
- Read `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md` before broad package,
  dependency, data, feature, backtest, research-cycle, artifact, or live-boundary
  changes.
- Write a work packet before coding.
- Keep changes inside the allowed paths listed by the work packet.
- Before collecting data, writing a collector, materializing a feature slice, or
  adding venue support, query the archive inventory and strategy
  data-requirement resolver. Use existing archive refs when they satisfy the
  request; collect or materialize only the exact missing
  instrument/family/time range described by a `DataGapRequest`.
- Collector templates remain template-only. Venue probes require a
  `DataGapRequest` with checked archive refs or coverage-report evidence; bare
  hand-written gaps are not sufficient.
- Update `docs/KNOWN_ISSUES.md` when a blocking risk is discovered.
- Do not advance a stage while any P0 issue is open or four or more P1 issues are unresolved.
- BTC and ETH are fixture, smoke-test, reference, and legacy evidence symbols;
  they are not the full v2 product scope.

## Research boundary

- Research outputs are not live signals.
- Research artifacts must stay `research_only`, `observe_only`, and `promotion_ready: false` unless a later promotion process changes them.
- Research modules must not import live order-placement adapters.
- Research jobs must not place orders, change live runtime mode, or write live configuration.
- V2 research commands and artifacts must not imply paper-ready, live-ready,
  trade-ready, order-ready, sizing-ready, signal-ready, candidate-pack-ready,
  or promotion-ready status.
- Performance claims require reproducible manifests and validation evidence.
- Fast-lane or artifact-light sweep output is triage evidence until replayed or
  sampled under the Python/reference engine. Do not claim speedup without
  benchmark evidence. Use fast-lane parity reports and reference rerun plans
  for suspicious or promising fast results before treating them as durable
  research evidence.

## Validation baseline

Use focused validation for scoped work and broaden tests when shared contracts change:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

## Windows async validation caveat

On local Windows sessions, broad pytest runs can intermittently fail with
`WinError 10055` while pytest-asyncio or TestClient creates an event-loop
self-pipe. This happens before the affected test body runs and usually
indicates local socket/buffer exhaustion, not a source assertion failure.
WPR106-526 converted the previous async fixture-pack contract to a synchronous
collected-manifest fixture, so `tests/contracts -q` should no longer require a
pytest-asyncio setup path.

If a broader suite still hits `WinError 10055`, isolate the affected test and
rerun the remaining suite with `-k "not <test_name>"`, for example:

```powershell
$env:PYTHONPATH='src'; py -3.11 -m pytest path\to\test_file.py::test_name -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests -q -k "not test_name"
```

Record the split results and the setup failure in the work packet. Treat this
as a local validation-host caveat unless a test assertion fails after setup.
